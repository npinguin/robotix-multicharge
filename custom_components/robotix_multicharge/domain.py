"""Three charge-domain concepts; no Home Assistant runtime imports."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


def _positive(value: float | None, name: str) -> None:
    if value is not None and (not isfinite(value) or value <= 0):
        raise ValueError(f"{name} must be positive and finite")


@dataclass(frozen=True, kw_only=True)
class ChargeableAsset:
    """An object needing charge. Type is descriptive, not a planner switch."""

    uid: str
    name: str
    kind: str = "car"
    usable_capacity_kwh: float | None = None
    target_soc_pct: float | None = None
    max_charge_kw: float | None = None

    def __post_init__(self) -> None:
        if not self.uid.strip() or not self.name.strip() or not self.kind.strip():
            raise ValueError("asset identity and kind are required")
        _positive(self.usable_capacity_kwh, "usable_capacity_kwh")
        _positive(self.max_charge_kw, "max_charge_kw")
        if self.target_soc_pct is not None and (
            not isfinite(self.target_soc_pct) or not 0 <= self.target_soc_pct <= 100
        ):
            raise ValueError("target_soc_pct must be within 0..100")


@dataclass(frozen=True, kw_only=True)
class Charger:
    """A single physically verified charge point belonging to a Controller."""

    uid: str
    name: str
    controller_uid: str
    control_kind: str  # on_off | variable_current
    rated_power_kw: float
    phase_count: int | None = None
    min_current_a: float | None = None
    max_current_a: float | None = None

    def __post_init__(self) -> None:
        if not all(v.strip() for v in (self.uid, self.name, self.controller_uid)):
            raise ValueError("charger identity and controller are required")
        if self.control_kind not in ("on_off", "variable_current"):
            raise ValueError("unsupported charger control_kind")
        _positive(self.rated_power_kw, "rated_power_kw")
        if self.phase_count is not None and self.phase_count not in (1, 2, 3):
            raise ValueError("phase_count must be 1, 2 or 3")
        for name in ("min_current_a", "max_current_a"):
            _positive(getattr(self, name), name)
        if self.control_kind == "on_off" and (
            self.min_current_a is not None or self.max_current_a is not None
        ):
            raise ValueError("on_off cannot claim variable-current capability")
        if self.control_kind == "variable_current" and (
            self.min_current_a is None
            or self.max_current_a is None
            or self.min_current_a > self.max_current_a
        ):
            raise ValueError("variable current requires verified min/max")


@dataclass(frozen=True, kw_only=True)
class ChargeController:
    """One coordinated planner, not a whole-house EMS."""

    uid: str
    name: str
    max_parallel: int = 1
    max_group_power_kw: float | None = None

    def __post_init__(self) -> None:
        if not self.uid.strip() or not self.name.strip():
            raise ValueError("controller identity is required")
        if self.max_parallel < 1:
            raise ValueError("max_parallel must be >= 1")
        _positive(self.max_group_power_kw, "max_group_power_kw")
