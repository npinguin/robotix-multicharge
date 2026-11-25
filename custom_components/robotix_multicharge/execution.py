"""Single native HA switch/current executor, strict admission and physical readback.

Only user-selected and activated switch entities can be controlled.
MultiCharge owns its own commands and reports capability-appropriate readback.
"""
from __future__ import annotations

import asyncio
import logging
from hashlib import sha256
from json import dumps
from math import floor, isfinite
from datetime import datetime, timedelta, timezone
from copy import deepcopy
from uuid import uuid4
from time import monotonic

from .source_evidence import Evidence, binding, connection, intervals, number, soc_with_health
from .configuration import is_plan_presentation_only_change
from .history import receipt_overlaps
from .planner import (resolve_recurring_ready_by, charging_window_allows,
                      qualified_price_policy_cap)

_LOGGER = logging.getLogger(__name__)
START_POWER_KW = 0.10
STOP_POWER_KW = 0.05
READBACK_SECONDS = 45
NATIVE_SERVICE_TIMEOUT_SECONDS = 45


def stop_power_limit(charger):
    """Small chargers must not mistake genuine charging for stopped."""
    rated = float(charger["rated_power_kw"])
    return max(0.002, min(STOP_POWER_KW, rated * 0.10))


def start_power_limit(charger):
    """Read back a positive fraction of qualified nominal charger power."""
    return max(stop_power_limit(charger) * 2,
               min(START_POWER_KW, float(charger["rated_power_kw"]) * 0.25))


