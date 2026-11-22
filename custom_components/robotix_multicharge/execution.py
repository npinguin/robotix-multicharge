"""Real native HA switch START/STOP, strict admission and physical readback.

Only explicitly selected switch entities can be controlled. External EVSC
ownership remains the default. Hardware cutover and commissioning are not
implied by passing software tests.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .source_evidence import binding, connection, number

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

    def detach(self):
        """Do not replay commands on unload or a restarted runtime."""
        self._stopped = True

    def snapshot(self):
        return {uid: dict(record) for uid, record in self._outcomes.items()}

    def session_snapshot(self):
        """Only physically observed active charging sessions, never proposals."""
        return {uid: dict(record) for uid, record in self._sessions.items()}

    def capabilities(self):
        """Expose exact current action eligibility; no optimistic UI guessing."""
        result = {}
        at = datetime.now(timezone.utc)
        for charger in self.runtime.configuration["chargers"]:
            uid = charger["id"]
            if self._stopped:
                reason = "INTEGRATION_UNLOADED"
            elif charger.get("kind") != "on_off":
                reason = "VARIABLE_CURRENT_NOT_IMPLEMENTED"
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
                reason = self._admit_start(charger, at)
            stop_allowed = (
                not self._stopped
                and charger.get("kind") == "on_off"
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

    def _admit_start(self, charger, at):
        cfg = self.runtime.configuration
        ctl = cfg["controller"]
        if ctl.get("mode") != "Force Charge":
            return "MANUAL_START_REQUIRES_FORCE_CHARGE"
        asset = next(
            (a for a in cfg["assets"] if a["id"] == charger.get("asset")), None
        )
        if asset is None:
            return "ASSET_NOT_ASSIGNED"
        if charger.get("phase_count") not in (1, 2, 3):
            return "PHYSICAL_PHASES_UNVERIFIED"
        if (asset.get("max_charge_kw") is not None
                and charger["rated_power_kw"] > asset["max_charge_kw"]):
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
        cap = ctl.get("max_power_kw")
        if cap is None:
            return "SITE_POWER_CAPACITY_UNVERIFIED"
        authority = ctl.get("binding_entity") or ctl.get("site_power_entity")
        if authority:
            envelope, quality = binding(self.runtime.hass, authority, at)
            if envelope is None or quality != "OK":
                return "BINDING_CAPACITY_UNAVAILABLE"
            until = at + timedelta(seconds=30)
            slots = [s for s in envelope.slots if s.start <= at and s.end >= until]
            if len(slots) != 1 or envelope.valid_until < until:
                return "BINDING_CAPACITY_SLOT_MISSING"
            cap = min(cap, slots[0].max_charging_kw)
        occupied = 0
        reserved = charger["rated_power_kw"]
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
                reserved += other["rated_power_kw"]
            elif power.value > STOP_POWER_KW:
                return "OTHER_CHARGER_POWER_WITH_SWITCH_OFF"
        if occupied >= ctl["max_parallel"]:
            return "MAX_PARALLEL_REACHED"
        if reserved > cap + 1e-9:
            return "SITE_CAPACITY_EXCEEDED"
        return None

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
            end = min(
                end, datetime.fromisoformat(
                    asset["ready_by"].replace("Z", "+00:00")
                ).astimezone(timezone.utc)
            )
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
        }
        return None

    async def supervise(self):
        """Protect commissioned on/off chargers against Off and lost safety input.

        This is the SAME sole physical writer and native STOP path as manual
        operation. No automatic START or command replay exists.
        """
        if self._stopped or self._supervising:
            return
        self._supervising = True
        try:
            cfg = self.runtime.configuration
            controller = cfg["controller"]
            at = datetime.now(timezone.utc)
            active = []
            for c in cfg["chargers"]:
                if (c.get("kind") != "on_off"
                        or c.get("control_owner") != "multicharge"
                        or c.get("physical_commissioned") is not True):
                    continue
                state = self._switch(self.runtime.hass, c.get("control_entity"))
                if state is None:
                    _LOGGER.error("Physical charger state unknown: %s", c["id"])
                    continue
                if state.state == "on":
                    active.append(c)
            if not active:
                return
            # Manual START belongs exclusively to Force Charge. Switching to
            # any advisory mode must stop the formerly authorized session.
            hold = controller.get("mode") != "Force Charge"
            cap = controller.get("max_power_kw")
            if cap is None:
                hold = True
            source = controller.get("binding_entity") or controller.get("site_power_entity")
            if source:
                envelope, quality = binding(self.runtime.hass, source, at)
                if envelope is None or quality != "OK":
                    hold = True
                else:
                    until = at + timedelta(seconds=30)
                    slots = [s for s in envelope.slots if s.start <= at and s.end >= until]
                    if len(slots) != 1 or envelope.valid_until < until:
                        hold = True
                    else:
                        cap = min(cap, slots[0].max_charging_kw) if cap is not None else None
            # Every configured charger consumes the same site budget,
            # regardless of whether MultiCharge or another HA owner controls it.
            reserved = 0.0
            charging_count = 0
            for c in cfg["chargers"]:
                physical = number(self.runtime.hass, c.get("power_entity"), "power", at)
                state = self._switch(self.runtime.hass, c.get("control_entity"))
                if physical.quality != "ok" or state is None:
                    hold = True
                    continue
                if state.state == "on":
                    reserved += c["rated_power_kw"]
                    charging_count += 1
                elif physical.value > STOP_POWER_KW:
                    hold = True
            if cap is not None and (
                charging_count > controller["max_parallel"]
                or reserved > cap + 1e-9
            ):
                hold = True
            for charger in active:
                cable = connection(self.runtime.hass, charger.get("connected_entity"), at)
                power = number(self.runtime.hass, charger.get("power_entity"), "power", at)
                session_reason = self._session_stop_reason(charger, at)
                unsafe = (
                    hold or cable.quality != "ok" or cable.value is not True
                    or power.quality != "ok"
                    or power.value > charger["rated_power_kw"] * 1.10
                    or session_reason is not None
                )
                if unsafe:
                    _LOGGER.warning(
                        "Stopping %s: mode/capacity/source or %s",
                        charger["id"], session_reason or "SAFETY_ADMISSION"
                    )
                    outcome = await self.execute(charger["id"], "stop")
                    if outcome["status"] != "confirmed":
                        _LOGGER.error(
                            "Protective charger STOP not physically confirmed: %s %s",
                            charger["id"], outcome["reason"]
                        )
        finally:
            self._supervising = False

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
                      request_id=None, readback_seconds=READBACK_SECONDS):
        """Perform a real HA switch call; success requires fresh independent power."""
        if action not in ("start", "stop"):
            raise ValueError("unsupported physical action")
        at = datetime.now(timezone.utc)
        request_id = request_id or uuid4().hex
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            raise ValueError("request ID must be 1..128 characters")
        async with self._lock:
            previous = self._requests.get(request_id)
            if previous is not None:
                if previous["charger_id"] != charger_id or previous["action"] != action:
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
            if charger.get("kind") != "on_off":
                return result("rejected", "VARIABLE_CURRENT_NOT_IMPLEMENTED")
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
            if action == "start":
                if state.state != "off":
                    return result("rejected", "SWITCH_ALREADY_ON")
                if charger_id in self._quarantine:
                    return result("rejected", "PREVIOUS_COMMAND_UNCONFIRMED")
                reason = self._admit_start(charger, at)
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
                if observed is not None:
                    if action == "start":
                        reason = self._start_session(charger, observed)
                        self._start_pending.discard(charger_id)
                        if reason is not None:
                            await self._protective_stop(charger, context)
                            return result(
                                "execution_unknown",
                                reason + ";PROTECTIVE_STOP_SENT",
                                service_sent=True
                            )
                    return result("confirmed", "INDEPENDENT_POWER_READBACK",
                                  observed_at=observed.observed_at,
                                  measured_kw=observed.value,
                                  service_sent=True)
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
