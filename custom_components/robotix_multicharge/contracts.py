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
    effective_price_per_kwh: float  # negative allowed; no spot-to-all-in inference
    currency: str  # explicit ISO-4217 currency; never a country assumption
    basis: Literal["effective", "spot", "variable_reference"] = "effective"

    def __post_init__(self) -> None:
        _interval(self.start, self.end)
        if self.basis not in ("effective", "spot", "variable_reference"):
            raise ValueError("price basis must be effective or spot")
        if not isfinite(self.effective_price_per_kwh):
            raise ValueError("price must be finite")
        if (not isinstance(self.currency, str)
                or len(self.currency) != 3
                or not self.currency.isascii()
                or not self.currency.isupper()
                or not self.currency.isalpha()):
            raise ValueError("price currency must be an uppercase ISO-4217 code")


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
    remaining_duration_minutes: float | None = None
    max_power_kw: float | None = None
    not_before: datetime | None = None
    remaining_budget_amount: float | None = None
    budget_currency: str | None = None
    continuous_charging: bool = False
    budget_remaining_minutes: float | None = None
    minimum_priority_kwh: float = 0.0
    low_soc_priority_kwh: float = 0.0
    maximum_price_per_kwh: float | None = None
    low_price_trigger_per_kwh: float | None = None
    price_currency: str | None = None
    opportunistic_kind: str = "off"
    opportunistic_level_pct: float | None = None

    def __post_init__(self) -> None:
        if not self.asset_uid.strip():
            raise ValueError("asset identity required")
        if type(self.continuous_charging) is not bool:
            raise ValueError("charging continuity requires a boolean")
        for field in ("minimum_priority_kwh", "low_soc_priority_kwh"):
            kw = getattr(self, field)
            if type(kw) not in (int, float) or not isfinite(kw) or kw < 0:
                raise ValueError("minimum/low-SoC priority requires finite energy")
            if self.remaining_grid_kwh is not None and kw > self.remaining_grid_kwh + 1e-9:
                raise ValueError("priority energy exceeds actual demand")
        for field in ("maximum_price_per_kwh", "low_price_trigger_per_kwh"):
            value = getattr(self, field)
            if value is not None and (
                    type(value) not in (int, float) or not isfinite(value)):
                raise ValueError("price policy requires finite numeric value")
        if any(getattr(self, name) is not None for name in (
                "maximum_price_per_kwh", "low_price_trigger_per_kwh")):
            if (not isinstance(self.price_currency, str)
                    or len(self.price_currency) != 3
                    or not self.price_currency.isascii()
                    or not self.price_currency.isupper()
                    or not self.price_currency.isalpha()):
                raise ValueError("explicit price-policy currency required")
        elif self.price_currency is not None and (
                not isinstance(self.price_currency, str)
                or len(self.price_currency) != 3
                or not self.price_currency.isascii()
                or not self.price_currency.isupper()
                or not self.price_currency.isalpha()):
            raise ValueError("invalid selected source currency")
        if self.opportunistic_kind not in ("off", "type1", "type2"):
            raise ValueError("unsupported opportunistic price policy")
        if (self.opportunistic_kind != "off"
                and self.maximum_price_per_kwh is None):
            raise ValueError("opportunistic mode requires a verified price cap")
        if self.opportunistic_level_pct is not None and (
                type(self.opportunistic_level_pct) not in (int, float)
                or not isfinite(self.opportunistic_level_pct)
                or not 0 <= self.opportunistic_level_pct <= 100):
            raise ValueError("opportunistic level outside 0..100")
        if self.remaining_grid_kwh is not None and (
            not isfinite(self.remaining_grid_kwh) or self.remaining_grid_kwh < 0
        ):
            raise ValueError("remaining demand must be nonnegative or unknown")
        if self.ready_by is not None:
            _time(self.ready_by)
        if self.not_before is not None:
            _time(self.not_before)
        if isinstance(self.priority, bool) or not isinstance(self.priority, int) or not 0 <= self.priority <= 100:
            raise ValueError("priority must be a verified integer 0..100")
        if self.max_power_kw is not None and (
            not isfinite(self.max_power_kw) or self.max_power_kw <= 0
        ):
            raise ValueError("asset charging power cap must be positive and finite")
        if self.budget_remaining_minutes is not None:
            if (type(self.budget_remaining_minutes) not in (float, int)
                    or not isfinite(self.budget_remaining_minutes)
                    or not 0 <= self.budget_remaining_minutes <= 24 * 60
                    or self.remaining_budget_amount is None):
                raise ValueError("budget time limit is independent safety field")
        if self.remaining_budget_amount is not None:
            if (type(self.remaining_budget_amount) not in (int, float)
                    or not isfinite(self.remaining_budget_amount)
                    or self.remaining_budget_amount < 0):
                raise ValueError("budget must be a finite nonnegative amount")
            if (not isinstance(self.budget_currency, str)
                    or len(self.budget_currency) != 3
                    or not self.budget_currency.isascii()
                    or not self.budget_currency.isalpha()
                    or not self.budget_currency.isupper()):
                raise ValueError("budget currency required")
            if self.remaining_grid_kwh is not None or self.remaining_duration_minutes is not None:
                raise ValueError("choose energy, duration or currency budget")
        elif self.budget_currency is not None:
            raise ValueError("budget currency without amount")
        if self.remaining_duration_minutes is not None:
            if (type(self.remaining_duration_minutes) not in (int, float)
                    or not isfinite(self.remaining_duration_minutes)
                    or self.remaining_duration_minutes <= 0):
                raise ValueError("duration must be positive finite minutes")
            if self.remaining_grid_kwh is not None:
                raise ValueError("choose energy or duration, not both")


