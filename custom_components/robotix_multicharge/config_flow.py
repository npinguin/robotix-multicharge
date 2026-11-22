"""Guided native setup and one-authority expert YAML import."""

from __future__ import annotations

from copy import deepcopy
from re import sub

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .configuration import default_configuration, validate_configuration
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
                self._draft = default_configuration(user_input["name"])
                self._draft["controller"]["max_parallel"] = user_input["max_parallel"]
                self._draft["controller"]["max_power_kw"] = user_input["max_power_kw"]
                self._draft["controller"]["mode"] = "Off"
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
        return vol.Schema({
            vol.Required("name", default="Home charging"): str,
            vol.Required("max_parallel", default=1):
                vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
            vol.Required("max_power_kw", default=3.6):
                vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            vol.Optional("phase_limits_a"): str,
        })

    async def async_step_charger(self, user_input=None):
        if user_input is not None:
            try:
                if user_input["action"] == "add":
                    uid = _id(user_input["name"])
                    if not uid or any(c["id"] == uid for c in self._draft["chargers"]):
                        raise ValueError("charger identity must be unique")
                    charger = {
                        "id": uid,
                        "name": user_input["name"],
                        "kind": user_input["kind"],
                        "rated_power_kw": user_input["rated_power_kw"],
                    }
                    for key in ("phase_count", "min_current_a", "max_current_a",
                                "connected_entity", "power_entity", "energy_entity",
                                "control_entity", "voltage_v", "current_step_a",
                                "fixed_current_a", "circuit_id", "circuit_limit_a",
                                "current_control_entity", "current_readback_entity"):
                        if user_input.get(key) is not None:
                            charger[key] = user_input[key]
                    if user_input.get("phase_ids"):
                        charger["phase_ids"] = _phases(user_input["phase_ids"])
                    trial = deepcopy(self._draft)
                    trial["chargers"].append(charger)
                    validate_configuration(trial)
                    self._draft = trial
                    if user_input["add_another"]:
                        return self.async_show_form(step_id="charger",
                                                    data_schema=self._charger_schema())
                return await self.async_step_asset()
            except (KeyError, ValueError):
                return self.async_show_form(
                    step_id="charger", data_schema=self._charger_schema(),
                    errors={"base": "invalid_config"},
                )
        return self.async_show_form(step_id="charger", data_schema=self._charger_schema())

    @staticmethod
    def _charger_schema():
        return vol.Schema({
            vol.Required("action", default="add"): vol.In(["add", "finish"]),
            vol.Optional("name"): str,
            vol.Required("kind", default="on_off"): vol.In(["on_off", "variable_current"]),
            vol.Optional("rated_power_kw"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            vol.Optional("phase_count"): vol.In([1, 2, 3]),
            vol.Optional("min_current_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            vol.Optional("max_current_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            vol.Optional("phase_ids"): str,
            vol.Optional("voltage_v"): vol.All(vol.Coerce(float), vol.Range(min=200, max=260)),
            vol.Optional("current_step_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            vol.Optional("fixed_current_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            vol.Optional("circuit_id"): str,
            vol.Optional("circuit_limit_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            vol.Optional("current_control_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="number")
            ),
            vol.Optional("current_readback_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
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
            vol.Optional("control_entity"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "number"])
            ),
            vol.Required("add_another", default=False): bool,
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
        return {"summary": (
            f"{len(cfg['chargers'])} charging points, {len(cfg['assets'])} assets, "
            f"{cfg['controller']['max_power_kw']} kW configured group ceiling. "
            "Charging remains physically disabled until separately commissioned."
        )}

    async def async_step_import(self, user_input):
        """Import startup YAML; never replace an unrelated user-owned entry."""
        await self.async_set_unique_id(DOMAIN)
        cfg = validate_configuration(user_input)
        entries = self._async_current_entries()
        if entries:
            entry = entries[0]
            if entry.data.get("source") != "yaml":
                return self.async_abort(reason="configuration_conflict")
            if entry.data.get("configuration") != cfg:
                self.hass.config_entries.async_update_entry(
                    entry, data={"source": "yaml", "configuration": cfg}
                )
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(entry.entry_id)
                )
                return self.async_abort(reason="configuration_updated")
            return self.async_abort(reason="already_configured")
        return self.async_create_entry(
            title=NAME, data={"source": "yaml", "configuration": cfg}
        )


class RobotixMultiChargeOptionsFlow(config_entries.OptionsFlowWithReload):
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

    async def async_step_init(self, user_input=None):
        if self.config_entry.data.get("source") == "yaml":
            return self.async_abort(reason="yaml_managed")
        return self.async_show_menu(
            step_id="init", menu_options=["controller", "asset", "charger", "display"]
        )

    async def async_step_controller(self, user_input=None):
        cfg = self._current()
        if user_input is not None:
            cfg["controller"]["name"] = user_input["name"]
            cfg["controller"]["max_parallel"] = user_input["max_parallel"]
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
                    vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
                vol.Optional("max_power_kw"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
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
                vol.Optional("capacity_kwh"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
                vol.Optional("temporary"): bool,
                vol.Optional("expires_at"): str,
                vol.Optional("charge_efficiency"): vol.All(
                    vol.Coerce(float), vol.Range(min=0.01, max=1)
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
                vol.Optional("rated_power_kw"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),

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
                vol.Optional("phase_count"): vol.All(vol.Coerce(int), vol.In([1, 2, 3])),
                vol.Optional("min_current_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
                vol.Optional("max_current_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
                vol.Optional("phase_ids"): str,
                vol.Optional("voltage_v"): vol.All(vol.Coerce(float), vol.Range(min=200, max=260)),
                vol.Optional("current_step_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
                vol.Optional("fixed_current_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
                vol.Optional("circuit_id"): str,
                vol.Optional("circuit_limit_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
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
