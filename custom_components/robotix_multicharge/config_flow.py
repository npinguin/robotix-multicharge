"""Guided native setup and one-authority expert JSON/YAML import."""

from __future__ import annotations

from copy import deepcopy
import json
from datetime import datetime, timezone
from re import sub

import voluptuous as vol
import yaml
from homeassistant import config_entries
from homeassistant.helpers import selector

from .configuration import (
    default_configuration, is_plan_presentation_only_change,
    validate_configuration, configuration_revision,
    apply_new_asset_defaults, energy_dashboard_suggestions,
)
from .source_evidence import number
from .execution import stop_power_limit
from .const import DOMAIN, NAME


ENERGY_ENTITY_FIELDS = (
    "solar_power_entity", "home_power_entity", "grid_power_entity",
    "solar_surplus_entity", "solar_entity", "price_entity",
    "current_price_entity", "export_price_entity",
)


async def _energy_dashboard_defaults(hass):
    """Read HA's own Energy Dashboard preferences without editing them.

    The optional first-party Energy integration is not required for manual
    setup or to run the standalone MultiCharge controller.
    """
    # Do not initialize an Energy Dashboard the owner never configured.
    # The manually selected native HA entities work with no Energy loaded.
    if "energy" not in hass.config.components:
        return {}
    try:
        from homeassistant.components.energy.data import async_get_manager

        manager = await async_get_manager(hass)
        return energy_dashboard_suggestions(manager.data)
    except (ImportError, ValueError, RuntimeError, KeyError, TypeError):
        return {}


def _optional_native_entity(key, defaults):
    """Use real Home Assistant EntitySelectors with validated suggestion IDs."""
    current = defaults.get(key)
    if current:
        return vol.Optional(key, default=current)
    return vol.Optional(key)


def _id(value: str) -> str:
    return sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _phases(raw):
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


