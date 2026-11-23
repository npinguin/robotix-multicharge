"""Native HA names for the existing three logical MultiCharge devices."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_query import apply_native_preference, require_native_admin
from .const import DOMAIN
from .configuration import WEEKDAYS


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
                      "binding_entity", "solar_power_entity",
                      "home_power_entity", "grid_power_entity",
                      "solar_surplus_entity", "current_price_entity",
                      "export_price_entity")
    )
    entities.extend(
        _SourceBindingText(entry, runtime, "asset", asset, field)
        for asset in config["assets"]
        for field in ("soc_entity", "price_currency")
    )
    entities.extend(
        _AssetWindowText(entry, runtime, asset, day)
        for asset in config["assets"] for day in WEEKDAYS
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
        await require_native_admin(self.hass, self._context)
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
        await require_native_admin(self.hass, self._context)
        value = value.strip() if isinstance(value, str) else ""
        await apply_native_preference(
            self.hass, self.entry, self.runtime,
            self.kind, self.uid, {self.field: value or None},
        )


class _AssetWindowText(TextEntity):
    """One native source-of-truth HA Text per weekday on the owning Asset.

    The card offers human-friendly start/end controls and calls this entity.
    Empty value means no window for this day; no second timetable or writer.
    """
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = None
    _attr_native_min = 0
    _attr_native_max = 11

    def __init__(self, entry, runtime, asset, day):
        self.entry, self.runtime, self.uid, self.day = (
            entry, runtime, asset["id"], day
        )
        self._attr_unique_id = f"{DOMAIN}:asset:{self.uid}:charging_window_{day}"
        self._attr_name = f"{day.capitalize()} charging window"
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
        window = (asset or {}).get("charging_windows", {}).get(self.day)
        self._attr_native_value = (
            f"{window['start']}-{window['end']}" if window else ""
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

    async def async_set_value(self, value: str):
        await require_native_admin(self.hass, self._context)
        if not isinstance(value, str) or len(value) > 11:
            raise ValueError("window_format_invalid")
        asset = next((a for a in self.runtime.configuration["assets"]
                      if a["id"] == self.uid), None)
        if asset is None:
            raise ValueError("asset_not_found")
        windows = dict(asset.get("charging_windows") or {})
        if value.strip():
            parts = value.strip().split("-")
            if len(parts) != 2:
                raise ValueError("window_format_invalid")
            windows[self.day] = {"start": parts[0], "end": parts[1]}
        else:
            windows.pop(self.day, None)
        await apply_native_preference(
            self.hass, self.entry, self.runtime, "asset", self.uid,
            {"charging_windows": windows or None},
        )
