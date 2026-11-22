"""Deterministic, source-neutral quarter-hour charging proposals.

A proposal NEVER grants a physical write.  Unknown capacity is not unlimited,
and source price/solar/binding coverage is never filled with fabricated zeros.
The HA adapter supplies qualified source readings; the command owner is separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import ceil, isfinite
from typing import Mapping, Sequence

from .contracts import (
    ChargeDemand, ChargePlan, PlannedChargeSlot, PowerEnvelope, PowerLimitSlot,
    PriceSlot,
)
from .domain import ChargeController, Charger

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

    reasons: dict[str, str] = {}
    shortfall: dict[str, float | None] = {}
    coverage: dict[str, str] = {}
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
    active: dict[datetime, set[str]] = {}
    seen: set[str] = set()
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
        if demand.remaining_grid_kwh is None and demand.remaining_duration_minutes is None:
            reasons[uid] = "DEMAND_UNKNOWN"
            shortfall[uid] = None
            coverage[uid] = "UNAVAILABLE"
            continue
        if demand.remaining_grid_kwh == 0:
            reasons[uid] = "TARGET_MET"
            shortfall[uid] = 0.0
            coverage[uid] = "NOT_REQUIRED"
            continue
        if demand.ready_by is None:
            reasons[uid] = "DEADLINE_UNKNOWN"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        deadline = _utc(demand.ready_by)
        if deadline <= begin:
            reasons[uid] = "DEADLINE_PASSED"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "UNAVAILABLE"
            continue
        if mode == "Off":
            reasons[uid] = "OFF"
            shortfall[uid] = demand.remaining_grid_kwh
            coverage[uid] = "NOT_REQUIRED"
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
        # Fixed nominal power is an *advisory* full-slot estimate.  It is never
        # interpreted as a verified physical current setpoint.
        power = charger.rated_power_kw
        needed = (
            ceil(demand.remaining_duration_minutes / 15)
            if demand.remaining_duration_minutes is not None
            else ceil(demand.remaining_grid_kwh / (power / 4) - 1e-10)
        )
        possible: list[tuple[float, datetime]] = []
        missing_price = False
        missing_solar = False
        missing_binding = False
        for slot in intervals:
            finish = slot + QUARTER
            if finish > deadline:
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
            if used_kw.get(slot, 0.0) + power > cap + 1e-9:
                continue
            if len(active.get(slot, ())) >= controller.max_parallel:
                continue
            tariff = _cover((tariffs or {}).get(uid, ()), slot, finish)
            if mode == "Economy" and tariff is None:
                missing_price = True
                continue
            rate = (
                tariff.effective_eur_per_kwh if tariff is not None
                else 0.0  # ordering ONLY: never a claimed or published price
            )
            # Price sorting is permitted only for qualified slot values.
            key = rate if mode == "Economy" else 0.0
            possible.append((key, slot))
        possible.sort(key=lambda item: (item[0], item[1]))
        chosen = sorted(slot for _, slot in possible[:needed])
        for slot in chosen:
            allocations.append(PlannedChargeSlot(
                charger_uid=uid,
                asset_uid=demand.asset_uid,
                start=slot,
                end=slot + QUARTER,
                power_kw=power,
            ))
            active.setdefault(slot, set()).add(uid)
            used_kw[slot] = used_kw.get(slot, 0.0) + power
        proposed[uid] = round(len(chosen) * power / 4, 5)
        remaining_slots = max(0, needed - len(chosen))
        shortfall[uid] = (
            round(max(0.0, demand.remaining_grid_kwh - proposed[uid]), 5)
            if demand.remaining_grid_kwh is not None
            else None
        )
        if remaining_slots == 0:
            reasons[uid] = "PROPOSED"
            coverage[uid] = "COMPLETE"
        else:
            reasons[uid] = (
                "BINDING_CAPACITY_UNAVAILABLE" if missing_binding
                else "SOLAR_UNAVAILABLE" if mode == "Solar" and missing_solar
                else "PRICE_UNAVAILABLE" if mode == "Economy" and missing_price
                else "INSUFFICIENT_CAPACITY_OR_TIME"
            )
            coverage[uid] = "INCOMPLETE"

    allocations.sort(key=lambda s: (s.start, s.charger_uid))
    signature = "|".join((
        controller.uid, mode,
        *(
            f"{s.charger_uid}:{s.start.isoformat()}:{s.power_kw}"
            for s in allocations
        ),
        *(f"{uid}:{reasons[uid]}" for uid in sorted(reasons)),
    ))
    revision = sha256(signature.encode("utf-8")).hexdigest()[:16]
    plan = ChargePlan(
        controller_uid=controller.uid,
        revision=revision,
        generated_at=at,
        status="proposed" if allocations else "unavailable",
        slots=tuple(allocations),
    )
    return PlanAssessment(
        plan=plan,
        reasons=reasons,
        shortfall_kwh=shortfall,
        proposed_kwh=proposed,
        coverage=coverage,
    )
