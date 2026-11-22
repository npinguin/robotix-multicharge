"""Native source-neutral logical HA entities for charging status and evidence.

All measurements originate from explicitly selected source devices. We do not
copy their identities, reparent devices or assert physical command ownership.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    cfg = runtime.configuration
    entities = [_LogicalReadinessSensor("controller", cfg["controller"], runtime)]
    entities.extend(
        _LogicalReadinessSensor("asset", row, runtime) for row in cfg["assets"]
    )
    entities.extend(
        _LogicalReadinessSensor("charger", row, runtime) for row in cfg["chargers"]
    )
    entities.append(_PlanStatusSensor(cfg["controller"], runtime))
    entities.append(
        _LogicalEvidenceSensor("controller", cfg["controller"], runtime, "power")
    )
    for asset in cfg["assets"]:
        entities.append(_LogicalEvidenceSensor("asset", asset, runtime, "soc"))
    for charger in cfg["chargers"]:
        entities.append(_LogicalEvidenceSensor("charger", charger, runtime, "power"))
        entities.append(_LogicalEvidenceSensor("charger", charger, runtime, "connected"))
        if charger.get("energy_entity"):
            entities.append(_LogicalSessionEnergySensor(charger, runtime))
    async_add_entities(entities)


class _NativeMultiChargeSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, kind: str, data: dict, runtime) -> None:
        self.kind = kind
        self.data = data
        self.runtime = runtime
        self._unsubscribe = None
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

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._unsubscribe = self.runtime.subscribe(self._refresh)
        self._refresh()

    @callback
    def _refresh(self):
        self._update_value()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        await super().async_will_remove_from_hass()

    def _update_value(self):
        raise NotImplementedError


class _LogicalReadinessSensor(_NativeMultiChargeSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, kind: str, data: dict, runtime) -> None:
        super().__init__(kind, data, runtime)
        self._attr_name = "Readiness"
        self._attr_unique_id = f"{DOMAIN}:{kind}:{data['id']}:readiness"
        self._update_value()

    def _update_value(self):
        outcomes = self.runtime.executor.snapshot()
        caps = self.runtime.executor.capabilities()
        active = [
            uid for uid, cap in caps.items()
            if cap["start_allowed"] or cap["stop_allowed"]
        ]
        confirmed = outcomes.get(self.data["id"], {}).get("status") == "confirmed"
        if self.kind == "controller":
            status = "manual_controls_available" if active else "not_commissioned"
            operational = any(row.get("status") == "confirmed" for row in outcomes.values())
        elif self.kind == "charger":
            cap = caps.get(self.data["id"], {})
            if confirmed:
                obs = self.runtime.observations.get("chargers", {}).get(self.data["id"], {})
                power = obs.get("power_kw")
                operational = bool(power is not None and power.quality == "ok")
                status = "physical_readback_confirmed" if operational else "readback_stale"
            elif cap.get("start_allowed") or cap.get("stop_allowed"):
                status = "manual_controls_available"
                operational = False
            else:
                status = "not_commissioned" if self.data.get("physical_commissioned") is not True else "unavailable"
                operational = False
        else:
            obs = self.runtime.observations.get("assets", {}).get(self.data["id"], {})
            soc = obs.get("soc")
            status = (
                "source_observed" if soc is not None and soc.quality == "ok"
                else "demand_configured" if (
                    self.data.get("requested_kwh") is not None
                    or self.data.get("requested_duration_minutes") is not None
                )
                else "needs_input"
            )
            operational = False
        self._attr_native_value = status
        assessment = self.runtime.assessment
        self._attr_extra_state_attributes = {
            "logical_id": self.data["id"],
            "concept": self._attr_device_info["model"],
            "operational": operational,
            "planning_status": (
                assessment.plan.status if assessment is not None else "unavailable"
            ),
            "command_outcome": outcomes.get(self.data["id"]),
        }


class _PlanStatusSensor(_NativeMultiChargeSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, controller: dict, runtime) -> None:
        super().__init__("controller", controller, runtime)
        self._attr_name = "Plan status"
        self._attr_unique_id = f"{DOMAIN}:controller:{controller['id']}:plan_status"
        self._update_value()

    def _update_value(self):
        summary = self.runtime.summary()
        self._attr_native_value = summary["status"]
        self._attr_extra_state_attributes = {
            "mode": self.runtime.configuration["controller"]["mode"],
            "revision": summary.get("revision"),
            "reason_by_charger": summary.get("reason_by_charger", {}),
            "coverage_by_charger": summary.get("coverage_by_charger", {}),
            "strategy_by_charger": summary.get("strategy_by_charger", {}),
            "planned_kwh_by_charger": summary.get("planned_kwh_by_charger", {}),
            "read_only": True,
            "physical_actuation_authorized": summary.get(
                "physical_actuation_authorized", False
            ),
            "command_outcomes": summary.get("command_outcomes", {}),
        }


class _LogicalEvidenceSensor(_NativeMultiChargeSensor):
    """Quality-gated live value. Missing/stale is unknown, never measured zero."""

    def __init__(self, kind: str, data: dict, runtime, property_name: str) -> None:
        super().__init__(kind, data, runtime)
        self.property_name = property_name
        names = {"power": "Actual power", "soc": "Battery level",
                 "connected": "Connection"}
        self._attr_name = names[property_name]
        self._attr_unique_id = (
            f"{DOMAIN}:{kind}:{data['id']}:{property_name}"
        )
        if property_name == "power":
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif property_name == "soc":
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        self._update_value()

    def _update_value(self):
        source_name = None
        observation = None
        if self.kind == "controller":
            # Only report a site total when every configured Charger is
            # independently measured with qualified fresh power.
            raw = list(self.runtime.observations.get("chargers", {}).values())
            if raw and len(raw) == len(self.runtime.configuration["chargers"]):
                values = [row.get("power_kw") for row in raw]
                if all(e is not None and e.quality == "ok" for e in values):
                    self._attr_native_value = round(
                        sum(e.value for e in values), 6
                    )
                    self._attr_extra_state_attributes = {
                        "quality": "ok", "coverage": "all_configured_chargers"
                    }
                    return
            self._attr_native_value = None
            self._attr_extra_state_attributes = {
                "quality": "unknown", "coverage": "incomplete"
            }
            return
        if self.kind == "asset":
            observation = self.runtime.observations.get("assets", {}).get(
                self.data["id"], {}
            ).get("soc")
            source_name = self.data.get("soc_entity")
        elif self.kind == "charger":
            readings = self.runtime.observations.get("chargers", {}).get(
                self.data["id"], {}
            )
            observation = readings.get(
                "connected" if self.property_name == "connected" else "power_kw"
            )
            source_name = self.data.get(
                "connected_entity" if self.property_name == "connected"
                else "power_entity"
            )

        self._attr_native_value = None
        if observation is not None and observation.quality == "ok":
            if self.property_name == "connected":
                self._attr_native_value = (
                    "connected" if observation.value else "disconnected"
                )
            else:
                self._attr_native_value = observation.value
        self._attr_extra_state_attributes = {
            "quality": observation.quality if observation else "unknown",
            "reason": observation.reason if observation else "SOURCE_NOT_SELECTED",
            "observed_at": (
                observation.observed_at.isoformat()
                if observation is not None and observation.observed_at else None
            ),
            "source_entity_id": source_name,
        }


class _LogicalSessionEnergySensor(_NativeMultiChargeSensor):
    """Recorder-backed actual kWh for a confirmed active physical charge session.

    This is NOT a lifetime meter duplicate. No active qualified session means
    unavailable, not zero. HA Recorder owns the historic observations.
    """
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = "kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, charger: dict, runtime) -> None:
        super().__init__("charger", charger, runtime)
        self._attr_name = "Session energy"
        self._attr_unique_id = f"{DOMAIN}:charger:{charger['id']}:session_energy"
        self._update_value()

    def _update_value(self):
        session = self.runtime.executor.session_snapshot().get(self.data["id"])
        self._attr_native_value = (
            session["actual_energy_kwh"]
            if session is not None else None
        )
        self._attr_extra_state_attributes = {
            "quality": "measured" if (
                session is not None and session["actual_energy_kwh"] is not None
            ) else "unknown",
            "asset_id": session["asset_id"] if session else None,
            "started_at": session["started_at"] if session else None,
            "meter_source": self.data.get("energy_entity"),
        }