def _native_status_labels(raw):
    """Parse user-supplied native EVSE states, never infer provider semantics."""
    if not isinstance(raw, str):
        raise ValueError("Expected comma-separated native EVSE states")
    return [item.strip() for item in raw.split(",") if item.strip()]


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
    before = {item["id"]: item for item in current["chargers"]}
    after = {item["id"]: item for item in updated["chargers"]}
    # The reconciliation gate protects physical writers, not harmless edits
    # to a monitoring-only site. No Charger is commissioned by editing a
    # name, price source or uncommissioned external Charger mapping.
    physical_writer = any(
        row.get("control_owner") == "multicharge"
        and row.get("physical_commissioned") is True
        for row in [*before.values(), *after.values()]
    )
    if not physical_writer:
        return
    executor = runtime.executor
    if (not executor._persistence_verified or executor._inflight
            or executor._start_pending or executor._quarantine):
        raise ValueError("EXPERT_IMPORT_REQUIRES_RECONCILED_CONTROL_STATE")
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
                                "connected_entity", "connected_states",
                                "disconnected_states", "energy_entity",
                                "session_entity", "kind", "rated_power_kw"))):
            continue
        if (uid in runtime.executor._sessions or
                uid in runtime.executor._start_pending):
            raise ValueError("YAML_UPDATE_CHARGER_BUSY")
        # Read-only external hardware can be mapped without asserting idle:
        # MultiCharge has no physical command authority over this charger.
        # Active or commissioned MultiCharge writers retain full idle checks.
        if (previous.get("control_owner") != "multicharge"
                and previous.get("physical_commissioned") is not True):
            continue
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
        """Offer an actual first-install choice, not a mandatory partial wizard."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if user_input is not None:
            # Preserve direct legacy user-flow submissions from older HA clients.
            return await self.async_step_guided(user_input)
        # Install the single native Config Entry immediately. Every site,
        # Charger and Asset setting is configured subsequently in MultiCharge.
        # Do not force a native HA wizard or free-text JSON/YAML upon users.
        cfg = default_configuration()
        return self.async_create_entry(
            title=NAME, data={"source": "ui", "configuration": cfg},
        )

    async def async_step_guided(self, user_input=None):
        """Existing guided onboarding remains unchanged after the mode choice."""
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
                preset = await _energy_dashboard_defaults(self.hass) if (
                    user_input.get("use_energy_dashboard")) else {}
                ctl = self._draft["controller"]
                for field in ENERGY_ENTITY_FIELDS:
                    value = user_input.get(field) or preset.get(field)
                    if value:
                        ctl[field] = value
                if user_input.get("binding_entity"):
                    ctl["binding_entity"] = user_input["binding_entity"]
                ctl["solar_source_kind"] = user_input.get(
                    "solar_source_kind", "none")
                ctl["grid_power_direction"] = user_input.get(
                    "grid_power_direction", "import_positive")
                validate_configuration(self._draft)
            except (KeyError, ValueError):
                return self.async_show_form(
                    step_id="guided", data_schema=self._site_schema(),
                    errors={"base": "invalid_config"},
                )
            return await self.async_step_charger()
        return self.async_show_form(
            step_id="guided", data_schema=self._site_schema()
        )

    async def async_step_expert(self, user_input=None):
        """Optional expert first-install path; default install stays one-click."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        errors = {}
        if user_input is not None:
            try:
                cfg = validate_configuration(_parse_editor_yaml(user_input["yaml_text"]))
                if any(row.get("control_owner") != "external"
                       or row.get("physical_commissioned") is True
                       for row in cfg["chargers"]):
                    raise ValueError("Commissioning is never performed by initial setup")
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=NAME, data={"source": "ui", "configuration": cfg},
                )
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_config"
        return self.async_show_form(
            step_id="expert", errors=errors,
            data_schema=vol.Schema({
                vol.Required("yaml_text", default=(user_input or {}).get(
                    "yaml_text", json.dumps(default_configuration(), indent=2),
                )): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            }),
            description_placeholders={"note": "Optional complete configuration; one Config Entry."},
        )

    def _site_schema(suggestions=None):
        suggestions = suggestions or {}
        # Explicit box widgets, never implicit range sliders in HA forms.
        # The unverified electrical ceiling is genuinely optional.
        return vol.Schema({
            vol.Optional("name", default="Home charging"): str,
            vol.Optional("mode", default="Automatic"): vol.In(
                ["Automatic", "Solar", "Economy", "Ready By", "Force Charge", "Off"]
            ),
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
            vol.Optional("use_energy_dashboard", default=False): bool,
            vol.Optional("solar_source_kind", default="none"): vol.In({
                "none": "Not selected / monitoring only",
                "intervals": "Qualified 15-minute Solar forecast intervals",
                "grid_export": "Live measured grid export",
                "direct_surplus": "Live measured available solar surplus",
            }),
            vol.Optional("grid_power_direction", default="import_positive"): vol.In({
                "import_positive": "Positive = import, negative = export (HA default)",
                "export_positive": "Positive = export, negative = import",
            }),
            **{
                _optional_native_entity(key, suggestions):
                    selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
                for key in ENERGY_ENTITY_FIELDS
            },
            vol.Optional("binding_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
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
                for field in ("connected_states", "disconnected_states"):
                    if field in user_input:
                        charger[field] = _native_status_labels(user_input[field])
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
            vol.Optional("connected_states"): str,
            vol.Optional("disconnected_states"): str,
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
                    for key in ("soc_entity", "soc_stale_entity", "capacity_kwh", "target_soc",
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
            vol.Optional("soc_stale_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
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
                # The historical wizard's Sources page selects an interval
                # provider. Preserve that explicit choice even if the Site
                # step initially defaulted to monitoring-only.
                if (user_input.get("solar_entity")
                        and trial["controller"].get("solar_source_kind", "none") == "none"):
                    trial["controller"]["solar_source_kind"] = "intervals"
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
            f"{limit}. Physical controls can be commissioned from "
            "Home Assistant Options > Commission, using independent native "
            "sensor and safe-idle readback. No RHI modules are required."
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

    async def _safe_structural_save(self, configuration):
        """Never change a commissioned physical writer without real idle proof.

        The native Options flow uses the same executor lock / guards as expert
        YAML. A fresh uncommissioned setup may still be edited while offline.
        """
        if self.config_entry.data.get("source") in ("yaml", "json"):
            return None
        try:
            updated = validate_configuration(configuration)
        except ValueError:
            return None
        def same_version():
            return (
                not hasattr(self, "_form_baseline_revision")
                or configuration_revision(self._current())
                == self._form_baseline_revision
            )

        if not same_version():
            return None
        runtime = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if runtime is None:
            old = self._current()
            if any(
                row.get("control_owner") == "multicharge"
                and row.get("physical_commissioned") is True
                for row in [*old["chargers"], *updated["chargers"]]
            ):
                return None
            return self._saved(updated)
        try:
            async with runtime.executor._lock:
                if not same_version():
                    return None
                _assert_safe_yaml_ui_commit(runtime, updated)
                return self._saved(updated)
        except ValueError:
            return None

    async def async_step_commission(self, user_input=None):
        """Opt-in standalone physical ownership with source-qualified idle gate.

        A deliberate operator assertion is required because Home Assistant
        cannot inspect hidden provider automations for competing EVSE writes.
        No device command is issued by this flow.
        """
        current = self._current()
        if not current["chargers"]:
            return self.async_abort(reason="no_chargers")
        errors = {}
        if user_input is not None:
            charger_id = user_input.get("charger_id")
            desired = bool(user_input.get("commission"))
            if (not charger_id
                    or (desired and not user_input.get("exclusive_writer_confirmed"))
                    or (desired and not user_input.get("electrical_limits_confirmed"))):
                errors["base"] = "invalid_config"
            else:
                trial = deepcopy(current)
                selected = next(
                    (row for row in trial["chargers"] if row["id"] == charger_id),
                    None,
                )
                if selected is None:
                    errors["base"] = "invalid_config"
                else:
                    selected["control_owner"] = (
                        "multicharge" if desired else "external"
                    )
                    selected["physical_commissioned"] = desired
                    result = await self._safe_structural_save(trial)
                    if result is not None:
                        return result
                    errors["base"] = "invalid_config"
        choices = {row["id"]: row["name"] for row in current["chargers"]}
        return self.async_show_form(
            step_id="commission", errors=errors,
            data_schema=vol.Schema({
                vol.Required("charger_id"): vol.In(choices),
                vol.Required("commission", default=True): bool,
                vol.Required("exclusive_writer_confirmed", default=False): bool,
                vol.Required("electrical_limits_confirmed", default=False): bool,
            }),
            description_placeholders={
                "note": (
                    "Stand-alone Home Assistant ownership. Before enabling, "
                    "stop or disable every other controller/automation for "
                    "this exact physical Charger, verify its circuit and "
                    "hardware limits, and configure independent live "
                    "connection, switch and power readback. The Charger must "
                    "be observed OFF with near-zero power; active/unknown "
                    "control states, unavailable sources and unresolved "
                    "commands are rejected. No RHI integration is required."
                ),
            },
        )

    async def async_step_yaml(self, user_input=None):
        """Edit the complete current Config Entry with one native Save.

        Physical owner changes belong to Commission, not free-text edits.
        """
        cfg = self._current()
        if not hasattr(self, "_form_baseline_revision"):
            self._form_baseline_revision = configuration_revision(cfg)
        errors = {}
        if user_input is not None:
            try:
                proposed = validate_configuration(_parse_editor_yaml(user_input["yaml_text"]))
                if proposed["controller"]["id"] != cfg["controller"]["id"]:
                    raise ValueError("CONTROLLER_ID_IMMUTABLE")
                old = {row["id"]: row for row in cfg["chargers"]}
                new = {row["id"]: row for row in proposed["chargers"]}
                for uid, existing in old.items():
                    if uid not in new and (
                        existing.get("control_owner") == "multicharge"
                        or existing.get("physical_commissioned") is True
                    ):
                        raise ValueError("COMMISSIONING_ONLY_IN_NATIVE_FLOW")
                for row in proposed["chargers"]:
                    existing = old.get(row["id"], {})
                    if (
                        row.get("control_owner", "external")
                        != existing.get("control_owner", "external")
                        or row.get("physical_commissioned", False)
                        != existing.get("physical_commissioned", False)
                    ):
                        raise ValueError("COMMISSIONING_ONLY_IN_NATIVE_FLOW")
                result = await self._safe_structural_save(proposed)
                if result is not None:
                    return result
                errors["base"] = (
                    "selection_changed"
                    if configuration_revision(self._current())
                    != self._form_baseline_revision else "invalid_config"
                )
            except (KeyError, ValueError, TypeError):
                errors["base"] = "invalid_config"
        return self.async_show_form(
            step_id="yaml", errors=errors,
            data_schema=vol.Schema({
                vol.Required("yaml_text", default=(user_input or {}).get(
                    "yaml_text", json.dumps(cfg, indent=2),
                )): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            }),
            description_placeholders={
                "note": "Edit the existing Controller, Chargers, Assets, energy and prices. "
                        "Save updates this same Config Entry; hardware ownership is separate.",
            },
        )

    async def async_step_init(self, user_input=None):
        """Configure is optional after zero-source, one-click installation."""
        if self.config_entry.data.get("source") in ("yaml", "json"):
            return self.async_abort(reason="yaml_managed")
        self._form_baseline_revision = configuration_revision(self._current())
        return self.async_show_menu(
            step_id="init",
            menu_options=["controller", "charger_pick", "asset_pick", "energy",
                          "yaml", "display", "commission"],
        )

    async def async_step_energy(self, user_input=None):
        """Optional HA-standard source choices; Energy Dashboard is read-only.

        Import associations once into the same UI-owned Config Entry, without
        depending on the Energy integration during charging or copying its
        statistics as a second system of record.
        """
        cfg = self._current()
        discovered = await _energy_dashboard_defaults(self.hass)
        errors = {}
        if user_input is not None:
            trial = deepcopy(cfg)
            ctl = trial["controller"]
            preset = discovered if user_input.get("use_energy_dashboard") else {}
            for field in ENERGY_ENTITY_FIELDS:
                # Missing optional UI fields are not an instruction to erase a
                # previously selected native source. Explicit empty clears.
                if field not in user_input and field not in preset:
                    continue
                value = user_input.get(field) or preset.get(field)
                if value:
                    ctl[field] = value
                else:
                    ctl.pop(field, None)
            for field in ("solar_source_kind", "grid_power_direction"):
                if field in user_input:
                    ctl[field] = user_input[field]
            result = await self._safe_structural_save(trial)
            if result is not None:
                return result
            errors["base"] = "invalid_config"
        # Existing saved selection is the only default. Energy Dashboard
        # suggestions are intentionally NOT silently imported when the
        # operator leaves its opt-in checkbox unticked.
        chosen = {
            key: cfg["controller"][key] for key in ENERGY_ENTITY_FIELDS
            if cfg["controller"].get(key)
        }
        return self.async_show_form(
            step_id="energy", errors=errors,
            data_schema=vol.Schema({
                vol.Optional("use_energy_dashboard", default=False): bool,
                vol.Required("solar_source_kind", default=cfg["controller"].get(
                    "solar_source_kind", "none")): vol.In({
                        "none": "Monitoring only / not configured",
                        "intervals": "Qualified 15-minute Solar intervals",
                        "grid_export": "Live grid export power (W/kW)",
                        "direct_surplus": "Live available solar surplus power (W/kW)",
                    }),
                vol.Required("grid_power_direction", default=cfg["controller"].get(
                    "grid_power_direction", "import_positive")): vol.In({
                        "import_positive": "Import positive (HA Energy standard)",
                        "export_positive": "Export positive",
                    }),
                **{
                    _optional_native_entity(key, chosen):
                        selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
                    for key in ENERGY_ENTITY_FIELDS
                },
            }),
            description_placeholders={
                "note": (
                    "Choose existing native Home Assistant sensors. "
                    "Use Energy Dashboard imports its configured grid/solar "
                    "live power and current price entity references only when "
                    "opted in. Available suggestions: "
                    + (", ".join(f"{key}: {value}" for key, value in
                                 sorted(discovered.items())) or "none")
                    + ". Home consumption is selected manually, not "
                    "calculated by adding appliance counters. Power W/kW is "
                    "different from Energy Wh/kWh. Live prices are indicative "
                    "and cannot replace future tariff intervals."
                ),
            },
        )

    async def async_step_controller(self, user_input=None):
        """Edit actual site identity, strategy and planning limits in native HA."""
        cfg = self._current()
        current = cfg["controller"]
        errors = {}
        if user_input is not None:
            trial = deepcopy(cfg)
            ctl = trial["controller"]
            for key in ("name", "mode", "max_power_kw"):
                if key in user_input:
                    ctl[key] = user_input[key]
            if "max_parallel" in user_input:
                parallel = user_input["max_parallel"]
                if (type(parallel) not in (int, float)
                        or parallel != int(parallel)):
                    errors["base"] = "invalid_config"
                else:
                    # HA NumberSelector returns a float even with step=1;
                    # canonical schema correctly requires a positive int.
                    ctl["max_parallel"] = int(parallel)
            if user_input.get("phase_limits_a"):
                try:
                    ctl["phase_limits_a"] = _phase_limits(user_input["phase_limits_a"])
                except ValueError:
                    errors["base"] = "invalid_config"
            elif "phase_limits_a" in user_input:
                ctl.pop("phase_limits_a", None)
            if not errors:
                result = await self._safe_structural_save(trial)
                if result is not None:
                    return result
                errors["base"] = "invalid_config"
        schema = {
            vol.Required("name", default=current["name"]): str,
            vol.Required("mode", default=current.get("mode", "Automatic")):
                vol.In(["Automatic", "Solar", "Economy", "Ready By",
                        "Force Charge", "Off"]),
            vol.Required("max_parallel", default=current.get("max_parallel", 1)):
                selector.NumberSelector(selector.NumberSelectorConfig(
                    min=1, max=16, step=1, mode=selector.NumberSelectorMode.BOX,
                )),
            vol.Optional("phase_limits_a", default=",".join(
                f"{p}:{x}" for p, x in current.get("phase_limits_a", {}).items()
            )): str,
        }
        if current.get("max_power_kw") is not None:
            field = vol.Optional("max_power_kw", default=current["max_power_kw"])
        else:
            field = vol.Optional("max_power_kw")
        schema[field] = selector.NumberSelector(selector.NumberSelectorConfig(
            min=0.01, max=1000, step=0.1, mode=selector.NumberSelectorMode.BOX,
        ))
        return self.async_show_form(
            step_id="controller", data_schema=vol.Schema(schema), errors=errors,
        )

    async def async_step_asset_pick(self, user_input=None):
        """Choose an existing asset by name or add a new one; no ID guessing."""
        rows = self._current()["assets"]
        if user_input is not None:
            target = user_input["selected"]
            self._edit_asset_id = None if target == "__new__" else target
            return await self.async_step_asset()
        choices = {"__new__": "Add chargeable asset"}
        choices.update({row["id"]: row["name"] for row in rows})
        return self.async_show_form(
            step_id="asset_pick",
            data_schema=vol.Schema({vol.Required(
                "selected", default="__new__"): vol.In(choices)}),
        )

    async def async_step_asset(self, user_input=None):
        """Add, edit or delete the selected actual asset in one form."""
        cfg = self._current()
        selected = getattr(self, "_edit_asset_id", None)
        original = next(
            (dict(row) for row in cfg["assets"] if row["id"] == selected), {},
        )
        errors = {}
        if user_input is not None:
            uid = selected or _id(user_input.get("id") or user_input.get("name") or "")
            action = user_input.get("action", "save")
            if (not uid or (action == "delete" and not selected)
                    or (not selected and any(
                        row["id"] == uid for row in cfg["assets"]))):
                errors["base"] = "invalid_config"
            else:
                trial = deepcopy(cfg)
                if action == "delete":
                    trial["assets"] = [
                        row for row in trial["assets"] if row["id"] != uid
                    ]
                else:
                    record = next(
                        (dict(row) for row in trial["assets"] if row["id"] == uid),
                        {"id": uid},
                    )
                    if not user_input.get("name") and not record.get("name"):
                        errors["base"] = "invalid_config"
                    else:
                        for key in ("name", "kind", "soc_entity",
                                    "soc_stale_entity", "capacity_kwh",
                                    "target_soc", "vehicle_control_entity",
                                    "vehicle_current_entity"):
                            if key in user_input:
                                if user_input[key] not in (None, ""):
                                    record[key] = user_input[key]
                                else:
                                    record.pop(key, None)
                        record.setdefault("kind", "car")
                        if not any(row["id"] == uid for row in trial["assets"]):
                            apply_new_asset_defaults(record)
                            trial["assets"].append(record)
                        else:
                            trial["assets"] = [
                                record if row["id"] == uid else row
                                for row in trial["assets"]
                            ]
                if not errors:
                    result = await self._safe_structural_save(trial)
                    if result is not None:
                        return result
                    errors["base"] = "invalid_config"

        def field(key):
            return (vol.Optional(key, default=original[key])
                    if key in original else vol.Optional(key))

        schema = {
            vol.Required("action", default="save"): vol.In(
                ["save", "delete"] if selected else ["save"]),
            vol.Required("name", default=original.get("name", "")): str,
            vol.Required("kind", default=original.get("kind", "car")):
                vol.In(["car", "bicycle", "motorcycle", "scooter", "other"]),
            field("soc_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")),
            field("soc_stale_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")),
            field("vehicle_control_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")),
            field("vehicle_current_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="number")),
            field("capacity_kwh"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.01, max=1000, step=0.1,
                    mode=selector.NumberSelectorMode.BOX)),
            field("target_soc"): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=100, step=1,
                    mode=selector.NumberSelectorMode.BOX)),
        }
        if not selected:
            schema[vol.Optional("id")] = str
        return self.async_show_form(
            step_id="asset", data_schema=vol.Schema(schema), errors=errors,
        )

    async def async_step_charger_pick(self, user_input=None):
        """Choose a real charger by its name or create another."""
        rows = self._current()["chargers"]
        if user_input is not None:
            target = user_input["selected"]
            self._edit_charger_id = None if target == "__new__" else target
            return await self.async_step_charger()
        choices = {"__new__": "Add charger"}
        choices.update({row["id"]: row["name"] for row in rows})
        return self.async_show_form(
            step_id="charger_pick",
            data_schema=vol.Schema({vol.Required(
                "selected", default="__new__"): vol.In(choices)}),
        )

    async def async_step_charger(self, user_input=None):
        """Edit real HA sources without rewriting the electrical controls."""
        cfg = self._current()
        selected = getattr(self, "_edit_charger_id", None)
        original = next(
            (dict(row) for row in cfg["chargers"] if row["id"] == selected), {},
        )
        errors = {}
        if user_input is not None:
            uid = selected or _id(user_input.get("id") or user_input.get("name") or "")
            action = user_input.get("action", "save")
            if (not uid or (action == "delete" and not selected)
                    or (not selected and any(
                        row["id"] == uid for row in cfg["chargers"]))):
                errors["base"] = "invalid_config"
            else:
                trial = deepcopy(cfg)
                if action == "delete":
                    trial["chargers"] = [
                        row for row in trial["chargers"] if row["id"] != uid
                    ]
                else:
                    record = next(
                        (dict(row) for row in trial["chargers"] if row["id"] == uid),
                        {"id": uid, "control_owner": "external",
                         "physical_commissioned": False},
                    )
                    if not user_input.get("name") and not record.get("name"):
                        errors["base"] = "invalid_config"
                    else:
                        for key in ("name", "kind", "rated_power_kw",
                                    "control_entity", "connected_entity",
                                    "power_entity", "energy_entity",
                                    "current_control_entity",
                                    "current_readback_entity"):
                            if key in user_input:
                                if user_input[key] not in (None, ""):
                                    record[key] = user_input[key]
                                else:
                                    record.pop(key, None)
                        record.setdefault("kind", "on_off")
                        if "rated_power_kw" not in record:
                            errors["base"] = "invalid_config"
                        elif not any(row["id"] == uid for row in trial["chargers"]):
                            trial["chargers"].append(record)
                        else:
                            trial["chargers"] = [
                                record if row["id"] == uid else row
                                for row in trial["chargers"]
                            ]
                if not errors:
                    result = await self._safe_structural_save(trial)
                    if result is not None:
                        return result
                    errors["base"] = "invalid_config"

        def field(key):
            return (vol.Optional(key, default=original[key])
                    if key in original else vol.Optional(key))

        schema = {
            vol.Required("action", default="save"): vol.In(
                ["save", "delete"] if selected else ["save"]),
            vol.Required("name", default=original.get("name", "")): str,
            vol.Required("kind", default=original.get("kind", "on_off")):
                vol.In(["on_off", "variable_current"]),
            vol.Required("rated_power_kw", default=original.get(
                "rated_power_kw", 3.6)): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.01, max=1000, step=0.1,
                        mode=selector.NumberSelectorMode.BOX)),
            field("control_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")),
            field("connected_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"])),
            field("power_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")),
            field("energy_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")),
            field("current_control_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="number")),
            field("current_readback_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")),
        }
        if not selected:
            schema[vol.Optional("id")] = str
        return self.async_show_form(
            step_id="charger", data_schema=vol.Schema(schema), errors=errors,
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
