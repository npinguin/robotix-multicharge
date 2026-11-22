"""Native HA vehicle demand and priority controls, with one Config Entry owner."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_query import apply_native_preference
from .const import DOMAIN

FIELDS = {
    "target_soc": (0, 100, 1, "%"),
    "requested_kwh": (0, 200, 0.1, "kWh"),
    "requested_duration_minutes": (0, 1440, 15, "min"),
    "priority": (0, 100, 1, None),
}

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        _AssetNumber(entry, runtime, asset, field)
        for asset in runtime.configuration["assets"] for field in FIELDS
    )


class _AssetNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, runtime, asset, field):
        self.entry, self.runtime, self.uid, self.field = (
            entry, runtime, asset["id"], field
        )
        low, high, step, unit = FIELDS[field]
        self._attr_native_min_value = low
        self._attr_native_max_value = high
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{DOMAIN}:asset:{self.uid}:{field}"
        self._attr_translation_key = field
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"asset/{self.uid}")},
            "name": asset["name"], "manufacturer": "Robotix",
            "model": "ChargeableAsset",
        }
        self._unsubscribe = None
        self._refresh_value()

    def _refresh_value(self):
        asset = next((a for a in self.runtime.configuration["assets"]
                      if a["id"] == self.uid), None)
        self._attr_native_value = (
            asset.get(self.field, 0) if asset is not None else None
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

    async def async_set_native_value(self, value: float):
        if self.field in ("priority", "requested_duration_minutes"):
            if not float(value).is_integer():
                raise ValueError("whole_number_required")
            value = int(value)
        changes = {self.field: value}
        if self.field == "requested_duration_minutes":
            changes["requested_kwh"] = None
            if value == 0:
                changes["requested_duration_minutes"] = None
        elif self.field == "requested_kwh":
            changes["requested_duration_minutes"] = None
            if value == 0:
                changes["requested_kwh"] = None
        await apply_native_preference(
            self.hass, self.entry, self.runtime, "asset", self.uid, changes
        )
