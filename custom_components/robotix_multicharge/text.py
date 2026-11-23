"""Native HA names for the existing three logical MultiCharge devices."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_query import apply_native_preference
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    config = runtime.configuration
    entities = [
        _OwnerName(entry, runtime, kind, row)
        for kind, rows in (
            ("controller", [config["controller"]]),
            ("asset", config["assets"]),
            ("charger", config["chargers"]),
        )
        for row in rows
    ]
    entities.extend(
        _SourceBindingText(entry, runtime, "controller", config["controller"], field)
        for field in ("price_entity", "solar_entity", "site_power_entity",
                      "binding_entity")
    )
    entities.extend(
        _SourceBindingText(entry, runtime, "asset", asset, "soc_entity")
        for asset in config["assets"]
    )
    async_add_entities(entities)


class _OwnerName(TextEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min = 1
    _attr_native_max = 80

    def __init__(self, entry, runtime, kind, row):
        self.entry, self.runtime, self.kind, self.uid = (
            entry, runtime, kind, row["id"]
        )
        self._attr_unique_id = f"{DOMAIN}:{kind}:{self.uid}:name"
        self._attr_translation_key = "name"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{kind}/{self.uid}")},
            "name": row["name"],
            "manufacturer": "Robotix",
            "model": {
                "controller": "ChargeController",
                "asset": "ChargeableAsset",
                "charger": "Charger",
            }[kind],
        }
        self._unsubscribe = None
        self._refresh_value()

    def _refresh_value(self):
        group = (
            [self.runtime.configuration["controller"]]
            if self.kind == "controller"
            else self.runtime.configuration[
                "assets" if self.kind == "asset" else "chargers"
            ]
        )
        row = next((item for item in group if item["id"] == self.uid), None)
        self._attr_native_value = row.get("name") if row is not None else None

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

    async def async_set_value(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("name_required")
        await apply_native_preference(
            self.hass, self.entry, self.runtime,
            self.kind, self.uid, {"name": value.strip()},
        )



class _SourceBindingText(TextEntity):
    """Source IDs on their logical HA Device, one persisted Config Entry.

    This does not duplicate provider states or create another writer.
    Changes use the existing guarded native settings authority.
    """
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min = 0
    _attr_native_max = 255

    def __init__(self, entry, runtime, kind, row, field):
        self.entry, self.runtime = entry, runtime
        self.kind, self.uid, self.field = kind, row["id"], field
        self._attr_unique_id = f"{DOMAIN}:{kind}:{self.uid}:{field}"
        self._attr_translation_key = field
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{kind}/{self.uid}")},
            "name": row["name"], "manufacturer": "Robotix",
            "model": "ChargeController" if kind == "controller" else "ChargeableAsset",
        }
        self._unsubscribe = None
        self._refresh_value()

    def _refresh_value(self):
        rows = ([self.runtime.configuration["controller"]]
                if self.kind == "controller"
                else self.runtime.configuration["assets"])
        row = next((item for item in rows if item["id"] == self.uid), None)
        self._attr_native_value = (row.get(self.field, "") if row else "")

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

    async def async_set_value(self, value: str):
        actor = getattr(self.context, "user_id", None)
        user = await self.hass.auth.async_get_user(actor) if actor else None
        if user is None or not user.is_admin:
            raise RuntimeError("Source binding edits require an HA administrator")
        value = value.strip() if isinstance(value, str) else ""
        await apply_native_preference(
            self.hass, self.entry, self.runtime,
            self.kind, self.uid, {self.field: value or None},
        )
