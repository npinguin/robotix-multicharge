"""Safe native HA STOP buttons, never an unqualified START automation."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    # Structural commissioning controls the presence of the button. Provider
    # switches stay with their own native HA integration.
    async_add_entities([
        _ConfirmCurrentAssetButton(charger, runtime)
        for charger in runtime.configuration["chargers"]
        if charger.get("connected_entity")
    ] + [
        _SafeStopButton(charger, runtime)
        for charger in runtime.configuration["chargers"]
        if charger.get("control_owner") == "multicharge"
        and charger.get("physical_commissioned") is True
    ])


class _SafeStopButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:stop-circle-outline"

    def __init__(self, charger, runtime):
        self._charger_id = charger["id"]
        self.runtime = runtime
        self._attr_name = "Stop charging"
        self._attr_unique_id = f"{DOMAIN}:charger:{charger['id']}:stop"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"charger/{charger['id']}")},
            "name": charger["name"], "manufacturer": "Robotix",
            "model": "Charger",
        }

    async def async_press(self) -> None:
        outcome = await self.runtime.executor.execute(
            self._charger_id, "stop", context=self.context
        )
        if outcome["status"] != "confirmed":
            raise RuntimeError(
                "MultiCharge STOP not physically confirmed: " + outcome["reason"]
            )


class _ConfirmCurrentAssetButton(ButtonEntity):
    """Native per-Charger current-plug identity acknowledgement."""
    _attr_has_entity_name = True
    _attr_icon = "mdi:car-connected"

    def __init__(self, charger, runtime):
        self._charger_id = charger["id"]
        self.runtime = runtime
        self._attr_name = "Confirm connected vehicle"
        self._attr_unique_id = (
            f"{DOMAIN}:charger:{charger['id']}:confirm_connection"
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"charger/{charger['id']}")},
            "name": charger["name"], "manufacturer": "Robotix",
            "model": "Charger",
        }

    async def async_press(self) -> None:
        async with self.runtime.executor._lock:
            result = self.runtime.executor.confirm_current_connection(
                self._charger_id
            )
        if result["status"] != "confirmed":
            raise RuntimeError("Cannot confirm current vehicle: " + result["reason"])
        self.runtime.refresh()
