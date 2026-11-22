"""Read-only status entities on stable logical HA devices.

The product has no live charging engine yet. These are explicit setup diagnostics,
not fabricated SoC, charger readback, planning or permission to energize.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    cfg = hass.data[DOMAIN][entry.entry_id]
    entities = [_LogicalSetupSensor("controller", cfg["controller"])]
    entities.extend(_LogicalSetupSensor("asset", row) for row in cfg["assets"])
    entities.extend(_LogicalSetupSensor("charger", row) for row in cfg["chargers"])
    async_add_entities(entities)


class _LogicalSetupSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, kind: str, data: dict) -> None:
        self._attr_name = "Setup status"
        self._attr_unique_id = f"{DOMAIN}:{kind}:{data['id']}:setup"
        self._attr_native_value = "not_commissioned"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{kind}/{data['id']}")},
            "name": data["name"],
            "manufacturer": "Robotix",
            "model": {
                "controller": "ChargeController",
                "charger": "Charger",
                "asset": "ChargeableAsset",
            }[kind],
        }
        self._attr_extra_state_attributes = {
            "logical_id": data["id"],
            "concept": self._attr_device_info["model"],
            "operational": False,
        }
