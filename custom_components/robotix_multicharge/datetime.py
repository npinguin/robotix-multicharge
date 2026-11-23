"""Native HA Vehicle deadline and forecast arrival preferences."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_query import apply_native_preference
from .const import DOMAIN

FIELDS = ("ready_by", "expected_connection_at", "expires_at")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        _AssetDateTime(entry, runtime, asset, field)
        for asset in runtime.configuration["assets"] for field in FIELDS
    )


class _AssetDateTime(DateTimeEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = None

    def __init__(self, entry, runtime, asset, field):
        self.entry, self.runtime, self.uid, self.field = (
            entry, runtime, asset["id"], field
        )
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
        raw = asset.get(self.field) if asset else None
        self._attr_native_value = datetime.fromisoformat(raw) if raw else None
        # A guest expiry is an owned input for every Asset; it only becomes
        # writable when this Asset is actually configured as temporary.
        self._attr_available = bool(
            asset is not None
            and (self.field != "expires_at" or asset.get("temporary"))
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

    async def async_set_value(self, value: datetime):
        if not self.available:
            raise ValueError("ASSET_GUEST_EXPIRY_ONLY_FOR_TEMPORARY_ASSET")
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone_required")
        await apply_native_preference(
            self.hass, self.entry, self.runtime,
            "asset", self.uid, {self.field: value.isoformat()},
        )
