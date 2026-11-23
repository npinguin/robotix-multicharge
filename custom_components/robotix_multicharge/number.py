"""Native HA vehicle demand and priority controls, with one Config Entry owner."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_query import apply_native_preference
from .const import DOMAIN

FIELDS = {
    "target_soc": (0, 100, 1, "%"),
    "requested_kwh": (0, 200, 0.1, "kWh"),
    "requested_duration_minutes": (0, 1440, 15, "min"),
    "requested_budget_amount": (0, 10000, 0.01, "EUR"),
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
    for field in ("max_parallel", "max_power_kw"):
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
            self._attr_native_value = asset.get("priority", 0)

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
        self._attr_native_min_value = 1 if field == "max_parallel" else 0.1
        self._attr_native_max_value = 16 if field == "max_parallel" else 100
        self._attr_native_step = 1 if field == "max_parallel" else 0.1
        self._attr_native_unit_of_measurement = (
            None if field == "max_parallel" else "kW"
        )
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
        if self.field == "max_parallel":
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
        self._attr_entity_category = None
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
        required = ("voltage_v", "phase_ids", "min_current_a",
                    "max_current_a", "current_step_a")
        if (charger.get("kind") != "variable_current"
                or any(not charger.get(key) for key in required)):
            self._attr_available = False
            self._attr_native_value = None
            self._attr_native_min_value = 0.01
            self._attr_native_max_value = max(0.01, charger["rated_power_kw"])
            self._attr_extra_state_attributes = {
                "reason": "CHARGER_CURRENT_CAPABILITY_NOT_VERIFIED"
            }
            return
        self._attr_extra_state_attributes = {}
        factor = charger["voltage_v"] * len(charger["phase_ids"]) / 1000
        physical_min = charger["min_current_a"] * factor
        physical_max = min(charger["rated_power_kw"],
                           charger["max_current_a"] * factor)
        self._attr_native_min_value = round(physical_min, 4)
        self._attr_native_max_value = round(physical_max, 4)
        if self.field in ("min_charging_power_kw", "max_charging_power_kw"):
            default = physical_min if self.field == "min_charging_power_kw" else physical_max
            self._attr_native_value = charger.get(self.field, default)
            self._attr_available = True
        else:
            session = self.runtime.executor.session_snapshot().get(self.uid)
            current = session.get("target_current_a") if session else None
            self._attr_native_min_value = round(
                charger.get("min_charging_power_kw", physical_min), 4
            )
            self._attr_native_max_value = round(
                charger.get("max_charging_power_kw", physical_max), 4
            )
            self._attr_native_value = (
                round(current * factor, 4) if current is not None else None
            )
            self._attr_available = bool(
                charger.get("control_owner") == "multicharge"
                and charger.get("physical_commissioned") is True
                and current is not None
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
        actor = getattr(self.context, "user_id", None)
        user = await self.hass.auth.async_get_user(actor) if actor else None
        if user is None or not user.is_admin:
            raise RuntimeError("Charging power control requires an HA administrator")
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
        factor = charger["voltage_v"] * len(charger["phase_ids"]) / 1000
        minimum = charger["min_current_a"]
        step = charger.get("current_step_a")
        if factor <= 0 or not step:
            raise ValueError("CURRENT_CAPABILITY_UNVERIFIED")
        from math import isfinite
        floor_kw = charger.get("min_charging_power_kw", minimum * factor)
        ceiling_kw = charger.get(
            "max_charging_power_kw",
            min(charger["rated_power_kw"], charger["max_current_a"] * factor),
        )
        if (not isfinite(value) or value < floor_kw - 1e-6
                or value > ceiling_kw + 1e-6):
            raise ValueError("REQUESTED_POWER_OUTSIDE_VERIFIED_OPERATING_RANGE")
        # A kW target may fall between native Amp steps. Choose the closest
        # *legal* verified step in the owner's min/max envelope, then report
        # its actual accepted setpoint. Never silently clip an out-of-range
        # request or issue a raw manufacturer service call from the entity.
        from math import ceil, floor
        low = max(0, ceil((floor_kw / factor - minimum) / step - 1e-9))
        high = min(
            floor((charger["max_current_a"] - minimum) / step + 1e-9),
            floor((ceiling_kw / factor - minimum) / step + 1e-9),
        )
        if low > high:
            raise ValueError("NO_SUPPORTED_CURRENT_STEP")
        nearest = floor((float(value) / factor - minimum) / step + 0.5)
        current = round(minimum + max(low, min(high, nearest)) * step, 6)
        outcome = await self.runtime.executor.execute(
            self.uid, "set_current", current_a=current, context=self.context
        )
        if outcome["status"] != "confirmed":
            raise RuntimeError("Charging power not confirmed: " + outcome["reason"])
        self._refresh()
