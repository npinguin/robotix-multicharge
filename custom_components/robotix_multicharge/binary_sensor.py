"""Native physical Charger connection and charging state, independent of identity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass, BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        _ChargerBinary(charger, runtime, metric)
        for charger in runtime.configuration["chargers"]
        for metric in ("plugged", "charging")
    )


class _ChargerBinary(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, charger: dict, runtime, metric: str) -> None:
        self.runtime = runtime
        self.charger_id = charger["id"]
        self.metric = metric
        self._attr_unique_id = f"{DOMAIN}:charger:{self.charger_id}:{metric}"
        self._attr_translation_key = metric
        self._attr_device_class = (
            BinarySensorDeviceClass.PLUG
            if metric == "plugged" else BinarySensorDeviceClass.BATTERY_CHARGING
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"charger/{self.charger_id}")},
            "name": charger["name"], "manufacturer": "Robotix",
            "model": "Charger",
        }
        self._unsubscribe = None
        self._update_value()

    def _update_value(self):
        source = self.runtime.observations.get(
            "chargers", {}
        ).get(self.charger_id, {}).get(
            "connected" if self.metric == "plugged" else "power_kw"
        )
        if source is None or source.quality != "ok":
            self._attr_is_on = None
        elif self.metric == "plugged":
            self._attr_is_on = source.value is True
        else:
            self._attr_is_on = source.value > 0.05
        self._attr_extra_state_attributes = {
            "quality": source.quality if source is not None else "unknown",
            "observed_at": (
                source.observed_at.isoformat()
                if source is not None and source.observed_at is not None
                else None
            ),
        }

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._unsubscribe = self.runtime.subscribe(self._refresh)

    @callback
    def _refresh(self):
        self._update_value()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        await super().async_will_remove_from_hass()
