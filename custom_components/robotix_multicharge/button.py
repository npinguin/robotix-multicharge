"""Native guarded charging STOP, Pause/Resume and plug identity controls."""
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
    # Every logical Charger owns its native actions at registration.
    # Unsupported/uncommissioned actions are unavailable, never missing,
    # and the physical executor remains the only possible command writer.
    async_add_entities([
        _ConfirmCurrentAssetButton(charger, runtime)
        for charger in runtime.configuration["chargers"]
    ] + [
        action(charger, runtime)
        for charger in runtime.configuration["chargers"]
        for action in (_SafeStopButton, _PauseButton, _ResumeButton)
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

    @property
    def available(self) -> bool:
        charger = next(
            (c for c in self.runtime.configuration["chargers"]
             if c["id"] == self._charger_id), None
        )
        return bool(
            charger and charger.get("control_owner") == "multicharge"
            and charger.get("physical_commissioned") is True
        )

    async def async_press(self) -> None:
        if not self.available:
            raise RuntimeError("CHARGER_NOT_COMMISSIONED")
        outcome = await self.runtime.executor.execute(
            self._charger_id, "stop", context=self._context
        )
        if outcome["status"] != "confirmed":
            raise RuntimeError(
                "MultiCharge STOP not physically confirmed: " + outcome["reason"]
            )


class _AdminChargeActionButton(_SafeStopButton):
    """A native HA button must not bypass the admin-only command WebSocket."""

    async def _require_admin_context(self):
        actor = getattr(self._context, "user_id", None)
        user = await self.hass.auth.async_get_user(actor) if actor else None
        if user is None or not user.is_admin:
            raise RuntimeError("This charging action requires an HA administrator")


class _PauseButton(_AdminChargeActionButton):
    """Durable operator hold plus independently verified physical STOP."""
    _attr_icon = "mdi:pause-circle-outline"

    def __init__(self, charger, runtime):
        super().__init__(charger, runtime)
        self._attr_name = "Pause charging"
        self._attr_unique_id = f"{DOMAIN}:charger:{charger['id']}:pause"

    async def async_press(self) -> None:
        await self._require_admin_context()
        if not self.available:
            raise RuntimeError("CHARGER_NOT_COMMISSIONED")
        outcome = await self.runtime.executor.execute(
            self._charger_id, "pause", context=self._context
        )
        if outcome["status"] != "confirmed":
            raise RuntimeError(
                "MultiCharge Pause not confirmed: " + outcome["reason"]
            )


class _ResumeButton(_AdminChargeActionButton):
    """Release user hold; never issues an automatic physical START."""
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, charger, runtime):
        super().__init__(charger, runtime)
        self._attr_name = "Resume charging"
        self._attr_unique_id = f"{DOMAIN}:charger:{charger['id']}:resume"

    async def async_press(self) -> None:
        await self._require_admin_context()
        if not self.available:
            raise RuntimeError("CHARGER_NOT_COMMISSIONED")
        outcome = await self.runtime.executor.execute(
            self._charger_id, "resume", context=self._context
        )
        if outcome["status"] != "confirmed":
            raise RuntimeError(
                "MultiCharge Resume not confirmed: " + outcome["reason"]
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

    @property
    def available(self) -> bool:
        charger = next(
            (c for c in self.runtime.configuration["chargers"]
             if c["id"] == self._charger_id), None
        )
        return bool(charger and charger.get("connected_entity"))

    async def async_press(self) -> None:
        if not self.available:
            raise RuntimeError("CHARGER_CONNECTION_SOURCE_NOT_CONFIGURED")
        async with self.runtime.executor._lock:
            result = self.runtime.executor.confirm_current_connection(
                self._charger_id
            )
        if result["status"] != "confirmed":
            raise RuntimeError("Cannot confirm current vehicle: " + result["reason"])
        self.runtime.refresh()