class NativeSwitchExecutor:
    """Serialized physical command path for one controller, never a second planner."""

    def __init__(self, runtime):
        self.runtime = runtime
        self._lock = asyncio.Lock()
        self._outcomes = {}
        self._requests = {}
        self._quarantine = set()
        # A user Pause is a durable, charger-scoped admission hold. It is
        # neither a second planner nor an optimistic physical STOP receipt.
        self._paused = set()
        self._stopped = False
        self._supervising = False
        self._sessions = {}
        self._start_pending = set()
        self._current_pending = set()
        self._stop_requested = set()
        self._urgent_stop_requests = set()
        self._source_stop_tasks = {}
        self._draw_samples = {}
        self._accepted = {}
        self._accepted_history = {}
        self._grants = {}
        self._grant_configuration = None
        self._grant_plan_revision = None
        self._grant_prices = ()
        self._last_advance = None
        self._last_power_adjustment_tick = None
        self._regulating = False
        self._completed = {}
        self._inflight = {}
        self._session_history = []
        self.session_history_revision = 0
        self._persistence_verified = True
        # Current physical plug identity is volatile. Only an explicit
        # dedicated assignment may qualify a new fresh physical connection.
        self._plug_confirmations = {}
        self._plug_epochs = {}


    def _connection(self, charger, at):
        """Use the single canonical source reader and Charger-owned status map."""
        return connection(
            self.runtime.hass, charger.get("connected_entity"), at,
            connected_states=charger.get("connected_states"),
            disconnected_states=charger.get("disconnected_states"),
        )

    @staticmethod
    def duration_connection_allowed(observed):
        """An explicit finite switch request need not prove optional cable data."""
        if observed.quality == "ok":
            return observed.value is True
        return observed.reason in (
            "SOURCE_NOT_SELECTED", "SOURCE_MISSING", "SOURCE_UNAVAILABLE", "SOURCE_STALE",
        )

    def observe_connection_event(self, charger, old_state, new_state):
        """Track ordered native HA state transitions before refresh coalescing.

        A positive-to-positive mapped EVSE substate transition can keep an
        already confirmed plug only when the prior raw state/timestamp exactly
        matches the epoch we actually witnessed. Any gap, unavailable state,
        disconnect, rebind or unexpected transition immediately drops identity.
        This handles an unplug/replug that occurs between two refresh ticks.
        The callback never issues a charger command.
        """
        uid = charger["id"]
        entity = charger.get("connected_entity")
        mapped = charger.get("connected_states")
        existing = self._plug_epochs.get(uid)
        raw_old = str(getattr(old_state, "state", "")).strip().casefold()
        raw_new = str(getattr(new_state, "state", "")).strip().casefold()
        new_at = getattr(new_state, "last_changed", None)
        old_at = getattr(old_state, "last_changed", None)
        if (mapped and existing and existing.get("entity") == entity
                and raw_old in mapped and raw_new in mapped
                and existing.get("raw_state") == raw_old
                and isinstance(old_at, datetime) and old_at.utcoffset() is not None
                and isinstance(new_at, datetime) and new_at.utcoffset() is not None
                and existing.get("last_changed") ==
                    old_at.astimezone(timezone.utc).isoformat()
                # A real mapped positive-substate change advances time.
                # Same-raw attribute updates may preserve the same last_changed
                # timestamp, but provider re-creation must invalidate identity.
                and ((raw_old != raw_new and new_at > old_at)
                     or (raw_old == raw_new and new_at == old_at))):
            existing["raw_state"] = raw_new
            existing["last_changed"] = new_at.astimezone(timezone.utc).isoformat()
            return
        # Preserve no identity on an unobserved or non-continuous transition.
        # A subsequent fresh connected reading may start a NEW plug epoch,
        # using the current resident assignment, never a previous active session.
        self._plug_epochs.pop(uid, None)
        self._plug_confirmations.pop(uid, None)

    def observe_connection(self, charger, observed):
        """Observe continuity of a physical plug, not arbitrary EVSE substates.

        A native provider may change Preparing -> Charging while the same
        connector remains occupied. Disconnect, unknown, stale, rebind and
        restart clear the transient epoch; no previous identity is persisted.
        """
        uid = charger["id"]
        if observed.quality != "ok" or observed.value is not True:
            self._plug_epochs.pop(uid, None)
            self._plug_confirmations.pop(uid, None)
            return None
        entity = charger.get("connected_entity")
        source = self.runtime.hass.states.get(entity)
        changed = getattr(source, "last_changed", None)
        if not isinstance(changed, datetime) or changed.utcoffset() is None:
            self._plug_epochs.pop(uid, None)
            self._plug_confirmations.pop(uid, None)
            return None
        changed_at = changed.astimezone(timezone.utc).isoformat()
        raw_state = str(source.state).strip().casefold()
        existing = self._plug_epochs.get(uid)
        if existing and existing["entity"] == entity:
            if existing["last_changed"] == changed_at and (
                    existing["raw_state"] == raw_state):
                return existing["connected_at"]
            # Even mapped positive substates must not preserve an Asset based
            # solely on the latest snapshot: an unseen disconnect/replug
            # may have occurred. Only observe_connection_event can advance
            # this epoch using the ordered native HA event old/new pair.
        self._plug_epochs[uid] = {
            "entity": entity, "connected_at": changed_at,
            "last_changed": changed_at, "raw_state": raw_state,
        }
        self._plug_confirmations.pop(uid, None)
        return changed_at

    def connection_confirmation(self, charger, at):
        """Associate a fresh physical plug with the user's current assignment.

        Assignment is the resident declaration, not OEM vehicle recognition.
        Never carry a previous plug epoch into an active/inflight session.
        All existing electrical, ownership, connection and readback gates apply.
        """
        uid = charger["id"]
        observed = self._connection(charger, at)
        epoch = self.observe_connection(charger, observed)
        if epoch is None:
            return None
        receipt = self._plug_confirmations.get(uid)
        if (not receipt
                or receipt["asset_id"] != charger.get("asset")
                or receipt["connected_at"] != epoch):
            self._plug_confirmations.pop(uid, None)
            asset_id = charger.get("asset")
            asset = next((a for a in self.runtime.configuration["assets"]
                          if a["id"] == asset_id), None)
            if not asset:
                return None
            if asset.get("temporary") and datetime.fromisoformat(asset["expires_at"]) <= at:
                return None
            return {"asset_id": asset_id, "connected_at": epoch,
                    "confirmed_at": epoch, "basis": "user_assignment"}
        return {**receipt, "basis": "manual_confirmation"}

    def confirm_current_connection(self, charger_id, *, at=None):
        """Confirm the selected vehicle against one presently observed plug.

        Called by the owning HA-native Charger button under executor lock.
        This changes identity evidence only; it sends NO physical command.
        """
        now = at or datetime.now(timezone.utc)
        charger = next((c for c in self.runtime.configuration["chargers"]
                        if c["id"] == charger_id), None)
        if charger is None:
            return {"status": "rejected", "reason": "UNKNOWN_CHARGER"}
        asset = charger.get("asset")
        if not asset or not any(a["id"] == asset
                                for a in self.runtime.configuration["assets"]):
            return {"status": "rejected", "reason": "SELECT_VEHICLE_FIRST"}
        observed = self._connection(charger, now)
        if observed.quality != "ok" or observed.value is not True:
            self.observe_connection(charger, observed)
            return {"status": "rejected", "reason": "CURRENT_PHYSICAL_CONNECTION_UNKNOWN"}
        epoch = self.observe_connection(charger, observed)
        if epoch is None:
            return {"status": "rejected", "reason": "PLUG_INSTANCE_UNVERIFIED"}
        record = {
            "asset_id": asset,
            "connected_at": epoch,
            "confirmed_at": now.astimezone(timezone.utc).isoformat(),
        }
        self._plug_confirmations[charger_id] = record
        self.runtime.notify()
        return {"status": "confirmed", "reason": "CURRENT_PLUG_ASSET_CONFIRMED",
                **record}

    def _intent_key(self, asset, charger, occurrence):
        """Stable one-intent fingerprint; mutable SoC readings are never identity."""
        data = {
            "asset": asset["id"],
            "requested_kwh": asset.get("requested_kwh"),
            "duration": asset.get("requested_duration_minutes"),
            "target_soc": asset.get("target_soc"),
            "soc_source": asset.get("soc_entity"),
            "capacity": asset.get("capacity_kwh"),
            "efficiency": asset.get("charge_efficiency"),
            "ready_by": asset.get("ready_by"),
            "repeat": asset.get("ready_by_repeat", "none"),
            "occurrence": occurrence.isoformat() if isinstance(
                occurrence, datetime
            ) else occurrence,
        }
        # Preserve fingerprints for every existing non-budget legacy intent.
        # Additional fields are incorporated only when actually configured.
        for field in ("requested_budget_amount", "requested_budget_currency",
                      "ready_by_weekdays"):
            if asset.get(field) is not None:
                data[field] = asset[field]
        return sha256(dumps(data, sort_keys=True).encode()).hexdigest()

    def measured_intent_usage(self, asset, charger, occurrence, at=None):
        """Measured progress follows the Asset's intent, never its former EVSE."""
        now = at or datetime.now(timezone.utc)
        key = self._intent_key(asset, charger, occurrence)
        energy, duration, budget_amount = 0.0, 0.0, 0.0
        money_requested = asset.get("requested_budget_amount") is not None
        for receipt in self._session_history:
            if (receipt.get("intent_key") != key
                    or receipt.get("asset_id") != asset["id"]):
                continue
            if receipt.get("physical_stop_confirmed") is not True and not (
                    asset.get("requested_duration_minutes") is not None
                    and receipt.get("switch_stop_confirmed") is True):
                return {"energy_kwh": None, "duration_minutes": None,
                        "budget_amount": None}
            if money_requested:
                cost = receipt.get("budget_accrued_cost")
                if (receipt.get("budget_cost_quality") not in (
                        "qualified_effective_meter_increments",
                        "conservative_effective_upper_bound")
                        or cost is None):
                    return {"energy_kwh": None, "duration_minutes": None,
                            "budget_amount": None}
                budget_amount += cost
            duration += receipt["duration_minutes"]
            value = receipt.get("actual_energy_kwh")
            if asset.get("requested_kwh") is not None:
                if value is None:
                    return {"energy_kwh": None, "duration_minutes": None}
                energy += value
        for uid, session in self._sessions.items():
            if (session.get("asset_id") != asset["id"]
                    or session.get("intent_key") != key):
                continue
            duration += max(0, (now - session["started_at"]).total_seconds() / 60)
            if money_requested:
                if session.get("budget_quality") not in (
                        "qualified_effective_meter_increments",
                        "conservative_effective_upper_bound"):
                    return {"energy_kwh": None, "duration_minutes": None,
                            "budget_amount": None}
                budget_amount += session.get("budget_cost", 0.0)
            if asset.get("requested_kwh") is not None:
                source = next((c.get("energy_entity") for c in
                               self.runtime.configuration["chargers"]
                               if c["id"] == uid), None)
                if source is None or session.get("starting_energy_kwh") is None:
                    return {"energy_kwh": None, "duration_minutes": None}
                sample = number(self.runtime.hass, source, "energy", now)
                if sample.quality != "ok" or sample.value < session["starting_energy_kwh"] - 0.00001:
                    return {"energy_kwh": None, "duration_minutes": None}
                energy += max(0, sample.value - session["starting_energy_kwh"])
        return {"energy_kwh": round(energy, 6),
                "duration_minutes": round(duration, 4),
                "budget_amount": round(budget_amount, 6)}

    def intent_completed(self, asset, charger, deadline):
        key = self._intent_key(asset, charger, deadline)
        return self._completed.get(asset["id"]) == key

    def restore_state(self, snapshot):
        """Restore decision evidence only; NEVER restore physical ownership."""
        if snapshot is None:
            return
        try:
            if not isinstance(snapshot, dict) or snapshot.get("schema_major") != 1:
                raise ValueError("invalid persisted control schema")
            completed = snapshot["completed"]
            inflight = snapshot["inflight"]
            rows = snapshot["accepted"]
            sessions = snapshot.get("sessions", [])
            paused = snapshot.get("paused", [])
            configured = {c["id"] for c in self.runtime.configuration["chargers"]}
            if (not isinstance(paused, list) or len(paused) != len(set(paused))
                    or any(not isinstance(uid, str) or uid not in configured
                           for uid in paused)):
                raise ValueError("invalid paused charger state")
            if not isinstance(sessions, list):
                raise ValueError("invalid session history")
            if not isinstance(completed, dict) or not isinstance(inflight, dict):
                raise ValueError("invalid persisted intents")
            if not isinstance(rows, list) or len(rows) > 2000:
                raise ValueError("invalid accepted history")
            if not all(isinstance(k, str) and isinstance(x, str)
                       for d in (completed, inflight) for k, x in d.items()):
                raise ValueError("invalid intent fingerprints")
            history = {}
            for row in rows:
                start = datetime.fromisoformat(row["start"])
                end = datetime.fromisoformat(row["end"])
                if start.tzinfo is None or end.tzinfo is None or end <= start:
                    raise ValueError("invalid accepted slot")
                if row["status"] != "accepted" or not isinstance(row["charger_id"], str):
                    raise ValueError("invalid accepted outcome")
                confirmed = datetime.fromisoformat(row["confirmed_from"]) if row.get("confirmed_from") else start
                if not start <= confirmed < end:
                    raise ValueError("invalid accepted confirmation time")
                previous = confirmed
                close = datetime.fromisoformat(row["closed_at"]) if row.get("closed_at") else end
                if not confirmed <= close <= end:
                    raise ValueError("invalid accepted closing time")
                for change in row.get("changes", []):
                    stamp = datetime.fromisoformat(change["at"])
                    if not previous < stamp < close or any(
                            type(change[k]) not in (float, int) or not isfinite(change[k])
                            or change[k] < 0 for k in ("current_a", "power_kw")):
                        raise ValueError("invalid accepted modulation")
                    previous = stamp
                record = {**row, "start": start, "end": end}
                history[(record["charger_id"], start)] = record
            receipts = []
            for row in sessions:
                if not isinstance(row, dict):
                    raise ValueError("invalid session receipt")
                begun = datetime.fromisoformat(row["started_at"])
                ended = datetime.fromisoformat(row["ended_at"])
                if (begun.utcoffset() is None or ended.utcoffset() is None
                        or ended < begun or not isinstance(row["charger_id"], str)
                        or (row["asset_id"] is not None
                            and not isinstance(row["asset_id"], str))):
                    raise ValueError("invalid session identity")
                if row.get("intent_key") is not None and not isinstance(row["intent_key"], str):
                    raise ValueError("invalid receipt intent")
                amount = row.get("actual_energy_kwh")
                if amount is not None and (
                    type(amount) not in (int, float)
                    or not isfinite(amount) or amount < 0
                ):
                    raise ValueError("invalid session energy")
                cost = row.get("cost")
                if cost is not None and (
                    type(cost) not in (int, float) or not isfinite(cost)
                    or amount is None or not isinstance(row.get("currency"), str)
                ):
                    raise ValueError("invalid session valuation")
                budget = row.get("budget_accrued_cost")
                if budget is not None and (
                        type(budget) not in (float, int) or not isfinite(budget)
                        or budget < 0
                        or row.get("budget_cost_quality") not in (
                            "qualified_effective_meter_increments",
                            "conservative_effective_upper_bound")
                        or not isinstance(row.get("budget_currency"), str)):
                    raise ValueError("invalid budget progress receipt")
                receipts.append(dict(row))
            # Adopt ALL persisted decision evidence only after the *last*
            # field has passed validation. A corrupt trailing receipt cannot
            # partially alter pause, intent or attribution on this runtime.
            self._completed = dict(completed)
            self._inflight = dict(inflight)
            self._paused = set(paused)
            self._accepted_history = history
            self._session_history = receipts
            self.session_history_revision += 1
        except (ValueError, KeyError, TypeError, OverflowError):
            self._persistence_verified = False
            _LOGGER.error("Invalid charging control state: physical START held")

    def export_state(self):
        """Small native HA control receipt; never a competing meter history."""
        return {
            "schema_major": 1,
            "completed": dict(self._completed),
            "paused": sorted(self._paused),
            "sessions": list(self._session_history),
            "inflight": dict(self._inflight),
            "accepted": [
                {**record, "start": record["start"].isoformat(),
                 "end": record["end"].isoformat()}
                for record in self.accepted_slots().values()
            ],
        }

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

    def completed_sessions(self, *, limit=None, charger_id=None, asset_id=None,
                           start=None, end=None):
        """Filter before copying; only presentation callers limit the view."""
        if limit is not None and limit <= 0:
            return []
        rows = []
        history = self._session_history if limit is None else reversed(self._session_history)
        for row in history:
            if (charger_id is not None and row["charger_id"] != charger_id
                    or asset_id is not None and row["asset_id"] != asset_id
                    or start is not None and end is not None
                    and not receipt_overlaps(row, start, end)):
                continue
            rows.append(dict(row))
            if limit is not None and len(rows) == limit:
                break
        if limit is not None:
            rows.reverse()
        return rows

    def _archive_session(self, charger_id, finished_at, reason):
        """Only a physically confirmed STOP may produce a completed receipt."""
        session = self._sessions.get(charger_id)
        if session is None:
            return
        charger = next((c for c in self.runtime.configuration["chargers"]
                        if c["id"] == charger_id), None)
        begun = session["started_at"]
        end = max(finished_at or datetime.now(timezone.utc), begun)
        source = charger.get("energy_entity") if charger else None
        # Final physical STOP must reconcile the last meter increment, even
        # if a user pressed STOP before the 60-second budget supervisor poll.
        # This reuses the SAME source-qualified budget accounting path.
        if charger and session.get("requested_budget_amount") is not None:
            self._update_budget_progress(charger, session, end)
        delivered, meter_at, sample = None, None, None
        if session["starting_energy_kwh"] is not None and source:
            sample = number(self.runtime.hass, source, "energy", datetime.now(timezone.utc))
            if (sample.quality == "ok" and sample.observed_at is not None
                    and sample.observed_at >= begun):
                delta = sample.value - session["starting_energy_kwh"]
                if delta >= -0.00001:
                    delivered = round(max(delta, 0), 6)
                    meter_at = sample.observed_at.isoformat()
        if session.get("requested_budget_amount") is not None:
            last_meter = session.get("budget_last_meter_value")
            # Never persist a "qualified" zero-cost receipt if independently
            # measured energy exists after the last proven tariff increment.
            if (delivered is None or sample is None or last_meter is None
                    or sample.value > last_meter + 0.000001
                    or sample.value < last_meter - 0.000001):
                session["budget_quality"] = "unknown"
        cost, currency = None, None
        if (delivered is not None and self.runtime.observations.get(
                "sources", {}).get("tariff_quality") == "OK"):
            matching = [p for p in self.runtime.price_slots
                        if p.start <= begun and p.end >= end]
            if len(matching) == 1 and matching[0].basis == "effective":
                cost = round(delivered * matching[0].effective_price_per_kwh, 6)
                currency = matching[0].currency
        self._session_history.append({
            "charger_id": charger_id, "asset_id": session["asset_id"],
            "intent_key": session.get("intent_key"),
            "started_at": begun.isoformat(), "ended_at": end.isoformat(),
            "duration_minutes": round((end - begun).total_seconds() / 60, 3),
            "actual_energy_kwh": delivered,
            "energy_quality": "measured" if delivered is not None else "unknown",
            "meter_entity": source, "meter_observed_at": meter_at,
            "cost": cost, "currency": currency,
            "cost_quality": "qualified_effective_tariff" if cost is not None else "unknown",
            "stop_reason": reason, "physical_stop_confirmed": reason != "NATIVE_SWITCH_STATE",
            "switch_stop_confirmed": True,
            "budget_accrued_cost": (
                session.get("budget_cost")
                if session.get("budget_quality") in (
                    "qualified_effective_meter_increments",
                    "conservative_effective_upper_bound")
                else None
            ),
            "budget_cost_quality": session.get("budget_quality", "not_applicable"),
            "budget_currency": session.get("requested_budget_currency"),
            **({"draw_evidence": session["draw_evidence"]}
               if session.get("draw_evidence") and reason != "NATIVE_SWITCH_STATE" else {}),
        })
        self.session_history_revision += 1

    def accepted_slots(self):
        """Actual admitted slots only, never future proposals masquerading as execution."""
        threshold = datetime.now(timezone.utc) - timedelta(hours=48)
        return {
            key: deepcopy(value) for key, value in self._accepted_history.items()
            if value["end"] >= threshold
        }

    def capabilities(self):
        """Expose exact current action eligibility; no optimistic UI guessing."""
        result = {}
        at = datetime.now(timezone.utc)
        for configured in self.runtime.configuration["chargers"]:
            charger = self.effective_charger(configured)
            uid = charger["id"]
            if self._stopped:
                reason = "INTEGRATION_UNLOADED"
            elif not self._persistence_verified:
                reason = "CONTROL_STATE_UNVERIFIED"
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
            elif uid in self._paused:
                reason = "USER_PAUSED"
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
            # Keep a real, actionable readiness reason even on an
            # uncommissioned/empty site. Finite manual intent is a legitimate
            # UI preparation; physical START remains guarded by the executor.
            if charger.get("asset") is not None:
                manual_reason = "MANUAL_ONE_OFF_REQUIRES_UNASSIGNED_CHARGER"
            elif self._stopped:
                manual_reason = "INTEGRATION_UNLOADED"
            elif not self._persistence_verified:
                manual_reason = "CONTROL_STATE_UNVERIFIED"
            elif charger.get("control_owner") != "multicharge":
                manual_reason = "EXTERNAL_WRITER_OWNS_CHARGER"
            elif charger.get("physical_commissioned") is not True:
                manual_reason = "PHYSICAL_COMMISSIONING_REQUIRED"
            elif not str(charger.get("control_entity", "")).startswith("switch."):
                manual_reason = "NATIVE_SWITCH_REQUIRED"
            elif self._switch(self.runtime.hass, charger["control_entity"]) is None:
                manual_reason = "NATIVE_SWITCH_UNAVAILABLE"
            elif self._switch(self.runtime.hass, charger["control_entity"]).state != "off":
                manual_reason = "SWITCH_ALREADY_ON"
            else:
                manual_reason = self._admit_start(
                    charger, at,
                    target_current=(
                        charger.get("min_current_a")
                        if charger.get("kind") == "variable_current" else None
                    ),
                    manual_request={"duration_minutes": 30},
                )
            if manual_reason is None and uid in self._quarantine:
                manual_reason = "PREVIOUS_COMMAND_UNCONFIRMED"
            # Shared actual admission checks, evaluated for each finite goal.
            # A duration-only guest must not borrow the readiness of a meter goal.
            goals = {"duration": manual_reason or "READY"}
            for goal, request in (
                ("energy", {"energy_kwh": 1}),
                ("budget", {"cost_amount": 1, "currency": "EUR"}),
            ):
                if manual_reason not in (None, "PHYSICAL_CONNECTION_UNVERIFIED",
                                         "INDEPENDENT_POWER_UNAVAILABLE"):
                    goal_reason = manual_reason
                else:
                    goal_reason = self._admit_start(
                        charger, at, target_current=(
                            charger.get("min_current_a")
                            if charger["kind"] == "variable_current" else None
                        ), manual_request=request,
                    )
                if goal_reason is None and uid in self._quarantine:
                    goal_reason = "PREVIOUS_COMMAND_UNCONFIRMED"
                goals[goal] = goal_reason or "READY"
            result[uid] = {
                "manual_goal_reasons": goals,
                "paused": uid in self._paused,
                "pause_allowed": stop_allowed and uid not in self._paused
                    and self._persistence_verified,
                "resume_allowed": stop_allowed and uid in self._paused
                    and uid not in self._quarantine and self._persistence_verified,
                "manual_one_off_allowed": manual_reason is None,
                "manual_one_off_reason": manual_reason or "READY",
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
        if status == "confirmed" and action in ("stop", "pause"):
            # A stopped, physically confirmed and attributable session is
            # reconciled before a future planned session may resume. An
            # unknown meter delta keeps the earlier in-flight safety hold.
            session = self._sessions.get(uid)
            self._archive_session(uid, observed_at, reason)
            if session is not None:
                receipt = self._session_history[-1] if self._session_history else None
                hold_key = session.get("asset_id") or f"charger:{uid}"
                expected = session.get("intent_key") if session.get("asset_id") else None
                if (receipt is not None and receipt["charger_id"] == uid
                        and receipt.get("asset_id") == session.get("asset_id")
                        and receipt.get("intent_key") == expected
                        and (receipt.get("physical_stop_confirmed") is True
                             or (session.get("duration_without_connection") and receipt.get("switch_stop_confirmed")))
                        and (session.get("requested_kwh") is None
                             or receipt.get("actual_energy_kwh") is not None)):
                    self._inflight.pop(hold_key, None)
            if reason == "NATIVE_SWITCH_STATE":
                self._inflight.pop(f"charger:{uid}", None)
            self._quarantine.discard(uid)
            self._sessions.pop(uid, None)
            self._draw_samples.pop(uid, None)
            self._close_accepted_history(uid, observed_at)
            self._accepted.pop(uid, None)
        if status == "confirmed":
            # A command receipt legitimately changes the remaining-demand
            # proposal. Do not revoke a different charger's immutable grant
            # merely because our own confirmed command refreshed the view.
            # An unrelated revision change still invalidates this batch.
            prior = self.runtime.assessment
            own_refresh = (self._grant_configuration is not None and prior is not None
                           and prior.plan.revision == self._grant_plan_revision)
            self.runtime.refresh()
            if own_refresh:
                refreshed = self.runtime.assessment
                self._grant_plan_revision = refreshed.plan.revision if refreshed else None
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

    def _qualified_budget_price(self, at, currency):
        """One covered, actual effective native tariff, never spot/reference."""
        if self.runtime.observations.get("sources", {}).get("tariff_quality") != "OK":
            return None
        quotes = [
            item for item in self.runtime.price_slots
            if item.basis == "effective" and item.currency == currency
            and item.start <= at < item.end
        ]
        return quotes[0] if len(quotes) == 1 else None

    def _asset_price_policy_issue(self, asset, at, *, finite_goal=False):
        """One tariff/SoC policy for START and ongoing physical supervision.

        The owner never infers a currency, settled price or BMS SoC. A
        price policy can restrict an already energised Charger as well as
        prevent a new start, avoiding a second policy evaluator in HA.
        """
        if not any(asset.get(field) is not None for field in (
                "maximum_price_per_kwh", "low_price_trigger_per_kwh")):
            return None
        currency = asset.get("price_currency")
        if self.runtime.observations.get("sources", {}).get(
                "tariff_quality") != "OK":
            return "PRICE_SOURCE_UNAVAILABLE"
        current_quotes = [
            row for row in self.runtime.price_slots
            if row.start <= at < row.end and row.currency == currency
        ]
        if len(current_quotes) != 1:
            return "PRICE_POLICY_CURRENCY_MISMATCH"
        future_deadline = at + timedelta(hours=48)
        if (asset.get("ready_by")
                or asset.get("ready_by_repeat") == "specific_days"):
            try:
                raw = asset.get("ready_by")
                anchor = datetime.fromisoformat(raw) if raw else None
                repeat = asset.get("ready_by_repeat", "none")
                if repeat != "none":
                    due, issue = resolve_recurring_ready_by(
                        anchor, at, repeat,
                        self.runtime.hass.config.time_zone,
                        asset.get("ready_by_weekdays"),
                    )
                    if due is None:
                        return issue
                else:
                    due = anchor
                if due is not None:
                    future_deadline = min(future_deadline, due)
            except (ValueError, TypeError):
                return "READY_BY_INVALID"
        price_cap, issue = qualified_price_policy_cap(
            asset.get("maximum_price_per_kwh"),
            asset.get("opportunistic_kind", "off"),
            asset.get("opportunistic_level_pct"),
            currency, self.runtime.price_slots, at, future_deadline,
        )
        if issue:
            return issue
        actual_rate = current_quotes[0].effective_price_per_kwh
        low_price = asset.get("low_price_trigger_per_kwh")
        low_price_eligible = (
            low_price is not None and actual_rate <= low_price + 1e-9
        )
        priority_eligible = False
        if not finite_goal and (
                asset.get("minimum_soc_pct") is not None
                or asset.get("low_soc_trigger_pct") is not None):
            soc = soc_with_health(
                self.runtime.hass, asset.get("soc_entity"),
                asset.get("soc_stale_entity"), at,
            )
            if soc.quality != "ok":
                return "SOC_PRIORITY_SOURCE_UNAVAILABLE"
            priority_eligible = any(
                soc.value < asset[field]
                for field in ("minimum_soc_pct", "low_soc_trigger_pct")
                if asset.get(field) is not None
            )
        if (price_cap is not None and actual_rate > price_cap + 1e-9
                and not priority_eligible and not low_price_eligible):
            return "PRICE_LIMIT_BLOCKED"
        return None


    def _admit_start(self, charger, at, *, planned=False, target_current=None,
                     manual_request=None, plan_slot=None, own_intent=False,
                     energized=False):
        cfg = self.runtime.configuration
        ctl = cfg["controller"]
        if not self._persistence_verified:
            return "CONTROL_STATE_UNVERIFIED"
        if charger["id"] in self._paused:
            return "USER_PAUSED"
        if not planned and ctl.get("mode") != "Force Charge" and not (
                manual_request is not None and ctl.get("mode") == "Automatic"):
            return "MANUAL_START_REQUIRES_FORCE_CHARGE"
        if planned and ctl.get("mode") not in (
            "Automatic", "Solar", "Economy", "Ready By"
        ):
            return "AUTOMATIC_MODE_NOT_ENABLED"
        asset = next(
            (a for a in cfg["assets"] if a["id"] == charger.get("asset")), None
        )
        if manual_request is not None:
            if planned or charger.get("asset") is not None:
                return "MANUAL_ONE_OFF_REQUIRES_UNASSIGNED_CHARGER"
            if not isinstance(manual_request, dict):
                return "ONE_FINITE_MANUAL_LIMIT_REQUIRED"
            amount = manual_request.get("energy_kwh")
            duration = manual_request.get("duration_minutes")
            money = manual_request.get("cost_amount")
            currency = manual_request.get("currency")
            if money is not None:
                if (set(manual_request) != {"cost_amount", "currency"}
                        or type(money) not in (int, float)
                        or not isfinite(money) or not 0 < money <= 10000
                        or not isinstance(currency, str)
                        or len(currency) != 3 or not currency.isascii()
                        or not currency.isalpha() or not currency.isupper()):
                    return "MANUAL_BUDGET_INVALID"
            elif len(manual_request) != 1:
                return "ONE_FINITE_MANUAL_LIMIT_REQUIRED"
            if amount is not None:
                if type(amount) not in (float, int) or not isfinite(amount) or not 0 < amount <= 1000:
                    return "MANUAL_ENERGY_LIMIT_INVALID"
            elif money is None and (type(duration) is not int or not 1 <= duration <= 1440):
                return "MANUAL_DURATION_LIMIT_INVALID"
        else:
            if asset is None:
                return "ASSET_NOT_ASSIGNED"
            if (asset.get("temporary")
                    and datetime.fromisoformat(asset["expires_at"]) <= at):
                return "TEMPORARY_ASSET_EXPIRED"
            amount = asset.get("requested_kwh")
            duration = asset.get("requested_duration_minutes")
            money = asset.get("requested_budget_amount")
            currency = asset.get("requested_budget_currency")
        # Check the actual source before accounting or intent reconciliation:
        # a confirmed disconnect must report the physical blocker, not an
        # unrelated missing energy-meter progress from a completed session.
        cable = self._connection(charger, at)
        bounded_switch = charger["kind"] == "on_off" and duration is not None
        if (not (bounded_switch and self.duration_connection_allowed(cable))
                and (cable.quality != "ok" or cable.value is not True)):
            return "PHYSICAL_CONNECTION_UNVERIFIED"
        if asset is not None and asset.get("charging_windows"):
            if not charging_window_allows(
                asset["charging_windows"], at, timedelta(seconds=1),
                self.runtime.hass.config.time_zone,
            ):
                return "CHARGING_WINDOW_CLOSED"
        if asset is not None and asset.get("earliest_start_at"):
            earliest = datetime.fromisoformat(asset["earliest_start_at"])
            if at < earliest:
                return "EARLIEST_START_NOT_REACHED"
        if asset is not None:
            policy_issue = self._asset_price_policy_issue(
                asset, at,
                finite_goal=(amount is not None or duration is not None
                             or money is not None),
            )
            if policy_issue:
                return policy_issue
        if manual_request is None and (amount is not None or duration is not None or money is not None):
            raw_due = asset.get("ready_by")
            due = datetime.fromisoformat(raw_due) if raw_due else None
            if asset.get("ready_by_repeat", "none") != "none" and (due is not None or asset.get("ready_by_repeat") == "specific_days"):
                due, error = resolve_recurring_ready_by(
                    due, at, asset["ready_by_repeat"],
                    self.runtime.hass.config.time_zone,
                    asset.get("ready_by_weekdays"),
                )
                if due is None:
                    return error
            progress = self.measured_intent_usage(asset, charger, due, at)
            if money is not None:
                if progress.get("budget_amount") is None:
                    return "BUDGET_MEASURED_PROGRESS_UNAVAILABLE"
                money = max(0.0, money - progress["budget_amount"])
                # An indicative euro budget cannot grant unlimited charging
                # at free/negative prices. Per-intent physical running time
                # remains bounded across all earlier confirmed sessions.
                if (money <= 0.000001
                        or progress["duration_minutes"] >= 24 * 60
                        or self.intent_completed(asset, charger, due)):
                    return "TARGET_ALREADY_MET"
            if amount is not None:
                if progress["energy_kwh"] is None:
                    return "ASSET_MEASURED_PROGRESS_UNAVAILABLE"
                amount = max(0, amount - progress["energy_kwh"])
            if duration is not None:
                if progress["duration_minutes"] is None:
                    return "ASSET_DURATION_PROGRESS_UNAVAILABLE"
                duration = max(0, duration - progress["duration_minutes"])
                if duration <= 0:
                    return "TARGET_ALREADY_MET"
        if (charger["kind"] == "variable_current" or ctl.get("phase_limits_a")
                or charger.get("circuit_id")) and charger.get("phase_count") not in (1, 2, 3):
            return "PHYSICAL_PHASES_UNVERIFIED"
        requested_kw = charger["rated_power_kw"]
        if charger["kind"] == "variable_current":
            problem, requested_kw = self._requested_current(
                charger, target_current, at
            )
            if problem:
                return problem
        if (asset is not None and asset.get("max_charge_kw") is not None
                and requested_kw > asset["max_charge_kw"] + 1e-9):
            return "ASSET_POWER_CAP_REQUIRES_MODULATION"
        if amount is not None and amount > 0:
            if not charger.get("energy_entity"):
                return "MEASURED_ENERGY_METER_REQUIRED"
            meter = number(self.runtime.hass, charger["energy_entity"], "energy", at)
            if meter.quality != "ok":
                return "MEASURED_ENERGY_UNAVAILABLE"
        if amount is not None and amount <= 0:
            return "TARGET_ALREADY_MET"
        if money is not None:
            if not charger.get("energy_entity"):
                return "BUDGET_ENERGY_METER_REQUIRED"
            observed_meter = number(
                self.runtime.hass, charger["energy_entity"], "energy", at
            )
            if observed_meter.quality != "ok":
                return "BUDGET_ENERGY_METER_UNAVAILABLE"
            if self._qualified_budget_price(at, currency) is None:
                return "BUDGET_EFFECTIVE_TARIFF_UNAVAILABLE"
        if manual_request is None and duration is None and amount is None and money is None:
            if not all(k in asset for k in ("soc_entity", "target_soc")):
                return "ASSET_DEMAND_UNVERIFIED"
            if planned and not all(k in asset for k in ("capacity_kwh", "charge_efficiency")):
                return "ASSET_DEMAND_UNVERIFIED"
            soc = soc_with_health(
                    self.runtime.hass, asset["soc_entity"],
                    asset.get("soc_stale_entity"), at,
                )
            if soc.quality != "ok":
                return "ASSET_SOC_UNAVAILABLE"
            if soc.value >= asset["target_soc"]:
                return "TARGET_ALREADY_MET"
        if asset is not None and (
                asset.get("ready_by")
                or asset.get("ready_by_repeat") == "specific_days"):
            try:
                due = (datetime.fromisoformat(
                    asset["ready_by"].replace("Z", "+00:00")
                ) if asset.get("ready_by") else None)
                repeat = asset.get("ready_by_repeat", "none")
                if repeat != "none":
                    due, reason = resolve_recurring_ready_by(
                        due, at, repeat, self.runtime.hass.config.time_zone,
                        asset.get("ready_by_weekdays"),
                    )
                    if due is None:
                        return reason
                if due is None or due.tzinfo is None or due.utcoffset() is None or at >= due:
                    return "READY_BY_EXPIRED"
            except ValueError:
                return "READY_BY_INVALID"
        if (manual_request is None and not bounded_switch
                and self.connection_confirmation(charger, at) is None):
            return "CURRENT_PLUG_ASSET_UNCONFIRMED"
        this_power = number(self.runtime.hass, charger.get("power_entity"), "power", at)
        if this_power.quality != "ok" and not bounded_switch:
            return "INDEPENDENT_POWER_UNAVAILABLE"
        if this_power.quality == "ok":
            if not energized and this_power.value > start_power_limit(charger):
                return "POWER_ALREADY_PRESENT_WITHOUT_CONFIRMED_OWNER"
            if energized and this_power.value > requested_kw * 1.10 + 0.01:
                return "PHYSICAL_POWER_EXCEEDS_AUTHORIZED_LIMIT"
        # The final admission gate prevents a previous manual Force start
        # from replaying after a crash. Earlier source/guest checks keep their
        # more specific, equally fail-closed reasons.
        if not planned and not own_intent and (
            (asset is not None and asset["id"] in self._inflight)
            or (manual_request is not None
                and f"charger:{charger['id']}" in self._inflight)
        ):
            return "UNRESOLVED_PREVIOUS_CHARGE_INTENT"
        return self._physical_budget(
            charger, at, requested_kw,
            target_current if charger["kind"] == "variable_current"
            else charger.get("fixed_current_a"), plan_slot=plan_slot,
        )


    def effective_charger(self, charger):
        """Use native number bounds when not declared; never persist guesses."""
        if charger["kind"] != "variable_current":
            return charger
        if not str(charger.get("current_control_entity", "")).startswith("number."):
            return charger
        device = self.runtime.hass.states.get(charger["current_control_entity"])
        if device is None or device.state in ("unknown", "unavailable"):
            return charger
        try:
            attrs = device.attributes
            lo, hi, step = (float(attrs[key]) for key in ("min", "max", "step"))
            if (attrs.get("unit_of_measurement") != "A"
                    or not all(isfinite(x) for x in (lo, hi, step))
                    or lo <= 0 or hi < lo or step <= 0 or (hi-lo)/step > 1000):
                return charger
        except (KeyError, TypeError, ValueError, OverflowError):
            return charger
        # Both the configured ceiling and the actual native setpoint grid
        # constrain planning. Never propose a current the executor will reject.
        declared_min = charger.get("min_current_a", lo)
        declared_max = charger.get("max_current_a", hi)
        declared_step = charger.get("current_step_a", step)
        feasible = []
        for index in range(floor((hi-lo)/step+1e-7)+1):
            current = lo+index*step
            if current < declared_min-1e-7 or current > declared_max+1e-7:
                continue
            offset = (current-declared_min)/declared_step
            if abs(offset-round(offset)) <= 1e-6:
                feasible.append(round(current, 9))
        if not feasible:
            # Preserve the nominal rating for a labelled preview only.
            return {**charger, "min_current_a": None, "max_current_a": None,
                    "current_step_a": None}
        spacing = feasible[1]-feasible[0] if len(feasible)>1 else step
        if any(abs(b-a-spacing)>1e-6 for a, b in zip(feasible, feasible[1:])):
            return {**charger, "min_current_a": None, "max_current_a": None,
                    "current_step_a": None}
        return {**charger, "min_current_a": feasible[0],
                "max_current_a": feasible[-1], "current_step_a": round(spacing, 9)}

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
        if not str(entity).startswith("number.") or (reading and not str(reading).startswith("sensor.")):
            return "CURRENT_WRITE_OR_INDEPENDENT_READBACK_MISSING", None
        if not reading and not charger.get("power_entity"):
            return "CURRENT_OR_POWER_READBACK_REQUIRED", None
        device = self.runtime.hass.states.get(entity)
        if device is None or device.state in ("unavailable", "unknown"):
            return "CURRENT_CONTROL_UNAVAILABLE", None
        if device.attributes.get("unit_of_measurement") != "A":
            return "NATIVE_CURRENT_UNIT_UNSUPPORTED", None
        try:
            attrs = device.attributes
            hmin, hmax, hstep = (float(attrs["min"]), float(attrs["max"]),
                                 float(attrs["step"]))
            if (not all(isfinite(x) for x in (hmin,hmax,hstep)) or hstep <= 0
                    or current < hmin or current > hmax):
                return "NATIVE_CURRENT_CAPABILITY_MISMATCH", None
            if abs((current - hmin) / hstep - round((current - hmin) / hstep)) > 1e-5:
                return "NATIVE_CURRENT_STEP_MISMATCH", None
        except (KeyError, ValueError, TypeError, OverflowError, ZeroDivisionError):
            return "NATIVE_CURRENT_CAPABILITY_UNVERIFIED", None
        phases = charger.get("phase_ids") or []
        voltage = charger.get("voltage_v")
        count = charger.get("phase_count")
        if (count not in (1, 2, 3) or (phases and (
                count != len(phases) or len(phases) != len(set(phases))))
                or not isinstance(voltage, (float, int)) or not 200 <= voltage <= 260):
            return "ELECTRICAL_WIRING_UNVERIFIED", None
        kw = float(current) * voltage * count / 1000
        if (charger.get("min_charging_power_kw") is not None
                and kw + 1e-9 < charger["min_charging_power_kw"]):
            return "BELOW_USER_CHARGING_POWER_MINIMUM", None
        if (charger.get("max_charging_power_kw") is not None
                and kw > charger["max_charging_power_kw"] + 1e-9):
            return "ABOVE_USER_CHARGING_POWER_MAXIMUM", None
        if kw > charger["rated_power_kw"] + 1e-9:
            return "RATED_CHARGER_POWER_EXCEEDED", None
        asset = next((a for a in self.runtime.configuration["assets"] if a["id"] == charger.get("asset")), None)
        if asset and asset.get("max_charge_kw") is not None and kw > asset["max_charge_kw"] + 1e-9:
            return "ASSET_POWER_CAP_REQUIRES_MODULATION", None
        return None, round(kw, 6)


    def _highest_safe_current(self, charger, at, *, ceiling=None, plan_slot=None,
                              reserve_minima=False):
        """Highest currently qualified safe setpoint, bounded by any slot grant."""
        minimum = charger.get("min_current_a")
        maximum = charger.get("max_current_a")
        step = charger.get("current_step_a")
        if not all(isinstance(x, (float, int)) and isfinite(x) and x > 0
                   for x in (minimum, maximum, step)) or maximum < minimum:
            return None
        if ceiling is not None:
            maximum = min(maximum, ceiling)
        count = floor((maximum - minimum) / step + 1e-9)
        if count > 1000 or count < 0:
            return None
        for index in range(count, -1, -1):
            candidate = round(minimum + index * step, 6)
            reason, kw = self._requested_current(charger, candidate, at)
            if reason is None and self._physical_budget(
                charger, at, kw, candidate, plan_slot=plan_slot,
                reserve_minima=reserve_minima
            ) is None:
                return candidate
        return None

    def _physical_budget(self, charger, at, kw, current, *, plan_slot=None,
                         reserve_minima=False):
        """Conservative site, phase and circuit budget across all configured sources."""
        cfg = self.runtime.configuration
        ctl = cfg["controller"]
        cap = ctl.get("max_power_kw")
        selected = ctl.get("binding_entity") or ctl.get("site_power_entity")
        if selected:
            envelope, quality = binding(self.runtime.hass, selected, at)
            if envelope is None or quality != "OK":
                return "BINDING_CAPACITY_UNAVAILABLE"
            until = at + timedelta(seconds=30)
            slots = [s for s in envelope.slots if s.start <= at and s.end >= until]
            if len(slots) != 1 or envelope.valid_until < until:
                return "BINDING_CAPACITY_SLOT_MISSING"
            cap = slots[0].max_charging_kw if cap is None else min(cap, slots[0].max_charging_kw)
        occupied, reserved = 0, kw
        phase_totals = {}
        circuits = {}
        for other in cfg["chargers"]:
            if other["id"] == charger["id"]:
                continue
            power = number(self.runtime.hass, other.get("power_entity"), "power", at)
            state = self._switch(self.runtime.hass, other.get("control_entity"))
            # Use the declared rating as a reservation, not a fabricated measurement.
            if power.quality != "ok":
                power = Evidence(other["rated_power_kw"] if state is None or state.state == "on" else 0.0,
                                 "estimated", None, "DECLARED_CAPACITY_RESERVATION")
            # An inactive configured Charger need not expose a control switch.
            # Both a fresh physical disconnect AND zero measured power prove
            # this *present* plug cannot energize; do not reserve a phantom
            # parallel slot. Connected, stale or unknown physical state still
            # reserves declared capacity where required by configured shared limits.
            unknown_external_state = (
                state is None
                and other.get("control_owner") != "multicharge"
            )
            if other.get("control_owner") != "multicharge" and power.quality == "ok" and power.value <= stop_power_limit(other) and (state is None or state.state == "off"):
                continue
            if state is None and not unknown_external_state:
                return "OTHER_CHARGER_OWNER_OR_STATE_UNKNOWN"
            # Another independently controlled charger may start at any time
            # without exposing its switch. Reserve its full rated capacity
            # even when measured power is currently zero. Known measured
            # higher draw always wins over nominal.
            externally_powered = (
                other.get("control_owner") != "multicharge"
                and power.value > stop_power_limit(other)
            )
            is_active = (
                (state is not None and state.state == "on")
                or externally_powered or unknown_external_state
            )
            if is_active:
                occupied += 1
                amps = other.get("fixed_current_a")
                shared_circuit = (charger.get("circuit_id")
                                  and other.get("circuit_id") == charger.get("circuit_id"))
                phase_limits = bool(ctl.get("phase_limits_a"))
                needs_amps = phase_limits or shared_circuit
                reserved_kw = max(power.value, other["rated_power_kw"])
                if other["kind"] == "variable_current":
                    session = self._sessions.get(other["id"])
                    target = session.get("target_current_a") if session else None
                    if needs_amps or target is not None:
                        sensed = number(self.runtime.hass,
                                        other.get("current_readback_entity"), "current", at)
                        if sensed.quality != "ok":
                            if target is not None and not other.get("current_readback_entity"):
                                setting = number(self.runtime.hass, other.get("current_control_entity"),
                                                 "current", at)
                                if setting.quality == "ok" and abs(setting.value-target) <= max(
                                        0.25, other.get("current_step_a", 1) / 2):
                                    amps = target
                                    if other.get("voltage_v") and other.get("phase_count"):
                                        reserved_kw = max(power.value, target * other["voltage_v"]
                                                          * other["phase_count"] / 1000)
                                elif needs_amps:
                                    return "OTHER_CHARGER_CURRENT_UNAVAILABLE"
                            elif needs_amps:
                                return "OTHER_CHARGER_CURRENT_UNAVAILABLE"
                        elif target is not None:
                            amps = max(sensed.value, target)
                            if other.get("voltage_v") and other.get("phase_count"):
                                reserved_kw = max(power.value, amps * other["voltage_v"]
                                                  * other["phase_count"] / 1000)
                        else:
                            # External adjustable load can increase within
                            # its declared envelope; reserve that envelope
                            # where a configured ampere constraint depends on it.
                            limit = other.get("max_current_a")
                            if limit is None:
                                return "OTHER_CHARGER_CURRENT_RANGE_UNAVAILABLE"
                            amps = max(sensed.value, limit)
                if reserve_minima:
                    # A temporarily reduced active charger keeps its admitted
                    # conservative allocation. Only genuinely unreserved
                    # headroom can be spent by the normal regulation cycle.
                    grant = self._accepted.get(other["id"], {}).get("_slot")
                    session = self._sessions.get(other["id"])
                    if (grant is not None and session is not None
                            and grant.asset_uid == session.get("asset_id")
                            and grant.start <= at < grant.end):
                        reserved_kw = max(reserved_kw, grant.expected_power_kw)
                        if needs_amps and other["kind"] == "variable_current":
                            voltage = other.get("voltage_v")
                            count = other.get("phase_count")
                            if amps is None or not voltage or not count:
                                return "OTHER_CHARGER_CURRENT_UNAVAILABLE"
                            amps = max(amps, grant.expected_power_kw * 1000 / (voltage * count))
                reserved += reserved_kw
                if needs_amps and amps is None:
                    return "OTHER_CHARGER_CURRENT_UNAVAILABLE"
                if phase_limits:
                    if not other.get("phase_ids"):
                        return "OTHER_CHARGER_PHASES_UNVERIFIED"
                    for phase in other["phase_ids"]:
                        phase_totals[phase] = phase_totals.get(phase, 0) + amps
                if shared_circuit:
                    key = other["circuit_id"]
                    circuits[key] = circuits.get(key, 0) + amps
            elif power.value > stop_power_limit(other):
                return "OTHER_CHARGER_POWER_WITH_SWITCH_OFF"
        if occupied >= ctl["max_parallel"]:
            return "MAX_PARALLEL_REACHED"
        if cap is not None and reserved > cap + 1e-9:
            return "SITE_CAPACITY_EXCEEDED"
        solar_required = (ctl.get("mode") == "Solar"
                          or getattr(plan_slot, "strategy", None) == "solar")
        if solar_required and ctl.get("solar_source_kind") in ("grid_export", "direct_surplus"):
            available_solar, quality = self.runtime.native_surplus_power(at)
            if quality != "OK" or available_solar is None:
                return "NATIVE_SOLAR_SOURCE_UNQUALIFIED"
            if reserved > available_solar + 1e-9:
                return "NATIVE_SOLAR_SURPLUS_INSUFFICIENT"
        elif solar_required and plan_slot is not None:
            # A selected solar interval is a ceiling, not an entitlement
            # to import more power on a later regulation tick.
            solar, quality = intervals(self.runtime.hass, ctl.get("solar_entity"), "solar", at)
            covering = [row for row in solar if row.start <= at < row.end]
            if quality != "OK" or len(covering) != 1:
                return "SOLAR_SOURCE_UNAVAILABLE"
            if reserved > covering[0].max_charging_kw + 1e-9:
                return "SOLAR_SURPLUS_INSUFFICIENT"
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

    async def _native_service(self, domain, service, data, context):
        """Bound the native service wait independently of physical readback."""
        await asyncio.wait_for(
            self.runtime.hass.services.async_call(
                domain, service, data, blocking=True, context=context,
            ), timeout=NATIVE_SERVICE_TIMEOUT_SECONDS,
        )

    async def _set_native_current(self, charger, current, context):
        """Native HA write only, not confirmation of physical charging current."""
        await self._native_service(
            "number", "set_value",
            {"entity_id": charger["current_control_entity"], "value": float(current)},
            context,
        )

    def _current_confirmed(self, charger, current, requested_at):
        reading = number(self.runtime.hass, charger.get("current_readback_entity"),
                         "current", datetime.now(timezone.utc))
        watts = number(self.runtime.hass, charger.get("power_entity"), "power",
                       datetime.now(timezone.utc))
        target_kw = current * charger["voltage_v"] * charger["phase_count"] / 1000
        tolerance = max(0.25, charger.get("current_step_a", 1) / 2)
        # A native EVSE current setting is a ceiling, not a promise that
        # the vehicle will consume exactly that current. Confirm the setpoint
        # separately from actual draw; tapering or lower vehicle acceptance is valid.
        setting = number(self.runtime.hass, charger.get("current_control_entity"),
                         "current", datetime.now(timezone.utc))
        if not (setting.quality == "ok" and setting.observed_at is not None
                and setting.observed_at >= requested_at
                and abs(setting.value-current) <= tolerance
                and watts.quality == "ok" and watts.observed_at is not None
                and watts.observed_at >= requested_at
                and 0 <= watts.value <= target_kw * 1.10 + 0.01):
            return False
        if not charger.get("current_readback_entity"):
            return True
        return (reading.quality == "ok" and reading.observed_at is not None
                and reading.observed_at >= requested_at
                and 0 <= reading.value <= current + tolerance)

    async def _protective_stop(self, charger, context):
        """Best-effort real STOP on an unconfirmed START, never claim it succeeded."""
        try:
            await self._native_service(
                "switch", "turn_off", {"entity_id": charger["control_entity"]}, context,
            )
            return True
        except Exception:
            _LOGGER.exception("Protective STOP could not be delivered for %s",
                              charger["id"])
            return False

    def _update_budget_progress(self, charger, session, now):
        """One measured-increment calculation for live and final receipts."""
        # Physical metering is the source of progress. Price intervals
        # must cover each actually observed meter increment completely.
        currency = session["requested_budget_currency"]
        sample = number(
            self.runtime.hass, charger.get("energy_entity"), "energy", now
        )
        if sample.quality != "ok" or sample.observed_at is None:
            session["budget_quality"] = "unknown"
            return "BUDGET_ENERGY_METER_UNAVAILABLE"
        before = session.get("budget_last_meter_value")
        since = session.get("budget_last_meter_at")
        if before is None or since is None:
            session["budget_quality"] = "unknown"
            return "BUDGET_METER_BASELINE_MISSING"
        delta = sample.value - before
        if delta < -0.00001:
            session["budget_quality"] = "unknown"
            return "BUDGET_ENERGY_METER_RESET"
        if delta > 0.000001:
            if sample.observed_at <= since:
                session["budget_quality"] = "unknown"
                return "BUDGET_METER_TIMESTAMP_UNVERIFIED"
            # Meter delta may span several effective-price windows.
            # Without meter readings at the boundary, exact kWh split
            # is unknowable: consume the conservative MAX rate across
            # each actually covered interval, never an average invoice.
            covered_until = since
            max_rate = 0.0
            covered_periods = 0
            while covered_until < sample.observed_at:
                matches = [
                    p for p in self.runtime.price_slots
                    if p.basis == "effective" and p.currency == currency
                    and p.start <= covered_until < p.end
                ]
                if len(matches) != 1:
                    session["budget_quality"] = "unknown"
                    return "BUDGET_TARIFF_BOUNDARY_UNVERIFIED"
                price = matches[0]
                max_rate = max(max_rate, price.effective_price_per_kwh)
                next_boundary = min(price.end, sample.observed_at)
                if next_boundary <= covered_until:
                    session["budget_quality"] = "unknown"
                    return "BUDGET_TARIFF_BOUNDARY_UNVERIFIED"
                covered_until = next_boundary
                covered_periods += 1
            session["budget_cost"] += delta * max(0.0, max_rate)
            if covered_periods > 1:
                session["budget_quality"] = "conservative_effective_upper_bound"
            session["budget_last_meter_value"] = sample.value
            session["budget_last_meter_at"] = sample.observed_at
        return None

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
        if session["asset_id"] is None:
            if charger.get("asset") is not None:
                return "ACTIVE_SESSION_ASSIGNMENT_CHANGED"
        else:
            if asset is None or charger.get("asset") != session["asset_id"]:
                return "ACTIVE_SESSION_ASSIGNMENT_CHANGED"
            if not session.get("duration_without_connection"):
                identity = self.connection_confirmation(charger, now)
                if (identity is None or (session.get("connection_epoch") is not None
                        and identity["connected_at"] != session["connection_epoch"])):
                    return "CURRENT_PLUG_ASSET_UNCONFIRMED"
            if (asset.get("temporary")
                    and datetime.fromisoformat(asset["expires_at"]) <= now):
                return "TEMPORARY_ASSET_EXPIRED"
            if asset.get("charging_windows") and not charging_window_allows(
                asset["charging_windows"], now, timedelta(seconds=1),
                self.runtime.hass.config.time_zone,
            ):
                return "CHARGING_WINDOW_CLOSED"
            policy_issue = self._asset_price_policy_issue(
                asset, now, finite_goal=(
                    session["requested_kwh"] is not None
                    or session["requested_duration_minutes"] is not None
                    or session.get("requested_budget_amount") is not None),
            )
            if policy_issue:
                return policy_issue
        if now >= session["hard_stop_at"]:
            return "SESSION_SAFETY_DEADLINE_REACHED"
        if session["requested_duration_minutes"] is not None:
            if (now - session["started_at"]).total_seconds() >= (
                60 * session["requested_duration_minutes"]
            ):
                return "REQUESTED_DURATION_COMPLETE"
        if session["starting_energy_kwh"] is not None:
            obs = number(self.runtime.hass, charger.get("energy_entity"), "energy", now)
            required = (session["requested_kwh"] is not None
                        or session.get("requested_budget_amount") is not None)
            delivered = (obs.value - session["starting_energy_kwh"]
                         if obs.quality == "ok" else None)
            if delivered is None or delivered < -0.00001:
                if required:
                    return ("SESSION_ENERGY_METER_UNAVAILABLE" if delivered is None
                            else "SESSION_ENERGY_METER_RESET")
                # A missing optional meter affects accounting, not a finite
                # duration or SoC target. Do not reconstruct the lost baseline.
                session["starting_energy_kwh"] = None
                session["actual_energy_kwh"] = None
            else:
                session["actual_energy_kwh"] = round(max(0, delivered), 6)
                if (session["requested_kwh"] is not None
                        and delivered >= session["requested_kwh"]):
                    return "REQUESTED_ENERGY_COMPLETE"
        if session.get("requested_budget_amount") is not None:
            issue = self._update_budget_progress(charger, session, now)
            if issue:
                return issue
            currency = session["requested_budget_currency"]
            current = self._qualified_budget_price(now, currency)
            if current is None:
                session["budget_quality"] = "unknown"
                return "BUDGET_EFFECTIVE_TARIFF_UNAVAILABLE"
            remaining = (
                session["requested_budget_amount"] - session["budget_cost"]
            )
            if remaining <= 0.000001:
                return "REQUESTED_BUDGET_COMPLETE"
            # Leave conservative headroom for meter/provider cadence and STOP
            # latency; money shown to residents remains an estimate, not a bill.
            conservative_headroom = (
                max(0.0, current.effective_price_per_kwh)
                * charger["rated_power_kw"] * (120 / 3600) + 0.02
            )
            if remaining <= conservative_headroom:
                return "REQUESTED_BUDGET_COMPLETE"
        if session["soc_target"] is not None:
            # A same-type target edit is a current SoC objective, not a new meter intent.
            session["soc_target"] = asset.get("target_soc", session["soc_target"])
            soc = soc_with_health(
                    self.runtime.hass, asset.get("soc_entity"),
                    asset.get("soc_stale_entity"), now,
                )
            if soc.quality != "ok":
                return "SESSION_SOC_UNAVAILABLE"
            if soc.value >= session["soc_target"]:
                return "SOC_TARGET_REACHED"
        return None

    def _start_session(self, charger, observed, manual_request=None, *,
                       command_at, baseline, plug_epoch):
        """Adopt a confirmed physical start, with a bounded attributable intent."""
        asset = next(
            (a for a in self.runtime.configuration["assets"]
             if a["id"] == charger.get("asset")), None
        )
        if manual_request is None and asset is None:
            return "ASSET_NOT_ASSIGNED"
        now = datetime.now(timezone.utc)
        explicit_energy = (
            manual_request.get("energy_kwh") if manual_request is not None
            else asset.get("requested_kwh")
        )
        duration = (
            manual_request.get("duration_minutes") if manual_request is not None
            else asset.get("requested_duration_minutes")
        )
        budget = (
            manual_request.get("cost_amount") if manual_request is not None
            else asset.get("requested_budget_amount")
        )
        budget_currency = (
            manual_request.get("currency") if manual_request is not None
            else asset.get("requested_budget_currency")
        )
        intent_key = None
        budget_minutes = 24 * 60
        if asset is not None:
            raw_due = asset.get("ready_by")
            due = datetime.fromisoformat(raw_due) if raw_due else None
            if asset.get("ready_by_repeat", "none") != "none" and (due is not None or asset.get("ready_by_repeat") == "specific_days"):
                due, error = resolve_recurring_ready_by(
                    due, now, asset["ready_by_repeat"],
                    self.runtime.hass.config.time_zone,
                    asset.get("ready_by_weekdays"),
                )
                if due is None:
                    return error
            intent_key = self._intent_key(asset, charger, due)
            if explicit_energy is not None or duration is not None or budget is not None:
                progress = self.measured_intent_usage(asset, charger, due, now)
                if budget is not None:
                    if progress.get("budget_amount") is None or progress.get("duration_minutes") is None:
                        return "BUDGET_MEASURED_PROGRESS_UNAVAILABLE"
                    budget = max(0.0, budget - progress["budget_amount"])
                    budget_minutes = max(0.0, budget_minutes - progress["duration_minutes"])
                    if budget <= 0.000001 or budget_minutes <= 0:
                        return "TARGET_ALREADY_MET"
                if explicit_energy is not None:
                    if progress["energy_kwh"] is None:
                        return "ASSET_MEASURED_PROGRESS_UNAVAILABLE"
                    explicit_energy = max(0, explicit_energy - progress["energy_kwh"])
                if duration is not None:
                    if progress["duration_minutes"] is None:
                        return "ASSET_DURATION_PROGRESS_UNAVAILABLE"
                    duration = max(0, duration - progress["duration_minutes"])
        soc_target = (
            asset.get("target_soc")
            if (asset is not None and explicit_energy is None
                    and duration is None and budget is None)
            else None
        )
        starting_energy = None
        if charger.get("energy_entity"):
            sample = number(self.runtime.hass, charger["energy_entity"], "energy", now)
            if (baseline.quality == "ok" and sample.quality == "ok"
                    and sample.value >= baseline.value - 0.00001):
                starting_energy = baseline.value
            elif explicit_energy is not None or budget is not None:
                return ("SESSION_ENERGY_METER_RESET_AT_START"
                        if baseline.quality == sample.quality == "ok"
                        else "SESSION_ENERGY_METER_UNAVAILABLE")
        elif explicit_energy is not None or budget is not None:
            return "MEASURED_ENERGY_METER_REQUIRED"
        if budget is not None and self._qualified_budget_price(
                now, budget_currency) is None:
            return "BUDGET_EFFECTIVE_TARIFF_UNAVAILABLE"
        # Session cannot run longer than 24h on one manual authorization.
        end = command_at + timedelta(minutes=budget_minutes if budget is not None else 24 * 60)
        if duration is not None:
            end = min(end, command_at + timedelta(minutes=duration))
        if asset is not None and (
                asset.get("ready_by")
                or asset.get("ready_by_repeat") == "specific_days"):
            due = (datetime.fromisoformat(
                asset["ready_by"].replace("Z", "+00:00")
            ).astimezone(timezone.utc) if asset.get("ready_by") else None)
            if asset.get("ready_by_repeat", "none") != "none":
                due, _ = resolve_recurring_ready_by(
                    due, now, asset["ready_by_repeat"],
                    self.runtime.hass.config.time_zone,
                    asset.get("ready_by_weekdays"),
                )
            if due is None:
                return "READY_BY_UNAVAILABLE"
            end = min(end, due)
        identity = self.connection_confirmation(charger, now) if asset is not None else None
        if plug_epoch is not None and (identity is None or identity["connected_at"] != plug_epoch):
            return "CURRENT_PLUG_CHANGED_DURING_START"
        self._sessions[charger["id"]] = {
            "asset_id": asset["id"] if asset is not None else None,
            "connection_epoch": identity["connected_at"] if identity else None,
            "identity_basis": identity["basis"] if identity else None,
            "intent_key": intent_key,
            "manual_duration": manual_request is not None and duration is not None,
            "duration_without_connection": charger["kind"] == "on_off" and duration is not None,
            "manual_mode": (self.runtime.configuration["controller"]["mode"]
                            if manual_request is not None else None),
            "switch_only": observed.reason == "NATIVE_SWITCH_STATE",
            # Conservative control/accounting boundary; physical confirmation
            # is separately recorded, not backdated to the command.
            "started_at": command_at,
            "confirmed_at": observed.observed_at,
            "hard_stop_at": end,
            "requested_kwh": explicit_energy,
            "requested_duration_minutes": duration,
            "requested_budget_amount": budget,
            "requested_budget_currency": budget_currency,
            "budget_cost": 0.0 if budget is not None else None,
            "budget_quality": (
                "qualified_effective_meter_increments"
                if budget is not None else "not_applicable"
            ),
            "budget_last_meter_value": starting_energy,
            "budget_last_meter_at": command_at if budget is not None else None,
            "soc_target": soc_target,
            "starting_energy_kwh": starting_energy,
            "actual_energy_kwh": (round(max(0, sample.value-starting_energy), 6)
                                  if starting_energy is not None else None),
            "last_physical_readback": observed.observed_at,
            "target_current_a": None,
        }
        return None

    def _pending_start_issue(self, charger, at, plan_slot, current_a, manual_request,
                             configuration, *, energized=False):
        """Reuse admission after async boundaries, allowing only this intent."""
        current = self.runtime.configuration
        if current != configuration and not is_plan_presentation_only_change(configuration, current):
            return "CONFIGURATION_CHANGED_DURING_START"
        if plan_slot is not None and not self._grant_is_current(plan_slot, at):
            return "PLAN_SLOT_NOT_AUTHORIZED"
        # Re-read the native range and every applicable site/phase/circuit
        # constraint, not the old effective charger snapshot.
        raw = next((c for c in current["chargers"] if c["id"] == charger["id"]), None)
        if raw is None:
            return "UNKNOWN_CHARGER"
        fresh = self.effective_charger(raw)
        state = self._switch(self.runtime.hass, fresh.get("control_entity"))
        if state is None or (not energized and state.state != "off"):
            return "NATIVE_SWITCH_STATE_CHANGED_DURING_START"
        return self._admit_start(
            fresh, at, planned=plan_slot is not None, target_current=current_a,
            manual_request=manual_request, plan_slot=plan_slot, own_intent=True,
            energized=energized,
        )

    def _draw_binding(self, charger, asset):
        """Fingerprint only the existing identity and electrical source context."""
        fields = ("id", "asset", "kind", "control_entity", "connected_entity",
                  "connected_states", "disconnected_states", "power_entity",
                  "current_control_entity", "current_readback_entity", "phase_count",
                  "voltage_v", "phase_ids", "min_current_a", "max_current_a",
                  "current_step_a", "rated_power_kw", "min_charging_power_kw",
                  "max_charging_power_kw", "circuit_id", "circuit_limit_a")
        asset_fields = ("id", "kind", "soc_entity", "soc_stale_entity", "max_charge_kw",
                        "capacity_kwh", "charge_efficiency", "temporary")
        epochs = self.runtime.power_bindings.get(charger["id"], [])
        return sha256(dumps([
            {field: charger.get(field) for field in fields},
            {field: asset.get(field) for field in asset_fields},
            epochs[-1] if epochs else None,
        ], sort_keys=True).encode()).hexdigest()

    def prior_session_draw(self, charger, asset, at, soc):
        """Reuse a bounded observation, not a learned vehicle maximum.

        The newest same-owner receipt must itself contain qualified evidence.
        Old or changed source/wiring/SoC context returns to ordinary planning.
        The estimate never authorizes a command or changes reserved current.
        """
        if (charger["kind"] != "variable_current" or asset.get("temporary")
                or not asset.get("soc_entity") or soc.quality != "ok"
                or charger["id"] in self._sessions):
            return None
        for receipt in reversed(self._session_history):
            if (receipt["charger_id"] != charger["id"]
                    or receipt["asset_id"] != asset["id"]):
                continue
            draw = receipt.get("draw_evidence")
            if receipt.get("physical_stop_confirmed") is not True or not isinstance(draw, dict):
                return None
            try:
                stamp = datetime.fromisoformat(draw["observed_at"])
                begun = datetime.fromisoformat(receipt["started_at"])
                ended = datetime.fromisoformat(receipt["ended_at"])
                if (not begun <= stamp <= ended <= at
                        or at-stamp > timedelta(days=30)
                        or draw["binding"] != self._draw_binding(charger, asset)
                        or type(draw["sample_count"]) is not int or draw["sample_count"] < 3):
                    return None
                values = [draw[key] for key in ("power_kw", "setpoint_kw", "current_a",
                                                "soc_min", "soc_max")]
                if any(type(v) not in (int, float) or not isfinite(v) for v in values):
                    return None
                power_kw, setpoint_kw, current, soc_min, soc_max = values
                issue, qualified_kw = self._requested_current(charger, current, at)
                if (issue is not None or abs(qualified_kw-setpoint_kw) > 1e-6
                        or not 0 < power_kw <= setpoint_kw*1.10
                        or not 0 <= soc_min <= soc_max <= 100
                        or soc_max-soc_min > 5
                        or not soc_min-5 <= soc.value <= soc_max+5):
                    return None
            except (KeyError, TypeError, ValueError, OverflowError):
                return None
            return {"power_kw": power_kw, "setpoint_kw": setpoint_kw,
                    "observed_at": draw["observed_at"], "sample_count": draw["sample_count"],
                    "basis": "qualified_prior_session"}
        return None

    def qualified_session_draw(self, charger, asset, at, power, soc):
        """Short-lived same-session evidence, never a learned EV maximum.

        Require distinct fresh native reports under one verified setpoint,
        wiring, plug and narrow SoC band. A transient or changed setpoint
        cannot be treated as a sustained forecast. No persisted raw telemetry.
        """
        uid = charger["id"]
        session = self._sessions.get(uid)
        def clear():
            self._draw_samples.pop(uid, None)
            return None
        if (not session or charger["kind"] != "variable_current"
                or session.get("asset_id") != asset["id"]
                or uid in self._quarantine or uid in self._current_pending
                or uid in self._start_pending or uid in self._paused
                or power.quality != "ok" or power.observed_at is None
                or not timedelta(0) <= at-power.observed_at <= timedelta(minutes=2)
                or power.value <= start_power_limit(charger)):
            return clear()
        target = session.get("target_current_a")
        issue, setpoint_kw = self._requested_current(charger, target, at)
        if issue is not None:
            return clear()
        identity = self.connection_confirmation(charger, at)
        if (not identity or identity["connected_at"] != session.get("connection_epoch")
                or self._switch(self.runtime.hass, charger.get("control_entity")) is None
                or self._switch(self.runtime.hass, charger.get("control_entity")).state != "on"):
            return clear()
        setting = number(self.runtime.hass, charger.get("current_control_entity"), "current", at)
        if (setting.quality != "ok" or abs(setting.value-target) > 1e-6
                or power.value > target*charger["voltage_v"]*charger["phase_count"]/1000*1.10):
            return clear()
        if charger.get("current_readback_entity"):
            amps = number(self.runtime.hass, charger["current_readback_entity"], "current", at)
            if (amps.quality != "ok" or amps.observed_at is None
                    or not timedelta(0) <= at-amps.observed_at <= timedelta(minutes=2)
                    or amps.value > target+max(0.25, charger["current_step_a"]/2)):
                return clear()
            amp_kw = amps.value*charger["voltage_v"]*charger["phase_count"]/1000
            if abs(power.value-amp_kw) > max(0.15, power.value*0.20):
                return clear()
        soc_value = soc.value if soc.quality == "ok" else None
        key = (asset["id"], session["started_at"], identity["connected_at"], target,
               charger.get("power_entity"), charger.get("current_control_entity"),
               charger.get("current_readback_entity"), charger["phase_count"],
               charger["voltage_v"], tuple(charger.get("phase_ids", ())))
        prior = self._draw_samples.get(uid)
        rows = prior[1] if prior and prior[0] == key else []
        rows = [row for row in rows if timedelta(0) <= at-row[0] <= timedelta(minutes=10)]
        stamp = power.observed_at
        if stamp < session.get("confirmed_at", session["started_at"]):
            return clear()
        if rows and stamp < rows[-1][0]:
            return clear()
        if rows and stamp > rows[-1][0] and (
                stamp-rows[-1][0] > timedelta(minutes=3)
                or abs(power.value-rows[-1][1]) > max(0.1, rows[-1][1]*0.15)):
            rows = []
        if rows and ((soc_value is None) != (rows[0][2] is None)
                     or (soc_value is not None and abs(soc_value-rows[0][2]) > 5)):
            rows = []
        # Native providers can report every second. Keep enough temporal
        # span rather than evicting five minutes of evidence on every burst.
        if not rows or stamp-rows[-1][0] >= timedelta(seconds=30):
            rows.append((stamp, power.value, soc_value))
        rows = rows[-20:]
        self._draw_samples[uid] = (key, rows)
        if (len(rows) < 3 or rows[-1][0]-rows[0][0] < timedelta(minutes=5)
                or max(row[1] for row in rows)-min(row[1] for row in rows)
                   > max(0.1, min(row[1] for row in rows)*0.15)):
            return None
        draw = {"power_kw": round(min(row[1] for row in rows), 6),
                "setpoint_kw": setpoint_kw, "observed_at": rows[-1][0].isoformat(),
                "sample_count": len(rows), "basis": "sustained_current_session"}
        # Keep a single qualified summary in the original session receipt;
        # no historical raw samples, separate model, or persistence owner.
        if soc_value is not None and asset.get("soc_entity") and not asset.get("temporary"):
            session["draw_evidence"] = {
                **draw, "binding": self._draw_binding(charger, asset), "current_a": target,
                "soc_min": min(row[2] for row in rows),
                "soc_max": max(row[2] for row in rows),
            }
        return draw

    def _accept_slot(self, charger, slot, revision):
        """Accept only a physically confirmed current slot; keep bounded evidence."""
        # The native writer may have admitted a smaller setpoint than the
        # proposal. Never publish the proposed ceiling as physical acceptance.
        current = slot.current_a
        power = slot.power_kw
        if charger["kind"] == "variable_current":
            actual_target = self._sessions.get(charger["id"], {}).get("target_current_a")
            if actual_target is not None:
                current = actual_target
                power = round(current * charger["voltage_v"] * charger["phase_count"] / 1000, 6)
        confirmed = max(slot.start, datetime.now(timezone.utc))
        if confirmed >= slot.end or self._grants.get(charger["id"]) != slot:
            return False
        record = {
            "charger_id": charger["id"], "asset_id": slot.asset_uid,
            "start": slot.start, "end": slot.end,
            "confirmed_from": confirmed.isoformat(),
            "power_kw": power, "current_a": current,
            "revision": revision, "status": "accepted",
        }
        # Live authority never survives restart. The separately retained
        # quarter receipt is historical evidence only, not a replay grant.
        self._accepted[charger["id"]] = {
            **record, "_slot": slot, "_configuration": self._grant_configuration,
            "_prices": self._grant_prices,
        }
        self._accepted_history[(charger["id"], slot.start)] = record
        threshold = datetime.now(timezone.utc) - timedelta(hours=48)
        for key, old in list(self._accepted_history.items()):
            if old["end"] < threshold:
                del self._accepted_history[key]
        return True

    def _record_accepted_current(self, charger, current, at):
        accepted = self._accepted.get(charger["id"])
        if not accepted or not accepted["start"] <= at < accepted["end"]:
            return True
        if accepted["current_a"] is None or abs(accepted["current_a"] - current) <= 1e-6:
            return True
        power = round(current * charger["voltage_v"] * charger["phase_count"] / 1000, 6)
        receipt = self._accepted_history[(charger["id"], accepted["start"])]
        changes = receipt.setdefault("changes", [])
        if datetime.fromisoformat(changes[-1]["at"] if changes else
                                 receipt.get("confirmed_from", receipt["start"].isoformat())) >= at:
            # Do not fabricate chronology after a clock correction.
            self._persistence_verified = False
            return False
        accepted.update(current_a=current, power_kw=power)
        changes.append({"at": at.isoformat(), "current_a": current, "power_kw": power})
        return True

    def _close_accepted_history(self, uid, at):
        accepted = self._accepted.get(uid)
        if accepted and at is not None and at < accepted["end"]:
            confirmed = datetime.fromisoformat(accepted.get("confirmed_from", accepted["start"].isoformat()))
            receipt = self._accepted_history[(uid, accepted["start"])]
            # A stale STOP observation cannot extend the confirmed segment.
            close = max(confirmed, at)
            receipt["changes"] = [row for row in receipt.get("changes", [])
                                  if datetime.fromisoformat(row["at"]) < close]
            receipt["closed_at"] = close.isoformat()

    def _grant_is_current(self, slot, at):
        """Recheck grant after waiting for the native writer lock."""
        if (slot is None or self._grant_configuration is None
                or self._grants.get(slot.charger_uid) != slot
                or not slot.start <= at < slot.end):
            return False
        current = self.runtime.configuration
        assessment = self.runtime.assessment
        if not (assessment and assessment.plan.revision == self._grant_plan_revision
                and (current == self._grant_configuration
                     or is_plan_presentation_only_change(self._grant_configuration, current))):
            return False
        return self._slot_tariff_is_current(slot, at, self._grant_prices)

    def _slot_tariff_is_current(self, slot, at, prices):
        """A changed or lost selected tariff cannot inherit an earlier decision."""
        current = self.runtime.configuration
        asset = next((a for a in current["assets"] if a["id"] == slot.asset_uid), None)
        if asset is None:
            return False
        needs_price = (current["controller"]["mode"] == "Economy"
                       or slot.strategy in ("economy", "negative_tariff")
                       or any(asset.get(k) is not None for k in (
                           "maximum_price_per_kwh", "low_price_trigger_per_kwh",
                           "requested_budget_amount")))
        if needs_price:
            fresh, quality, _ = self.runtime.qualified_tariff(at)
            expected = [q for q in prices if q.start <= slot.start and q.end >= slot.end]
            available = [q for q in fresh if q.start <= at and q.end >= slot.end]
            if (quality != "OK" or len(expected) != 1 or len(available) != 1
                    or expected[0] != available[0]):
                return False
            # Opportunistic price thresholds depend on the future series.
            # A new horizon may change the selected strategy.
            if asset.get("opportunistic_kind", "off") != "off":
                if tuple(q for q in fresh if q.end > at) != tuple(
                        q for q in prices if q.end > at):
                    return False
        return True

    def _power_adjustment_due(self):
        interval = self.runtime.configuration["controller"].get(
            "power_adjustment_interval_minutes", 5,
        )
        # Wall time governs the quarter and physical receipts; elapsed
        # regulation time must not jump on NTP/timezone corrections.
        tick = monotonic()
        last = self._last_power_adjustment_tick
        if last is not None and tick-last < interval*60:
            return False
        self._last_power_adjustment_tick = tick
        return True

    def _active_grant_is_current(self, slot, at):
        """Revalidate an already admitted quarter; never authorize a new START."""
        if slot is None or not slot.start <= at < slot.end:
            return False
        uid = slot.charger_uid
        accepted = self._accepted.get(uid)
        session = self._sessions.get(uid)
        if (not accepted or accepted.get("_slot") != slot
                or not session or session.get("asset_id") != slot.asset_uid
                or session.get("manual_mode") is not None
                or uid in self._paused or uid in self._quarantine
                or not self._persistence_verified or self._stopped):
            return False
        if self.runtime.configuration["controller"].get("mode") not in (
            "Automatic", "Economy", "Solar", "Ready By",
        ):
            return False
        original = accepted.get("_configuration")
        if original is None:
            return False
        # A cadence edit is a runtime preference, not a new power grant.
        before, after = deepcopy(original), deepcopy(self.runtime.configuration)
        for cfg in (before, after):
            cfg["controller"].pop("power_adjustment_interval_minutes", None)
        if before != after and not is_plan_presentation_only_change(before, after):
            return False
        return self._slot_tariff_is_current(slot, at, accepted.get("_prices", ()))

    async def regulate_active_plan(self):
        """Spend fresh verified residual capacity in already admitted quarters.

        The same native writer and physical budget requalify each adjustment.
        The original forecast and minimum reservations are never rewritten.
        No unplanned START, separate scheduler, or delayed safety intervention.
        """
        if (self._stopped or self._supervising or self._regulating
                or not self._accepted or not self._power_adjustment_due()):
            return
        slots = {
            uid: record["_slot"] for uid, record in self._accepted.items()
            if record.get("_slot") is not None
        }
        self._regulating = True
        try:
            # Release first, then recompute upward candidates using actual
            # current readback and every other active minimum reservation.
            for increasing in (False, True):
                for configured in self.runtime.configuration["chargers"]:
                    uid = configured["id"]
                    slot = slots.get(uid)
                    now = datetime.now(timezone.utc)
                    if (configured.get("kind") != "variable_current"
                            or slot is None or slot.current_a is None
                            or not self._active_grant_is_current(slot, now)):
                        continue
                    charger = self.effective_charger(configured)
                    previous = self._sessions[uid].get("target_current_a")
                    if previous is None or self._session_stop_reason(charger, now):
                        continue
                    session = self._sessions[uid]
                    finite = (session.get("requested_duration_minutes") is not None
                              or session.get("requested_budget_amount") is not None)
                    # Finite time/money goals can restore their planned
                    # setpoint, never spend capacity beyond their original
                    # quarter reservation or change the budget projection.
                    target = self._highest_safe_current(
                        charger, now, plan_slot=slot, reserve_minima=True,
                        ceiling=slot.current_a if finite else None,
                    )
                    if target is None or abs(target - previous) <= 1e-6:
                        continue
                    # Normal redistribution may release boost, not another
                    # goal's minimum. Protective supervision separately
                    # enforces actual safety even when minima cannot fit.
                    factor = charger["voltage_v"] * charger["phase_count"] / 1000
                    if target * factor + 1e-6 < min(previous * factor, slot.expected_power_kw):
                        continue
                    if (target > previous) != increasing:
                        continue
                    await self.execute(uid, "set_current", current_a=target,
                                       plan_slot=slot, active_regulation=True)
        finally:
            self._regulating = False

    def _quarter_order(self, chargers, slots):
        """Release previous reservations before increasing or starting another load."""
        def order(charger):
            uid = charger["id"]
            switch = self._switch(self.runtime.hass, charger.get("control_entity"))
            if switch is None or switch.state != "on":
                return 3
            session = self._sessions.get(uid)
            slot = slots.get(uid)
            if not session or uid not in self._accepted or slot is None or slot.asset_uid != session["asset_id"]:
                return 0
            current = session.get("target_current_a")
            if current is not None and slot.current_a is not None and slot.current_a < current - 1e-6:
                return 1
            return 2
        return sorted(chargers, key=order)

    async def advance_plan(self, quarter_start):
        """Apply one qualified quarter plan through the only existing executor.

        Called only by the native HA quarter-hour callback. An arbitrary
        source refresh does not cause a new START, and boot never replays an
        accepted command without an independent current-session authority.
        """
        mode = self.runtime.configuration["controller"]["mode"]
        if (self._stopped or not self._persistence_verified
                or mode not in ("Automatic", "Economy", "Solar", "Ready By")):
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
        self._grant_configuration = deepcopy(self.runtime.configuration)
        self._grant_plan_revision = assessment.plan.revision
        self._grant_prices = tuple(self.runtime.price_slots)
        try:
            for configured in self._quarter_order(self.runtime.configuration["chargers"], slots):
                charger = self.effective_charger(configured)
                uid = charger["id"]
                if (charger.get("control_owner", "external") != "multicharge"
                        or charger.get("physical_commissioned") is not True
                        or uid in self._paused):
                    continue
                slot = slots.get(uid)
                switch = self._switch(self.runtime.hass, charger.get("control_entity"))
                if switch is None:
                    continue
                if switch.state == "on":
                    if self._sessions.get(uid, {}).get("manual_mode") == mode:
                        continue  # finite manual timer owns this session, not a quarter plan
                    # Never adopt an unconfirmed session after restart.
                    session = self._sessions.get(uid)
                    if session is None or uid not in self._accepted:
                        await self.execute(uid, "stop")
                        continue
                    now = datetime.now(timezone.utc)
                    if (slot is None or slot.asset_uid != session["asset_id"]
                            or not self._grant_is_current(slot, now)
                            or self._session_stop_reason(charger, now)):
                        await self.execute(uid, "stop")
                        continue
                    if charger["kind"] == "variable_current":
                        target = slot.current_a
                        if target is None:
                            await self.execute(uid, "stop")
                            continue
                        previous = session.get("target_current_a", 0)
                        # A lower new-quarter grant is binding and cannot wait.
                        # Normal energy/SoC increases belong to the one
                        # regulation cycle AFTER all quarter admissions.
                        if target < previous - 1e-6:
                            outcome = await self.execute(
                                uid, "set_current", current_a=target, plan_slot=slot
                            )
                            if outcome["status"] != "confirmed":
                                continue
                    # Still-owned physical session and verified slot continuity.
                    if not self._accept_slot(charger, slot, assessment.plan.revision):
                        await self.execute(uid, "stop")
                        continue
                    if not await self.runtime.persist_control_state():
                        self._persistence_verified = False
                        await self.execute(uid, "stop")
                    continue
                if slot is None:
                    continue
                asset = next((a for a in self.runtime.configuration["assets"]
                              if a["id"] == slot.asset_uid), None)
                if asset is None:
                    continue
                deadline = datetime.fromisoformat(asset["ready_by"]) if (
                    asset.get("ready_by")
                ) else None
                if asset.get("ready_by_repeat", "none") != "none" and (deadline is not None or asset.get("ready_by_repeat") == "specific_days"):
                    deadline, reason = resolve_recurring_ready_by(
                        deadline, quarter_start, asset["ready_by_repeat"],
                        self.runtime.hass.config.time_zone,
                        asset.get("ready_by_weekdays"),
                    )
                    if deadline is None:
                        continue
                intent = self._intent_key(asset, charger, deadline)
                if self._completed.get(asset["id"]) == intent:
                    continue
                # A crash, unknown physical outcome or earlier unsafe STOP
                # leaves an unresolved intent. Never replay the requested kWh
                # or duration without explicit reconciliation.
                if asset["id"] in self._inflight:
                    continue
                self._inflight[asset["id"]] = intent
                if not await self.runtime.persist_control_state():
                    self._persistence_verified = False
                    self._inflight.pop(asset["id"], None)
                    continue
                result = await self.execute(
                    uid, "start", current_a=slot.current_a, plan_slot=slot,
                )
                if result["status"] == "confirmed":
                    if not self._accept_slot(charger, slot, assessment.plan.revision):
                        await self.execute(uid, "stop")
                        continue
                    if self._last_power_adjustment_tick is None:
                        self._last_power_adjustment_tick = monotonic()
                elif result["status"] == "rejected":
                    self._inflight.pop(asset["id"], None)
                if not await self.runtime.persist_control_state():
                    self._persistence_verified = False
                    if result["status"] == "confirmed":
                        await self.execute(uid, "stop")
        finally:
            self._grants.clear()
            self._grant_configuration = None
            self._grant_plan_revision = None
            self._grant_prices = ()

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
            slot = self._accepted.get(charger["id"], {}).get("_slot")
            if problem is None and self._physical_budget(
                charger, at, power, candidate, plan_slot=slot
            ) is None:
                outcome = await self.execute(
                    charger["id"], "set_current", current_a=candidate
                )
                if outcome["status"] == "confirmed":
                    return True
                return False
            candidate = round(candidate - step, 6)
        return False

    def _active_safety(self, charger, at):
        """One safety decision, shared by normal supervision and pending-command events."""
        cfg = self.runtime.configuration
        mode = cfg["controller"]["mode"]
        uid = charger["id"]
        limit_reason = None
        cable = self._connection(charger, at)
        power = number(self.runtime.hass, charger.get("power_entity"), "power", at)
        session_reason = self._session_stop_reason(charger, at)
        accepted = self._accepted.get(uid)
        is_auto = mode in ("Automatic", "Solar", "Economy", "Ready By")
        # Reconciliation admits a new quarter before supervising it.
        # A missing/late callback or invalid new plan grants no grace.
        no_plan = is_auto and (
            accepted is None or accepted["end"] <= at
        )
        slot = accepted.get("_slot") if accepted else None
        if (is_auto and slot is not None and slot.start <= at < slot.end
                and not self._slot_tariff_is_current(slot, at, accepted.get("_prices", ()))):
            no_plan = True
        unowned = is_auto and accepted is None
        duration_without_connection = self._sessions.get(uid, {}).get("duration_without_connection", False)
        switch_only = self._sessions.get(uid, {}).get("switch_only", False)
        manual_mode = self._sessions.get(uid, {}).get("manual_mode")
        wrong_mode = mode == "Off" or (is_auto and (no_plan or unowned)
            and not (manual_mode == mode == "Automatic"))
        if manual_mode is not None and manual_mode != mode:
            wrong_mode = True
        if mode == "Force Charge" and accepted is not None:
            wrong_mode = True
        unsafe = (
            uid in self._paused or wrong_mode
            or ((not duration_without_connection or not self.duration_connection_allowed(cable))
                and (cable.quality != "ok" or cable.value is not True))
            or ((not switch_only and not duration_without_connection) and power.quality != "ok")
            or (power.quality == "ok" and power.value > charger["rated_power_kw"] * 1.10)
            or session_reason is not None
        )
        if charger["kind"] == "variable_current":
            amps = number(self.runtime.hass,
                charger.get("current_readback_entity"), "current", at)
            session = self._sessions.get(uid)
            current = session.get("target_current_a") if session else None
            if current is None:
                unsafe = True
            elif charger.get("current_readback_entity"):
                if (amps.quality != "ok" or amps.value > current + max(
                        0.25, charger.get("current_step_a", 1) / 2)):
                    unsafe = True
            else:
                setting = number(self.runtime.hass,
                    charger.get("current_control_entity"), "current", at)
                target_kw = current * charger["voltage_v"] * charger["phase_count"] / 1000
                if (setting.quality != "ok" or abs(setting.value-current) >
                        max(0.25, charger.get("current_step_a", 1) / 2)
                        or power.quality != "ok" or power.value > target_kw * 1.10 + 0.01):
                    unsafe = True
        if not unsafe:
            session = self._sessions.get(uid)
            kw = (charger["rated_power_kw"]
                  if charger["kind"] == "on_off" else
                  session["target_current_a"] * charger["voltage_v"]
                  * charger["phase_count"] / 1000)
            current = (charger.get("fixed_current_a")
                       if charger["kind"] == "on_off"
                       else session["target_current_a"])
            limit_reason = self._physical_budget(
                charger, at, kw, current,
                plan_slot=accepted.get("_slot") if accepted else None,
            )
            assigned = next((a for a in cfg["assets"] if a["id"] == charger.get("asset")), None)
            if assigned and assigned.get("max_charge_kw") is not None and kw > assigned["max_charge_kw"] + 1e-9:
                limit_reason = "ASSET_POWER_CAP_REQUIRES_MODULATION"
            if charger["kind"] == "variable_current":
                limit_reason = self._requested_current(charger, current, at)[0] or limit_reason
        return unsafe, limit_reason, session_reason

    async def _stop_active(self, charger, at, session_reason):
        cfg = self.runtime.configuration
        uid = charger["id"]
        is_auto = cfg["controller"]["mode"] in ("Automatic", "Solar", "Economy", "Ready By")
        completed_asset = None
        completed_intent = None
        if session_reason in (
            "REQUESTED_ENERGY_COMPLETE", "REQUESTED_DURATION_COMPLETE",
            "REQUESTED_BUDGET_COMPLETE", "SOC_TARGET_REACHED"
        ) and is_auto:
            asset = next((a for a in cfg["assets"]
                          if a["id"] == charger.get("asset")), None)
            if asset is not None:
                completed_asset = asset["id"]
                occurrence = datetime.fromisoformat(
                    asset["ready_by"]
                ) if asset.get("ready_by") else None
                if asset.get("ready_by_repeat", "none") != "none" and (occurrence is not None or asset.get("ready_by_repeat") == "specific_days"):
                    occurrence, _ = resolve_recurring_ready_by(
                        occurrence, at, asset["ready_by_repeat"],
                        self.runtime.hass.config.time_zone,
                        asset.get("ready_by_weekdays"),
                    )
                if (asset.get("requested_kwh") is not None
                        or asset.get("requested_duration_minutes") is not None
                        or asset.get("requested_budget_amount") is not None):
                    completed_intent = self._intent_key(
                        asset, charger, occurrence
                    )
        outcome = await self.execute(uid, "stop")
        if outcome["status"] == "confirmed" and completed_asset is not None:
            if completed_intent is not None:
                self._completed[completed_asset] = completed_intent
            self._inflight.pop(completed_asset, None)
            if not await self.runtime.persist_control_state():
                self._persistence_verified = False
        if outcome["status"] != "confirmed":
            _LOGGER.error("Protective charger STOP not physically confirmed: %s %s",
                          uid, outcome["reason"])

    def schedule_pending_protection(self, create_task, source_entity=None):
        """Use existing source events to dispatch STOP while reconcile awaits a command.

        No extra periodic job or writer. Do not race a same-EVSE native write.
        A peer safety violation cannot wait for a different EVSE's readback.
        Normal supervision still owns modulations and confirmation.
        """
        pending = self._start_pending | self._current_pending
        if not pending or self._stopped or not self._lock.locked():
            return
        at = datetime.now(timezone.utc)
        cfg = self.runtime.configuration
        for configured in cfg["chargers"]:
            uid = configured["id"]
            if (uid in pending or configured.get("control_owner") != "multicharge"
                    or configured.get("physical_commissioned") is not True
                    or configured.get("kind") not in ("on_off", "variable_current")):
                continue
            # Ordinary readback from a different pending command is not a
            # reason to revoke a continuing quarter before its own admission.
            if source_entity is not None:
                asset = next((a for a in cfg["assets"] if a["id"] == configured.get("asset")), {})
                sources = {v for row in (cfg["controller"], configured, asset)
                           for k, v in row.items()
                           if k.endswith("_entity") and isinstance(v, str)}
                if source_entity not in sources:
                    continue
            switch = self._switch(self.runtime.hass, configured.get("control_entity"))
            if switch is None or switch.state != "on":
                continue
            task = self._source_stop_tasks.get(uid)
            if task is not None and not task.done():
                continue
            charger = self.effective_charger(configured)
            unsafe, limit_reason, reason = self._active_safety(charger, at)
            if unsafe or limit_reason is not None:
                # Modulation cannot safely acquire the lock while another
                # command awaits readback. Fall back to the same guarded STOP.
                self._source_stop_tasks[uid] = create_task(self._stop_active(charger, at, reason))

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
            for configured in active:
                charger = self.effective_charger(configured)
                uid = charger["id"]
                # Native HA publishes the switch event before execute() has
                # adopted the command receipt. The same executor already
                # bounds that pending START and handles its readback timeout.
                # Do not queue a spurious STOP against a not-yet-adopted session.
                if uid in self._start_pending:
                    continue
                unsafe, limit_reason, session_reason = self._active_safety(charger, at)
                if not unsafe and limit_reason is not None:
                    unsafe = not await self._reduce_current(charger, at)
                if unsafe:
                    await self._stop_active(charger, at, session_reason)
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
            uid = charger["id"]
            pending = (uid in self._sessions or uid in self._start_pending
                       or uid in self._quarantine or f"charger:{uid}" in self._inflight
                       or (charger.get("asset") is not None and charger["asset"] in self._inflight))
            if uid not in (self._start_pending | self._current_pending) and state.state == "off" and (
                    (power.quality == "ok" and power.value <= stop_power_limit(charger))
                    or (not pending and power.quality != "ok")):
                # An idle output with no owned operation to reconcile need
                # not prove an unrelated meter to permit unload.
                continue
            outcome = await self.execute(charger["id"], "stop")
            if outcome["status"] != "confirmed":
                _LOGGER.error("Unconfirmed STOP blocks unload for %s: %s",
                              charger["id"], outcome["reason"])
                return False
        return True

    def _readback(self, charger, action, requested_at, *, bounded_switch=False):
        switch = self._switch(self.runtime.hass, charger["control_entity"])
        if switch is None or switch.state != ("on" if action == "start" else "off"):
            return None
        power = number(self.runtime.hass, charger.get("power_entity"), "power",
                       datetime.now(timezone.utc))
        if charger["kind"] == "on_off" and (not charger.get("power_entity") or (
                bounded_switch and (power.quality != "ok" or (
                    action == "start" and power.value <= start_power_limit(charger))))):
            observed_at = getattr(switch, "last_updated", None)
            if observed_at is None or observed_at < requested_at:
                return None
            return Evidence(None, "ok", observed_at, "NATIVE_SWITCH_STATE")
        if power.quality != "ok" or power.observed_at is None:
            return None
        if power.observed_at < requested_at:
            return None
        if action == "start" and (
            power.value <= start_power_limit(charger)
            or power.value > charger["rated_power_kw"] * 1.10
        ):
            return None
        if action in ("stop", "pause") and power.value > stop_power_limit(charger):
            return None
        return power

    async def execute(self, charger_id, action, *, context=None,
                      request_id=None, readback_seconds=READBACK_SECONDS,
                      current_a=None, plan_slot=None, manual_request=None,
                      active_regulation=False):
        """Perform a real HA switch call; success requires fresh independent power."""
        if action not in ("start", "stop", "set_current", "pause", "resume"):
            raise ValueError("unsupported physical action")
        at = datetime.now(timezone.utc)
        request_id = request_id or uuid4().hex
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            raise ValueError("request ID must be 1..128 characters")
        # STOP and Pause share one preemption path. Revoke the quarter before
        # waiting; a same-charger pending writer must finish/cancel first.
        if (action in ("stop", "pause") and request_id not in self._requests
                and not self._stopped):
            charger = next((c for c in self.runtime.configuration["chargers"]
                            if c["id"] == charger_id), None)
            if (charger is not None and charger.get("control_owner") == "multicharge"
                    and charger.get("physical_commissioned") is True
                    and charger.get("kind") in ("on_off", "variable_current")):
                self._grants.pop(charger_id, None)
                pending = self._start_pending | self._current_pending
                if charger_id in pending:
                    self._stop_requested.add(charger_id)
                elif pending and self._lock.locked() and request_id not in self._urgent_stop_requests:
                    switch = self._switch(self.runtime.hass, charger.get("control_entity"))
                    if switch is not None and switch.state == "on":
                        self._urgent_stop_requests.add(request_id)
                        # Dispatch only; the ordinary serialized path still
                        # owns independent confirmation and Pause persistence.
                        await self._protective_stop(charger, context)
        async with self._lock:
            self._urgent_stop_requests.discard(request_id)
            previous = self._requests.get(request_id)
            if previous is not None:
                if (previous["charger_id"] != charger_id
                        or previous["action"] != action
                        or previous.get("requested_current_a") != current_a
                        or previous.get("manual_request") != manual_request):
                    raise ValueError("request ID used for a different command")
                return {key: value for key, value in previous.items()
                        if key != "manual_request"}
            # Time captured before awaiting the lock can be an expired
            # quarter by admission time. All evidence checks use actual now.
            at = datetime.now(timezone.utc)
            cfg = self.runtime.configuration
            charger = next((c for c in cfg["chargers"] if c["id"] == charger_id), None)
            def result(status, reason, **extras):
                recorded = self._publish(charger_id, request_id, action, status,
                                         reason, at, **extras)
                self._requests[request_id] = {
                    **recorded, "manual_request": manual_request,
                }
                return recorded
            if active_regulation and (action != "set_current" or not self._regulating
                                      or not self._active_grant_is_current(plan_slot, at)):
                return result("rejected", "ACTIVE_REGULATION_NOT_AUTHORIZED")
            if charger is None:
                return result("rejected", "UNKNOWN_CHARGER")
            charger = self.effective_charger(charger)
            if self._stopped:
                return result("rejected", "INTEGRATION_UNLOADED")
            if action != "stop" and not self._persistence_verified:
                return result("rejected", "CONTROL_STATE_UNVERIFIED")
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
            if action == "resume":
                if charger_id not in self._paused:
                    return result("rejected", "CHARGER_NOT_PAUSED")
                if charger_id in self._quarantine or charger_id in self._sessions:
                    return result("rejected", "UNCONFIRMED_SESSION_CANNOT_RESUME")
                power = number(self.runtime.hass, charger.get("power_entity"),
                               "power", at)
                if (state.state != "off" or (charger.get("power_entity") and (
                        power.quality != "ok" or power.value > stop_power_limit(charger)))):
                    return result("rejected", "PHYSICAL_STOP_NOT_VERIFIED")
                self._paused.remove(charger_id)
                if not await self.runtime.persist_control_state():
                    self._paused.add(charger_id)
                    self._persistence_verified = False
                    return result("execution_unknown", "PAUSE_RELEASE_NOT_PERSISTED")
                # Resume only releases the admission hold; it NEVER energizes
                # hardware. A real future quarter plan or explicit manual
                # START must independently pass all physical gates.
                return result("confirmed", "PAUSE_RELEASED_NO_PHYSICAL_START",
                              observed_at=power.observed_at or getattr(state, "last_updated", None),
                              measured_kw=power.value if power.quality == "ok" else None)
            if action == "pause" and charger_id not in self._paused:
                self._paused.add(charger_id)
                if not await self.runtime.persist_control_state():
                    self._paused.discard(charger_id)
                    self._persistence_verified = False
                    return result("rejected", "PAUSE_HOLD_NOT_PERSISTED")
            if action in ("start", "set_current"):
                if charger["kind"] == "variable_current":
                    if current_a is None and action == "start" and plan_slot is None:
                        current_a = self._highest_safe_current(charger, at)
                        if current_a is None:
                            return result("rejected", "NO_SAFE_ADJUSTABLE_CURRENT")
                    if plan_slot is not None:
                        if ((not active_regulation and not self._grant_is_current(plan_slot, at))
                                or plan_slot.charger_uid != charger_id
                                or plan_slot.asset_uid != charger.get("asset")):
                            return result("rejected", "PLAN_SLOT_NOT_AUTHORIZED")
                        if active_regulation:
                            if (type(current_a) not in (int, float)
                                    or not isfinite(current_a) or plan_slot.current_a is None):
                                return result("rejected", "ACTIVE_REGULATION_INVALID_CURRENT")
                        else:
                            current_a = plan_slot.current_a
                            # A boost is optional. If fresh shared capacity has
                            # shrunk, preserve the usable part of this quarter.
                            if plan_slot.planning_power_kw is not None:
                                current_a = self._highest_safe_current(
                                    charger, at, ceiling=current_a, plan_slot=plan_slot,
                                )
                                if current_a is None:
                                    return result("rejected", "NO_SAFE_ADJUSTABLE_CURRENT")
                    problem, requested_kw = self._requested_current(charger, current_a, at)
                    if problem:
                        return result("rejected", problem)
                elif action == "set_current":
                    return result("rejected", "ON_OFF_CANNOT_MODULATE")
            if action == "set_current":
                if state.state != "on" or charger_id not in self._sessions:
                    return result("rejected", "CURRENT_CHANGE_REQUIRES_OWNED_SESSION")
                if charger_id in self._quarantine:
                    return result("rejected", "PREVIOUS_COMMAND_UNCONFIRMED")
                if self._session_stop_reason(charger, at) is not None:
                    return result("rejected", "ACTIVE_SESSION_NOT_SAFE_FOR_MODULATION")
                mode = cfg["controller"]["mode"]
                previous_current = self._sessions[charger_id].get("target_current_a")
                if mode != "Force Charge":
                    if mode not in ("Automatic", "Solar", "Economy", "Ready By"):
                        return result("rejected", "MODE_REQUIRES_PHYSICAL_STOP")
                    granted = plan_slot if active_regulation else self._grants.get(charger_id)
                    authorized = (self._active_grant_is_current(granted, at)
                                  if active_regulation else self._grant_is_current(granted, at))
                    if (previous_current is None
                            or (current_a > previous_current + 1e-6
                                and (not authorized or granted.current_a is None
                                     or (not active_regulation
                                         and current_a > granted.current_a + 1e-6)))):
                        return result("rejected", "CURRENT_INCREASE_REQUIRES_ACCEPTED_SLOT")
                cable = self._connection(charger, at)
                if cable.quality != "ok" or cable.value is not True:
                    return result("rejected", "PHYSICAL_CONNECTION_UNVERIFIED")
                effective_slot = plan_slot or self._accepted.get(charger_id, {}).get("_slot")
                reason = self._physical_budget(charger, at, requested_kw, current_a,
                                               plan_slot=effective_slot,
                                               reserve_minima=active_regulation)
                if reason:
                    return result("rejected", reason)
                self._current_pending.add(charger_id)
                try:
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
                        now = datetime.now(timezone.utc)
                        current_problem, kw = self._requested_current(self.effective_charger(charger), current_a, now)
                        issue = ("STOP_REQUESTED_DURING_CURRENT_CHANGE"
                                 if charger_id in self._stop_requested else
                                 self._session_stop_reason(charger, now) or current_problem
                                 or self._physical_budget(charger, now, kw, current_a,
                                                          plan_slot=effective_slot,
                                                          reserve_minima=active_regulation))
                        if issue:
                            protective = await self._protective_stop(charger, context)
                            return result("execution_unknown", issue
                                          + (";PROTECTIVE_STOP_SENT" if protective
                                             else ";PROTECTIVE_STOP_UNCONFIRMED"), service_sent=True)
                        if self._current_confirmed(charger, current_a, at):
                            confirmed_at = datetime.now(timezone.utc)
                            if effective_slot is not None and (
                                    confirmed_at >= effective_slot.end
                                    or not self._slot_tariff_is_current(
                                        effective_slot, confirmed_at,
                                        self._grant_prices if not active_regulation and plan_slot is not None
                                        else self._accepted.get(charger_id, {}).get("_prices", ()),
                                    )):
                                await self._protective_stop(charger, context)
                                return result("execution_unknown", "GRANT_EXPIRED_OR_CHANGED_DURING_READBACK;PROTECTIVE_STOP_SENT",
                                              service_sent=True)
                            self._sessions[charger_id]["target_current_a"] = current_a
                            if (not self._record_accepted_current(charger, current_a, confirmed_at)
                                    or not await self.runtime.persist_control_state()):
                                self._persistence_verified = False
                                await self._protective_stop(charger, context)
                                return result("execution_unknown",
                                              "CURRENT_HISTORY_NOT_PERSISTED;PROTECTIVE_STOP_SENT",
                                              service_sent=True)
                            out = result("confirmed", ("INDEPENDENT_CURRENT_READBACK" if charger.get("current_readback_entity")
                                else "NATIVE_SETPOINT_AND_POWER_READBACK"),
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
                except asyncio.CancelledError:
                    protective = await self._protective_stop(charger, context)
                    result("execution_unknown", "CURRENT_COMMAND_CANCELLED"
                           + (";PROTECTIVE_STOP_SENT" if protective
                              else ";PROTECTIVE_STOP_UNCONFIRMED"), service_sent=True)
                    raise
                finally:
                    self._current_pending.discard(charger_id)
                    self._stop_requested.discard(charger_id)
            try:
                if action == "start":
                    start_configuration = deepcopy(cfg)
                    if state.state != "off":
                        return result("rejected", "SWITCH_ALREADY_ON")
                    if charger_id in self._quarantine:
                        return result("rejected", "PREVIOUS_COMMAND_UNCONFIRMED")
                    if plan_slot is not None:
                        if (not self._grant_is_current(plan_slot, at)
                                or plan_slot.charger_uid != charger_id
                                or plan_slot.asset_uid != charger.get("asset")):
                            return result("rejected", "PLAN_SLOT_NOT_AUTHORIZED")
                    reason = self._admit_start(
                        charger, at, planned=plan_slot is not None,
                        target_current=current_a, manual_request=manual_request,
                        plan_slot=plan_slot,
                    )
                    if reason:
                        return result("rejected", reason)
                    self._stop_requested.discard(charger_id)
                    self._start_pending.add(charger_id)
                    if plan_slot is None:
                        # Automatic START already stores its own intent before
                        # entering execute(). Manual/one-off START must obey the
                        # *same* durable admission boundary before any HA service.
                        asset = next((
                            row for row in cfg["assets"]
                            if row["id"] == charger.get("asset")
                        ), None)
                        if asset is not None:
                            due = datetime.fromisoformat(asset["ready_by"]) if (
                                asset.get("ready_by")
                            ) else None
                            if asset.get("ready_by_repeat", "none") != "none" and (due is not None or asset.get("ready_by_repeat") == "specific_days"):
                                due, issue = resolve_recurring_ready_by(
                                    due, at, asset["ready_by_repeat"],
                                    self.runtime.hass.config.time_zone,
                                    asset.get("ready_by_weekdays"),
                                )
                                if due is None:
                                    return result("rejected", issue)
                            hold_key = asset["id"]
                            hold_intent = self._intent_key(asset, charger, due)
                        else:
                            hold_key = f"charger:{charger_id}"
                            hold_intent = sha256(dumps({
                                "charger": charger_id, "one_off": manual_request,
                            }, sort_keys=True).encode()).hexdigest()
                        self._inflight[hold_key] = hold_intent
                        if not await self.runtime.persist_control_state():
                            self._inflight.pop(hold_key, None)
                            self._persistence_verified = False
                            return result("rejected", "MANUAL_INTENT_NOT_PERSISTED")
                elif state.state == "off":
                    power = number(self.runtime.hass, charger.get("power_entity"),
                                   "power", at)
                    if not charger.get("power_entity") and charger["kind"] == "on_off":
                        outcome = result("confirmed", "NATIVE_SWITCH_STATE",
                                         observed_at=getattr(state, "last_updated", None))
                        if not await self.runtime.persist_control_state():
                            self._persistence_verified = False
                        return outcome
                    if (power.quality == "ok"
                            and power.value <= stop_power_limit(charger)):
                        outcome = result("confirmed", "ALREADY_PHYSICALLY_STOPPED",
                                         observed_at=power.observed_at,
                                         measured_kw=power.value)
                        if not await self.runtime.persist_control_state():
                            self._persistence_verified = False
                        return outcome
                bounded_switch = charger["kind"] == "on_off" and (
                    (manual_request is not None and manual_request.get("duration_minutes") is not None)
                    or (action == "start" and any(a["id"] == charger.get("asset")
                        and a.get("requested_duration_minutes") is not None for a in cfg["assets"]))
                    or self._sessions.get(charger_id, {}).get("duration_without_connection", False))
                self._publish(charger_id, request_id, action, "requested",
                              "REQUESTED", at)
                try:
                    if action == "start" and charger["kind"] == "variable_current":
                        await self._set_native_current(charger, current_a, context)
                    if action == "start":
                        command_at = datetime.now(timezone.utc)
                        issue = ("STOP_REQUESTED_DURING_START"
                                 if charger_id in self._stop_requested else
                                 self._pending_start_issue(
                                     charger, command_at, plan_slot, current_a, manual_request,
                                     start_configuration,
                                 ))
                        if issue:
                            if plan_slot is None:
                                self._inflight.pop(hold_key, None)
                                if not await self.runtime.persist_control_state():
                                    self._persistence_verified = False
                            return result("rejected", issue)
                        baseline = number(self.runtime.hass, charger.get("energy_entity"),
                                          "energy", command_at)
                        identity = self.connection_confirmation(charger, command_at)
                        plug_epoch = identity["connected_at"] if identity else None
                    await self._native_service(
                        "switch", "turn_on" if action == "start" else "turn_off",
                        {"entity_id": entity}, context,
                    )
                except asyncio.CancelledError:
                    if action == "start":
                        await self._protective_stop(charger, context)
                    result("execution_unknown", "COMMAND_CANCELLED_DURING_SERVICE",
                           service_sent=True)
                    raise
                except Exception as exc:
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
                    if action == "start":
                        now = datetime.now(timezone.utc)
                        issue = ("STOP_REQUESTED_DURING_START"
                                 if charger_id in self._stop_requested else
                                 self._pending_start_issue(
                                     charger, now, plan_slot, current_a, manual_request,
                                     start_configuration, energized=True,
                                 ))
                        if issue is None and plug_epoch is not None:
                            identity = self.connection_confirmation(charger, now)
                            if identity is None or identity["connected_at"] != plug_epoch:
                                issue = "CURRENT_PLUG_CHANGED_DURING_START"
                        if issue is not None:
                            protective = await self._protective_stop(charger, context)
                            return result("execution_unknown", issue
                                          + (";PROTECTIVE_STOP_SENT" if protective
                                             else ";PROTECTIVE_STOP_UNCONFIRMED"), service_sent=True)
                    if self._stopped:
                        return result("execution_unknown", "INTEGRATION_UNLOADED_PENDING",
                                      service_sent=True)
                    observed = self._readback(charger, action,
                                              command_at if action == "start" else at,
                                              bounded_switch=bounded_switch)
                    if (observed is not None and action == "start"
                            and charger["kind"] == "variable_current"
                            and not self._current_confirmed(charger, current_a, at)):
                        observed = None
                    if observed is not None:
                        if action == "start":
                            reason = self._start_session(
                                charger, observed, manual_request, command_at=command_at,
                                baseline=baseline, plug_epoch=plug_epoch,
                            )
                            if reason is None and charger["kind"] == "variable_current":
                                self._sessions[charger_id]["target_current_a"] = current_a
                            if reason is not None:
                                protective = await self._protective_stop(charger, context)
                                return result(
                                    "execution_unknown",
                                    reason + (";PROTECTIVE_STOP_SENT" if protective
                                              else ";PROTECTIVE_STOP_UNCONFIRMED"),
                                    service_sent=True
                                )
                        outcome = result("confirmed", ("NATIVE_SWITCH_STATE" if observed.reason == "NATIVE_SWITCH_STATE"
                                          else "INDEPENDENT_POWER_READBACK"),
                                      observed_at=observed.observed_at,
                                      measured_kw=observed.value,
                                      service_sent=True)
                        if action in ("stop", "pause") and not await self.runtime.persist_control_state():
                            self._persistence_verified = False
                        return outcome
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
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
                        if action == "start":
                            await self._protective_stop(charger, context)
                        result("execution_unknown", "COMMAND_CANCELLED_AWAITING_READBACK",
                               service_sent=True)
                        raise
            finally:
                if action == "start":
                    self._start_pending.discard(charger_id)
                    self._stop_requested.discard(charger_id)
