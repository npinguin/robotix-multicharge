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
from .planner import compile_plan, minimum_planning_power, missing_current_conversion, resolve_recurring_ready_by
from .source_evidence import (
    Evidence, binding, connection, intervals, number, session_status,
    live_power, live_price, soc_with_health,
)
from .execution import NativeSwitchExecutor
from .cost_archive import (
    hour_slices, merge_slices, read_archive, write_archive,
    pending_archive_snapshot, restore_pending_archive,
)
from .history import (
    civil_cost_days, civil_period_costs, planned_costs, read_actual_history,
    reconcile_power_bindings, reconcile_tariff_bindings, session_costs,
)

_LOGGER = logging.getLogger(__name__)


def _evidence(value):
    """Public JSON-shaped observation, never an implicit successful reading."""
    if value is None:
        return {"value": None, "quality": "unknown", "reason": "NOT_OBSERVED",
                "observed_at": None}
    return {"value": value.value, "quality": value.quality,
            "reason": value.reason,
            "observed_at": value.observed_at.isoformat() if value.observed_at else None}


def _display_power(hass, entity, at, *, signed=False):
    """Retain a clearly labeled last report for UI only, not control."""
    reading = live_power(hass, entity, at, signed=signed)
    result = _evidence(reading)
    if reading.quality == "stale" and reading.observed_at:
        previous = live_power(hass, entity, reading.observed_at, signed=signed)
        if previous.quality == "ok":
            result["last_reported_value"] = previous.value
    return result


