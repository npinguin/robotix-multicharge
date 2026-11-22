"""Real native HA switch START/STOP, strict admission and physical readback.

Only explicitly selected switch entities can be controlled. External EVSC
ownership remains the default. Hardware cutover and commissioning are not
implied by passing software tests.
"""
from __future__ import annotations

import asyncio
import logging
from math import isfinite
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .source_evidence import binding, connection, number
from .planner import resolve_recurring_ready_by

_LOGGER = logging.getLogger(__name__)
START_POWER_KW = 0.10
STOP_POWER_KW = 0.05
READBACK_SECONDS = 45


class NativeSwitchExecutor:
    """Serialized physical command path for one controller, never a second planner."""

    def __init__(self, runtime):
        self.runtime = runtime
        self._lock = asyncio.Lock()
        self._outcomes = {}
        self._requests = {}
        self._quarantine = set()
        self._stopped = False
        self._supervising = False
        self._sessions = {}
        self._start_pending = set()
        self._accepted = {}
        self._accepted_history = {}
        self._grants = {}
        self._last_advance = None
        self._completed = {}

    def detach(self):
        """Do not replay commands on unload or a restarted runtime."""
        self._stopped = True

    def snapshot(self):
        return {uid: dict(record) for uid, record in self._outcomes.items()}

    def session_snapshot(self):
        """Only observed active sessions. ISO timestamps allow native HA consumers."""
        return {
            uid: {
                key: value.isoformat() if isinstance(value, datetime) else value
                for key, value in record.items()
            }
            for uid, record in self._sessions.items()
        }

    def accepted_slots(self):
        """Actual admitted slots only, never future proposals masquerading as execution."""
        threshold = datetime.now(timezone.utc) - timedelta(hours=48)
        return {
            key: dict(value) for key, value in self._accepted_history.items()
            if value["end"] >= threshold
        }

    def capabilities(self):
        """Expose exact current action eligibility; no optimistic UI guessing."""
        result = {}
        at = datetime.now(timezone.utc)
        for charger in self.runtime.configuration["chargers"]:
            uid = charger["id"]
            if self._stopped:
                reason = "INTEGRATION_UNLOADED"
            elif charger.get("kind") not in ("on_off", "variable_current"):
                reason = "CHARGER_CONTROL_UNSUPPORTED"
            elif not str(charger.get("control_entity", "")).startswith("switch."):
                reason = "NATIVE_SWITCH_REQUIRED"
            elif charger.get("control_owner", "external") != "multicharge":
                reason = "EXTERNAL_WRITER_OWNS_CHARGER"
            elif charger.get("physical_commissioned") is not True:
                reason = "PHYSICAL_COMMISSIONING_REQUIRED"
            elif self._switch(self.runtime.hass, charger["control_entity"]) is None:
                reason = "NATIVE_SWITCH_UNAVAILABLE"
            elif self._switch(self.runtime.hass, charger["control_entity"]).state == "on":
                reason = "SWITCH_ALREADY_ON"
            else:
                reason = self._admit_start(charger, at, target_current=(
                    charger.get("min_current_a")
                    if charger["kind"] == "variable_current" else None
                ))
            stop_allowed = (
                not self._stopped
                and charger.get("kind") in ("on_off", "variable_current")
                and charger.get("control_owner") == "multicharge"
                and charger.get("physical_commissioned") is True
                and self._switch(self.runtime.hass, charger.get("control_entity")) is not None
            )
            result[uid] = {
                "start_allowed": reason is None and uid not in self._quarantine,
                "stop_allowed": stop_allowed,
                "reason": "PREVIOUS_COMMAND_UNCONFIRMED"
                          if reason is None and uid in self._quarantine
                          else reason or "READY",
            }
        return result

    def _publish(self, uid, request_id, action, status, reason, requested_at,
                 *, observed_at=None, measured_kw=None, service_sent=False):
        result = {
            "charger_id": uid,
            "request_id": request_id,
            "action": action,
            "status": status,
            "reason": reason,
            "requested_at": requested_at.isoformat(),
            "readback_at": observed_at.isoformat() if observed_at else None,
            "measured_power_kw": measured_kw,
            "service_sent": service_sent,
        }
        self._outcomes[uid] = result
        if status == "execution_unknown":
            self._quarantine.add(uid)
        if status == "confirmed" and action == "stop":
            self._quarantine.discard(uid)
            self._sessions.pop(uid, None)
            self._accepted.pop(uid, None)
        if status == "confirmed":
            self.runtime.refresh()
        else:
            self.runtime.notify()
        return result

    @staticmethod
    def _switch(hass, entity):
        if not isinstance(entity, str) or not entity.startswith("switch."):
            return None
        state = hass.states.get(entity)
        if state is None or state.state not in ("on", "off"):
            return None
        return state

    def _admit_start(self, charger, at, *, planned=False, target_current=None):
        cfg = self.runtime.configuration
        ctl = cfg["controller"]
        if not planned and ctl.get("mode") != "Force Charge":
            return "MANUAL_START_REQUIRES_FORCE_CHARGE"
        if planned and ctl.get("mode") not in (
            "Automatic", "Solar", "Economy", "Ready By"
        ):
            return "AUTOMATIC_MODE_NOT_ENABLED"
        asset = next(
            (a for a in cfg["assets"] if a["id"] == charger.get("asset")), None
        )
        if asset is None:
            return "ASSET_NOT_ASSIGNED"
        if charger.get("phase_count") not in (1, 2, 3):
            return "PHYSICAL_PHASES_UNVERIFIED"
        requested_kw = charger["rated_power_kw"]
        if charger["kind"] == "variable_current":
            problem, requested_kw = self._requested_current(
                charger, target_current, at
            )
            if problem:
                return problem
        if (asset.get("max_charge_kw") is not None
                and requested_kw > asset["max_charge_kw"] + 1e-9):
            return "ASSET_POWER_CAP_REQUIRES_MODULATION"
        amount = asset.get("requested_kwh")
        duration = asset.get("requested_duration_minutes")
        if amount is not None and amount > 0:
            if not charger.get("energy_entity"):
                return "MEASURED_ENERGY_METER_REQUIRED"
            meter = number(self.runtime.hass, charger["energy_entity"], "energy", at)
            if meter.quality != "ok":
                return "MEASURED_ENERGY_UNAVAILABLE"
        if amount is not None and amount <= 0:
            return "TARGET_ALREADY_MET"
        if duration is None and amount is None:
            if not all(k in asset for k in (
                "soc_entity", "capacity_kwh", "target_soc", "charge_efficiency"
            )):
                return "ASSET_DEMAND_UNVERIFIED"
            soc = number(self.runtime.hass, asset["soc_entity"], "soc", at)
            if soc.quality != "ok":
                return "ASSET_SOC_UNAVAILABLE"
            if soc.value >= asset["target_soc"]:
                return "TARGET_ALREADY_MET"
        if asset.get("ready_by"):
            try:
                due = datetime.fromisoformat(
                    asset["ready_by"].replace("Z", "+00:00")
                )
                repeat = asset.get("ready_by_repeat", "none")
                if repeat != "none":
                    due, reason = resolve_recurring_ready_by(
                        due, at, repeat, self.runtime.hass.config.time_zone
                    )
                    if due is None:
                        return reason
                if due.tzinfo is None or due.utcoffset() is None or at >= due:
                    return "READY_BY_EXPIRED"
            except ValueError:
                return "READY_BY_INVALID"
        cable = connection(self.runtime.hass, charger.get("connected_entity"), at)
        if cable.quality != "ok" or cable.value is not True:
            return "PHYSICAL_CONNECTION_UNVERIFIED"
        this_power = number(self.runtime.hass, charger.get("power_entity"), "power", at)
        if this_power.quality != "ok":
            return "INDEPENDENT_POWER_UNAVAILABLE"
        if this_power.value > START_POWER_KW:
            return "POWER_ALREADY_PRESENT_WITHOUT_CONFIRMED_OWNER"
        return self._physical_budget(
            charger, at, requested_kw,
            target_current if charger["kind"] == "variable_current"
            else charger.get("fixed_current_a"),
        )


    def _requested_current(self, charger, current, at):
        """Reject a claimed adjustable capability until native source metadata agrees."""
        if charger.get("kind") != "variable_current":
            return "CHARGER_NOT_ADJUSTABLE", None
        if (not isinstance(current, (float, int)) or isinstance(current, bool)
                or not isfinite(current)):
            return "CURRENT_SETPOINT_REQUIRED", None
        lo, hi, step = (charger.get("min_current_a"), charger.get("max_current_a"),
                        charger.get("current_step_a"))
        if not all(isinstance(v, (float, int)) and v > 0 for v in (lo, hi, step)):
            return "CURRENT_RANGE_UNVERIFIED", None
        if current < lo - 1e-7 or current > hi + 1e-7:
            return "CURRENT_OUTSIDE_VERIFIED_RANGE", None
        steps = round((current - lo) / step)
        if abs(lo + steps * step - current) > 1e-6:
            return "CURRENT_STEP_UNSUPPORTED", None
        entity = charger.get("current_control_entity")
        reading = charger.get("current_readback_entity")
        if not str(entity).startswith("number.") or not str(reading).startswith("sensor."):
            return "CURRENT_WRITE_OR_INDEPENDENT_READBACK_MISSING", None
        device = self.runtime.hass.states.get(entity)
        if device is None or device.state in ("unavailable", "unknown"):
            return "CURRENT_CONTROL_UNAVAILABLE", None
        try:
            attrs = device.attributes
            hmin, hmax, hstep = (float(attrs["min"]), float(attrs["max"]),
                                 float(attrs["step"]))
            if hstep <= 0 or current < hmin or current > hmax:
                return "NATIVE_CURRENT_CAPABILITY_MISMATCH", None
            if abs((current - hmin) / hstep - round((current - hmin) / hstep)) > 1e-5:
                return "NATIVE_CURRENT_STEP_MISMATCH", None
        except (KeyError, ValueError, TypeError, OverflowError, ZeroDivisionError):
            return "NATIVE_CURRENT_CAPABILITY_UNVERIFIED", None
        phases = charger.get("phase_ids") or []
        voltage = charger.get("voltage_v")
        if (charger.get("phase_count") != len(phases)
                or len(phases) != len(set(phases))
                or not phases or not isinstance(voltage, (float, int))):
            return "ELECTRICAL_WIRING_UNVERIFIED", None
        kw = float(current) * voltage * len(phases) / 1000
        if kw > charger["rated_power_kw"] + 1e-9:
            return "RATED_CHARGER_POWER_EXCEEDED", None
        return None, round(kw, 6)

    def _physical_budget(self, charger, at, kw, current):
        """Conservative site, phase and circuit budget across all configured sources."""
        cfg = self.runtime.configuration
        ctl = cfg["controller"]
        cap = ctl.get("max_power_kw")
        if cap is None:
            return "SITE_POWER_CAPACITY_UNVERIFIED"
        selected = ctl.get("binding_entity") or ctl.get("site_power_entity")
        if selected:
            envelope, quality = binding(self.runtime.hass, selected, at)
            if envelope is None or quality != "OK":
                return "BINDING_CAPACITY_UNAVAILABLE"
            until = at + timedelta(seconds=30)
            slots = [s for s in envelope.slots if s.start <= at and s.end >= until]
            if len(slots) != 1 or envelope.valid_until < until:
                return "BINDING_CAPACITY_SLOT_MISSING"
            cap = min(cap, slots[0].max_charging_kw)
        occupied, reserved = 0, kw
        phase_totals = {}
        circuits = {}
        for other in cfg["chargers"]:
            if other["id"] == charger["id"]:
                continue
            power = number(self.runtime.hass, other.get("power_entity"), "power", at)
            if power.quality != "ok":
                return "OTHER_CHARGER_POWER_UNAVAILABLE"
            state = self._switch(self.runtime.hass, other.get("control_entity"))
            if state is None:
                return "OTHER_CHARGER_OWNER_OR_STATE_UNKNOWN"
            if state.state == "on":
                occupied += 1
                amps = other.get("fixed_current_a")
                if other["kind"] == "variable_current":
                    sensed = number(self.runtime.hass,
                                    other.get("current_readback_entity"), "current", at)
                    if sensed.quality != "ok":
                        return "OTHER_CHARGER_CURRENT_UNAVAILABLE"
                    session = self._sessions.get(other["id"])
                    if session and session.get("target_current_a") is not None:
                        amps = max(sensed.value, session["target_current_a"])
                        reserved += max(power.value, amps * other["voltage_v"]
                                        * len(other["phase_ids"]) / 1000)
                    else:
                        amps = other["max_current_a"]
                        reserved += other["rated_power_kw"]
                else:
                    reserved += other["rated_power_kw"]
                if ctl.get("phase_limits_a") or other.get("circuit_id"):
                    if amps is None or not other.get("phase_ids"):
                        return "OTHER_CHARGER_PHASES_UNVERIFIED"
                    for phase in other["phase_ids"]:
                        phase_totals[phase] = phase_totals.get(phase, 0) + amps
                    if other.get("circuit_id"):
                        key = other["circuit_id"]
                        circuits[key] = circuits.get(key, 0) + amps
            elif power.value > STOP_POWER_KW:
                return "OTHER_CHARGER_POWER_WITH_SWITCH_OFF"
        if occupied >= ctl["max_parallel"]:
            return "MAX_PARALLEL_REACHED"
        if reserved > cap + 1e-9:
            return "SITE_CAPACITY_EXCEEDED"
        phases = charger.get("phase_ids") or []
        if ctl.get("phase_limits_a"):
            limits = ctl["phase_limits_a"]
            if current is None or not phases or any(p not in limits for p in phases):
                return "PHYSICAL_PHASES_UNVERIFIED"
            if any(phase_totals.get(p, 0) + current > limits[p] + 1e-9 for p in phases):
                return "SITE_PHASE_CURRENT_EXCEEDED"
        if charger.get("circuit_id"):
            if current is None or charger.get("circuit_limit_a") is None:
                return "CIRCUIT_CURRENT_UNVERIFIED"
            if (circuits.get(charger["circuit_id"], 0) + current >
                    charger["circuit_limit_a"] + 1e-9):
                return "CIRCUIT_CURRENT_EXCEEDED"
        return None

    async def _set_native_current(self, charger, current, context):
        """Native HA write only, not confirmation of physical charging current."""
        await self.runtime.hass.services.async_call(
            "number", "set_value",
            {"entity_id": charger["current_control_entity"], "value": float(current)},
            blocking=True, context=context,
        )

    def _current_confirmed(self, charger, current, requested_at):
        reading = number(self.runtime.hass, charger.get("current_readback_entity"),
                         "current", datetime.now(timezone.utc))
        watts = number(self.runtime.hass, charger.get("power_entity"), "power",
                       datetime.now(timezone.utc))
        target_kw = current * charger["voltage_v"] * len(charger["phase_ids"]) / 1000
        return (reading.quality == "ok" and reading.observed_at is not None
                and reading.observed_at >= requested_at
                and watts.quality == "ok" and watts.observed_at is not None
                and watts.observed_at >= requested_at
                and START_POWER_KW < watts.value <= target_kw * 1.10 + 0.01
                and abs(reading.value - current) <= max(0.25,
                    charger.get("current_step_a", 1) / 2))

    async def _protective_stop(self, charger, context):
        """Best-effort real STOP on an unconfirmed START, never claim it succeeded."""
        try:
            await self.runtime.hass.services.async_call(
                "switch", "turn_off",
                {"entity_id": charger["control_entity"]},
                blocking=True, context=context
            )
            return True
        except Exception:
            _LOGGER.exception("Protective STOP could not be delivered for %s",
                              charger["id"])
            return False

    def _session_stop_reason(self, charger, now):
        """Demand closure is based on observed energy, time or SoC, never a guess."""
        session = self._sessions.get(charger["id"])
        if session is None:
            if charger["id"] in self._start_pending:
                return None
            return "ACTIVE_CHARGING_UNOWNED_AFTER_RESTART"
        asset = next(
            (a for a in self.runtime.configuration["assets"]
             if a["id"] == session["asset_id"]), None
        )
        if asset is None or charger.get("asset") != session["asset_id"]:
            return "ACTIVE_SESSION_ASSIGNMENT_CHANGED"
        if now >= session["hard_stop_at"]:
            return "SESSION_SAFETY_DEADLINE_REACHED"
        if session["requested_duration_minutes"] is not None:
            if (now - session["started_at"]).total_seconds() >= (
                60 * session["requested_duration_minutes"]
            ):
                return "REQUESTED_DURATION_COMPLETE"
        if session["requested_kwh"] is not None:
            obs = number(self.runtime.hass, charger.get("energy_entity"), "energy", now)
            if obs.quality != "ok":
                return "SESSION_ENERGY_METER_UNAVAILABLE"
            delivered = obs.value - session["starting_energy_kwh"]
            if delivered < -0.00001:
                return "SESSION_ENERGY_METER_RESET"
            session["actual_energy_kwh"] = round(max(0, delivered), 6)
            if delivered >= session["requested_kwh"]:
                return "REQUESTED_ENERGY_COMPLETE"
        if session["soc_target"] is not None:
            soc = number(self.runtime.hass, asset.get("soc_entity"), "soc", now)
            if soc.quality != "ok":
                return "SESSION_SOC_UNAVAILABLE"
            if soc.value >= session["soc_target"]:
                return "SOC_TARGET_REACHED"
        return None

    def _start_session(self, charger, observed):
        """Adopt only freshly confirmed START, never existing switch-on at boot."""
        asset = next(
            a for a in self.runtime.configuration["assets"]
            if a["id"] == charger["asset"]
        )
        now = datetime.now(timezone.utc)
        explicit_energy = asset.get("requested_kwh")
        duration = asset.get("requested_duration_minutes")
        soc_target = (
            asset.get("target_soc")
            if explicit_energy is None and duration is None else None
        )
        starting_energy = None
        if explicit_energy is not None:
            baseline = number(
                self.runtime.hass, charger.get("energy_entity"), "energy", now
            )
            if baseline.quality != "ok":
                return "SESSION_ENERGY_METER_UNAVAILABLE"
            starting_energy = baseline.value
        # Session cannot run longer than 24h on one manual authorization.
        end = now + timedelta(hours=24)
        if duration is not None:
            end = min(end, now + timedelta(minutes=duration))
        if asset.get("ready_by"):
            due = datetime.fromisoformat(
                asset["ready_by"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            if asset.get("ready_by_repeat", "none") != "none":
                due, _ = resolve_recurring_ready_by(
                    due, now, asset["ready_by_repeat"],
                    self.runtime.hass.config.time_zone
                )
            if due is None:
                return "READY_BY_UNAVAILABLE"
            end = min(end, due)
        self._sessions[charger["id"]] = {
            "asset_id": asset["id"],
            "started_at": now,
            "hard_stop_at": end,
            "requested_kwh": explicit_energy,
            "requested_duration_minutes": duration,
            "soc_target": soc_target,
            "starting_energy_kwh": starting_energy,
            "actual_energy_kwh": 0.0 if starting_energy is not None else None,
            "last_physical_readback": observed.observed_at,
            "target_current_a": None,
        }
        return None

    def _accept_slot(self, charger, slot, revision):
        """Accept only a physically confirmed current slot; keep bounded evidence."""
        record = {
            "charger_id": charger["id"], "asset_id": slot.asset_uid,
            "start": slot.start, "end": slot.end,
            "power_kw": slot.power_kw, "current_a": slot.current_a,
            "revision": revision, "status": "accepted",
        }
        self._accepted[charger["id"]] = record
        self._accepted_history[(charger["id"], slot.start)] = record
        threshold = datetime.now(timezone.utc) - timedelta(hours=48)
        for key, old in list(self._accepted_history.items()):
            if old["end"] < threshold:
                del self._accepted_history[key]

    async def advance_plan(self, quarter_start):
        """Apply one qualified quarter plan through the only existing executor.

        Called only by the native HA quarter-hour callback. An arbitrary
        source refresh does not cause a new START, and boot never replays an
        accepted command without an independent current-session authority.
        """
        mode = self.runtime.configuration["controller"]["mode"]
        if self._stopped or mode not in ("Automatic", "Economy", "Solar", "Ready By"):
            return
        if self._last_advance == quarter_start:
            return
        self._last_advance = quarter_start
        assessment = self.runtime.assessment
        if assessment is None or assessment.plan.status != "proposed":
            return
        slots = {
            slot.charger_uid: slot for slot in assessment.plan.slots
            if slot.start == quarter_start and slot.end == quarter_start + timedelta(minutes=15)
        }
        self._grants = dict(slots)
        try:
            for charger in self.runtime.configuration["chargers"]:
                uid = charger["id"]
                if (charger.get("control_owner", "external") != "multicharge"
                        or charger.get("physical_commissioned") is not True):
                    continue
                slot = slots.get(uid)
                switch = self._switch(self.runtime.hass, charger.get("control_entity"))
                if switch is None:
                    continue
                if switch.state == "on":
                    # Never adopt an unowned session after restart or handover.
                    session = self._sessions.get(uid)
                    if session is None or uid not in self._accepted:
                        await self.execute(uid, "stop")
                        continue
                    if slot is None or slot.asset_uid != session["asset_id"]:
                        await self.execute(uid, "stop")
                        continue
                    if charger["kind"] == "variable_current":
                        target = slot.current_a
                        if target is None:
                            await self.execute(uid, "stop")
                            continue
                        if abs(target - session.get("target_current_a", 0)) > 1e-6:
                            outcome = await self.execute(
                                uid, "set_current", current_a=target
                            )
                            if outcome["status"] != "confirmed":
                                continue
                    # Still-owned physical session and verified slot continuity.
                    self._accept_slot(charger, slot, assessment.plan.revision)
                    continue
                if slot is None:
                    continue
                asset = next((a for a in self.runtime.configuration["assets"]
                              if a["id"] == slot.asset_uid), None)
                if asset is None:
                    continue
                # An explicit fixed demand completed in this runtime cannot be
                # silently restarted next quarter. Repeated Ready By intentions
                # are keyed by the resolved actual deadline occurrence.
                resolved = None
                if asset.get("ready_by"):
                    resolved = asset["ready_by"]
                    if asset.get("ready_by_repeat", "none") != "none":
                        due, reason = resolve_recurring_ready_by(
                            datetime.fromisoformat(resolved), quarter_start,
                            asset["ready_by_repeat"],
                            self.runtime.hass.config.time_zone,
                        )
                        if due is None:
                            continue
                        resolved = due.isoformat()
                if (asset["id"] in self._completed
                        and self._completed[asset["id"]] == resolved):
                    continue
                result = await self.execute(
                    uid, "start", current_a=slot.current_a, plan_slot=slot,
                )
                if result["status"] == "confirmed":
                    self._accept_slot(charger, slot, assessment.plan.revision)
        finally:
            self._grants.clear()

    async def _reduce_current(self, charger, at):
        """Only confirmed smaller supported setpoints may avert a safety STOP."""
        session = self._sessions.get(charger["id"])
        if charger["kind"] != "variable_current" or not session:
            return False
        existing = session.get("target_current_a")
        if existing is None:
            return False
        step, minimum = charger["current_step_a"], charger["min_current_a"]
        candidate = round(existing - step, 6)
        while candidate + 1e-9 >= minimum:
            problem, power = self._requested_current(charger, candidate, at)
            if problem is None and self._physical_budget(
                charger, at, power, candidate
            ) is None:
                outcome = await self.execute(
                    charger["id"], "set_current", current_a=candidate
                )
                if outcome["status"] == "confirmed":
                    accepted = self._accepted.get(charger["id"])
                    if accepted is not None:
                        accepted["current_a"] = candidate
                        accepted["power_kw"] = power
                    return True
                return False
            candidate = round(candidate - step, 6)
        return False

    async def supervise(self):
        """Reconcile physical truth; never treat stale/unknown as safe capacity.

        Automatic START is exclusively advance_plan at a real quarter boundary.
        This guard may reduce verified adjustable current or physically STOP;
        it never independently starts a charger.
        """
        if self._stopped or self._supervising:
            return
        self._supervising = True
        try:
            cfg = self.runtime.configuration
            ctl = cfg["controller"]
            mode = ctl["mode"]
            at = datetime.now(timezone.utc)
            active = []
            for c in cfg["chargers"]:
                if (c.get("kind") not in ("on_off", "variable_current")
                        or c.get("control_owner") != "multicharge"
                        or c.get("physical_commissioned") is not True):
                    continue
                state = self._switch(self.runtime.hass, c.get("control_entity"))
                if state is None:
                    _LOGGER.error("Physical charger state unknown: %s", c["id"])
                    continue
                if state.state == "on":
                    active.append(c)
            for charger in active:
                uid = charger["id"]
                cable = connection(self.runtime.hass, charger.get("connected_entity"), at)
                power = number(self.runtime.hass, charger.get("power_entity"), "power", at)
                session_reason = self._session_stop_reason(charger, at)
                accepted = self._accepted.get(uid)
                is_auto = mode in ("Automatic", "Solar", "Economy", "Ready By")
                # Give a pending quarter callback a brief handover window.
                in_grace = (at - datetime.fromtimestamp(
                    int(at.timestamp()) // 900 * 900, timezone.utc
                )).total_seconds() < 10
                no_plan = is_auto and (
                    accepted is None or accepted["end"] <= at and not in_grace
                )
                unowned = is_auto and accepted is None
                wrong_mode = mode == "Off" or (is_auto and (no_plan or unowned))
                if mode == "Force Charge" and accepted is not None:
                    wrong_mode = True
                unsafe = (
                    wrong_mode or cable.quality != "ok" or cable.value is not True
                    or power.quality != "ok"
                    or power.value > charger["rated_power_kw"] * 1.10
                    or session_reason is not None
                )
                if charger["kind"] == "variable_current":
                    amps = number(self.runtime.hass,
                        charger.get("current_readback_entity"), "current", at)
                    session = self._sessions.get(uid)
                    current = session.get("target_current_a") if session else None
                    if (amps.quality != "ok" or current is None
                            or amps.value > current + max(
                                0.25, charger["current_step_a"] / 2
                            )):
                        unsafe = True
                if not unsafe:
                    session = self._sessions.get(uid)
                    kw = (charger["rated_power_kw"]
                          if charger["kind"] == "on_off" else
                          session["target_current_a"] * charger["voltage_v"]
                          * len(charger["phase_ids"]) / 1000)
                    current = (charger.get("fixed_current_a")
                               if charger["kind"] == "on_off"
                               else session["target_current_a"])
                    limit_reason = self._physical_budget(charger, at, kw, current)
                    if limit_reason is not None:
                        if not await self._reduce_current(charger, at):
                            unsafe = True
                if unsafe:
                    if session_reason in (
                        "REQUESTED_ENERGY_COMPLETE", "REQUESTED_DURATION_COMPLETE",
                        "SOC_TARGET_REACHED"
                    ) and is_auto:
                        asset = next((a for a in cfg["assets"]
                                      if a["id"] == charger.get("asset")), None)
                        if asset is not None:
                            occurrence = asset.get("ready_by")
                            if occurrence and asset.get("ready_by_repeat", "none") != "none":
                                due, _ = resolve_recurring_ready_by(
                                    datetime.fromisoformat(occurrence), at,
                                    asset["ready_by_repeat"], self.runtime.hass.config.time_zone
                                )
                                occurrence = due.isoformat() if due else None
                            self._completed[asset["id"]] = occurrence
                    outcome = await self.execute(uid, "stop")
                    if outcome["status"] != "confirmed":
                        _LOGGER.error("Protective charger STOP not physically confirmed: %s %s",
                                      uid, outcome["reason"])
        finally:
            self._supervising = False

    async def shutdown(self):
        """Stop each owned charger before unload, with actual power readback."""
        for charger in self.runtime.configuration["chargers"]:
            if (charger.get("kind") not in ("on_off", "variable_current")
                    or charger.get("control_owner", "external") != "multicharge"
                    or charger.get("physical_commissioned") is not True):
                continue
            state = self._switch(self.runtime.hass, charger.get("control_entity"))
            if state is None:
                _LOGGER.error("Cannot unload: charger state unknown for %s",
                              charger["id"])
                return False
            power = number(self.runtime.hass, charger.get("power_entity"),
                           "power", datetime.now(timezone.utc))
            if state.state == "off" and power.quality == "ok" and power.value <= STOP_POWER_KW:
                continue
            outcome = await self.execute(charger["id"], "stop")
            if outcome["status"] != "confirmed":
                _LOGGER.error("Unconfirmed STOP blocks unload for %s: %s",
                              charger["id"], outcome["reason"])
                return False
        return True

    def _readback(self, charger, action, requested_at):
        switch = self._switch(self.runtime.hass, charger["control_entity"])
        if switch is None or switch.state != ("on" if action == "start" else "off"):
            return None
        power = number(self.runtime.hass, charger.get("power_entity"), "power",
                       datetime.now(timezone.utc))
        if power.quality != "ok" or power.observed_at is None:
            return None
        if power.observed_at < requested_at:
            return None
        if action == "start" and power.value <= START_POWER_KW:
            return None
        if action == "stop" and power.value > STOP_POWER_KW:
            return None
        return power

    async def execute(self, charger_id, action, *, context=None,
                      request_id=None, readback_seconds=READBACK_SECONDS,
                      current_a=None, plan_slot=None):
        """Perform a real HA switch call; success requires fresh independent power."""
        if action not in ("start", "stop", "set_current"):
            raise ValueError("unsupported physical action")
        at = datetime.now(timezone.utc)
        request_id = request_id or uuid4().hex
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            raise ValueError("request ID must be 1..128 characters")
        async with self._lock:
            previous = self._requests.get(request_id)
            if previous is not None:
                if (previous["charger_id"] != charger_id
                        or previous["action"] != action
                        or previous.get("requested_current_a") != current_a):
                    raise ValueError("request ID used for a different command")
                return dict(previous)
            cfg = self.runtime.configuration
            charger = next((c for c in cfg["chargers"] if c["id"] == charger_id), None)
            def result(status, reason, **extras):
                recorded = self._publish(charger_id, request_id, action, status,
                                         reason, at, **extras)
                self._requests[request_id] = dict(recorded)
                return recorded
            if charger is None:
                return result("rejected", "UNKNOWN_CHARGER")
            if self._stopped:
                return result("rejected", "INTEGRATION_UNLOADED")
            if charger.get("kind") not in ("on_off", "variable_current"):
                return result("rejected", "CHARGER_CONTROL_UNSUPPORTED")
            entity = charger.get("control_entity")
            if not entity or not entity.startswith("switch."):
                return result("rejected", "NATIVE_SWITCH_REQUIRED")
            if charger.get("control_owner", "external") != "multicharge":
                return result("rejected", "EXTERNAL_WRITER_OWNS_CHARGER")
            if charger.get("physical_commissioned") is not True:
                return result("rejected", "PHYSICAL_COMMISSIONING_REQUIRED")
            state = self._switch(self.runtime.hass, entity)
            if state is None:
                return result("rejected", "NATIVE_SWITCH_UNAVAILABLE")
            if action in ("start", "set_current"):
                if charger["kind"] == "variable_current":
                    if current_a is None and action == "start" and plan_slot is None:
                        current_a = charger["min_current_a"]
                    if plan_slot is not None and action == "start":
                        current_a = plan_slot.current_a
                    problem, requested_kw = self._requested_current(charger, current_a, at)
                    if problem:
                        return result("rejected", problem)
                elif action == "set_current":
                    return result("rejected", "ON_OFF_CANNOT_MODULATE")
            if action == "set_current":
                if state.state != "on" or charger_id not in self._sessions:
                    return result("rejected", "CURRENT_CHANGE_REQUIRES_OWNED_SESSION")
                cable = connection(self.runtime.hass, charger.get("connected_entity"), at)
                if cable.quality != "ok" or cable.value is not True:
                    return result("rejected", "PHYSICAL_CONNECTION_UNVERIFIED")
                reason = self._physical_budget(charger, at, requested_kw, current_a)
                if reason:
                    return result("rejected", reason)
                self._publish(charger_id, request_id, action, "requested", "REQUESTED", at)
                try:
                    await self._set_native_current(charger, current_a, context)
                except Exception as exc:
                    await self._protective_stop(charger, context)
                    return result("execution_unknown",
                                  "NATIVE_CURRENT_SERVICE_EXCEPTION:" + type(exc).__name__,
                                  service_sent=True)
                deadline = asyncio.get_running_loop().time() + readback_seconds
                while True:
                    if self._current_confirmed(charger, current_a, at):
                        self._sessions[charger_id]["target_current_a"] = current_a
                        out = result("confirmed", "INDEPENDENT_CURRENT_READBACK",
                            observed_at=datetime.now(timezone.utc),
                            measured_kw=number(self.runtime.hass,
                                charger.get("power_entity"), "power",
                                datetime.now(timezone.utc)).value, service_sent=True)
                        self._requests[request_id]["requested_current_a"] = current_a
                        return out
                    if asyncio.get_running_loop().time() >= deadline:
                        await self._protective_stop(charger, context)
                        return result("execution_unknown", "CURRENT_READBACK_TIMEOUT;PROTECTIVE_STOP_SENT",
                                      service_sent=True)
                    await asyncio.sleep(0.25)
            if action == "start":
                if state.state != "off":
                    return result("rejected", "SWITCH_ALREADY_ON")
                if charger_id in self._quarantine:
                    return result("rejected", "PREVIOUS_COMMAND_UNCONFIRMED")
                if plan_slot is not None:
                    if (self._grants.get(charger_id) != plan_slot
                            or not plan_slot.start <= at < plan_slot.end
                            or plan_slot.charger_uid != charger_id
                            or plan_slot.asset_uid != charger.get("asset")):
                        return result("rejected", "PLAN_SLOT_NOT_AUTHORIZED")
                reason = self._admit_start(
                    charger, at, planned=plan_slot is not None,
                    target_current=current_a,
                )
                if reason:
                    return result("rejected", reason)
            elif state.state == "off":
                power = number(self.runtime.hass, charger.get("power_entity"),
                               "power", at)
                if power.quality == "ok" and power.value <= STOP_POWER_KW:
                    return result("confirmed", "ALREADY_PHYSICALLY_STOPPED",
                                  observed_at=power.observed_at,
                                  measured_kw=power.value)
            if action == "start":
                self._start_pending.add(charger_id)
            self._publish(charger_id, request_id, action, "requested",
                          "REQUESTED", at)
            try:
                if action == "start" and charger["kind"] == "variable_current":
                    await self._set_native_current(charger, current_a, context)
                await self.runtime.hass.services.async_call(
                    "switch", "turn_on" if action == "start" else "turn_off",
                    {"entity_id": entity}, blocking=True, context=context
                )
            except asyncio.CancelledError:
                self._start_pending.discard(charger_id)
                if action == "start":
                    await self._protective_stop(charger, context)
                result("execution_unknown", "COMMAND_CANCELLED_DURING_SERVICE",
                       service_sent=True)
                raise
            except Exception as exc:
                self._start_pending.discard(charger_id)
                _LOGGER.exception("Native charge %s service failed for %s",
                                  action, charger_id)
                protective = (await self._protective_stop(charger, context)
                              if action == "start" else False)
                return result("execution_unknown",
                              "NATIVE_SERVICE_EXCEPTION:" + type(exc).__name__
                              + (";PROTECTIVE_STOP_SENT" if protective else ";PROTECTIVE_STOP_UNCONFIRMED"),
                              service_sent=True)
            self._publish(charger_id, request_id, action,
                          "accepted_unconfirmed", "AWAITING_PHYSICAL_READBACK",
                          at, service_sent=True)
            deadline = asyncio.get_running_loop().time() + readback_seconds
            while True:
                if self._stopped:
                    self._start_pending.discard(charger_id)
                    return result("execution_unknown", "INTEGRATION_UNLOADED_PENDING",
                                  service_sent=True)
                observed = self._readback(charger, action, at)
                if (observed is not None and action == "start"
                        and charger["kind"] == "variable_current"
                        and not self._current_confirmed(charger, current_a, at)):
                    observed = None
                if observed is not None:
                    if action == "start":
                        reason = self._start_session(charger, observed)
                        self._start_pending.discard(charger_id)
                        if reason is None and charger["kind"] == "variable_current":
                            self._sessions[charger_id]["target_current_a"] = current_a
                        if reason is not None:
                            await self._protective_stop(charger, context)
                            return result(
                                "execution_unknown",
                                reason + ";PROTECTIVE_STOP_SENT",
                                service_sent=True
                            )
                    outcome = result("confirmed", "INDEPENDENT_POWER_READBACK",
                                  observed_at=observed.observed_at,
                                  measured_kw=observed.value,
                                  service_sent=True)
                    return outcome
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    self._start_pending.discard(charger_id)
                    _LOGGER.error("Native charge %s not confirmed for %s",
                                  action, charger_id)
                    protective = (await self._protective_stop(charger, context)
                                  if action == "start" else False)
                    return result("execution_unknown",
                                  "PHYSICAL_READBACK_TIMEOUT"
                                  + (";PROTECTIVE_STOP_SENT" if protective else
                                     ";PROTECTIVE_STOP_UNCONFIRMED" if action == "start" else ""),
                                  service_sent=True)
                try:
                    await asyncio.sleep(min(0.5, remaining))
                except asyncio.CancelledError:
                    self._start_pending.discard(charger_id)
                    if action == "start":
                        await self._protective_stop(charger, context)
                    result("execution_unknown", "COMMAND_CANCELLED_AWAITING_READBACK",
                           service_sent=True)
                    raise
