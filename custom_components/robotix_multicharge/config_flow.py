"""Guided native setup and one-authority expert JSON/YAML import."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from re import sub

import voluptuous as vol
import yaml
from homeassistant import config_entries
from homeassistant.helpers import selector

from .configuration import (
    default_configuration, is_plan_presentation_only_change,
    configuration_revision, prepare_expert_yaml_revision, validate_configuration,
    apply_new_asset_defaults,
)
from .source_evidence import number
from .execution import stop_power_limit
from .const import DOMAIN, NAME


def _id(value: str) -> str:
    return sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _phases(raw):
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


def _phase_limits(raw):
    entries = [item.strip() for item in raw.split(",") if item.strip()]
    try:
        return {phase.strip().upper(): float(value) for phase, value in
                (entry.split(":", 1) for entry in entries)}
    except (ValueError, TypeError) as exc:
        raise ValueError("Use L1:16,L2:16,L3:16") from exc


def _assert_safe_expert_import(runtime, updated, *, source_changed=False):
    """Refuse structural import while any affected writer cannot prove idle.

    Inspect BOTH the currently installed writer and proposed owner/wiring.
    A new MultiCharge owner cannot take control of an externally active EVSE.
    No import may consume unresolved stored commands as if they were idle.
    """
    current = runtime.configuration
    if (not source_changed and (
            updated == current
            or is_plan_presentation_only_change(current, updated))):
        return
    executor = runtime.executor
    if (not executor._persistence_verified or executor._inflight
            or executor._start_pending or executor._quarantine):
        raise ValueError("EXPERT_IMPORT_REQUIRES_RECONCILED_CONTROL_STATE")
    before = {item["id"]: item for item in current["chargers"]}
    after = {item["id"]: item for item in updated["chargers"]}
    now = datetime.now(timezone.utc)
    for uid in before.keys() | after.keys():
        old = before.get(uid)
        proposed = after.get(uid)
        checked = [
            row for row in (old, proposed)
            if row and row.get("control_owner") == "multicharge"
            and row.get("physical_commissioned") is True
        ]
        if not checked:
            continue
        if uid in executor._sessions:
            raise ValueError("EXPERT_IMPORT_REQUIRES_VERIFIED_IDLE_CHARGERS")
        for charger in checked:
            switch = executor._switch(
                runtime.hass, charger.get("control_entity")
            )
            power = number(
                runtime.hass, charger.get("power_entity"), "power", now
            )
            if (switch is None or switch.state != "off" or power.quality != "ok"
                    or power.value > stop_power_limit(charger)):
                raise ValueError("EXPERT_IMPORT_REQUIRES_VERIFIED_IDLE_CHARGERS")


def _parse_editor_yaml(text):
    """Parse bounded data-only YAML/JSON without silent duplicate overrides."""
    if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 131072:
        raise ValueError("YAML must contain 1–128 KiB of mapping data")

    class StrictSafeLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            seen = set()
            for key_node, _ in node.value:
                key = self.construct_object(key_node, deep=deep)
                if not isinstance(key, (str, int, float, bool)):
                    raise ValueError("YAML mapping keys must be scalar")
                if key in seen:
                    raise ValueError("duplicate YAML key")
                seen.add(key)
            return super().construct_mapping(node, deep=deep)

    try:
        document = yaml.load(text, Loader=StrictSafeLoader)
    except yaml.YAMLError as exc:
        raise ValueError("YAML syntax error or unsupported YAML tag") from exc
    if not isinstance(document, dict):
        raise ValueError("YAML root must be a mapping")
    return document


def _yaml_review_summary(old, new):
    lines = []
    fields = sorted(key for key in set(old["controller"]) | set(new["controller"])
                    if old["controller"].get(key) != new["controller"].get(key))
    lines.append("Site settings: " + (", ".join(fields) if fields else "unchanged"))
    for category in ("chargers", "assets"):
        prior = {row["id"]: row for row in old[category]}
        current = {row["id"]: row for row in new[category]}
        adds = sorted(current.keys() - prior.keys())
        removes = sorted(prior.keys() - current.keys())
        updates = sorted(key for key in current.keys() & prior.keys()
                         if current[key] != prior[key])
        lines.append(f"{category.title()}: {len(current)} total")
        for label, keys in (("Add", adds), ("Modify", updates), ("Remove", removes)):
            if keys:
                lines.append(f"  {label}: {', '.join(keys)}")
    lines.extend((
        "Physical charger control owner: unchanged",
        "Commissioning: unchanged; this edit sends no charging command.",
    ))
    return "\n".join(lines)


def _assert_safe_yaml_ui_commit(runtime, updated):
    """Recheck source and safety immediately before native Options Save."""
    _assert_safe_expert_import(runtime, updated)
    existing = {charger["id"]: charger for charger in runtime.configuration["chargers"]}
    revised = {charger["id"]: charger for charger in updated["chargers"]}
    # Even an external-owner charger must be measured idle to remove or change
    # its historical association; a name-only edit never needs this gate.
    for uid, previous in existing.items():
        current = revised.get(uid)
        if (current is not None and
                all(previous.get(key) == current.get(key)
                    for key in ("asset", "control_entity", "power_entity",
                                "connected_entity", "energy_entity",
                                "session_entity", "kind", "rated_power_kw"))):
            continue
        if (uid in runtime.executor._sessions or
                uid in runtime.executor._start_pending):
            raise ValueError("YAML_UPDATE_CHARGER_BUSY")
        if previous.get("power_entity"):
            observed = number(
                runtime.hass, previous["power_entity"], "power",
                datetime.now(timezone.utc),
            )
            if (observed.quality != "ok" or
                    observed.value > stop_power_limit(previous)):
                raise ValueError("YAML_UPDATE_REQUIRES_VERIFIED_IDLE")
        elif previous.get("control_owner") == "multicharge":
            raise ValueError("YAML_UPDATE_REQUIRES_VERIFIED_IDLE")
        switch = runtime.executor._switch(
            runtime.hass, previous.get("control_entity"),
        )
        if switch is not None and switch.state != "off":
            raise ValueError("YAML_UPDATE_REQUIRES_VERIFIED_IDLE")


class RobotixMultiChargeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Native beginner wizard; the resulting Config Entry remains sole authority."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return RobotixMultiChargeOptionsFlow()

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if user_input is not None:
            try:
                self._draft = default_configuration(user_input.get("name") or "Home charging")
                self._draft["controller"]["max_parallel"] = int(user_input.get("max_parallel", 1))
                if user_input.get("max_power_kw") is not None:
                    self._draft["controller"]["max_power_kw"] = user_input["max_power_kw"]
                self._draft["controller"]["mode"] = user_input.get("mode", "Automatic")
                if user_input.get("phase_limits_a"):
                    self._draft["controller"]["phase_limits_a"] = _phase_limits(
                        user_input["phase_limits_a"])
                validate_configuration(self._draft)
            except (KeyError, ValueError):
                return self.async_show_form(
                    step_id="user", data_schema=self._site_schema(),
                    errors={"base": "invalid_config"},
                )
            return await self.async_step_charger()
        return self.async_show_form(step_id="user", data_schema=self._site_schema())

    @staticmethod
    def _site_schema():
        # Explicit box widgets, never implicit range sliders in HA forms.
        # The unverified electrical ceiling is genuinely optional.
        return vol.Schema({
            vol.Optional("name", default="Home charging"): str,
            vol.Optional("max_parallel", default=1): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=16, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional("max_power_kw"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1,
                    mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional("phase_limits_a"): str,
        })

    async def async_step_charger(self, user_input=None):
        """Basic connection first. All metering/electrical proof is optional here."""
        if user_input is not None:
            try:
                if user_input["action"] == "add":
                    name = (user_input.get("name") or "").strip()
                    control = user_input.get("control_entity")
                    if not name or not control:
                        raise ValueError("charger name and command entity required to add")
                    uid = _id(name)
                    if not uid or any(c["id"] == uid for c in self._draft["chargers"]):
                        raise ValueError("charger identity must be unique")
                    # Safe setup defaults are planning assumptions, never electrical proof.
                    charger = {
                        "id": uid, "name": name, "kind": "on_off",
                        "rated_power_kw": 3.6, "control_entity": control,
                        "control_owner": "external", "physical_commissioned": False,
                    }
                    trial = deepcopy(self._draft)
                    trial["chargers"].append(charger)
                    self._draft = validate_configuration(trial)
                    self._advanced_charger_id = uid
                    self._add_another_after_details = bool(
                        user_input.get("add_another", False)
                    )
                    if user_input.get("configure_details"):
                        return await self.async_step_charger_details()
                    if self._add_another_after_details:
                        return self.async_show_form(
                            step_id="charger", data_schema=self._charger_schema()
                        )
                return await self.async_step_asset()
            except (KeyError, ValueError):
                return self.async_show_form(
                    step_id="charger", data_schema=self._charger_schema(),
                    errors={"base": "invalid_config"},
                )
        return self.async_show_form(step_id="charger", data_schema=self._charger_schema())

    @staticmethod
    def _charger_schema():
        # Name and command are mandatory only *when adding*: on Finish the
        # same form must allow users to leave them blank.
        return vol.Schema({
            vol.Required("action", default="add"): vol.In(["add", "finish"]),
            vol.Optional("name"): str,
            vol.Optional("control_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")
            ),
            vol.Optional("configure_details", default=False): bool,
            vol.Optional("add_another", default=False): bool,
        })

    async def _after_charger_details(self):
        if self._add_another_after_details:
            return self.async_show_form(
                step_id="charger", data_schema=self._charger_schema()
            )
        return await self.async_step_asset()

    async def async_step_charger_details(self, user_input=None):
        """Optional technical sources: never required for read-only setup."""
        if user_input is not None:
            try:
                trial = deepcopy(self._draft)
                charger = next(
                    c for c in trial["chargers"] if c["id"] == self._advanced_charger_id
                )
                for field in ("kind", "rated_power_kw", "connected_entity",
                              "power_entity", "energy_entity"):
                    if user_input.get(field) is not None:
                        charger[field] = user_input[field]
                if (user_input.get("configure_electrical")
                        or charger["kind"] == "variable_current"):
                    # Min/max current is mandatory only if this capability was
                    # actually selected; allow the user to enter it next.
                    self._pending_charger_details = trial
                    return await self.async_step_charger_electrical()
                self._draft = validate_configuration(trial)
                if hasattr(self, "_pending_charger_details"):
                    del self._pending_charger_details
                return await self._after_charger_details()
            except (KeyError, ValueError, StopIteration):
                return self.async_show_form(
                    step_id="charger_details", data_schema=self._charger_details_schema(),
                    errors={"base": "invalid_config"},
                )
        return self.async_show_form(
            step_id="charger_details", data_schema=self._charger_details_schema()
        )

    @staticmethod
    def _charger_details_schema():
        return vol.Schema({
            vol.Optional("kind", default="on_off"):
                vol.In(["on_off", "variable_current"]),
            vol.Optional("rated_power_kw", default=3.6): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1,
                    mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional("connected_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"])
            ),
            vol.Optional("power_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional("energy_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional("configure_electrical", default=False): bool,
        })

    async def async_step_charger_electrical(self, user_input=None):
        """Optional wiring/current proof. No actuation gets commissioned here."""
        if user_input is not None:
            try:
                trial = deepcopy(
                    getattr(self, "_pending_charger_details", self._draft)
                )
                charger = next(
                    c for c in trial["chargers"] if c["id"] == self._advanced_charger_id
                )
                for field in ("phase_count", "min_current_a", "max_current_a",
                              "voltage_v", "current_step_a", "fixed_current_a",
                              "circuit_id", "circuit_limit_a",
                              "current_control_entity", "current_readback_entity"):
                    if user_input.get(field) is not None:
                        charger[field] = user_input[field]
                if user_input.get("phase_ids"):
                    charger["phase_ids"] = _phases(user_input["phase_ids"])
                self._draft = validate_configuration(trial)
                return await self._after_charger_details()
            except (KeyError, ValueError, StopIteration):
                return self.async_show_form(
                    step_id="charger_electrical", data_schema=self._charger_electrical_schema(),
                    errors={"base": "invalid_config"},
                )
        return self.async_show_form(
            step_id="charger_electrical", data_schema=self._charger_electrical_schema()
        )

    @staticmethod
    def _charger_electrical_schema():
        return vol.Schema({
            vol.Optional("phase_count"): vol.In([1, 2, 3]),
            vol.Optional("phase_ids"): str,
            vol.Optional("voltage_v"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=200, max=260, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional("min_current_a"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1,
                    mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional("max_current_a"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1,
                    mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional("current_step_a"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.01, max=100, step=0.1,
                    mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional("fixed_current_a"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1,
                    mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional("circuit_id"): str,
            vol.Optional("circuit_limit_a"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1,
                    mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional("current_control_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="number")
            ),
            vol.Optional("current_readback_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        })

    async def async_step_asset(self, user_input=None):
        if user_input is not None:
            try:
                if user_input["action"] == "add":
                    uid = _id(user_input["name"])
                    if not uid or any(a["id"] == uid for a in self._draft["assets"]):
                        raise ValueError("asset identity must be unique")
                    asset = {"id": uid, "name": user_input["name"],
                             "kind": user_input["kind"]}
                    for key in ("soc_entity", "capacity_kwh", "target_soc",
                                "requested_kwh", "requested_duration_minutes",
                                "ready_by", "ready_by_repeat", "charge_efficiency", "max_charge_kw",
                                "temporary", "expires_at",
                                "priority"):
                        if user_input.get(key) is not None:
                            asset[key] = user_input[key]
                    apply_new_asset_defaults(asset)
                    trial = deepcopy(self._draft)
                    trial["assets"].append(asset)
                    validate_configuration(trial)
                    self._draft = trial
                    if user_input["add_another"]:
                        return self.async_show_form(step_id="asset",
                                                    data_schema=self._asset_schema())
                return await self.async_step_sources()
            except (KeyError, ValueError):
                return self.async_show_form(
                    step_id="asset", data_schema=self._asset_schema(),
                    errors={"base": "invalid_config"},
                )
        return self.async_show_form(step_id="asset", data_schema=self._asset_schema())

    @staticmethod
    def _asset_schema():
        return vol.Schema({
            vol.Required("action", default="add"): vol.In(["add", "finish"]),
            vol.Optional("name"): str,
            vol.Required("kind", default="car"): vol.In(
                ["car", "bicycle", "motorcycle", "scooter", "other"]
            ),
            vol.Optional("soc_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional("capacity_kwh"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            vol.Optional("target_soc"): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            vol.Optional("requested_kwh"): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional("requested_duration_minutes"):
                vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional("ready_by"): selector.DateTimeSelector(),
            vol.Optional("ready_by_repeat"): vol.In(["none", "daily", "weekly"]),
            vol.Optional("temporary"): bool,
            vol.Optional("expires_at"): str,
            vol.Optional("charge_efficiency"):
                vol.All(vol.Coerce(float), vol.Range(min=0.01, max=1)),
            vol.Optional("max_charge_kw"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            vol.Optional("priority"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
            vol.Required("add_another", default=False): bool,
        })

    async def async_step_sources(self, user_input=None):
        if user_input is not None:
            try:
                trial = deepcopy(self._draft)
                for name in ("price_entity", "solar_entity", "binding_entity"):
                    if user_input.get(name):
                        trial["controller"][name] = user_input[name]
                for charger in trial["chargers"]:
                    selected = user_input.get("assign_" + charger["id"])
                    if selected:
                        charger["asset"] = selected
                self._draft = validate_configuration(trial)
                return await self.async_step_verify()
            except (KeyError, ValueError):
                return self.async_show_form(
                    step_id="sources", data_schema=self._sources_schema(),
                    errors={"base": "invalid_config"},
                )
        return self.async_show_form(step_id="sources",
                                    data_schema=self._sources_schema())

    def _sources_schema(self):
        schema = {
            vol.Optional("price_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional("solar_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional("binding_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        }
        candidates = [""] + [a["id"] for a in self._draft["assets"]]
        for charger in self._draft["chargers"]:
            schema[vol.Optional("assign_" + charger["id"])] = vol.In(candidates)
        return vol.Schema(schema)

    async def async_step_verify(self, user_input=None):
        if user_input is not None:
            if user_input.get("confirm") is not True:
                return self.async_show_form(
                    step_id="verify", data_schema=self._verify_schema(),
                    errors={"base": "verification_required"},
                    description_placeholders=self._verification_summary(),
                )
            try:
                cfg = validate_configuration(self._draft)
            except ValueError:
                return self.async_abort(reason="invalid_config")
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=NAME, data={"source": "ui", "configuration": cfg}
            )
        return self.async_show_form(
            step_id="verify", data_schema=self._verify_schema(),
            description_placeholders=self._verification_summary(),
        )

    @staticmethod
    def _verify_schema():
        return vol.Schema({vol.Required("confirm", default=False): bool})

    def _verification_summary(self):
        cfg = self._draft
        ceiling = cfg["controller"].get("max_power_kw")
        limit = (f"{ceiling} kW group ceiling (not field-verified)"
                 if ceiling is not None else "Group power ceiling not yet configured")
        return {"summary": (
            f"{len(cfg['chargers'])} charging points, {len(cfg['assets'])} assets. "
            f"{limit}. Charging remains physically disabled until "
            "separately commissioned."
        )}

    async def async_step_import(self, user_input):
        """Import expert JSON/YAML via native Config Entry, without any wizard."""
        await self.async_set_unique_id(DOMAIN)
        cfg = validate_configuration(user_input)
        expert_format = self.context.get("expert_format", "yaml")
        if expert_format not in ("yaml", "json"):
            raise ValueError("Unsupported expert configuration format")
        entries = self._async_current_entries()
        if entries:
            # An existing setup can adopt expert YAML without deleting/readding
            # the HA Config Entry: this preserves its entry ID, logical devices,
            # registry identities, Recorder history and physical replay store.
            entry = entries[0]
            existing_runtime = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
            if existing_runtime is not None:
                _assert_safe_expert_import(
                    existing_runtime, cfg,
                    source_changed=entry.data.get("source") != expert_format,
                )
            elif entry.data.get("configuration") != cfg or (
                    entry.data.get("source") != expert_format):
                # An unloaded Config Entry cannot prove that any formerly or
                # newly owned commissioned EVSE is physically idle. Refuse a
                # structural import rather than mutating its command owner.
                old_chargers = entry.data.get("configuration", {}).get(
                    "chargers", []
                )
                if any(
                    row.get("control_owner") == "multicharge"
                    and row.get("physical_commissioned") is True
                    for row in [*old_chargers, *cfg["chargers"]]
                ):
                    raise ValueError(
                        "EXPERT_IMPORT_REQUIRES_LOADED_VERIFIED_CHARGERS"
                    )
            next_data = {"source": expert_format, "configuration": cfg}
            next_options = {
                key: value for key, value in entry.options.items()
                if key != "configuration"
            }
            if (entry.data != next_data or entry.options != next_options):
                self.hass.config_entries.async_update_entry(
                    entry, data=next_data, options=next_options
                )
                # Loaded entries already have the canonical update listener.
                # Do not request a second reload/STOP on the same live charger.
                if entry.entry_id not in self.hass.data.get(DOMAIN, {}):
                    self.hass.async_create_task(
                        self.hass.config_entries.async_reload(entry.entry_id)
                    )
                return self.async_abort(reason="configuration_updated")
            return self.async_abort(reason="already_configured")
        return self.async_create_entry(
            title=NAME, data={"source": expert_format, "configuration": cfg}
        )


class RobotixMultiChargeOptionsFlow(config_entries.OptionsFlow):
    """UI-owned settings; YAML entries remain read-only until explicit migration."""

    def _current(self):
        return deepcopy(self.config_entry.options.get(
            "configuration", self.config_entry.data["configuration"]
        ))

    def _saved(self, config):
        try:
            result = validate_configuration(config)
        except ValueError:
            return None
        return self.async_create_entry(
            title="", data={**self.config_entry.options, "configuration": result}
        )

    async def async_step_yaml(self, user_input=None):
        """Edit one full or scoped YAML document through native Options Flow.

        Drafts live only inside the current HA flow; no physical action or
        Config Entry mutation takes place before independent Review & Save.
        """
        if self.config_entry.data.get("source") in ("yaml", "json"):
            return self.async_abort(reason="yaml_managed")
        if not hasattr(self, "_yaml_baseline_revision"):
            self._yaml_baseline_revision = configuration_revision(self._current())
            self._yaml_text = yaml.safe_dump(
                self._current(), sort_keys=False, allow_unicode=True,
            )
            self._yaml_mode = "replace"
        errors = {}
        self._yaml_validation_error = ""
        if user_input is not None:
            self._yaml_text = user_input.get("yaml_text", self._yaml_text)
            self._yaml_mode = user_input.get("mode", self._yaml_mode)
            try:
                if self._yaml_baseline_revision != configuration_revision(self._current()):
                    raise ValueError("configuration changed since editor opened")
                document = _parse_editor_yaml(self._yaml_text)
                proposed = prepare_expert_yaml_revision(
                    self._current(), document, self._yaml_mode,
                )
                self._yaml_draft = proposed
                self._yaml_summary = _yaml_review_summary(
                    self._current(), proposed,
                )
                return await self.async_step_yaml_review()
            except (ValueError, TypeError, KeyError) as exc:
                errors["base"] = "invalid_config"
                self._yaml_validation_error = str(exc)[:260]
        return self.async_show_form(
            step_id="yaml", errors=errors,
            data_schema=vol.Schema({
                vol.Required("mode", default=self._yaml_mode): vol.In({
                    "replace": "Complete configuration (replace omitted assets/chargers)",
                    "merge": "Scoped changes (preserve omitted assets/chargers)",
                }),
                vol.Required("yaml_text", default=self._yaml_text):
                    selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            }),
            description_placeholders={
                "note": (
                    "Data-only YAML. The existing Home Assistant Config Entry remains "
                    "authoritative. Review all additions/removals before Save. "
                    "Physical commissioning or owner changes are blocked."
                    + (f"\nValidation: {self._yaml_validation_error}"
                       if self._yaml_validation_error else "")
                ),
            },
        )

    async def async_step_yaml_review(self, user_input=None):
        if not hasattr(self, "_yaml_draft"):
            return await self.async_step_yaml()
        errors = {}
        review_error = ""
        if user_input is not None:
            if user_input.get("edit_again"):
                return await self.async_step_yaml()
            if not user_input.get("confirm"):
                errors["base"] = "confirm_save"
            elif self.config_entry.data.get("source") in ("yaml", "json"):
                errors["base"] = "yaml_managed"
            elif self._yaml_baseline_revision != configuration_revision(self._current()):
                errors["base"] = "selection_changed"
            else:
                try:
                    updated = prepare_expert_yaml_revision(
                        self._current(), _parse_editor_yaml(self._yaml_text),
                        self._yaml_mode,
                    )
                    if updated != self._yaml_draft:
                        raise ValueError("reviewed YAML draft no longer matches")
                    # Prefer the loaded canonical runtime and fail closed for
                    # commissioned writers if their idle state is unobservable.
                    runtime = self.hass.data.get(DOMAIN, {}).get(
                        self.config_entry.entry_id,
                    )
                    if runtime is None:
                        if any(c.get("control_owner") == "multicharge"
                               and c.get("physical_commissioned") is True
                               for c in [*self._current()["chargers"],
                                         *updated["chargers"]]):
                            raise ValueError("active writer requires verified runtime")
                        result = self._saved(updated)
                    else:
                        # Serialize the final safety check with the sole native
                        # writer's admission/STOP lock. No frontend-supplied
                        # status is trusted for this decision.
                        async with runtime.executor._lock:
                            if self._yaml_baseline_revision != configuration_revision(
                                    self._current()):
                                raise ValueError("configuration changed")
                            _assert_safe_yaml_ui_commit(runtime, updated)
                            result = self._saved(updated)
                    if result is None:
                        raise ValueError("configuration rejected")
                    return result
                except (ValueError, KeyError, TypeError) as exc:
                    errors["base"] = "invalid_config"
                    review_error = str(exc)[:260]
        return self.async_show_form(
            step_id="yaml_review", errors=errors,
            data_schema=vol.Schema({
                vol.Required("confirm", default=False): bool,
                vol.Optional("edit_again", default=False): bool,
            }),
            description_placeholders={
                "summary": self._yaml_summary
                + (f"\nValidation: {review_error}" if review_error else ""),
            },
        )

    async def async_step_init(self, user_input=None):
        if self.config_entry.data.get("source") in ("yaml", "json"):
            return self.async_abort(reason="yaml_managed")
        return self.async_show_menu(
            step_id="init", menu_options=["controller", "asset", "charger", "display", "yaml"]
        )

    async def async_step_controller(self, user_input=None):
        cfg = self._current()
        if user_input is not None:
            cfg["controller"]["name"] = user_input["name"]
            cfg["controller"]["max_parallel"] = int(user_input["max_parallel"])
            if user_input.get("max_power_kw"):
                cfg["controller"]["max_power_kw"] = user_input["max_power_kw"]
            else:
                cfg["controller"].pop("max_power_kw", None)
            if user_input.get("mode"):
                cfg["controller"]["mode"] = user_input["mode"]
            if user_input.get("phase_limits_a"):
                cfg["controller"]["phase_limits_a"] = _phase_limits(user_input["phase_limits_a"])
            for key in ("price_entity", "solar_entity", "binding_entity"):
                if user_input.get(key):
                    cfg["controller"][key] = user_input[key]
                else:
                    cfg["controller"].pop(key, None)
            result = self._saved(cfg)
            if result is not None:
                return result
        return self.async_show_form(
            step_id="controller",
            data_schema=vol.Schema({
                vol.Required("name", default=cfg["controller"]["name"]): str,
                vol.Required("max_parallel", default=cfg["controller"]["max_parallel"]):
                    selector.NumberSelector(selector.NumberSelectorConfig(
                        min=1, max=16, step=1, mode=selector.NumberSelectorMode.BOX
                    )),
                vol.Optional("max_power_kw"): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.01, max=1000, step=0.1,
                        mode=selector.NumberSelectorMode.BOX
                    )),
                vol.Optional("phase_limits_a",
                             default=",".join(f"{p}:{x}" for p,x in
                                    cfg["controller"].get("phase_limits_a", {}).items())): str,
                vol.Optional("price_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("solar_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("binding_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }),
            errors={"base": "invalid_config"} if user_input else {},
        )

    async def async_step_asset(self, user_input=None):
        cfg = self._current()
        if user_input is not None:
            uid = _id(user_input.get("id") or user_input.get("name") or "")
            action = user_input.get("action", "save")
            if not uid:
                result = None
            elif action == "delete":
                cfg["assets"] = [a for a in cfg["assets"] if a["id"] != uid]
                result = self._saved(cfg)
            else:
                asset = next((dict(a) for a in cfg["assets"] if a["id"] == uid), {})
                asset.update({
                    "id": uid,
                    "name": user_input.get("name") or asset.get("name"),
                    "kind": user_input.get("kind") or asset.get("kind", "car"),
                })
                for field in ("soc_entity", "capacity_kwh", "target_soc", "max_charge_kw",
                              "requested_kwh", "requested_duration_minutes",
                              "ready_by", "ready_by_repeat", "charge_efficiency", "priority",
                              "temporary", "expires_at",
                              "expected_connection_at"):
                    if user_input.get(field) is not None and user_input.get(field) != "":
                        asset[field] = user_input[field]
                cfg["assets"] = [a for a in cfg["assets"] if a["id"] != uid] + [asset]
                result = self._saved(cfg)
            if result is not None:
                return result
        return self.async_show_form(
            step_id="asset",
            data_schema=vol.Schema({
                vol.Required("action", default="save"): vol.In(["save", "delete"]),
                vol.Optional("id"): str,
                vol.Optional("name"): str,
                vol.Optional("kind"): vol.In(
                    ["car", "bicycle", "motorcycle", "scooter", "other"]
                ),
                vol.Optional("soc_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("capacity_kwh"): selector.NumberSelector(selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1, mode=selector.NumberSelectorMode.BOX
                )),
                vol.Optional("temporary"): bool,
                vol.Optional("expires_at"): str,
                vol.Optional("charge_efficiency"): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.01, max=1, step=0.01,
                        mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }),
            errors={"base": "invalid_config"} if user_input else {},
        )

    async def async_step_charger(self, user_input=None):
        cfg = self._current()
        if user_input is not None:
            uid = _id(user_input.get("id") or user_input.get("name") or "")
            action = user_input.get("action", "save")
            if not uid:
                result = None
            elif action == "delete":
                cfg["chargers"] = [c for c in cfg["chargers"] if c["id"] != uid]
                result = self._saved(cfg)
            else:
                charger = next((dict(c) for c in cfg["chargers"] if c["id"] == uid), {})
                charger["id"] = uid
                if user_input.get("name"):
                    charger["name"] = user_input["name"]
                if user_input.get("kind"):
                    charger["kind"] = user_input["kind"]
                elif "kind" not in charger:
                    charger["kind"] = "on_off"
                if user_input.get("rated_power_kw") is not None:
                    charger["rated_power_kw"] = user_input["rated_power_kw"]
                for field in ("asset", "control_entity", "connected_entity", "power_entity",
                              "energy_entity", "phase_count", "min_current_a", "max_current_a",
                              "voltage_v", "current_step_a", "fixed_current_a",
                              "circuit_id", "circuit_limit_a", "current_control_entity",
                              "current_readback_entity",
                              "control_owner", "physical_commissioned"):

                    if user_input.get(field) is not None and user_input.get(field) != "":
                        charger[field] = user_input[field]
                if user_input.get("phase_ids"):
                    charger["phase_ids"] = _phases(user_input["phase_ids"])
                cfg["chargers"] = [c for c in cfg["chargers"] if c["id"] != uid] + [charger]
                result = self._saved(cfg)
            if result is not None:
                return result
        return self.async_show_form(
            step_id="charger",
            data_schema=vol.Schema({
                vol.Required("action", default="save"): vol.In(["save", "delete"]),
                vol.Optional("id"): str,
                vol.Optional("name"): str,
                vol.Optional("kind"): vol.In(["on_off", "variable_current"]),
                vol.Optional("rated_power_kw"): selector.NumberSelector(selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1, mode=selector.NumberSelectorMode.BOX
                )),

                vol.Optional("control_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["switch", "input_boolean", "number"])
                ),
                vol.Optional("connected_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"])
                ),
                vol.Optional("power_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("energy_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("control_owner"): vol.In(["external", "multicharge"]),
                vol.Optional("physical_commissioned"): bool,
                vol.Optional("phase_count"): vol.In([1, 2, 3]),
                vol.Optional("min_current_a"): selector.NumberSelector(selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1, mode=selector.NumberSelectorMode.BOX
                )),
                vol.Optional("max_current_a"): selector.NumberSelector(selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1, mode=selector.NumberSelectorMode.BOX
                )),
                vol.Optional("phase_ids"): str,
                vol.Optional("voltage_v"): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=200, max=260, step=1,
                        mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional("current_step_a"): selector.NumberSelector(selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1, mode=selector.NumberSelectorMode.BOX
                )),
                vol.Optional("fixed_current_a"): selector.NumberSelector(selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1, mode=selector.NumberSelectorMode.BOX
                )),
                vol.Optional("circuit_id"): str,
                vol.Optional("circuit_limit_a"): selector.NumberSelector(selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1, mode=selector.NumberSelectorMode.BOX
                )),
                vol.Optional("current_control_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number")
                ),
                vol.Optional("current_readback_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }),
            errors={"base": "invalid_config"} if user_input else {},
        )

    async def async_step_display(self, user_input=None):
        """Optional frontend is a display preference, never a charging control."""
        current = self.config_entry.options.get("enable_ux", True)
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={**self.config_entry.options, "enable_ux": bool(user_input["enable_ux"])},
            )
        return self.async_show_form(
            step_id="display",
            data_schema=vol.Schema({vol.Required("enable_ux", default=current): bool}),
        )