class MultiChargeRuntime:
    def __init__(self, hass, configuration):
        self.hass = hass
        self.configuration = configuration
        self.assessment = None
        self.forecast_assessment = None
        self.forecast_assumptions = {}
        self.forecast_excluded = {}
        self.goal_assessments = {}
        self.observations = {"chargers": {}, "assets": {}, "sources": {}}
        self.excluded = {}
        self.price_slots = ()
        self.planned_costs = {}
        self.session_costs = {}
        self.period_costs = {}
        self._daily_costs = {}
        self._archive_checked_days = set()
        self._archive_partial = {}
        self._archive_pending = {}
        self._archive_unreadable = None
        self._closed_cost_days = set()
        self.statistics_namespace = None
        self._session_cost_identity = None
        self.nordpool_prices = None
        self.executor = NativeSwitchExecutor(self)
        self._control_store = None
        self.power_bindings = reconcile_power_bindings(None, configuration, datetime.now(timezone.utc))
        self.energy_bindings = reconcile_power_bindings({}, configuration, datetime.now(timezone.utc), field="energy_entity")
        self.tariff_bindings = reconcile_tariff_bindings(None, configuration, datetime.now(timezone.utc))
        self._save_lock = asyncio.Lock()
        self._settings_action = None
        self._listeners = set()
        self._unsubscribers = []
        self.active = True

    def _current_session_cost_identity(self):
        """Invalidate stale projections on source, ownership or session changes."""
        return (
            configuration_revision(self.configuration),
            tuple(sorted((uid, row.get("started_at"), row.get("asset_id"))
                         for uid, row in self.executor.session_snapshot().items())),
            tuple((row["charger_id"], row["started_at"], row["ended_at"])
                  for row in self.executor.completed_sessions()),
        )

    async def refresh_session_costs(self):
        """Shared session and civil-period projections, bounded Recorder work.

        Reuse the recent history read for current day evidence; backfill one
        older day in the same coalesced minute task, never a full-year query
        in the command or browser path. Missing purged data remains partial.
        """
        at = datetime.now(timezone.utc)
        cfg = self.configuration
        identity = self._current_session_cost_identity()
        receipts = self.executor.completed_sessions()
        active = self.executor.session_snapshot()
        zone = getattr(getattr(self.hass, "config", None), "time_zone", "UTC")
        days = civil_cost_days(at, zone)
        today = next(reversed(days))
        self._daily_costs = {day: row for day, row in self._daily_costs.items()
                             if day in days and (day == today or day in self._closed_cost_days
                                                 or day in self._archive_pending)}
        self._archive_checked_days.intersection_update(days)
        self._closed_cost_days.intersection_update(days)
        self._archive_partial = {day: row for day, row in self._archive_partial.items() if day in days}
        # Pending writes retain their original UTC boundaries and survive
        # calendar-year rollover. Only native readback may retire them.
        common = dict(
            session_receipts=receipts, price_slots=self.price_slots,
            power_bindings=self.power_bindings, energy_bindings=self.energy_bindings,
            tariff_bindings=self.tariff_bindings, active_sessions=active,
            tariff_entity=(cfg["controller"].get("price_entity") or
                           cfg["controller"].get("current_price_entity")),
        )
        _, _, estimates, observed, metrics, daily = await read_actual_history(
            self.hass, cfg, at-timedelta(hours=48), at+timedelta(minutes=1),
            include_valuations=True, include_observed_sessions=True,
            financial_days={today: days[today]}, **common,
        )
        if not self.active or identity != self._current_session_cost_identity():
            return
        self._daily_costs.update(daily)
        self.period_costs = civil_period_costs(days, self._daily_costs)
        self.session_costs = session_costs(receipts, active, observed, estimates, metrics)
        self._session_cost_identity = identity
        self.notify()

        # Recover native statistics in bounded month-sized windows; reconstruct
        # one absent raw civil day per cycle, never query a year of raw states.
        unchecked = [day for day in reversed(days)
                     if day != today and day not in self._archive_checked_days]
        if unchecked:
            window = {day: days[day] for day in unchecked[:31]}
            archived = await read_archive(self.hass, self.statistics_namespace, window,
                                          cfg, self.power_bindings, receipts)
            if not self.active or identity != self._current_session_cost_identity():
                return
            if archived is not None:
                self._archive_checked_days.update(window)
                for day, (a, b) in window.items():
                    keys = hour_slices(a, b)
                    pieces = {key: archived[key] for key in keys if key in archived}
                    if len(pieces) == len(keys):
                        self._daily_costs[day] = merge_slices(pieces)
                        self._closed_cost_days.add(day)
                    elif pieces:
                        self._archive_partial[day] = pieces

        await self._retry_cost_archive(days, cfg, receipts, identity)
        if not self.active or identity != self._current_session_cost_identity():
            return

        missing = next((day for day in reversed(days) if day != today
                        and day not in self._closed_cost_days
                        and day not in self._archive_pending
                        and day in self._archive_checked_days), None)
        if self._archive_unreadable is not None:
            missing = None  # retain malformed original evidence for repair, never overwrite it
        if missing:
            a, b = days[missing]
            slices = hour_slices(a, b)
            previous = self._archive_partial.get(missing, {})
            pending = {key: pair for key, pair in slices.items() if key not in previous}
            _, quality, older = await read_actual_history(
                self.hass, cfg, a, b, financial_days=pending, **common,
            )
            if not self.active or identity != self._current_session_cost_identity():
                return
            if quality not in ("RECORDER_UNAVAILABLE", "RECORDER_NOT_LOADED"):
                self._daily_costs[missing] = merge_slices({**older, **previous})
                self._archive_partial.pop(missing, None)
                if quality == "FINANCIAL_DAY" and any(
                        row["controller"]["site"]["observed_seconds"] > 0 for row in older.values()):
                    # Write ahead only the unacknowledged slices in the existing
                    # HA Store. Recorder remains the durable history authority.
                    self._archive_pending[missing] = {
                        "start": a, "end": b, "projections": older,
                    }
                    if self.executor._persistence_verified and await self.persist_control_state():
                        try:
                            write_archive(self.hass, self.statistics_namespace, pending, older)
                        except (ImportError, RuntimeError, ValueError, OSError):
                            _LOGGER.exception("Native charging cost retention unavailable")
                else:
                    self._closed_cost_days.add(missing)
        self.period_costs = civil_period_costs(days, self._daily_costs)
        self.notify()

    async def _retry_cost_archive(self, days, cfg, receipts, identity):
        """One bounded readback/retry using the original, not revalued, evidence."""
        retry_day = next(iter(self._archive_pending), None)
        if retry_day is None:
            return
        queued = self._archive_pending[retry_day]
        bounds = (queued["start"], queued["end"])
        projections = queued["projections"]
        restored = await read_archive(
            self.hass, self.statistics_namespace, {retry_day: bounds},
            cfg, self.power_bindings, receipts,
        )
        if not self.active or identity != self._current_session_cost_identity():
            return
        if restored is None:
            return
        missing = {key: row for key, row in projections.items() if key not in restored}
        slices = hour_slices(*bounds)
        # A timezone edit may change civil-day geometry; original evidence
        # is still archived at its exact UTC slice boundaries.
        if days.get(retry_day) == bounds:
            self._daily_costs[retry_day] = merge_slices({**projections, **restored})
            if len(restored) == len(slices):
                self._closed_cost_days.add(retry_day)
        if not self.executor._persistence_verified:
            return
        # A failed write or process restart must never trigger revaluation
        # from raw data that may already have been purged.
        self._archive_pending.pop(retry_day)
        if missing:
            self._archive_pending[retry_day] = {**queued, "projections": missing}
        if not await self.persist_control_state():
            # Do not retire any original receipt before Store acknowledges.
            self._archive_pending[retry_day] = queued
            return
        if missing:
            try:
                write_archive(self.hass, self.statistics_namespace, slices, missing)
            except (ImportError, RuntimeError, ValueError, OSError):
                _LOGGER.exception("Native charging cost retention retry failed")


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
        previous = snapshot.get("power_bindings") if isinstance(snapshot, dict) else None
        try:
            self.power_bindings = reconcile_power_bindings(
                previous, self.configuration, datetime.now(timezone.utc))
        except (ValueError, TypeError, KeyError, OverflowError):
            _LOGGER.warning("Invalid stored power binding history; earlier intervals are unknown")
            self.power_bindings = reconcile_power_bindings(
                {}, self.configuration, datetime.now(timezone.utc))
        previous_energy = snapshot.get("energy_bindings", {}) if isinstance(snapshot, dict) else {}
        try:
            self.energy_bindings = reconcile_power_bindings(
                previous_energy, self.configuration, datetime.now(timezone.utc), field="energy_entity",
            )
        except (ValueError, TypeError, KeyError, OverflowError):
            _LOGGER.warning("Invalid stored energy binding history; earlier meter intervals are unknown")
            self.energy_bindings = reconcile_power_bindings(
                {}, self.configuration, datetime.now(timezone.utc), field="energy_entity",
            )
        previous_tariffs = snapshot.get("tariff_bindings") if isinstance(snapshot, dict) else None
        try:
            self.tariff_bindings = reconcile_tariff_bindings(
                previous_tariffs, self.configuration, datetime.now(timezone.utc))
        except (ValueError, TypeError, KeyError, OverflowError):
            _LOGGER.warning("Invalid stored tariff binding history; earlier valuations are unknown")
            self.tariff_bindings = reconcile_tariff_bindings(
                {}, self.configuration, datetime.now(timezone.utc))
        if isinstance(snapshot, dict):
            pending = snapshot.get("pending_cost_archive", {})
            try:
                self._archive_pending = restore_pending_archive(pending)
            except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
                self._archive_unreadable = pending if pending is not None else []
                _LOGGER.error("Invalid pending native cost archive; original retry evidence retained")
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
                    "power_bindings": self.power_bindings,
                    "energy_bindings": self.energy_bindings,
                    "tariff_bindings": self.tariff_bindings,
                    "pending_cost_archive": (
                        self._archive_unreadable if self._archive_unreadable is not None
                        else pending_archive_snapshot(self._archive_pending)
                    ),
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
        if (self._session_cost_identity is not None
                and self._session_cost_identity != self._current_session_cost_identity()):
            self.session_costs = {}
            self.period_costs = {}
            self._session_cost_identity = None
        # Native entity listeners share one projection during this synchronous dispatch.
        self._notification_capabilities = self.executor.capabilities() if self._listeners else None
        self._notification_live = self.live_state() if self._listeners else None
        self._notification_charger_states = self.charger_states(self._notification_capabilities) if self._listeners else None
        try:
            for listener in tuple(self._listeners):
                listener()
        finally:
            self._notification_capabilities = None
            self._notification_live = None
            self._notification_charger_states = None

    def projected_capabilities(self):
        cached = getattr(self, "_notification_capabilities", None)
        return cached if cached is not None else self.executor.capabilities()

    def stop(self):
        self.active = False
        self.executor.detach()
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        self._listeners.clear()

    def qualified_tariff(self, at):
        """One native price reader for proposals and fresh physical admission."""
        setting = self.configuration["controller"]
        tariff_source = setting.get("price_entity") or setting.get("current_price_entity")
        tariff_coverage = {}
        tariff, tariff_quality = intervals(
            self.hass, tariff_source, "price", at, coverage_details=tariff_coverage,
        )
        if (tariff_quality != "OK" and self.nordpool_prices
                and self.nordpool_prices[0] == tariff_source):
            _, cached, quality, fetched_at = self.nordpool_prices
            if at - fetched_at <= timedelta(minutes=45) and any(row.end > at for row in cached):
                tariff, tariff_quality = cached, quality
            elif quality != "OK":
                tariff_quality = quality
        return tuple(tariff), tariff_quality, tariff_coverage

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
            if soc_based and reading.quality == "ok" and asset.get("target_soc") is not None and reading.value >= asset["target_soc"]:
                amount = 0.0
            if soc_based and amount != 0 and (
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
            if soc_based and amount is None:
                reason = ("NO_CHARGING_GOAL" if asset.get("target_soc") is None
                          else "SOC_SOURCE_UNAVAILABLE" if reading.quality != "ok"
                          else "BATTERY_CAPACITY_NOT_CONFIGURED" if "capacity_kwh" not in asset
                          else "CHARGE_EFFICIENCY_NOT_CONFIGURED")
                self.excluded[uid] = reason
                self.forecast_excluded[uid] = reason
                continue
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
                # A measured SoC target is a live goal, not a permanently
                # completed finite-energy receipt. A later SoC drop must
                # appear as new remaining demand, not as a reached target.
                if self.executor.intent_completed(asset, raw, deadline):
                    if soc_based and amount > 0:
                        # A previously completed occurrence cannot silently
                        # replay. Preserve measured current SoC as the truth.
                        self.excluded[uid] = "SOC_TARGET_DROPPED_AFTER_COMPLETION"
                        self.forecast_excluded[uid] = "SOC_TARGET_DROPPED_AFTER_COMPLETION"
                        continue
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
            draw_at = at
            wall = datetime.now(timezone.utc)
            # The native quarter callback anchors planning to the quarter,
            # but actual provider readbacks may arrive a few seconds later.
            if at <= wall < at+timedelta(seconds=10):
                draw_at = wall
            draw = (self.executor.qualified_session_draw(raw, asset, draw_at, power, reading)
                    if amount is not None and not disconnected else None)
            if draw is not None:
                self.observations["chargers"][uid]["session_draw_estimate"] = draw
            request = ChargeDemand(
                asset_uid=asset["id"], charger_uid=uid,
                observed_session_draw_kw=draw["power_kw"] if draw else None,
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
            identity_unconfirmed = (
                not disconnected and not inactive and not duration_without_connection
                and self.executor.connection_confirmation(raw, at) is None
            )
            # An Active, confirmed charger without electrical conversion
            # can still show a rated-kW preview, never a guessed current.
            capability_unverified = missing_current_conversion(chargers[uid])
            if disconnected or inactive or identity_unconfirmed or capability_unverified:
                if disconnected:
                    self.executor.connection_confirmation(raw, at)
                self.excluded[uid] = (
                    "DISCONNECTED" if disconnected else "CHARGER_INACTIVE" if inactive
                    else "CURRENT_PLUG_ASSET_UNCONFIRMED" if identity_unconfirmed
                    else "VARIABLE_CURRENT_CAPABILITY_UNVERIFIED"
                )
                indicative_demands.append(request)
                self.forecast_assumptions[uid] = {
                    "asset_id": asset["id"], "charger_id": uid,
                    "assumption": (
                        "USER_EXPECTED_CONNECTION_TIME" if assumed_arrival
                        else "IF_CONNECTED_NOW" if disconnected else "IF_ACTIVATED" if inactive
                        else "IF_SELECTED_VEHICLE_CONFIRMED" if identity_unconfirmed
                        else "IF_CAPABILITY_VERIFIED"
                    ),
                    "assumed_connection_at": (
                        max(at, assumed_arrival).isoformat()
                        if assumed_arrival else at.isoformat()
                    ),
                    "physically_connected": cable.value if cable.quality == "ok" else None,
                    "power_capability_verified": not capability_unverified,
                    "may_execute": False,
                    "reserves_capacity": False,
                }
            else:
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
        tariff_source = setting.get("price_entity") or setting.get("current_price_entity")
        tariff, tariff_quality, tariff_coverage = self.qualified_tariff(at)
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
        # A separately selected import-price entity owns the current reading.
        # Forecast data must not impersonate it, including when it is unavailable.
        live_source = setting.get("current_price_entity")
        separate_live_source = live_source and live_source != tariff_source
        if separate_live_source or (
                current_price["quality"] != "ok" and native_price.quality == "ok"):
            current_price = {
                "quality": native_price.quality, "value": native_price.value,
                "currency": native_currency, "basis": "current_only",
            }
            if native_price.quality != "ok":
                current_price["reason"] = native_price.reason
        self.observations["sources"] = {
            "tariff_quality": tariff_quality, "solar_quality": solar_quality,
            "tariff_source": tariff_source,
            "tariff_basis": tariff[0].basis if tariff else None,
            "tariff_coverage_until": tariff[-1].end.isoformat() if tariff else None,
            "tariff_slot_count": len(tariff),
            "tariff_tomorrow_quality": tariff_coverage.get("tomorrow_quality"),
            "binding_quality": binding_quality,
            "current_price": current_price,
            "solar_power": _display_power(self.hass, setting.get("solar_power_entity"), at),
            "home_power": _display_power(self.hass, setting.get("home_power_entity"), at),
            "grid_power": _display_power(self.hass, setting.get("grid_power_entity"), at, signed=True),
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
        except (ValueError, TypeError, OverflowError) as exc:
            _LOGGER.warning("MultiCharge proposal unavailable: %s", exc)
            self.assessment = None
            self.excluded["controller"] = "INVALID_PLANNING_INPUT"
        if indicative_demands and self.assessment is not None:
            try:
                # A failed optional preview cannot erase the real plan.
                self.forecast_assessment = compile_plan(
                    controller, chargers, indicative_demands, at,
                    mode=setting["mode"],
                    tariffs={uid: tariff for uid in chargers}, solar=solar,
                    binding=external_binding,
                    reserved_slots=self.assessment.plan.slots,
                    charging_windows=active_windows, site_time_zone=site_zone,
                    indicative_only=True,
                )
            except (ValueError, TypeError, OverflowError) as exc:
                _LOGGER.warning("MultiCharge indicative proposal unavailable: %s", exc)
                self.forecast_excluded["controller"] = "INVALID_PLANNING_INPUT"
        # Project the SAME planner result, before any chart-range filtering.
        # The forecast visibility preference is presentation, not goal truth.
        self.goal_assessments = {}
        requests = {d.charger_uid: d for d in (*demands, *indicative_demands)}
        for row in cfg["chargers"]:
            uid = row["id"]
            asset = assets.get(row.get("asset"))
            if asset is None:
                continue
            request = requests.get(uid)
            conditional = uid in self.forecast_assumptions
            assessment = self.forecast_assessment if conditional else self.assessment
            reason = (
                assessment.reasons.get(uid) if assessment else None
            ) or self.forecast_excluded.get(uid) or self.excluded.get(uid) or "INVALID_PLANNING_INPUT"
            due = request.ready_by if request else None
            proposed = assessment.proposed_kwh.get(uid) if assessment else None
            shortfall = assessment.shortfall_kwh.get(uid) if assessment else None
            coverage = assessment.coverage.get(uid) if assessment else None
            status = "cannot_assess"
            recovery = bool(assessment and
                "deadline_recovery" in assessment.strategy.get(uid, "").split(","))
            soc = self.observations["assets"][asset["id"]]["soc"]
            measured_target_met = (
                all(asset.get(k) is None for k in (
                    "requested_kwh", "requested_duration_minutes", "requested_budget_amount"
                )) and asset.get("target_soc") is not None
                and soc.quality == "ok" and soc.value >= asset["target_soc"]
            )
            if measured_target_met:
                status, reason = "target_met", "TARGET_MET"
                proposed, shortfall = 0.0, 0.0
            elif reason == "TARGET_MET":
                status = "target_met"
            elif conditional and not self.forecast_assumptions[uid]["power_capability_verified"]:
                # A conservative minimum-power preview is useful for orientation,
                # but assumed electrical conversion cannot qualify the deadline.
                status, reason = "cannot_assess", "VARIABLE_CURRENT_CAPABILITY_UNVERIFIED"
                shortfall = None
            elif reason == "PROPOSED" and coverage == "COMPLETE":
                status = "achievable" if due is not None and setting["mode"] != "Force Charge" and not recovery else "planned"
            elif (due is not None and due <= at + timedelta(hours=48)
                    and setting["mode"] != "Force Charge"
                    and reason in ("DEADLINE_PASSED", "INSUFFICIENT_CAPACITY_OR_TIME",
                                   "PRICE_LIMIT_BLOCKED", "CHARGING_WINDOW_LIMITED")):
                status = "shortfall"
            future = [
                slot for slot in assessment.plan.slots
                if slot.charger_uid == uid and slot.end > at
            ] if assessment and not measured_target_met else []
            # Adjacent quarters form one display window; retain all gaps.
            # The same planner slots remain authoritative for actual power.
            windows = []
            for slot in sorted(future, key=lambda item: item.start):
                if windows and windows[-1]["end"] == slot.start.isoformat():
                    windows[-1]["end"] = slot.end.isoformat()
                else:
                    windows.append({"start": slot.start.isoformat(), "end": slot.end.isoformat()})
            self.goal_assessments[uid] = {
                "timeline_start": at.isoformat(),
                "timeline_end": (at + timedelta(hours=48)).isoformat(),
                "timeline_windows": windows,
                "next_charge_at": min(slot.start for slot in future).isoformat() if future else None,
                "planned_finish_at": max(slot.end for slot in future).isoformat() if future else None,
                "asset_id": asset["id"], "status": status, "reason": reason,
                "conditional": conditional, "deadline": (
                    due.isoformat() if due else self.observations["assets"][asset["id"]]["next_ready_by"]
                ),
                "required_grid_kwh": 0.0 if measured_target_met else request.remaining_grid_kwh if request else None,
                "planned_grid_kwh": proposed, "shortfall_grid_kwh": shortfall,
                "coverage": coverage,
                "assumption": self.forecast_assumptions.get(uid, {}).get("assumption"),
                "power_capability_verified": self.forecast_assumptions.get(uid, {}).get(
                    "power_capability_verified", not missing_current_conversion(chargers[uid])),
                "minimum_planning_power_kw": minimum_planning_power(chargers[uid]),
                "minimum_planning_power_assumed": missing_current_conversion(chargers[uid]),
                "deadline_recovery": recovery,
                "maximum_reserved_power_kw": max((slot.power_kw for slot in future), default=None),
                "headroom_boost": any(
                    slot.planning_power_kw is not None
                    and slot.power_kw > minimum_planning_power(chargers[uid])+1e-6
                    and slot.strategy != "deadline_recovery" for slot in future),
                "session_draw_estimate": self.observations["chargers"][uid].get("session_draw_estimate"),
            }
        # Revalue the current proposal once per planner refresh, not per entity notification.
        self.planned_costs = planned_costs(
            self.assessment.plan.slots if self.assessment else (),
            self.price_slots, at,
        )
        self.notify()

    def charger_states(self, capabilities=None):
        """Four read-only projections of the existing source and control truth."""
        cached = getattr(self, "_notification_charger_states", None)
        if cached is not None:
            return cached
        if capabilities is None:
            capabilities = self.projected_capabilities()
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
            if goal_reason == "MANUAL_START_REQUIRES_FORCE_CHARGE" and charger.get("asset") is not None:
                # A disabled manual action is not the readiness of an
                # automatic charging plan. Use the same planner evidence.
                goal_reason = self.excluded.get(uid)
                if goal_reason is None and self.assessment is not None:
                    goal_reason = self.assessment.reasons.get(uid)
                if goal_reason == "PROPOSED":
                    goal_reason = "READY"
                elif goal_reason is None:
                    goal_reason = "INVALID_PLANNING_INPUT"
            if reported == "fault":
                readiness, reason = "error", "CHARGER_REPORTED_FAULT"
            elif reported == "unavailable" or (charger.get("control_entity") and switch is None and activation == "active"):
                readiness, reason = "unavailable", "CHARGER_SOURCE_UNAVAILABLE"
            elif activation == "inactive":
                readiness, reason = "waiting", "CHARGER_INACTIVE"
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
                elif goal_reason not in (None, "READY", "MANUAL_START_REQUIRES_FORCE_CHARGE", "SWITCH_ALREADY_ON"):
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
        cached = getattr(self, "_notification_live", None)
        if cached is not None:
            return cached
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
            "active_chargers": sum(c.get("control_owner") == "multicharge" and c.get("physical_commissioned") is True for c in chargers),
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
                for x in self.projected_capabilities().values()
            ),
            "command_outcomes": self.executor.snapshot(),
            "active_sessions": self.executor.session_snapshot(),
            "completed_sessions": self.executor.completed_sessions(limit=200),
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
        ) and charger_id not in self.power_bindings:
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
                    "proposed_power_kw": slot.expected_power_kw,
                    "reserved_power_kw": slot.power_kw,
                    "proposed_current_a": slot.current_a,
                    "proposed_energy_kwh": round(
                        slot.expected_power_kw * (slot.end - slot.start).total_seconds() / 3600, 6
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
            if accepted.get("confirmed_from") or accepted.get("changes") or accepted.get("closed_at"):
                # Proposal remains a quarter; actual confirmed admission
                # cannot be backdated to its planned beginning.
                close = (datetime.fromisoformat(accepted["closed_at"])
                         if accepted.get("closed_at") else accepted["end"])
                cursor = (datetime.fromisoformat(accepted["confirmed_from"])
                          if accepted.get("confirmed_from") else accepted["start"])
                power, current = accepted["power_kw"], accepted["current_a"]
                changes = [*accepted.get("changes", []),
                           {"at": close.isoformat(), "power_kw": None, "current_a": None}]
                for change in changes:
                    stamp = datetime.fromisoformat(change["at"])
                    if cursor < stamp and stamp > first and cursor < last:
                        slots.append({
                            "charger_id": accepted["charger_id"],
                            "asset_id": accepted["asset_id"],
                            "start": cursor.isoformat(), "end": stamp.isoformat(),
                            "proposed_power_kw": None, "proposed_energy_kwh": None,
                            "proposed_current_a": None,
                            "accepted_power_kw": power, "accepted_current_a": current,
                            "accepted_timing_quality": ("confirmed_interval"
                                if accepted.get("confirmed_from") else "legacy_quarter_receipt"),
                            "actual_power_kw": None, "actual_energy_kwh": None,
                        })
                    cursor, power, current = stamp, change["power_kw"], change["current_a"]
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
            match["accepted_timing_quality"] = "legacy_quarter_receipt"
        slots.sort(key=lambda row: (row["start"], row["charger_id"]))
        forecast_slots = []
        if (self.forecast_assessment is not None
                and self.configuration["controller"].get("show_indicative_forecast", True)):
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
        at = datetime.now(timezone.utc)
        def view_costs(assessment):
            return planned_costs(
                [slot for slot in assessment.plan.slots
                 if (charger_id is None or slot.charger_uid == charger_id)
                 and (asset_id is None or slot.asset_uid == asset_id)] if assessment else (),
                self.price_slots, max(at, first), until=last,
            )["controller"]["site"]
        return {
            "schema_major": 1,
            "plan_palette": dict(PLAN_COLORS),
            "planned_costs": self.planned_costs,
            "view_planned_cost": view_costs(assessment),
            "view_indicative_cost": view_costs(self.forecast_assessment)
                if self.configuration["controller"].get("show_indicative_forecast", True) else None,
            "session_costs": self.session_costs,
            "period_costs": self.period_costs,
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
            "goal_assessments": {
                uid: dict(result) for uid, result in self.goal_assessments.items()
                if (charger_id is None or uid == charger_id)
                and (asset_id is None or result["asset_id"] == asset_id)
            },
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
                for x in self.projected_capabilities().values()
            ),
        }
