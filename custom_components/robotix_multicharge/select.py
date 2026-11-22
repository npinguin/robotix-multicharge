"""Native HA device-owned charging preferences; Config Entry remains sole authority."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_query import apply_native_preference
from .configuration import PLAN_COLORS
from .const import DOMAIN

MODES = {
    "automatic": "Automatic", "solar": "Solar", "economy": "Economy",
    "ready_by": "Ready By", "force_charge": "Force Charge", "off": "Off",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    choices = runtime.configuration
    entities = [
        _OwnedSelect(entry, runtime, "controller", choices["controller"], field)
        for field in ("plan_label_mode", "plan_color_by",
                      "show_indicative_forecast", "mode")
    ]
    for asset in choices["assets"]:
        entities.append(_OwnedSelect(entry, runtime, "asset", asset, "plan_color"))
        entities.append(_OwnedSelect(entry, runtime, "asset", asset, "ready_by_repeat"))
        entities.append(_OwnedSelect(entry, runtime, "asset", asset, "kind"))
    for charger in choices["chargers"]:
        entities.append(_OwnedSelect(entry, runtime, "charger", charger, "plan_color"))
        entities.append(_OwnedSelect(entry, runtime, "charger", charger, "asset"))
    async_add_entities(entities)


class _OwnedSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry, runtime, kind, data, field):
        self.entry = entry
        self.runtime = runtime
        self.kind = kind
        self.uid = data["id"]
        self.field = field
        self._unsubscribe = None
        self._attr_unique_id = f"{DOMAIN}:{kind}:{self.uid}:{field}"
        self._attr_translation_key = (
            "selected_vehicle" if field == "asset" else field
        )
        if field == "mode":
            self._attr_entity_category = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{kind}/{self.uid}")},
            "name": data["name"],
            "manufacturer": "Robotix",
            "model": {
                "controller": "ChargeController", "charger": "Charger",
                "asset": "ChargeableAsset",
            }[kind],
        }
        self._refresh_value()

    def _record(self):
        collection = (
            [self.runtime.configuration["controller"]]
            if self.kind == "controller"
            else self.runtime.configuration[
                "assets" if self.kind == "asset" else "chargers"
            ]
        )
        return next((row for row in collection if row["id"] == self.uid), None)

    def _options(self):
        if self.field == "plan_color":
            return list(PLAN_COLORS)
        if self.field == "plan_label_mode":
            return ["vehicle", "charger", "both"]
        if self.field == "plan_color_by":
            return ["vehicle", "charger"]
        if self.field == "show_indicative_forecast":
            return ["on", "off"]
        if self.field == "mode":
            return list(MODES)
        if self.field == "ready_by_repeat":
            return ["none", "daily", "weekly"]
        if self.field == "kind":
            return ["car", "bicycle", "motorcycle", "scooter", "other"]
        # The selected Charger owns the ONLY editable assignment relationship.
        # User-facing select options are names, not opaque vehicle IDs.
        assets = self.runtime.configuration["assets"]
        duplicates = {
            row["name"] for row in assets
            if sum(other["name"] == row["name"] for other in assets) > 1
        }
        return ["none"] + [
            f"{row['name']} ({row['id']})" if row["name"] in duplicates
            else row["name"] for row in assets
        ]

    def _refresh_value(self):
        self._attr_options = self._options()
        current = self._record()
        if current is None:
            self._attr_current_option = None
        elif self.field == "asset":
            assets = self.runtime.configuration["assets"]
            selected = next((
                row for row in assets if row["id"] == current.get("asset")
            ), None)
            if selected is None:
                self._attr_current_option = "none"
            else:
                duplicates = sum(
                    a["name"] == selected["name"] for a in assets
                ) > 1
                self._attr_current_option = (
                    f"{selected['name']} ({selected['id']})" if duplicates
                    else selected["name"]
                )
        elif self.field == "mode":
            self._attr_current_option = next((
                name for name, source in MODES.items()
                if source == current.get("mode")
            ), "off")
        elif self.field == "show_indicative_forecast":
            self._attr_current_option = (
                "on" if current.get(self.field, True) else "off"
            )
        else:
            self._attr_current_option = current.get(
                self.field, "none" if self.field == "ready_by_repeat" else None
            )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._unsubscribe = self.runtime.subscribe(self._refresh)

    @callback
    def _refresh(self):
        self._refresh_value()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        await super().async_will_remove_from_hass()

    async def async_select_option(self, option: str) -> None:
        if option not in self._options():
            raise ValueError("unsupported_choice")
        if self.field == "asset":
            assets = self.runtime.configuration["assets"]
            selected = None if option == "none" else next((
                row["id"] for row in assets
                if (f"{row['name']} ({row['id']})" if sum(
                    a["name"] == row["name"] for a in assets
                ) > 1 else row["name"]) == option
            ), None)
            if option != "none" and selected is None:
                raise ValueError("unknown_vehicle")
            value = selected
        elif self.field == "show_indicative_forecast":
            value = option == "on"
        elif self.field == "mode":
            value = MODES[option]
        else:
            value = option
        await apply_native_preference(
            self.hass, self.entry, self.runtime,
            self.kind, self.uid, {self.field: value},
        )
