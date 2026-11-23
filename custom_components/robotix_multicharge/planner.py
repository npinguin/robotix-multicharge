"""Deterministic, source-neutral quarter-hour charging proposals.

A proposal NEVER grants a physical write.  Unknown capacity is not unlimited,
and source price/solar/binding coverage is never filled with fabricated zeros.
The HA adapter supplies qualified source readings; the command owner is separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from hashlib import sha256
from math import ceil, floor, isfinite
from typing import Mapping, Sequence

from .contracts import (
    ChargeDemand, ChargePlan, PlannedChargeSlot, PowerEnvelope, PowerLimitSlot,
    PriceSlot,
)
from .domain import ChargeController, Charger

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _valid_wall_utc(local_day: date, clock: str, zone: ZoneInfo) -> datetime:
    """Reuse EVSC V2's real local-minute/DST semantics without its runtime.

    A spring gap moves to the first actual minute; a repeated autumn minute
    picks the later occurrence. Never compare naive local time as UTC.
    """
    wall = datetime.combine(local_day, time.fromisoformat(clock))
    for minute in range(181):
        candidate = wall + timedelta(minutes=minute)
        possible = []
        for fold in (0, 1):
            aware = candidate.replace(tzinfo=zone, fold=fold)
            utc = aware.astimezone(timezone.utc)
            if utc.astimezone(zone).replace(tzinfo=None) == candidate:
                possible.append(utc)
        if possible:
            return max(possible)
    raise ValueError("DST local time cannot be resolved")


def _next_specific_day(now: datetime, weekdays: Mapping[str, str],
                       site_time_zone: str) -> tuple[datetime | None, str]:
    if not weekdays or set(weekdays) - set(WEEKDAYS):
        return None, "DEADLINE_UNAVAILABLE"
    zone = ZoneInfo(site_time_zone)
    today = now.astimezone(zone).date()
    for offset in range(8):
        day = today + timedelta(days=offset)
        clock = weekdays.get(WEEKDAYS[day.weekday()])
        if clock is None:
            continue
        candidate = _valid_wall_utc(day, clock, zone)
        if candidate > now.astimezone(timezone.utc):
            return candidate, "RECURRING"
    return None, "DEADLINE_UNAVAILABLE"


def charging_window_allows(windows: Mapping[str, Mapping[str, str]],
                           when: datetime, duration: timedelta,
                           site_time_zone: str) -> bool:
    """Only complete intervals inside a selected local weekday window count.

    Cross-midnight windows belong to their chosen start weekday. A missing
    window policy means no additional calendar restriction.
    """
    if not windows:
        return True
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("charging window requires aware instant")
    zone = ZoneInfo(site_time_zone)
    local_day = when.astimezone(zone).date()
    first = when.astimezone(timezone.utc)
    last = first + duration
    for day in (local_day - timedelta(days=1), local_day):
        window = windows.get(WEEKDAYS[day.weekday()])
        if window is None:
            continue
        start = _valid_wall_utc(day, window["start"], zone)
        end_day = day + timedelta(days=(window["end"] <= window["start"]))
        end = _valid_wall_utc(end_day, window["end"], zone)
        if start <= first and last <= end:
            return True
    return False


def qualified_price_policy_cap(
    cap: float | None, kind: str, level: float | None,
    currency: str | None, prices: Sequence[PriceSlot],
    first: datetime, deadline: datetime,
) -> tuple[float | None, str | None]:
    """Shared source-qualified upstream price policy, never a second planner.

    The original upstream Type1/Type2 strategy adjusts the *allowed rate*
    based on the last actually observed future quote, not a guessed spot.
    Returned 'error' is explicit; no caller may treat it as a zero price.
    """
    if kind == "off":
        return cap, None
    if kind not in ("type1", "type2") or cap is None:
        return None, "INVALID_PRICE_POLICY"
    future = [
        p for p in prices if p.end > first and p.start < deadline
        and p.currency == currency
    ]
    if not future:
        return None, "PRICE_SOURCE_UNAVAILABLE"
    last = max(future, key=lambda q: q.start)
    fraction = (level if level is not None else
                (50.0 if kind == "type1" else 90.0))
    if kind == "type1":
        threshold = cap * fraction / 100
        if last.effective_price_per_kwh < threshold:
            return threshold, None
        return cap, None
    last_price = last.effective_price_per_kwh
    calculated = (last_price * fraction / 100 if last_price >= 0
                  else last_price * (200 - fraction) / 100)
    return min(cap, calculated), None


def resolve_recurring_ready_by(
    anchor: datetime | None, now: datetime, repeat: str, site_time_zone: str,
    weekday_times: Mapping[str, str] | None = None,
) -> tuple[datetime | None, str]:
    """Resolve the next real wall-clock deadline without inventing DST instants.

    Recurrence is local to the HA site time zone; ambiguous or nonexistent
    upcoming wall times fail closed rather than silently shifting deadlines.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if repeat == "specific_days":
        return _next_specific_day(now, weekday_times or {}, site_time_zone)
    if anchor is None or anchor.tzinfo is None or anchor.utcoffset() is None:
        raise ValueError("Ready By anchor must be timezone-aware")
    if repeat == "none":
        return anchor, "ONE_OFF"
    if repeat not in ("daily", "weekly"):
        raise ValueError("unsupported Ready By repetition")
    zone = ZoneInfo(site_time_zone)
    local_anchor = anchor.astimezone(zone)
    local_now = now.astimezone(zone)
    day = max(local_anchor.date(), local_now.date())
    if repeat == "weekly":
        day += timedelta(days=(local_anchor.weekday() - day.weekday()) % 7)
    step = 1 if repeat == "daily" else 7
    for _ in range(370 if repeat == "daily" else 54):
        wall = datetime.combine(
            day, time(local_anchor.hour, local_anchor.minute,
                      local_anchor.second, local_anchor.microsecond)
        )
        first = wall.replace(tzinfo=zone, fold=0)
        second = wall.replace(tzinfo=zone, fold=1)
        # The two possible offsets differ on ambiguous and nonexistent times.
        # Reject the first upcoming invalid occurrence; do not shift by an
        # implicit hour or quietly skip a user's required departure.
        if first.utcoffset() != second.utcoffset():
            if first > local_now:
                return None, "DEADLINE_DST_UNRESOLVED"
        elif first > local_now and first >= local_anchor:
            return first, "RECURRING"
        day += timedelta(days=step)
    return None, "DEADLINE_UNAVAILABLE"


