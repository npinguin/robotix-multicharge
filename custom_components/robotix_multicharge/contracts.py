"""Typed candidate charging contracts. These are not yet a published HA API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Literal


def _time(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")


def _interval(start: datetime, end: datetime) -> None:
    _time(start)
    _time(end)
    if end <= start:
        raise ValueError("interval must have positive duration")


@dataclass(frozen=True)
class PriceSlot:
    start: datetime
    end: datetime
    effective_eur_per_kwh: float  # may be negative; spot is not assumed all-in

    def __post_init__(self) -> None:
        _interval(self.start, self.end)
        if not isfinite(self.effective_eur_per_kwh):
            raise ValueError("price must be finite")


@dataclass(frozen=True)
class PowerLimitSlot:
    start: datetime
    end: datetime
    max_charging_kw: float  # zero is a real hold

    def __post_init__(self) -> None:
        _interval(self.start, self.end)
        if not isfinite(self.max_charging_kw) or self.max_charging_kw < 0:
            raise ValueError("limit must be nonnegative and finite")


@dataclass(frozen=True)
class PowerEnvelope:
    """Revisioned optional supervisory allocation; binding limits are enforceable."""

    provider_id: str
    revision: str
    issued_at: datetime
    valid_until: datetime
    authority: Literal["advisory", "binding"]
    slots: tuple[PowerLimitSlot, ...]

    def __post_init__(self) -> None:
        _interval(self.issued_at, self.valid_until)
        if not self.provider_id.strip() or not self.revision.strip():
            raise ValueError("provider identity and revision required")
        if self.authority not in ("advisory", "binding"):
            raise ValueError("invalid envelope authority")
        if any(slot.end > self.valid_until for slot in self.slots):
            raise ValueError("envelope includes expired allocation")
        if any(a.end > b.start for a, b in zip(self.slots, self.slots[1:])):
            raise ValueError("overlapping or unordered slots")

    def current(self, at: datetime) -> bool:
        _time(at)
        return self.issued_at <= at < self.valid_until


@dataclass(frozen=True)
class ChargeDemand:
    asset_uid: str
    charger_uid: str | None
    remaining_grid_kwh: float | None
    ready_by: datetime | None
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.asset_uid.strip():
            raise ValueError("asset identity required")
        if self.remaining_grid_kwh is not None and (
            not isfinite(self.remaining_grid_kwh) or self.remaining_grid_kwh < 0
        ):
            raise ValueError("remaining demand must be nonnegative or unknown")
        if self.ready_by is not None:
            _time(self.ready_by)


@dataclass(frozen=True)
class PlannedChargeSlot:
    charger_uid: str
    asset_uid: str | None
    start: datetime
    end: datetime
    power_kw: float

    def __post_init__(self) -> None:
        if not self.charger_uid.strip():
            raise ValueError("charger identity required")
        _interval(self.start, self.end)
        if not isfinite(self.power_kw) or self.power_kw < 0:
            raise ValueError("planned power must be nonnegative")


@dataclass(frozen=True)
class ChargePlan:
    """A charging proposal or accepted plan is never measured reality."""

    controller_uid: str
    revision: str
    generated_at: datetime
    status: Literal["proposed", "accepted", "unavailable"]
    slots: tuple[PlannedChargeSlot, ...]

    def __post_init__(self) -> None:
        if not self.controller_uid.strip() or not self.revision.strip():
            raise ValueError("controller identity and revision required")
        _time(self.generated_at)
        if self.status not in ("proposed", "accepted", "unavailable"):
            raise ValueError("invalid plan status")
