"""Source-neutral HA planning runtime and the guarded one-writer command owner.

Planning alone never authorizes a physical command. Manual and quarter-slot
requests share the one guarded native executor with independent observations,
bounded history and explicit verified command outcomes.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .contracts import ChargeDemand, PowerEnvelope, PowerLimitSlot
from .configuration import configuration_revision, PLAN_COLORS
from .domain import ChargeController, Charger
from .planner import compile_plan, resolve_recurring_ready_by
from .source_evidence import (
    Evidence, binding, connection, intervals, number, session_status,
    live_power, live_price, soc_with_health,
)
from .execution import NativeSwitchExecutor

_LOGGER = logging.getLogger(__name__)


def _evidence(value):
    """Public JSON-shaped observation, never an implicit successful reading."""
    if value is None:
        return {"value": None, "quality": "unknown", "reason": "NOT_OBSERVED",
                "observed_at": None}
    return {"value": value.value, "quality": value.quality,
            "reason": value.reason,
            "observed_at": value.observed_at.isoformat() if value.observed_at else None}


class MultiChargeRuntime:
    def __init__(self, hass, configuration):
        self.hass = hass
        self.configuration = configuration
        self.assessment = None
        self.forecast_assessment = None
        self.forecast_assumptions = {}
        self.forecast_excluded = {}
        self.observations = {"chargers": {}, "assets": {}, "sources": {}}
        self.excluded = {}
        self.price_slots = ()
        self.executor = NativeSwitchExecutor(self)
        self._control_store = None
        self._save_lock = asyncio.Lock()
        self._settings_action = None
        self._listeners = set()
        self._unsubscribers = []
        self.active = True

    def native_surplus_power(self, at):
        """Compute strictly current, not forecast solar/export capacity.

        No PV generation reading alone establishes chargeable surplus. Live
        grid import/export can be interpreted only with a configured sign,
        while retained owned sessions are added back once, from real power
        readback and a confirmed internal physical session.
        """
        ctl = self.configuration["controller"]
        source_kind = ctl.get("solar_source_kind", "none")
        if source_kind not in ("grid_export", "direct_surplus"):
            return None, "NATIVE_SOLAR_NOT_SELECTED"
        if source_kind == "direct_surplus":
            source = live_power(
                self.hass, ctl.get("solar_surplus_entity"), at,
            )
            return (source.value, "OK") if source.quality == "ok" else (
                None, source.reason,
            )
        source = live_power(
            self.hass, ctl.get("grid_power_entity"), at, signed=True,
        )
        if source.quality != "ok":
            return None, source.reason
        exported = (
            -source.value if ctl.get("grid_power_direction") == "import_positive"
            else source.value
        )
        available = max(0.0, exported)
        for charger in self.configuration["chargers"]:
            if (charger.get("control_owner") != "multicharge"
                    or charger.get("physical_commissioned") is not True):
                continue
            state = self.executor._switch(
                self.hass, charger.get("control_entity"),
            )
            if state is None:
                return None, "OWNED_CHARGER_SWITCH_UNKNOWN"
            if state.state != "on":
                continue
            session = self.executor._sessions.get(charger["id"])
            if session is None:
                return None, "OWNED_CHARGER_SESSION_UNKNOWN"
            measured = live_power(
                self.hass, charger.get("power_entity"), at,
            )
            if measured.quality != "ok":
                return None, "OWNED_CHARGER_POWER_UNKNOWN"
            available += measured.value
        return round(available, 6), "OK"

    def attach_control_store(self, store, snapshot):
        self._control_store = store
        self.executor.restore_state(snapshot)
        recorded = snapshot.get("settings_action") if isinstance(snapshot, dict) else None
        if (isinstance(recorded, dict)
                and isinstance(recorded.get("expected_revision"), str)
                and recorded.get("scope") in ("controller", "asset", "charger")
                and recorded.get("action") in ("save", "create", "delete")
                and isinstance(recorded.get("requested_at"), str)):
            self._settings_action = dict(recorded)

    def settings_action_snapshot(self):
        if self._settings_action is None:
            return None
        recorded = dict(self._settings_action)
        observed_revision = configuration_revision(self.configuration)
        recorded["observed_revision"] = observed_revision
        if recorded.get("status") != "rejected":
            recorded["status"] = (
                "confirmed" if recorded["expected_revision"] == observed_revision
                else "accepted_unconfirmed"
            )
        return recorded

    def record_settings_action(self, scope, target_id, action, changes,
                               expected_revision, *, status="accepted_unconfirmed",
                               reason=None):
        self._settings_action = {
            "scope": scope, "target_id": target_id, "action": action,
            "fields": sorted(str(field) for field in changes),
            "expected_revision": expected_revision,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "reason": reason,
        }
        self.notify()

    async def persist_control_state(self):
        if self._control_store is None:
            return True  # isolated developer tests, never a production HA fallback
        try:
            async with self._save_lock:
                await self._control_store.async_save({
                    **self.executor.export_state(),
                    "settings_action": self._settings_action,
                })
            return True
        except (OSError, ValueError, RuntimeError):
            _LOGGER.exception("Failed to persist charging control evidence")
            return False

    def set_unsubscribe(self, unsubscribe):
        self._unsubscribers.append(unsubscribe)

    def subscribe(self, callback):
        self._listeners.add(callback)
        return lambda: self._listeners.discard(callback)

    def notify(self):
        for listener in tuple(self._listeners):
            listener()

    def stop(self):
        self.active = False
        self.executor.detach()
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        self._listeners.clear()

    def refresh(self, at=None):
        at = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        cfg = self.configuration
        setting = cfg["controller"]
        controller = ChargeController(
            uid=setting["id"], name=setting["name"],
            max_parallel=setting["max_parallel"],
            max_group_power_kw=setting.get("max_power_kw"),
            phase_limits_a=setting.get("phase_limits_a"),
        )
        assets = {a["id"]: a for a in cfg["assets"]}
        chargers = {}
        demands = []
        indicative_demands = []
        self.forecast_assessment = None
        self.forecast_assumptions = {}
        self.forecast_excluded = {}
        self.observations = {"chargers": {}, "assets": {}, "sources": {}}
        self.excluded = {}
        # Observe every logical asset, including unassigned assets and explicit
        # kWh/duration intents. Do not reconstruct a second OEM/vehicle truth.
        for asset in cfg["assets"]:
            recurrence = asset.get("ready_by_repeat", "none")
            saved_due = asset.get("ready_by")
            due = datetime.fromisoformat(saved_due) if saved_due else None
            reason = "ONE_OFF"
            if recurrence != "none" and (
                    due is not None or recurrence == "specific_days"):
                try:
                    due, reason = resolve_recurring_ready_by(
                        due, at, recurrence, self.hass.config.time_zone,
                        asset.get("ready_by_weekdays"),
                    )
                except (ValueError, TypeError, KeyError):
                    due, reason = None, "DEADLINE_INVALID"
            self.observations["assets"][asset["id"]] = {
                "soc": soc_with_health(
                    self.hass, asset.get("soc_entity"),
                    asset.get("soc_stale_entity"), at,
                ),
                "next_ready_by": due.isoformat() if due is not None else None,
                "deadline_quality": reason,
            }
        for configured in cfg["chargers"]:
            raw = self.executor.effective_charger(configured)
            uid = raw["id"]
            chargers[uid] = Charger(
                uid=uid, name=raw["name"], controller_uid=controller.uid,
                control_kind=raw["kind"], rated_power_kw=raw["rated_power_kw"],
                phase_count=raw.get("phase_count"),
                min_current_a=raw.get("min_current_a"),
                max_current_a=raw.get("max_current_a"),
                phase_ids=tuple(raw.get("phase_ids", ())),
                voltage_v=raw.get("voltage_v"),
                current_step_a=raw.get("current_step_a"),
                min_charging_power_kw=raw.get("min_charging_power_kw"),
                max_charging_power_kw=raw.get("max_charging_power_kw"),
                fixed_current_a=raw.get("fixed_current_a"),
                circuit_id=raw.get("circuit_id"),
                circuit_limit_a=raw.get("circuit_limit_a"),
            )
            cable = connection(
                self.hass, raw.get("connected_entity"), at,
                connected_states=raw.get("connected_states"),
                disconnected_states=raw.get("disconnected_states"),
            )
            # Observe disconnect/unknown even when this Charger is excluded
            # from planning; a later fresh connected state needs a new identity.
            self.executor.observe_connection(raw, cable)
            power = number(self.hass, raw.get("power_entity"), "power", at)
            session = session_status(self.hass, raw.get("session_entity"), at)
            self.observations["chargers"][uid] = {
                "connected": cable, "power_kw": power, "session": session,
            }
            asset = assets.get(raw.get("asset"))
            duration_without_connection = (raw["kind"] == "on_off"
                and asset is not None and asset.get("requested_duration_minutes") is not None
                and self.executor.duration_connection_allowed(cable))
            if not duration_without_connection and (
                    cable.value not in (True, False) or cable.quality != "ok"):
                self.excluded[uid] = "CONNECTION_UNCONFIRMED"
                self.forecast_excluded[uid] = "CONNECTION_UNCONFIRMED"
                continue
            disconnected = cable.quality == "ok" and cable.value is False
            if uid in self.executor._paused:
                self.excluded[uid] = "USER_PAUSED"
                self.forecast_excluded[uid] = "USER_PAUSED"
                continue
            asset = assets.get(raw.get("asset"))
            if asset is None:
                self.excluded[uid] = (
                    "DISCONNECTED" if disconnected else "NO_CHARGEABLE_ASSET"
                )
                self.forecast_excluded[uid] = "NO_ASSIGNED_ASSET"
                continue
            if (asset.get("temporary")
                    and datetime.fromisoformat(asset["expires_at"]) <= at):
                self.excluded[uid] = "TEMPORARY_ASSET_EXPIRED"
                continue
            amount = asset.get("requested_kwh")
            minutes = asset.get("requested_duration_minutes")
            budget = asset.get("requested_budget_amount")
            soc_based = amount is None and minutes is None and budget is None
            reading = self.observations["assets"][asset["id"]]["soc"]
            minimum_priority = 0.0
            low_soc_priority = 0.0
            budget_minutes = 24 * 60 if budget is not None else None
            if soc_based and (
                    asset.get("minimum_soc_pct") is not None
                    or asset.get("low_soc_trigger_pct") is not None):
                if (reading.quality != "ok"
                        or "capacity_kwh" not in asset
                        or "charge_efficiency" not in asset):
                    self.excluded[uid] = "SOC_PRIORITY_SOURCE_UNAVAILABLE"
                    continue
            if soc_based:
                if (
                    reading.quality == "ok"
                    and "target_soc" in asset
                    and "capacity_kwh" in asset
                    and "charge_efficiency" in asset
                ):
                    amount = max(
                        0.0,
                        (asset["target_soc"] - reading.value)
                        * asset["capacity_kwh"] / 100 / asset["charge_efficiency"],
                    )
                    if asset.get("minimum_soc_pct") is not None:
                        minimum_priority = min(
                            amount,
                            max(0.0, (asset["minimum_soc_pct"] - reading.value)
                                * asset["capacity_kwh"] / 100
                                / asset["charge_efficiency"]),
                        )
                    if asset.get("low_soc_trigger_pct") is not None:
                        low_soc_priority = min(
                            amount,
                            max(0.0, (asset["low_soc_trigger_pct"] - reading.value)
                                * asset["capacity_kwh"] / 100
                                / asset["charge_efficiency"]),
                        )
            ready = asset.get("ready_by")
            deadline = datetime.fromisoformat(ready) if ready else None
            repeat = asset.get("ready_by_repeat", "none")
            if repeat != "none" and (deadline is not None or repeat == "specific_days"):
                zone = getattr(getattr(self.hass, "config", None),
                               "time_zone", "UTC")
                deadline, reason = resolve_recurring_ready_by(
                    deadline, at, repeat, zone, asset.get("ready_by_weekdays")
                )
                if deadline is None:
                    self.excluded[uid] = reason
                    continue
            if amount is not None or minutes is not None or budget is not None:
                progress = self.executor.measured_intent_usage(asset, raw, deadline, at)
                if amount is not None:
                    if progress["energy_kwh"] is None:
                        self.excluded[uid] = "ASSET_MEASURED_PROGRESS_UNAVAILABLE"
                        continue
                    amount = max(0, amount - progress["energy_kwh"])
                if budget is not None:
                    if progress.get("budget_amount") is None:
                        self.excluded[uid] = "BUDGET_MEASURED_PROGRESS_UNAVAILABLE"
                        continue
                    budget = max(0, budget - progress["budget_amount"])
                    budget_minutes = max(
                        0.0, 24 * 60 - progress["duration_minutes"],
                    )
                    if progress["duration_minutes"] >= 24 * 60:
                        # A zero-cost or negative-price period cannot become
                        # an unbounded recurring budget intent.
                        budget = 0.0
                if minutes is not None:
                    if progress["duration_minutes"] is None:
                        self.excluded[uid] = "ASSET_DURATION_PROGRESS_UNAVAILABLE"
                        continue
                    minutes = max(0, minutes - progress["duration_minutes"])
                    if minutes <= 0:
                        # ChargeDemand requires strictly positive minutes.
                        # A completed finite duration is a zero-demand plan,
                        # never an exception that kills an HA refresh.
                        amount, minutes = 0.0, None
                if self.executor.intent_completed(asset, raw, deadline):
                    if budget is not None:
                        budget = 0.0
                    else:
                        amount, minutes = 0.0, None
            # Target SoC can itself have changed since the last meter
            # receipt. A priority guarantee must NEVER exceed the actually
            # remaining verified battery demand of this controller cycle.
            if amount is not None:
                minimum_priority = min(minimum_priority, amount)
                low_soc_priority = min(low_soc_priority, amount)
            assumed_arrival = (
                datetime.fromisoformat(asset["expected_connection_at"])
                if disconnected and asset.get("expected_connection_at") else None
            )
            earliest = (
                datetime.fromisoformat(asset["earliest_start_at"])
                if asset.get("earliest_start_at") else None
            )
            eligible_after = max(
                (instant for instant in (earliest, assumed_arrival)
                 if instant is not None), default=None,
            )
            request = ChargeDemand(
                asset_uid=asset["id"], charger_uid=uid,
                remaining_grid_kwh=amount, ready_by=deadline,
                priority=asset.get("priority", 0),
                continuous_charging=asset.get("continuous_charging", False),
                minimum_priority_kwh=minimum_priority,
                low_soc_priority_kwh=low_soc_priority,
                maximum_price_per_kwh=asset.get("maximum_price_per_kwh"),
                low_price_trigger_per_kwh=asset.get("low_price_trigger_per_kwh"),
                price_currency=asset.get("price_currency"),
                opportunistic_kind=asset.get("opportunistic_kind", "off"),
                opportunistic_level_pct=asset.get("opportunistic_level_pct"),
                remaining_duration_minutes=minutes,
                remaining_budget_amount=budget,
                budget_remaining_minutes=budget_minutes,
                budget_currency=(asset.get("requested_budget_currency")
                                 if budget is not None else None),
                max_power_kw=asset.get("max_charge_kw"),
                not_before=eligible_after,
            )
            inactive = raw.get("control_owner") != "multicharge" or raw.get("physical_commissioned") is not True
            if disconnected or inactive:
                if disconnected:
                    self.executor.connection_confirmation(raw, at)
                self.excluded[uid] = "DISCONNECTED" if disconnected else "CHARGER_INACTIVE"
                indicative_demands.append(request)
                self.forecast_assumptions[uid] = {
                    "asset_id": asset["id"], "charger_id": uid,
                    "assumption": (
                        "USER_EXPECTED_CONNECTION_TIME" if assumed_arrival
                        else "IF_CONNECTED_NOW" if disconnected else "IF_ACTIVATED"
                    ),
                    "assumed_connection_at": (
                        max(at, assumed_arrival).isoformat()
                        if assumed_arrival else at.isoformat()
                    ),
                    "physically_connected": cable.value if cable.quality == "ok" else None,
                    "may_execute": False,
                    "reserves_capacity": False,
                }
            else:
                if not duration_without_connection and self.executor.connection_confirmation(raw, at) is None:
                    self.excluded[uid] = "CURRENT_PLUG_ASSET_UNCONFIRMED"
                    continue
                demands.append(request)
        # Asset power reuses the Charger observation. A selected Vehicle alone
        # never proves the identity of an actively charging battery.
        sessions = self.executor.session_snapshot()
        for asset in cfg["assets"]:
            uid = asset["id"]
            assigned = next(
                (c for c in cfg["chargers"] if c.get("asset") == uid), None
            )
            readings = self.observations["assets"][uid]
            readings["power_charger_id"] = assigned["id"] if assigned else None
            power = Evidence(None, "unknown", None, "CHARGER_NOT_ASSIGNED")
            if assigned is not None:
                observed = self.observations["chargers"].get(assigned["id"], {})
                cable, source_power = observed.get("connected"), observed.get("power_kw")
                session = sessions.get(assigned["id"])
                if cable is None or cable.quality != "ok" or cable.value is not True:
                    power = Evidence(None, "unknown",
                                     cable.observed_at if cable else None,
                                     "CONNECTION_UNCONFIRMED")
                elif not session or session.get("asset_id") != uid:
                    power = Evidence(None, "unknown", None,
                                     "CHARGING_SESSION_UNCONFIRMED")
                elif source_power is None or source_power.quality != "ok":
                    power = Evidence(None, source_power.quality if source_power else "unknown",
                                     source_power.observed_at if source_power else None,
                                     source_power.reason if source_power else
                                     "POWER_SOURCE_UNAVAILABLE")
                else:
                    power = source_power
            readings["effective_power_kw"] = power
        tariff, tariff_quality = intervals(
            self.hass, setting.get("price_entity"), "price", at
        )
        if not setting.get("price_entity") and setting.get("current_price_entity"):
            candidate, quality = intervals(self.hass, setting["current_price_entity"], "price", at)
            if quality == "OK":
                tariff, tariff_quality = candidate, quality
        solar_kind = setting.get(
            "solar_source_kind", "intervals" if setting.get("solar_entity") else "none",
        )
        solar, solar_quality = (), "SOLAR_NOT_SELECTED"
        if solar_kind == "intervals":
            solar, solar_quality = intervals(
                self.hass, setting.get("solar_entity"), "solar", at
            )
        elif solar_kind in ("grid_export", "direct_surplus"):
            instant, solar_quality = self.native_surplus_power(at)
            if instant is not None:
                # A live W/kW reading cannot be tomorrow's solar forecast.
                # Only permit the immediately starting quarter; a new
                # quarter requires another fresh independent measurement.
                begin = datetime.fromtimestamp(
                    ((int(at.timestamp()) + 899) // 900) * 900,
                    timezone.utc,
                )
                if begin - at <= timedelta(minutes=2):
                    solar = (PowerLimitSlot(
                        begin, begin + timedelta(minutes=15), instant,
                    ),)
                else:
                    solar_quality = "LIVE_MEASUREMENT_NO_FUTURE_FORECAST"
        self.price_slots = tuple(tariff)
        current = [row for row in tariff if row.start <= at < row.end]
        current_price = (
            {"quality": "ok", "value": current[0].effective_price_per_kwh,
             "currency": current[0].currency, "basis": current[0].basis}
            if tariff_quality == "OK" and len(current) == 1 else
            {"quality": "unknown", "value": None, "currency": None}
        )
        external_binding = None
        binding_quality = "NOT_CONFIGURED"
        # Never ignore the pre-existing site_power_entity configuration:
        # it must meet the same versioned binding envelope semantics.
        capacity_source = setting.get("binding_entity") or setting.get(
            "site_power_entity"
        )
        if capacity_source:
            external_binding, binding_quality = binding(
                self.hass, capacity_source, at
            )
            if external_binding is None:
                # A selected but missing/invalid capacity supervisor is
                # restrictive, NEVER equivalent to no optional supervisor.
                external_binding = PowerEnvelope(
                    "unavailable", "no-grant", at, at + timedelta(hours=48),
                    "binding", (),
                )
                self.excluded["controller"] = "BINDING_CAPACITY_UNAVAILABLE"
        native_price, native_currency = live_price(
            self.hass, setting.get("current_price_entity"), at,
        )
        native_export_price, export_currency = live_price(
            self.hass, setting.get("export_price_entity"), at,
        )
        if current_price["quality"] != "ok" and native_price.quality == "ok":
            current_price = {
                "quality": "ok", "value": native_price.value,
                "currency": native_currency, "basis": "current_only",
            }
        self.observations["sources"] = {
            "tariff_quality": tariff_quality, "solar_quality": solar_quality,
            "binding_quality": binding_quality,
            "current_price": current_price,
            "solar_power": _evidence(live_power(
                self.hass, setting.get("solar_power_entity"), at,
            )),
            "home_power": _evidence(live_power(
                self.hass, setting.get("home_power_entity"), at,
            )),
            "grid_power": _evidence(live_power(
                self.hass, setting.get("grid_power_entity"), at, signed=True,
            )),
            "surplus_power": _evidence(live_power(
                self.hass, setting.get("solar_surplus_entity"), at,
            )),
            "available_solar_kw": (
                {"quality": solar_quality, "value": instant
                 if solar_kind in ("grid_export", "direct_surplus") else None}
                if solar_kind in ("grid_export", "direct_surplus")
                else {"quality": solar_quality, "value": None}
            ),
            "current_export_price": {
                **_evidence(native_export_price), "currency": export_currency,
                "basis": "current_only",
            },
        }
        # Asset-local calendar preferences restrict the ONE Controller planner.
        # No HA time automation or second executable charging calendar exists.
        active_windows = {
            charger["id"]: assets[charger["asset"]]["charging_windows"]
            for charger in cfg["chargers"]
            if charger.get("asset") in assets
            and assets[charger["asset"]].get("charging_windows")
        }
        site_zone = getattr(getattr(self.hass, "config", None),
                            "time_zone", "UTC")
        try:
            self.assessment = compile_plan(
                controller, chargers, demands, at, mode=setting["mode"],
                tariffs={uid: tariff for uid in chargers}, solar=solar,
                binding=external_binding,
                charging_windows=active_windows, site_time_zone=site_zone,
            )
            if indicative_demands and setting.get("show_indicative_forecast", True):
                # The real plan is complete FIRST; forecast slots only consume
                # leftover group, phase, circuit and parallel capacity.
                self.forecast_assessment = compile_plan(
                    controller, chargers, indicative_demands, at,
                    mode=setting["mode"],
                    tariffs={uid: tariff for uid in chargers}, solar=solar,
                    binding=external_binding,
                    reserved_slots=self.assessment.plan.slots,
                    charging_windows=active_windows, site_time_zone=site_zone,
                )
        except (ValueError, TypeError, OverflowError) as exc:
            _LOGGER.warning("MultiCharge proposal unavailable: %s", exc)
            self.assessment = None
            self.forecast_assessment = None
            self.forecast_excluded["controller"] = "INVALID_PLANNING_INPUT"
            self.excluded["controller"] = "INVALID_PLANNING_INPUT"
        self.notify()

    def charger_states(self, capabilities=None):
        """Four read-only projections of the existing source and control truth."""
        if capabilities is None:
            capabilities = self.executor.capabilities()
        states = {}
        for charger in self.configuration["chargers"]:
            uid = charger["id"]
            obs = self.observations.get("chargers", {}).get(uid, {})
            cable, power, session = (obs.get(k) for k in ("connected", "power_kw", "session"))
            connected = cable.value if cable is not None and cable.quality == "ok" else None
            measured = power.value if power is not None and power.quality == "ok" else None
            reported = session.value if session is not None and session.quality == "ok" else None
            activation = "active" if charger.get("control_owner") == "multicharge" and charger.get("physical_commissioned") is True else "inactive"
            switch = self.executor._switch(self.hass, charger.get("control_entity"))
            # Preserve conflicts as unknown rather than choose a convenient source.
            if ((connected is False and (reported in ("charging", "paused") or
                                         measured is not None and measured > 0.05))
                    or (reported in ("paused", "stopped", "completed", "idle", "inactive")
                        and measured is not None and measured > 0.05)):
                activity = "unknown"
            elif reported == "charging" or (measured is not None and measured > 0.05):
                activity = "charging"
            elif reported == "paused":
                activity = "paused"
            elif (reported in ("stopped", "completed", "idle", "inactive")
                  or connected is False or (measured is not None and measured <= 0.05)):
                activity = "stopped"
            else:
                activity = "unknown"
            capability = capabilities.get(uid, {})
            goal_reason = (capability.get("reason") if charger.get("asset") is not None
                           else capability.get("manual_one_off_reason"))
            if reported == "fault":
                readiness, reason = "error", "CHARGER_REPORTED_FAULT"
            elif reported == "unavailable" or (charger.get("control_entity") and switch is None and activation == "active"):
                readiness, reason = "unavailable", "CHARGER_SOURCE_UNAVAILABLE"
            elif activation == "active" and capability.get("paused"):
                readiness, reason = "waiting", "USER_PAUSED"
            elif activation == "active" and goal_reason in ("CONTROL_STATE_UNVERIFIED", "PREVIOUS_COMMAND_UNCONFIRMED"):
                readiness, reason = "unknown", goal_reason
            elif reported == "paused":
                readiness, reason = "waiting", session.reason if session.reason != "OK" else "PROVIDER_SUSPENDED"
            elif (switch is not None or reported in ("charging", "stopped", "idle", "completed")
                  or (measured is not None and measured > 0.05)):
                if activation == "active" and connected is True and goal_reason in (
                    "TARGET_ALREADY_MET", "MAX_PARALLEL_REACHED", "SITE_CAPACITY_EXCEEDED",
                    "CHARGING_WINDOW_CLOSED", "EARLIEST_START_NOT_REACHED",
                    "NATIVE_SOLAR_SURPLUS_INSUFFICIENT", "AUTOMATIC_MODE_NOT_ENABLED",
                ) and goal_reason != "TARGET_ALREADY_MET":
                    readiness, reason = "waiting", goal_reason
                else:
                    readiness, reason = "ready", "EQUIPMENT_OBSERVED"
            else:
                readiness, reason = "unknown", "NOT_OBSERVED"
            states[uid] = {
                "activation": activation,
                "connection_state": ("asset_connected" if connected is True else
                                     "no_asset_connected" if connected is False else "unknown"),
                "connection_basis": ("user_confirmed" if cable is not None
                                     and cable.reason == "USER_CONFIRMED_CONNECTION"
                                     else "source_observed" if connected is not None else "unknown"),
                "charging_session": activity,
                "charging_state": readiness,
                "reason": reason,
                "goal_reason": goal_reason,
                "switch_state": switch.state if switch is not None else None,
            }
        return states

    def live_state(self):
        """Near-real-time controller projection from native source and command evidence.

        All counts are unknown if any required physical source is unavailable.
        Never count an unknown or unplugged charger as zero measured power.
        """
        chargers = self.configuration["chargers"]
        observations = self.observations.get("chargers", {})
        cables = [observations.get(c["id"], {}).get("connected") for c in chargers]
        powers = [observations.get(c["id"], {}).get("power_kw") for c in chargers]
        cable_ok = all(item is not None and item.quality == "ok" for item in cables)
        power_ok = all(item is not None and item.quality == "ok" for item in powers)
        outcomes = self.executor.snapshot()
        actions = sorted(
            outcomes.values(),
            key=lambda row: (row.get("requested_at") or "", row.get("request_id") or ""),
        )
        pending = any(
            r.get("status") in ("requested", "accepted_unconfirmed")
            for r in actions
        )
        unresolved_restart = (
            not self.executor._persistence_verified or bool(
                self.executor._inflight and not self.executor.session_snapshot()
                and not pending
            )
        )
        command_status = (
            "hold" if unresolved_restart
            else "unconfirmed" if any(r.get("status") == "execution_unknown" for r in actions)
            else "pending" if pending
            else "rejected" if any(r.get("status") == "rejected" for r in actions)
            else "confirmed" if actions else "idle"
        )
        return {
            "configured_chargers": len(chargers),
            "connected_chargers": sum(int(e.value is True) for e in cables) if cable_ok else None,
            "charging_chargers": sum(int(e.value > 0.05) for e in powers) if power_ok else None,
            "actual_power_kw": round(sum(e.value for e in powers), 6) if power_ok else None,
            "observed_power_subtotal_kw": (round(sum(e.value for e in powers if e is not None
                                                       and e.quality == "ok"), 6)
                                           if any(e is not None and e.quality == "ok" for e in powers)
                                           else None),
            "observed_power_chargers": sum(e is not None and e.quality == "ok" for e in powers),
            "connection_quality": "ok" if cable_ok else "unknown",
            "power_quality": "ok" if power_ok else "unknown",
            "mode": self.configuration["controller"]["mode"],
            "configuration_revision": configuration_revision(self.configuration),
            "last_action": dict(actions[-1]) if actions else None,
            "action_health": command_status,
            "command_outcomes": outcomes,
            "settings_action": self.settings_action_snapshot(),
        }

    def summary(self):
        assessment = self.assessment
        if assessment is None:
            return {"status": "unavailable", "reason": "INVALID_PLANNING_INPUT"}
        return {
            "status": assessment.plan.status,
            "forecast_status": (
                self.forecast_assessment.plan.status
                if self.forecast_assessment else "not_available"
            ),
            "forecast_assumptions": dict(self.forecast_assumptions),
            "forecast_kwh_by_charger": (
                dict(self.forecast_assessment.proposed_kwh)
                if self.forecast_assessment else {}
            ),
            "forecast_reasons": {
                **self.forecast_excluded,
                **(self.forecast_assessment.reasons
                   if self.forecast_assessment else {}),
            },
            "live": self.live_state(),
            "revision": assessment.plan.revision,
            "generated_at": assessment.plan.generated_at.isoformat(),
            "reason_by_charger": {**self.excluded, **assessment.reasons},
            "planned_kwh_by_charger": dict(assessment.proposed_kwh),
            "shortfall_kwh_by_charger": dict(assessment.shortfall_kwh),
            "coverage_by_charger": dict(assessment.coverage),
            "strategy_by_charger": dict(assessment.strategy),
            "read_only": True,
            "physical_actuation_authorized": any(
                x["start_allowed"] or x["stop_allowed"]
                for x in self.executor.capabilities().values()
            ),
            "command_outcomes": self.executor.snapshot(),
            "active_sessions": self.executor.session_snapshot(),
            "completed_sessions": self.executor.completed_sessions(),
            "accepted_slots": [{
                **row, "start": row["start"].isoformat(),
                "end": row["end"].isoformat(),
            } for row in self.executor.accepted_slots().values()],
        }

    def read_plan(self, start: datetime, end: datetime, *,
                  charger_id: str | None = None, asset_id: str | None = None):
        """Bounded, read-only, versioned plan for native HA consumers.

        No future observed power/energy, copied currency valuation or
        implicit execution authority is advertised.
        """
        if (start.tzinfo is None or start.utcoffset() is None
                or end.tzinfo is None or end.utcoffset() is None):
            raise ValueError("aware interval required")
        first, last = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
        if not first < last or last - first > timedelta(hours=49):
            raise ValueError("plan query must be a positive interval <=49h (two real civil days)")
        if charger_id is not None and not any(
            c["id"] == charger_id for c in self.configuration["chargers"]
        ):
            raise ValueError("unknown charger")
        if asset_id is not None and not any(
            a["id"] == asset_id for a in self.configuration["assets"]
        ) and not any(
            receipt["asset_id"] == asset_id
            for receipt in self.executor.completed_sessions()
        ):
            raise ValueError("unknown asset")
        assessment = self.assessment
        slots = []
        if assessment is not None:
            for slot in assessment.plan.slots:
                if slot.start >= last or slot.end <= first:
                    continue
                if charger_id is not None and slot.charger_uid != charger_id:
                    continue
                if asset_id is not None and slot.asset_uid != asset_id:
                    continue
                slots.append({
                    "charger_id": slot.charger_uid,
                    "asset_id": slot.asset_uid,
                    "start": slot.start.isoformat(),
                    "end": slot.end.isoformat(),
                    "proposed_power_kw": slot.power_kw,
                    "proposed_current_a": slot.current_a,
                    "proposed_energy_kwh": round(
                        slot.power_kw * (slot.end - slot.start).total_seconds() / 3600, 6
                    ),
                    "accepted_power_kw": None,
                    "actual_power_kw": None,
                    "actual_energy_kwh": None,
                })
        # Accepted slots are admitted physical history, not an inferred plan.
        for accepted in self.executor.accepted_slots().values():
            if accepted["start"] >= last or accepted["end"] <= first:
                continue
            if charger_id is not None and accepted["charger_id"] != charger_id:
                continue
            if asset_id is not None and accepted["asset_id"] != asset_id:
                continue
            match = next((row for row in slots if
                row["charger_id"] == accepted["charger_id"]
                and row["start"] == accepted["start"].isoformat()), None)
            if match is None:
                match = {
                    "charger_id": accepted["charger_id"],
                    "asset_id": accepted["asset_id"],
                    "start": accepted["start"].isoformat(),
                    "end": accepted["end"].isoformat(),
                    "proposed_power_kw": None,
                    "proposed_energy_kwh": None,
                    "proposed_current_a": None,
                    "actual_power_kw": None,
                    "actual_energy_kwh": None,
                }
                slots.append(match)
            match["accepted_power_kw"] = accepted["power_kw"]
            match["accepted_current_a"] = accepted["current_a"]
        slots.sort(key=lambda row: (row["start"], row["charger_id"]))
        forecast_slots = []
        if self.forecast_assessment is not None:
            for forecast in self.forecast_assessment.plan.slots:
                if forecast.start >= last or forecast.end <= first:
                    continue
                if charger_id is not None and charger_id != forecast.charger_uid:
                    continue
                if asset_id is not None and asset_id != forecast.asset_uid:
                    continue
                forecast_slots.append({
                    "charger_id": forecast.charger_uid,
                    "asset_id": forecast.asset_uid,
                    "start": forecast.start.isoformat(),
                    "end": forecast.end.isoformat(),
                    "indicative_power_kw": forecast.power_kw,
                    "indicative_current_a": forecast.current_a,
                    "indicative_energy_kwh": round(
                        forecast.power_kw * (
                            forecast.end - forecast.start
                        ).total_seconds() / 3600, 6
                    ),
                    "status": "indicative_only",
                    "may_execute": False,
                    "reserves_capacity": False,
                    "assumption": self.forecast_assumptions[forecast.charger_uid]["assumption"],
                })
        history = [
            receipt for receipt in self.executor.completed_sessions()
            if datetime.fromisoformat(receipt["started_at"]) < last
            and datetime.fromisoformat(receipt["ended_at"]) >= first
            and (charger_id is None or receipt["charger_id"] == charger_id)
            and (asset_id is None or receipt["asset_id"] == asset_id)
        ]
        capabilities = self.executor.capabilities()
        return {
            "schema_major": 1,
            "plan_palette": dict(PLAN_COLORS),
            "live": self.live_state(),
            "configuration_revision": configuration_revision(self.configuration),
            "controller_id": self.configuration["controller"]["id"],
            "revision": assessment.plan.revision if assessment else None,
            "generated_at": (
                assessment.plan.generated_at.isoformat() if assessment else None
            ),
            "valid_until": (
                (assessment.plan.generated_at + timedelta(minutes=2)).isoformat()
                if assessment else None
            ),
            "timezone": getattr(
                getattr(self.hass, "config", None), "time_zone", "UTC"
            ),
            "quality": dict(self.observations.get("sources", {})),
            "shortfall_kwh": (
                dict(assessment.shortfall_kwh) if assessment else {}
            ),
            "start": first.isoformat(),
            "end": last.isoformat(),
            "status": assessment.plan.status if assessment else "unavailable",
            "coverage": dict(assessment.coverage) if assessment else {},
            "strategy_by_charger": dict(assessment.strategy) if assessment else {},
            "reasons": {**self.excluded, **assessment.reasons} if assessment else dict(self.excluded),
            "slots": slots,
            "forecast_slots": forecast_slots,
            "forecast_status": (
                self.forecast_assessment.plan.status
                if self.forecast_assessment else "not_available"
            ),
            "forecast_assumptions": {
                uid: dict(meta) for uid, meta in self.forecast_assumptions.items()
                if (charger_id is None or uid == charger_id)
                and (asset_id is None or meta["asset_id"] == asset_id)
            },
            "forecast_reasons": {
                **self.forecast_excluded,
                **(self.forecast_assessment.reasons
                   if self.forecast_assessment else {}),
            },
            "command_outcomes": self.executor.snapshot(),
            "command_capabilities": capabilities,
            "charger_states": self.charger_states(capabilities),
            "connection_identity": {
                c["id"]: self.executor.connection_confirmation(c, datetime.now(timezone.utc))
                for c in self.configuration["chargers"]
            },
            "active_sessions": self.executor.session_snapshot(),
            "completed_sessions": history,
            "price_slots": [
                {"start": row.start.isoformat(), "end": row.end.isoformat(),
                 "price_per_kwh": row.effective_price_per_kwh,
                 "currency": row.currency, "basis": row.basis}
                for row in self.price_slots
                if row.start < last and row.end > first
            ],
            "configuration": self.configuration,
            "observations": {
                "assets": {
                    uid: {
                        "soc": _evidence(readings.get("soc")),
                        "next_ready_by": readings.get("next_ready_by"),
                        "deadline_quality": readings.get("deadline_quality"),
                        "effective_power_kw": _evidence(readings.get("effective_power_kw")),
                        "power_charger_id": readings.get("power_charger_id"),
                    }
                    for uid, readings in self.observations.get("assets", {}).items()
                },
                "chargers": {
                    uid: {
                        "connected": _evidence(readings.get("connected")),
                        "power_kw": _evidence(readings.get("power_kw")),
                        "session": _evidence(readings.get("session")),
                    }
                    for uid, readings in self.observations.get("chargers", {}).items()
                },
                "sources": dict(self.observations.get("sources", {})),
            },
            "read_only": True,
            "physical_actuation_authorized": any(
                x["start_allowed"] or x["stop_allowed"]
                for x in self.executor.capabilities().values()
            ),
        }