@dataclass(frozen=True)
class PlannedChargeSlot:
    charger_uid: str
    asset_uid: str | None
    start: datetime
    end: datetime
    power_kw: float
    current_a: float | None = None

    def __post_init__(self) -> None:
        if not self.charger_uid.strip():
            raise ValueError("charger identity required")
        _interval(self.start, self.end)
        if not isfinite(self.power_kw) or self.power_kw < 0:
            raise ValueError("planned power must be nonnegative")
        if self.current_a is not None and (
            not isfinite(self.current_a) or self.current_a <= 0
        ):
            raise ValueError("planned current must be positive and verified")


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

# Candidate canonical evidence. These are never duplicate source HA devices.
SourceQuality = Literal["ok", "degraded", "stale", "unknown", "unavailable", "invalid"]


@dataclass(frozen=True, kw_only=True)
class AssetObservation:
    """SoC with an explicit source, quality and observation instant."""

    asset_uid: str
    soc_pct: float | None
    observed_at: datetime | None
    quality: SourceQuality
    provenance: Literal["oem", "manual", "estimated", "unknown"] = "unknown"

    def __post_init__(self) -> None:
        if not self.asset_uid.strip():
            raise ValueError("asset identity required")
        if self.observed_at is not None:
            _time(self.observed_at)
        if self.soc_pct is not None and (
            not isfinite(self.soc_pct) or not 0 <= self.soc_pct <= 100
        ):
            raise ValueError("SoC must be within 0..100 or unknown")
        if self.quality == "ok" and (
            self.soc_pct is None or self.observed_at is None
            or self.provenance == "unknown"
        ):
            raise ValueError("available SoC requires measured value, time and provenance")


@dataclass(frozen=True, kw_only=True)
class ChargerObservation:
    """Physical readback: a successful HA call does not establish charging."""

    charger_uid: str
    observed_at: datetime | None
    quality: SourceQuality
    connected: Literal["yes", "no", "unknown"] = "unknown"
    charging: Literal["yes", "no", "unknown"] = "unknown"
    actual_power_kw: float | None = None
    session_energy_kwh: float | None = None

    def __post_init__(self) -> None:
        if not self.charger_uid.strip():
            raise ValueError("charger identity required")
        if self.observed_at is not None:
            _time(self.observed_at)
        for name, value in (
            ("actual power", self.actual_power_kw),
            ("session energy", self.session_energy_kwh),
        ):
            if value is not None and (not isfinite(value) or value < 0):
                raise ValueError(f"{name} must be nonnegative finite or unknown")
        if self.quality == "ok" and self.observed_at is None:
            raise ValueError("qualified physical readback needs observation time")
        if self.quality != "ok" and self.charging == "yes":
            raise ValueError("unqualified source cannot prove charging")


@dataclass(frozen=True, kw_only=True)
class CommandOutcome:
    """Distinct requested/accepted/confirmed command outcomes by request ID."""

    charger_uid: str
    request_id: str
    status: Literal[
        "requested", "accepted_unconfirmed", "confirmed", "rejected",
        "execution_unknown",
    ]
    readback_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.charger_uid.strip() or not self.request_id.strip():
            raise ValueError("command and charger identity required")
        if self.readback_at is not None:
            _time(self.readback_at)
        if self.status == "confirmed" and self.readback_at is None:
            raise ValueError("confirmed requires independent physical readback")
        if self.status != "confirmed" and self.readback_at is not None:
            raise ValueError("nonconfirmed outcome may not claim physical readback")
