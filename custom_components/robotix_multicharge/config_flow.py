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


class RobotixMultiChargeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return RobotixMultiChargeOptionsFlow()

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required("name", default="Home charging"): str}),
            )
        try:
            cfg = validate_configuration(default_configuration(user_input["name"]))
        except ValueError:
            return self.async_show_form(step_id="user", errors={"base": "invalid_config"})
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=NAME, data={"source": "ui", "configuration": cfg}
        )

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
        return self.async_create_entry(title="", data={"configuration": result})

    async def async_step_init(self, user_input=None):
        if self.config_entry.data.get("source") == "yaml":
            return self.async_abort(reason="yaml_managed")
        return self.async_show_menu(
            step_id="init", menu_options=["controller", "asset", "charger"]
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
            cfg["controller"]["mode"] = user_input["mode"]
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
                vol.Required("mode", default=cfg["controller"].get("mode", "Off")):
                    vol.In(["Automatic", "Solar", "Economy", "Ready By", "Force Charge", "Off"]),
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
                asset.update({"id": uid, "name": user_input["name"], "kind": user_input["kind"]})
                for field in ("soc_entity", "capacity_kwh", "target_soc", "max_charge_kw",
                              "requested_kwh", "requested_duration_minutes",
                              "ready_by", "charge_efficiency", "priority"):
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
                vol.Required("kind", default="car"): vol.In(
                    ["car", "bicycle", "motorcycle", "scooter", "other"]
                ),
                vol.Optional("soc_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("capacity_kwh"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
                vol.Optional("target_soc"): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                vol.Optional("max_charge_kw"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
                vol.Optional("requested_kwh"): vol.All(vol.Coerce(float), vol.Range(min=0)),
                vol.Optional("requested_duration_minutes"): vol.All(
                    vol.Coerce(int), vol.Range(min=1)
                ),
                vol.Optional("ready_by"): selector.DateTimeSelector(),
                vol.Optional("charge_efficiency"): vol.All(
                    vol.Coerce(float), vol.Range(min=0.01, max=1)
                ),
                vol.Optional("priority"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
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
                charger.update({"id": uid, "name": user_input.get("name"),
                                "kind": user_input["kind"],
                                "rated_power_kw": user_input.get("rated_power_kw")})
                for field in ("asset", "control_entity", "connected_entity", "power_entity",
                              "energy_entity", "phase_count", "min_current_a", "max_current_a"):
                    if user_input.get(field) is not None and user_input.get(field) != "":
                        charger[field] = user_input[field]
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
                vol.Required("kind", default="on_off"): vol.In(["on_off", "variable_current"]),
                vol.Optional("rated_power_kw"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
                vol.Optional("asset"): vol.In([""] + [a["id"] for a in cfg["assets"]]),
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
                vol.Optional("phase_count"): vol.All(vol.Coerce(int), vol.In([1, 2, 3])),
                vol.Optional("min_current_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
                vol.Optional("max_current_a"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            }),
            errors={"base": "invalid_config"} if user_input else {},
        )
