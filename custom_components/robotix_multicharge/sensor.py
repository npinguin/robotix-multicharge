"""Native source-neutral logical HA entities for charging status and evidence.

All measurements originate from explicitly selected source devices. We do not
copy their identities, reparent devices or assert physical command ownership.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .source_evidence import number

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
    for field in ("mode", "configuration_revision", "connected_chargers",
                  "charging_chargers", "action_health", "last_action",
                  "last_settings_action"):
        entities.append(_ControllerLiveSensor(cfg["controller"], runtime, field))
    entities.append(
        _LogicalEvidenceSensor("controller", cfg["controller"], runtime, "power")
    )
    for asset in cfg["assets"]:
        entities.append(_LogicalEvidenceSensor("asset", asset, runtime, "soc"))
        entities.append(_AssetIntentSensor(asset, runtime))
    for charger in cfg["chargers"]:
        entities.append(_LogicalEvidenceSensor("charger", charger, runtime, "power"))
        entities.append(_LogicalEvidenceSensor("charger", charger, runtime, "connected"))
        entities.append(_CommandStatusSensor(charger, runtime))
        entities.append(_ChargerAssignmentSensor(charger, runtime))
        if charger.get("kind") == "variable_current":
            entities.append(_ChargerCurrentSensor(charger, runtime, "setpoint"))
            entities.append(_ChargerCurrentSensor(charger, runtime, "actual"))
        if charger.get("energy_entity"):
            entities.append(_LogicalSessionEnergySensor(charger, runtime))
            entities.append(_LastSessionEnergySensor(charger, runtime))
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



class _CommandStatusSensor(_NativeMultiChargeSensor):
    """Logical outcome, never an optimistic reflection of a service call."""
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, charger: dict, runtime) -> None:
        super().__init__("charger", charger, runtime)
        self._attr_name = "Command status"
        self._attr_unique_id = f"{DOMAIN}:charger:{charger['id']}:command_status"
        self._update_value()

    def _update_value(self):
        result = self.runtime.executor.snapshot().get(self.data["id"])
        self._attr_native_value = result.get("status") if result else "not_requested"
        self._attr_extra_state_attributes = {
            "reason": result.get("reason") if result else None,
            "request_id": result.get("request_id") if result else None,
            "physical_readback_at": result.get("readback_at") if result else None,
        }


class _LastSessionEnergySensor(_NativeMultiChargeSensor):
    """Latest persistently measured session, separate from active meter reading."""
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = "kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, charger: dict, runtime) -> None:
        super().__init__("charger", charger, runtime)
        self._attr_name = "Last session energy"
        self._attr_unique_id = f"{DOMAIN}:charger:{charger['id']}:last_session_energy"
        self._update_value()

    def _update_value(self):
        rows = [
            r for r in self.runtime.executor.completed_sessions()
            if r["charger_id"] == self.data["id"]
        ]
        last = rows[-1] if rows else None
        self._attr_native_value = last["actual_energy_kwh"] if last else None
        self._attr_extra_state_attributes = {
            "quality": last["energy_quality"] if last else "unknown",
            "asset_id": last["asset_id"] if last else None,
            "ended_at": last["ended_at"] if last else None,
            "cost": last["cost"] if last else None,
            "currency": last["currency"] if last else None,
            "cost_quality": last["cost_quality"] if last else "unknown",
        }



class _ControllerLiveSensor(_NativeMultiChargeSensor):
    """Controller-level HA status, sourced from the same live native evidence."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, controller: dict, runtime, field: str) -> None:
        super().__init__("controller", controller, runtime)
        self.field = field
        self._attr_name = {
            "mode": "Charging mode",
            "configuration_revision": "Settings revision",
            "connected_chargers": "Connected chargers",
            "charging_chargers": "Charging chargers",
            "action_health": "Action health",
            "last_action": "Last physical action",
            "last_settings_action": "Last settings action",
        }[field]
        self._attr_unique_id = f"{DOMAIN}:controller:{controller['id']}:{field}"
        self._update_value()

    def _update_value(self):
        live = self.runtime.live_state()
        if self.field == "connected_chargers":
            quality = live["connection_quality"]
        elif self.field == "charging_chargers":
            quality = live["power_quality"]
        elif self.field in ("mode", "configuration_revision"):
            quality = "configured"
        elif self.field == "last_settings_action":
            quality = ("observed" if live["settings_action"] is not None
                       else "not_requested")
        elif self.field == "action_health" and live["action_health"] in (
            "hold", "unconfirmed"
        ):
            quality = "unconfirmed"
        else:
            quality = "observed" if live["last_action"] is not None else "not_requested"
        self._attr_extra_state_attributes = {"quality": quality}
        if self.field == "last_settings_action":
            setting = live["settings_action"]
            self._attr_native_value = setting["action"] if setting else "none"
            self._attr_extra_state_attributes.update({
                "scope": setting.get("scope") if setting else None,
                "target_id": setting.get("target_id") if setting else None,
                "fields": setting.get("fields") if setting else None,
                "status": setting.get("status") if setting else None,
                "requested_at": setting.get("requested_at") if setting else None,
                "expected_revision": setting.get("expected_revision") if setting else None,
                "observed_revision": setting.get("observed_revision") if setting else None,
            })
        elif self.field == "last_action":
            action = live["last_action"]
            self._attr_native_value = action["action"] if action else "none"
            self._attr_extra_state_attributes.update({
                "charger_id": action.get("charger_id") if action else None,
                "status": action.get("status") if action else None,
                "reason": action.get("reason") if action else None,
                "requested_at": action.get("requested_at") if action else None,
                "readback_at": action.get("readback_at") if action else None,
                "request_id": action.get("request_id") if action else None,
                "measured_power_kw": action.get("measured_power_kw") if action else None,
            })
        else:
            self._attr_native_value = live[self.field]
        if self.field == "configuration_revision":
            ctl = self.runtime.configuration["controller"]
            self._attr_extra_state_attributes.update({
                "mode": ctl.get("mode"),
                "max_parallel": ctl.get("max_parallel"),
                "site_max_power_kw": ctl.get("max_power_kw"),
                "phase_limits_a": ctl.get("phase_limits_a"),
                "source": "native_config_entry",
                "assignments": {
                    c["id"]: c.get("asset")
                    for c in self.runtime.configuration["chargers"]
                },
                "asset_intentions": {
                    asset["id"]: {
                        "requested_kwh": asset.get("requested_kwh"),
                        "duration_minutes": asset.get("requested_duration_minutes"),
                        "target_soc": asset.get("target_soc"),
                        "ready_by": asset.get("ready_by"),
                        "priority": asset.get("priority", 0),
                    }
                    for asset in self.runtime.configuration["assets"]
                },
            })
        if self.field == "action_health":
            self._attr_extra_state_attributes.update({
                "confirmed_count": sum(
                    r.get("status") == "confirmed"
                    for r in live["command_outcomes"].values()
                ),
                "pending_count": sum(
                    r.get("status") == "requested"
                    for r in live["command_outcomes"].values()
                ),
                "unconfirmed_count": sum(
                    r.get("status") == "execution_unknown"
                    for r in live["command_outcomes"].values()
                ),
                "last_charger_id": (
                    live["last_action"]["charger_id"]
                    if live["last_action"] is not None else None
                ),
                "by_charger": {
                    uid: {
                        "action": outcome.get("action"),
                        "status": outcome.get("status"),
                        "reason": outcome.get("reason"),
                        "requested_at": outcome.get("requested_at"),
                        "readback_at": outcome.get("readback_at"),
                    }
                    for uid, outcome in live["command_outcomes"].items()
                },
                "confirmed_current_a_by_charger": {
                    uid: session.get("target_current_a")
                    for uid, session in self.runtime.executor.session_snapshot().items()
                    if session.get("target_current_a") is not None
                },
            })