QUARTER = timedelta(minutes=15)
MODES = frozenset(("Automatic", "Solar", "Economy", "Ready By", "Force Charge", "Off"))


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("time must be timezone-aware")
    return value.astimezone(timezone.utc)


def _ceil_quarter(value: datetime) -> datetime:
    at = _utc(value)
    seconds = at.timestamp()
    return datetime.fromtimestamp(ceil(seconds / 900) * 900, timezone.utc)


def _cover(slots: Sequence[PriceSlot | PowerLimitSlot], start: datetime,
           end: datetime):
    matching = [s for s in slots if _utc(s.start) <= start and _utc(s.end) >= end]
    return matching[0] if len(matching) == 1 else None


@dataclass(frozen=True)
class PlanAssessment:
    """Read-only result: a proposed schedule is not an observed charge session."""

    plan: ChargePlan
    reasons: Mapping[str, str]
    shortfall_kwh: Mapping[str, float | None]
    proposed_kwh: Mapping[str, float]
    coverage: Mapping[str, str]
    strategy: Mapping[str, str]


def compile_plan(
    controller: ChargeController,
    chargers: Mapping[str, Charger],
    demands: Sequence[ChargeDemand],
    now: datetime,
    *,
    mode: str = "Ready By",
    tariffs: Mapping[str, Sequence[PriceSlot]] | None = None,
    solar: Sequence[PowerLimitSlot] | None = None,
    binding: PowerEnvelope | None = None,
    horizon_hours: int = 48,
    reserved_slots: Sequence[PlannedChargeSlot] = (),
    charging_windows: Mapping[str, Mapping[str, Mapping[str, str]]] | None = None,
    site_time_zone: str | None = None,
) -> PlanAssessment:
    """Calculate one deterministic, bounded, non-actuating Controller proposal.

    Slots are UTC-aligned 15-minute intervals; the frontend converts to the
    actual HA local date (which may contain 92, 96 or 100 quarter-hours).
    Tariff slots must cover an entire interval and be unambiguous.  A binding
    source is a *hard* ceiling, including zero, expiry, holes and conflicts.
    Group capacity must be explicitly configured before any allocation.
    """
    at = _utc(now)
    if mode not in MODES:
        raise ValueError("unsupported mode")
    if not isinstance(horizon_hours, int) or not 1 <= horizon_hours <= 48:
        raise ValueError("horizon must be 1..48 hours")
    if binding is not None and binding.authority != "binding":
        raise ValueError("advisory capacity is not a physical binding ceiling")
    # Comparing nominal prices in different currencies creates a false
    # financial optimization; one Charger needs one actual currency basis.
    if tariffs is not None:
        for charger_id, prices in tariffs.items():
            if len({price.currency for price in prices}) > 1:
                raise ValueError(f"mixed tariff currencies for charger {charger_id}")

    reasons: dict[str, str] = {}
    shortfall: dict[str, float | None] = {}
    coverage: dict[str, str] = {}
    strategy: dict[str, str] = {}
    proposed: dict[str, float] = {}
    allocations: list[PlannedChargeSlot] = []
    ends = at + timedelta(hours=horizon_hours)
    begin = _ceil_quarter(at)
    intervals: list[datetime] = []
    cursor = begin
    while cursor + QUARTER <= ends:
        intervals.append(cursor)
        cursor += QUARTER

    used_kw: dict[datetime, float] = {}
    used_phase_a: dict[datetime, dict[str, float]] = {}
    used_circuit_a: dict[datetime, dict[str, float]] = {}
    active: dict[datetime, set[str]] = {}
    seen: set[str] = set()
    # Forecast scenarios run AFTER the live proposal: its existing physical
    # allocations consume capacity but cannot be changed by a hypothetical EV.
    # This is still the ONE planning engine, never a second executable plan.
    for locked in reserved_slots:
        start = _utc(locked.start)
        if start not in intervals or _utc(locked.end) != start + QUARTER:
            continue
        owner = chargers.get(locked.charger_uid)
        if owner is None:
            raise ValueError("reserved charger is unknown")
        used_kw[start] = used_kw.get(start, 0.0) + locked.power_kw
        active.setdefault(start, set()).add(locked.charger_uid)
        current = locked.current_a if owner.control_kind == "variable_current" else owner.fixed_current_a
        if current is not None:
            for phase in owner.phase_ids:
                phases = used_phase_a.setdefault(start, {})
                phases[phase] = phases.get(phase, 0.0) + current
            if owner.circuit_id:
                circuits = used_circuit_a.setdefault(start, {})
                circuits[owner.circuit_id] = circuits.get(owner.circuit_id, 0.0) + current
    ranked = sorted(demands, key=lambda d: (
        -d.priority, _utc(d.ready_by) if d.ready_by else datetime.max.replace(
            tzinfo=timezone.utc), d.charger_uid or "", d.asset_uid,
    ))
    for demand in ranked:
        uid = demand.charger_uid
        if not uid or uid not in chargers:
            raise ValueError("demand must reference an existing charger")
        if uid in seen:
            raise ValueError("duplicate charging request for one physical charger")
        seen.add(uid)
        charger = chargers[uid]
        if charger.controller_uid != controller.uid:
            raise ValueError("charger belongs to another Controller")
        proposed[uid] = 0.0
        if mode == "Off":
            reasons[uid] = "OFF"
            strategy[uid] = "Off"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "NOT_REQUIRED"
            continue
        if (demand.remaining_grid_kwh is None
                and demand.remaining_duration_minutes is None
                and demand.remaining_budget_amount is None):
            reasons[uid] = "DEMAND_UNKNOWN"
            shortfall[uid] = None
            coverage[uid] = "UNAVAILABLE"
            continue
        if demand.remaining_grid_kwh == 0 or demand.remaining_budget_amount == 0:
            reasons[uid] = "TARGET_MET"
            shortfall[uid] = 0.0
            coverage[uid] = "NOT_REQUIRED"
            continue
        if demand.ready_by is None and mode == "Ready By":
            reasons[uid] = "DEADLINE_UNKNOWN"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        # Economy, Solar and Automatic can plan to the bounded horizon when
        # no departure is configured. Force Charge explicitly ignores a later
        # deadline, but NEVER the electrical or evidence limits.
        deadline = (
            _utc(demand.ready_by)
            if demand.ready_by is not None and mode != "Force Charge"
            else ends
        )
        if deadline <= begin:
            reasons[uid] = "DEADLINE_PASSED"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        if controller.max_group_power_kw is None:
            reasons[uid] = "GROUP_CAPACITY_UNQUALIFIED"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        if not isfinite(charger.rated_power_kw) or charger.rated_power_kw <= 0:
            reasons[uid] = "CHARGER_CAPABILITY_UNQUALIFIED"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        if (
            charger.control_kind == "on_off"
            and demand.max_power_kw is not None
            and demand.max_power_kw + 1e-9 < charger.rated_power_kw
        ):
            # A full-power fixed-slot proposal would exceed the asset cap.
            # Variable-current control needs separately verified voltage,
            # phase, min/max and setpoint readback before it can be accepted.
            reasons[uid] = "ASSET_POWER_LIMIT_REQUIRES_VERIFIED_MODULATION"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        # A verified adjustable charger can propose stepped current, never a
        # fictitious fractional on/off switch. Unknown wiring remains unavailable.
        adjustable = charger.control_kind == "variable_current"
        if adjustable and (
            not charger.phase_ids or charger.voltage_v is None
            or charger.current_step_a is None
        ):
            reasons[uid] = "VARIABLE_CURRENT_CAPABILITY_UNVERIFIED"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        if controller.phase_limits_a is not None and (
            not charger.phase_ids or charger.voltage_v is None
            or any(p not in controller.phase_limits_a for p in charger.phase_ids)
            or (not adjustable and charger.fixed_current_a is None)
        ):
            reasons[uid] = "PHASE_WIRING_UNVERIFIED"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        if charger.circuit_id and charger.circuit_limit_a is None:
            reasons[uid] = "CIRCUIT_LIMIT_UNVERIFIED"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        # Upstream v2.6.1 price policies are Asset-owned preferences,
        # interpreted by the ONE 15-min Controller planner. A price limit
        # never invents a currency or source interval.
        effective_cap, price_policy_error = qualified_price_policy_cap(
            demand.maximum_price_per_kwh, demand.opportunistic_kind,
            demand.opportunistic_level_pct, demand.price_currency,
            (tariffs or {}).get(uid, ()), begin, deadline,
        )
        if price_policy_error:
            reasons[uid] = price_policy_error
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        possible = []
        blocked_price = set()
        low_price_eligible = set()
        missing_price = False
        missing_solar = False
        missing_binding = False
        outside_window = False
        for slot in intervals:
            finish = slot + QUARTER
            window = (charging_windows or {}).get(uid)
            if window:
                if not site_time_zone:
                    raise ValueError("charging window requires site time zone")
                if not charging_window_allows(window, slot, QUARTER, site_time_zone):
                    outside_window = True
                    continue
            if (finish > deadline or
                    demand.not_before is not None and slot < _utc(demand.not_before)):

                continue
            cap = controller.max_group_power_kw
            if binding is not None:
                if (_utc(binding.issued_at) > slot
                        or _utc(binding.valid_until) < finish):
                    missing_binding = True
                    continue
                bound = _cover(binding.slots, slot, finish)
                if bound is None:
                    missing_binding = True
                    continue
                cap = min(cap, bound.max_charging_kw)
            if mode == "Solar":
                source = _cover(solar or (), slot, finish)
                if source is None:
                    missing_solar = True
                    continue
                cap = min(cap, source.max_charging_kw)
            if len(active.get(slot, ())) >= controller.max_parallel:
                continue
            remaining_kw = cap - used_kw.get(slot, 0.0)
            if demand.max_power_kw is not None:
                remaining_kw = min(remaining_kw, demand.max_power_kw)
            phases = charger.phase_ids
            voltage = charger.voltage_v
            if adjustable:
                remaining_kw = min(remaining_kw, charger.rated_power_kw)
                current_cap = min(charger.max_current_a,
                                  remaining_kw * 1000 / (voltage * len(phases)))
                if charger.max_charging_power_kw is not None:
                    current_cap = min(
                        current_cap,
                        charger.max_charging_power_kw * 1000
                        / (voltage * len(phases))
                    )
                if controller.phase_limits_a is not None:
                    current_cap = min(current_cap, *(
                        controller.phase_limits_a[p] - used_phase_a.get(slot, {}).get(p, 0)
                        for p in phases
                    ))
                if charger.circuit_id:
                    current_cap = min(
                        current_cap, charger.circuit_limit_a
                        - used_circuit_a.get(slot, {}).get(charger.circuit_id, 0)
                    )
                steps = floor((current_cap - charger.min_current_a + 1e-9)
                              / charger.current_step_a)
                current = (charger.min_current_a + max(0, steps) * charger.current_step_a)
                if current_cap + 1e-9 < charger.min_current_a:
                    continue
                power = round(current * voltage * len(phases) / 1000, 6)
                if (charger.min_charging_power_kw is not None
                        and power + 1e-9 < charger.min_charging_power_kw):
                    continue
            else:
                power = charger.rated_power_kw
                current = charger.fixed_current_a
                if power > remaining_kw + 1e-9:
                    continue
                if controller.phase_limits_a is not None and any(
                    used_phase_a.get(slot, {}).get(p, 0) + current >
                    controller.phase_limits_a[p] + 1e-9 for p in phases
                ):
                    continue
                if charger.circuit_id and (
                    current is None or used_circuit_a.get(slot, {}).get(
                        charger.circuit_id, 0
                    ) + current > charger.circuit_limit_a + 1e-9
                ):
                    continue
            tariff = _cover((tariffs or {}).get(uid, ()), slot, finish)
            if mode == "Economy" and tariff is None:
                missing_price = True
                continue
            if demand.remaining_budget_amount is not None:
                if (tariff is None or tariff.basis != "effective"
                        or tariff.currency != demand.budget_currency):
                    missing_price = True
                    continue
            rate = tariff.effective_price_per_kwh if tariff is not None else None
            if (effective_cap is not None
                    or demand.low_price_trigger_per_kwh is not None):
                if tariff is None or tariff.currency != demand.price_currency:
                    missing_price = True
                    continue
                if effective_cap is not None and rate > effective_cap + 1e-9:
                    blocked_price.add(slot)
                if (demand.low_price_trigger_per_kwh is not None
                        and rate <= demand.low_price_trigger_per_kwh + 1e-9):
                    low_price_eligible.add(slot)
            if mode == "Automatic":
                available_solar = _cover(solar or (), slot, finish)
                solar_covers = (
                    available_solar is not None
                    and used_kw.get(slot, 0.0) + power
                    <= available_solar.max_charging_kw + 1e-9
                )
                if rate is not None and rate < 0:
                    key, chosen_strategy = (-1, rate), "negative_tariff"
                elif solar_covers:
                    key, chosen_strategy = (0, 0.0), "solar"
                elif rate is not None:
                    key, chosen_strategy = (1, rate), "economy"
                else:
                    key, chosen_strategy = (2, 0.0), "ready_by_fallback"
            elif mode == "Economy":
                key, chosen_strategy = (0, rate), "economy"
            else:
                key, chosen_strategy = (0, 0.0), mode
            possible.append((key, slot, chosen_strategy, power, current, rate))
        possible.sort(key=lambda item: (item[0], item[1]))
        urgent_kwh = max(
            demand.minimum_priority_kwh, demand.low_soc_priority_kwh,
        )
        if demand.continuous_charging:
            # Select one real feasible price/SoC-compliant consecutive run.
            # A minimum-SoC override may use expensive early quarters ONLY
            # until the separately measured minimum energy is reached.
            if demand.remaining_budget_amount is not None:
                reasons[uid] = "CONTINUOUS_BUDGET_REQUIRES_FINITE_TIME"
                shortfall[uid] = None
                coverage[uid] = "UNAVAILABLE"
                continue
            chronological = sorted(possible, key=lambda item: item[1])
            best = None
            for index in range(len(chronological)):
                segment = []
                energy, minutes, cost, priority = 0.0, 0, 0.0, 0
                for item in chronological[index:]:
                    _, stamp, _, power, _, rate = item
                    if segment and stamp != segment[-1][1] + QUARTER:
                        break
                    if (stamp in blocked_price
                            and energy + 1e-9 >= urgent_kwh
                            and not (stamp == begin
                                     and stamp in low_price_eligible)):
                        break
                    segment.append(item)
                    energy += power / 4
                    minutes += 15
                    cost += (rate if rate is not None else 0) * power / 4
                    priority += item[0][0]
                    reached = (
                        minutes >= demand.remaining_duration_minutes
                        if demand.remaining_duration_minutes is not None
                        else energy + 1e-9 >= demand.remaining_grid_kwh
                    )
                    if reached:
                        candidate = (priority,
                                     0 if segment[0][1] == begin
                                     and begin in low_price_eligible else 1,
                                     round(cost, 8), segment[0][1],
                                     tuple(segment))
                        if best is None or candidate[:4] < best[:4]:
                            best = candidate
                        break
            if best is None:
                reasons[uid] = "CONTIGUOUS_WINDOW_UNAVAILABLE"
                shortfall[uid] = demand.remaining_grid_kwh
                coverage[uid] = "INCOMPLETE"
                continue
            possible = list(best[4])
        else:
            # Minimum SoC and a separate low-SoC trigger must be delivered
            # as early as possible; their energy is strictly bounded by
            # actual remaining target energy. Remaining demand respects
            # the explicit user price limit and cheapest global allocation.
            priority_rows = []
            used = set()
            critical_delivered = 0.0
            for item in sorted(possible, key=lambda x: x[1]):
                if critical_delivered + 1e-9 >= urgent_kwh:
                    break
                priority_rows.append(item)
                used.add(item[1])
                critical_delivered += item[3] / 4
            start_low = next((
                item for item in possible
                if item[1] == begin and item[1] in low_price_eligible
                and item[1] not in used
            ), None)
            if start_low is not None:
                priority_rows.append(start_low)
                used.add(start_low[1])
            possible = priority_rows + [
                item for item in possible
                if item[1] not in used and item[1] not in blocked_price
            ]
        chosen = []
        delivered = 0.0
        budget_consumed = 0.0
        for _, slot, selected_mode, power, current, rate in possible:
            if demand.remaining_budget_amount is not None:
                # A complete quarter must fit the remaining positive spend.
                # Negative tariffs never give unlimited credit or permission.
                if (rate is None or rate < 0 and not isfinite(rate)):
                    continue
                charge_cost = max(0.0, rate) * power / 4
                if budget_consumed + charge_cost > demand.remaining_budget_amount + 1e-9:
                    continue
                budget_consumed += charge_cost
            if demand.remaining_duration_minutes is not None:
                if len(chosen) * 15 >= demand.remaining_duration_minutes:
                    break
            elif (demand.remaining_budget_amount is None
                    and delivered + 1e-9 >= demand.remaining_grid_kwh):
                break
            chosen.append((slot, selected_mode, power, current))
            delivered += power / 4
        chosen.sort(key=lambda item: item[0])
        strategy[uid] = ",".join(sorted({method for _, method, _, _ in chosen})) if chosen else mode
        for slot, _, power, current in chosen:
            allocations.append(PlannedChargeSlot(
                charger_uid=uid, asset_uid=demand.asset_uid, start=slot,
                end=slot + QUARTER, power_kw=power,
                current_a=current if adjustable else None,
            ))
            active.setdefault(slot, set()).add(uid)
            used_kw[slot] = used_kw.get(slot, 0.0) + power
            if current is not None:
                phases_used = used_phase_a.setdefault(slot, {})
                for phase in phases:
                    phases_used[phase] = phases_used.get(phase, 0) + current
                if charger.circuit_id:
                    circuits = used_circuit_a.setdefault(slot, {})
                    circuits[charger.circuit_id] = (
                        circuits.get(charger.circuit_id, 0) + current
                    )
        proposed[uid] = round(delivered, 5)
        shortfall[uid] = (
            round(max(0.0, demand.remaining_grid_kwh - delivered), 5)
            if demand.remaining_grid_kwh is not None else None
        )
        completed = (
            budget_consumed + 1e-9 >= demand.remaining_budget_amount
            if demand.remaining_budget_amount is not None
            else len(chosen) * 15 >= demand.remaining_duration_minutes
            if demand.remaining_duration_minutes is not None
            else delivered + 1e-9 >= demand.remaining_grid_kwh
        )
        if completed:
            reasons[uid] = "PROPOSED"
            coverage[uid] = "COMPLETE"
        else:
            reasons[uid] = (
                "BINDING_CAPACITY_UNAVAILABLE" if missing_binding
                else "SOLAR_UNAVAILABLE" if mode == "Solar" and missing_solar
                else "BUDGET_EFFECTIVE_TARIFF_UNAVAILABLE" if (
                    demand.remaining_budget_amount is not None and missing_price)
                else "PRICE_UNAVAILABLE" if (
                    mode == "Economy" and missing_price
                    and demand.maximum_price_per_kwh is None
                    and demand.low_price_trigger_per_kwh is None)
                else "PRICE_SOURCE_UNAVAILABLE" if missing_price
                else "PRICE_LIMIT_BLOCKED" if blocked_price
                else "CHARGING_WINDOW_LIMITED" if outside_window
                else "INSUFFICIENT_CAPACITY_OR_TIME"
            )
            coverage[uid] = "INCOMPLETE"

    allocations.sort(key=lambda s: (s.start, s.charger_uid))
    signature = "|".join((
        controller.uid, mode,
        *(f"locked:{s.charger_uid}:{s.start.isoformat()}:{s.power_kw}:{s.current_a}"
          for s in reserved_slots),
        *(
            f"{s.charger_uid}:{s.start.isoformat()}:{s.power_kw}:{s.current_a}"
            for s in allocations
        ),
        *(f"{uid}:{reasons[uid]}:{strategy.get(uid, '')}" for uid in sorted(reasons)),
    ))
    revision = sha256(signature.encode("utf-8")).hexdigest()[:16]
    plan = ChargePlan(
        controller_uid=controller.uid,
        revision=revision,
        generated_at=at,
        status=(
            "proposed" if allocations or mode == "Off"
            or (reasons and all(reason == "TARGET_MET" for reason in reasons.values()))
            else "unavailable"
        ),
        slots=tuple(allocations),
    )
    return PlanAssessment(
        plan=plan,
        reasons=reasons,
        shortfall_kwh=shortfall,
        proposed_kwh=proposed,
        coverage=coverage,
        strategy=strategy,
    )
