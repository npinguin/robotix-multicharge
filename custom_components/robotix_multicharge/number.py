"""Native HA vehicle demand and priority controls, with one Config Entry owner."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_query import apply_native_preference, require_native_admin
from .const import DOMAIN, DEFAULT_ASSET_PRIORITY
from .configuration import charger_is_active, charger_operating_grid
from math import floor, isfinite

FIELDS = {
    "target_soc": (0, 100, 1, "%"),
    "requested_kwh": (0, 200, 0.1, "kWh"),
    "requested_duration_minutes": (0, 1440, 15, "min"),
    "requested_budget_amount": (0, 10000, 0.01, "EUR"),
    "minimum_soc_pct": (0, 100, 1, "%"),
    "maximum_price_per_kwh": (-100, 100, 0.01, None),
    "low_price_trigger_per_kwh": (-100, 100, 0.01, None),
    "low_soc_trigger_pct": (0, 100, 1, "%"),
    "opportunistic_level_pct": (0, 100, 1, "%"),
    "priority": (0, 100, 1, None),
    "max_charge_kw": (0.1, 100, 0.1, "kW"),
    "capacity_kwh": (0.1, 1000, 0.1, "kWh"),
    "charge_efficiency": (0.01, 1, 0.01, None),
}

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    entities = [
        _AssetNumber(entry, runtime, asset, field)
        for asset in runtime.configuration["assets"] for field in FIELDS
    ]
    for field in ("max_parallel", "max_power_kw", "power_adjustment_interval_minutes"):
        entities.append(_SiteNumber(entry, runtime, field))
    for charger in runtime.configuration["chargers"]:
        # The logical Charger owns its inputs from the moment it is added.
        # A variable-current hardware capability may be incomplete during
        # onboarding; its native Numbers still exist, but report unavailable
        # until independently verified physical limits are configured.
        if charger.get("kind") == "variable_current":
            for field in ("min_charging_power_kw", "max_charging_power_kw",
                          "set_charging_power_kw"):
                entities.append(_ChargerPowerNumber(entry, runtime, charger, field))
    async_add_entities(entities)


class _AssetNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = None
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
        if field in ("capacity_kwh", "charge_efficiency", "minimum_soc_pct", "maximum_price_per_kwh", "low_price_trigger_per_kwh", "low_soc_trigger_pct", "opportunistic_level_pct", "max_charge_kw"):
            self._attr_entity_category = EntityCategory.CONFIG
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
            asset.get(self.field) if asset is not None else None
        )
        if self.field == "priority" and asset is not None:
            self._attr_native_value = asset.get("priority", DEFAULT_ASSET_PRIORITY)

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
        await require_native_admin(self.hass, self._context)
        if self.field in ("priority", "requested_duration_minutes"):
            if not float(value).is_integer():
                raise ValueError("whole_number_required")
            value = int(value)
        changes = {self.field: value}
        if self.field == "requested_duration_minutes":
            changes["requested_kwh"] = None
            changes["requested_budget_amount"] = None
            changes["requested_budget_currency"] = None
            if value == 0:
                changes["requested_duration_minutes"] = None
        elif self.field == "requested_kwh":
            changes["requested_duration_minutes"] = None
            changes["requested_budget_amount"] = None
            changes["requested_budget_currency"] = None
            if value == 0:
                changes["requested_kwh"] = None
        elif self.field == "requested_budget_amount":
            changes["requested_kwh"] = None
            changes["requested_duration_minutes"] = None
            changes["requested_budget_currency"] = "EUR" if value > 0 else None
            if value == 0:
                changes["requested_budget_amount"] = None
        await apply_native_preference(
            self.hass, self.entry, self.runtime, "asset", self.uid, changes
        )



class _SiteNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = None
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, runtime, field):
        self.entry, self.runtime, self.field = entry, runtime, field
        ctl = runtime.configuration["controller"]
        self._attr_unique_id = f"{DOMAIN}:controller:{ctl['id']}:{field}"
        self._attr_translation_key = field
        minimum, maximum, step, unit = {
            "max_parallel": (1, 16, 1, None),
            "max_power_kw": (0.1, 100, 0.1, "kW"),
            "power_adjustment_interval_minutes": (1, 1440, 1, "min"),
        }[field]
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"controller/{ctl['id']}")},
            "name": ctl["name"], "manufacturer": "Robotix",
            "model": "ChargeController",
        }
        self._unsubscribe = None
        self._refresh_value()

    def _refresh_value(self):
        ctl = self.runtime.configuration["controller"]
        self._attr_native_value = ctl.get(self.field)

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
        await require_native_admin(self.hass, self._context)
        if self.field in ("max_parallel", "power_adjustment_interval_minutes"):
            if not float(value).is_integer():
                raise ValueError("whole_number_required")
            value = int(value)
        await apply_native_preference(
            self.hass, self.entry, self.runtime,
            "controller", self.runtime.configuration["controller"]["id"],
            {self.field: value},
        )



class _ChargerPowerNumber(NumberEntity):
    """Charger-owned kW limits and verified physical setpoint through one writer.

    Hardware Amp capabilities are not user preferences. Operating min/max are
    persisted within their verified envelope. Set power is a live action on a
    confirmed owned session, not a shadow scheduler or an invented measurement.
    """
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_mode = NumberMode.BOX

    def __init__(self, entry, runtime, charger, field):
        self.entry, self.runtime = entry, runtime
        self.uid, self.field = charger["id"], field
        self._attr_unique_id = f"{DOMAIN}:charger:{self.uid}:{field}"
        self._attr_translation_key = field
        self._attr_entity_category = (None if field == "set_charging_power_kw" else EntityCategory.CONFIG)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"charger/{self.uid}")},
            "name": charger["name"], "manufacturer": "Robotix",
            "model": "Charger",
        }
        self._attr_native_unit_of_measurement = "kW"
        self._attr_native_step = 0.01
        self._unsubscribe = None
        self._refresh_value()

    def _refresh_value(self):
        charger = next((c for c in self.runtime.configuration["chargers"]
                        if c["id"] == self.uid), None)
        if charger is None:
            self._attr_available = False
            self._attr_native_value = None
            return
        charger = self.runtime.executor.effective_charger(charger)
        grid = charger_operating_grid(charger)
        physical = charger_operating_grid(charger, preferences=False)
        self._attr_extra_state_attributes = {
            "effective_min_power_kw": round(grid[0] * grid[3], 6) if grid else None,
            "effective_max_power_kw": round(grid[1] * grid[3], 6) if grid else None,
        }
        # A configured kW limit is a preference/ceiling, not a setpoint.
        # Keep it editable even when the live native grid changes; never
        # replace the saved value with a transient hardware observation.
        self._attr_native_step = 0.01
        if self.field != "set_charging_power_kw":
            self._attr_available = True
            self._attr_native_min_value = 0.01
            self._attr_native_max_value = charger["rated_power_kw"]
            index = 0 if self.field == "min_charging_power_kw" else 1
            default = round(physical[index] * physical[3], 6) if physical else None
            self._attr_native_value = charger.get(self.field, default)
            if grid is None:
                self._attr_extra_state_attributes["reason"] = "USER_LIMIT_ONLY_CONVERSION_NOT_CONFIGURED"
            return
        if grid is None:
            self._attr_available = False
            self._attr_native_value = None
            self._attr_native_min_value = 0.01
            self._attr_native_max_value = charger["rated_power_kw"]
            self._attr_extra_state_attributes["reason"] = "CHARGER_CURRENT_CAPABILITY_NOT_VERIFIED"
            return
        minimum, maximum, step, factor = grid
        self._attr_native_min_value = round(minimum * factor, 6)
        self._attr_native_max_value = round(maximum * factor, 6)
        self._attr_native_step = round(step * factor, 6)
        session = self.runtime.executor.session_snapshot().get(self.uid)
        current = session.get("target_current_a") if session else None
        self._attr_native_value = round(current * factor, 6) if current is not None else None
        self._attr_available = bool(charger_is_active(charger) and current is not None)

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
        await require_native_admin(self.hass, self._context)
        if not self.available:
            raise ValueError("CHARGER_CURRENT_CAPABILITY_NOT_AVAILABLE")
        if self.field != "set_charging_power_kw":
            await apply_native_preference(
                self.hass, self.entry, self.runtime, "charger", self.uid,
                {self.field: float(value)},
            )
            return
        charger = next((c for c in self.runtime.configuration["chargers"]
                        if c["id"] == self.uid), None)
        if charger is None or charger.get("kind") != "variable_current":
            raise ValueError("CHARGER_NOT_ADJUSTABLE")
        charger = self.runtime.executor.effective_charger(charger)
        grid = charger_operating_grid(charger)
        if grid is None:
            raise ValueError("CURRENT_CAPABILITY_UNVERIFIED")
        minimum, maximum, step, factor = grid
        if (not isfinite(value) or value < minimum * factor - 1e-6
                or value > maximum * factor + 1e-6):
            raise ValueError("REQUESTED_POWER_OUTSIDE_VERIFIED_OPERATING_RANGE")
        # Select the closest legal native step inside the SAME operating grid.
        nearest = floor((float(value) / factor - minimum) / step + 0.5)
        current = round(min(maximum, minimum + max(0, nearest) * step), 6)
        outcome = await self.runtime.executor.execute(
            self.uid, "set_current", current_a=current, context=self._context
        )
        if outcome["status"] != "confirmed":
            raise RuntimeError("Charging power not confirmed: " + outcome["reason"])
        self._refresh()