class _ChargerAssignmentSensor(_NativeMultiChargeSensor):
    """Authoritative saved assignment; NEVER implies an identified plugged car."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, charger: dict, runtime) -> None:
        super().__init__("charger", charger, runtime)
        self._attr_name = "Selected vehicle"
        self._attr_unique_id = f"{DOMAIN}:charger:{charger['id']}:selected_vehicle"
        self._update_value()

    def _update_value(self):
        current = next(
            (c for c in self.runtime.configuration["chargers"]
             if c["id"] == self.data["id"]), self.data
        )
        self._attr_native_value = current.get("asset") or "none"
        connected = self.runtime.observations.get("chargers", {}).get(
            self.data["id"], {}
        ).get("connected")
        self._attr_extra_state_attributes = {
            "association": "saved_preference_not_vehicle_proof",
            "connection": (
                "connected" if connected.value is True else "disconnected"
                if connected.value is False else "unknown"
            ) if connected is not None and connected.quality == "ok" else "unknown",
            "connection_quality": connected.quality if connected else "unknown",
        }


class _AssetIntentSensor(_NativeMultiChargeSensor):
    """Asset-owned charging needs, unchanged when a physical Charger is reselected."""

    def __init__(self, asset: dict, runtime) -> None:
        super().__init__("asset", asset, runtime)
        self._attr_name = "Charging intention"
        self._attr_unique_id = f"{DOMAIN}:asset:{asset['id']}:intent"
        self._update_value()

    def _update_value(self):
        current = next(
            (a for a in self.runtime.configuration["assets"]
             if a["id"] == self.data["id"]), self.data
        )
        assigned = next(
            (c["id"] for c in self.runtime.configuration["chargers"]
             if c.get("asset") == current["id"]), None
        )
        if current.get("requested_kwh") is not None:
            status = "energy"
        elif current.get("requested_duration_minutes") is not None:
            status = "duration"
        elif current.get("target_soc") is not None:
            status = "target_soc"
        else:
            status = "unconfigured"
        self._attr_native_value = status
        self._attr_extra_state_attributes = {
            "selected_charger_id": assigned,
            "requested_kwh": current.get("requested_kwh"),
            "requested_duration_minutes": current.get("requested_duration_minutes"),
            "target_soc": current.get("target_soc"),
            "ready_by": current.get("ready_by"),
            "priority": current.get("priority", 0),
            "temporary": current.get("temporary", False),
            "expires_at": current.get("expires_at"),
            "connection_verified": False,  # saved assignment is not plug identity
        }


class _ChargerCurrentSensor(_NativeMultiChargeSensor):
    """Separate native HA numeric setpoint and source-confirmed actual current."""

    _attr_native_unit_of_measurement = "A"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, charger: dict, runtime, metric: str) -> None:
        super().__init__("charger", charger, runtime)
        if metric not in ("setpoint", "actual"):
            raise ValueError("unsupported charger current metric")
        self.metric = metric
        self._attr_name = (
            "Confirmed current setpoint" if metric == "setpoint"
            else "Actual current"
        )
        self._attr_unique_id = (
            f"{DOMAIN}:charger:{charger['id']}:"
            f"{'confirmed_current' if metric == 'setpoint' else 'actual_current'}"
        )
        self._update_value()

    def _update_value(self):
        session = self.runtime.executor.session_snapshot().get(self.data["id"])
        setpoint = session.get("target_current_a") if session else None
        source_id = self.data.get("current_readback_entity")
        actual = number(
            self.runtime.hass, source_id, "current", datetime.now(timezone.utc)
        )
        self._attr_native_value = (
            setpoint if self.metric == "setpoint"
            else actual.value if actual.quality == "ok" else None
        )
        self._attr_extra_state_attributes = {
            "confirmed_setpoint_a": setpoint,
            "physical_current_a": actual.value if actual.quality == "ok" else None,
            "readback_quality": actual.quality,
            "readback_at": actual.observed_at.isoformat()
            if actual.observed_at is not None else None,
            "source_entity_id": source_id,
            "session_confirmed": session is not None,
            "metric": self.metric,
        }
