"""Three charge-domain concepts; no Home Assistant runtime imports."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, isfinite
from typing import Mapping

from .const import MIN_AC_CURRENT_A


def _positive(value: float | None, name: str) -> None:
    if value is not None and (not isfinite(value) or value <= 0):
        raise ValueError(f"{name} must be positive and finite")


def operating_current_grid(minimum, maximum, step, phases, voltage, rating,
                           min_power=None, max_power=None, circuit_limit=None):
    """Qualified positive Amp grid inside static kW/circuit limits.

    Return (first A, last A, step A, kW/A), or None. Native grid origin
    is retained; dynamic site/peer/asset capacity is evaluated separately.
    """
    if (phases not in (1, 2, 3) or not all(
            type(v) in (int, float) and isfinite(v) and v > 0
            for v in (minimum, maximum, step, voltage, rating))
            or not 200 <= voltage <= 260 or maximum < minimum):
        return None
    factor = voltage * phases / 1000
    lower = max(MIN_AC_CURRENT_A, minimum, (min_power or 0) / factor)
    upper = min(maximum, rating / factor,
                max_power / factor if max_power is not None else maximum,
                circuit_limit if circuit_limit is not None else maximum)
    first = max(0, ceil((lower - minimum) / step - 1e-9))
    last = floor((upper - minimum) / step + 1e-9)
    if last < first:
        return None
    return (round(minimum + first * step, 9),
            round(minimum + last * step, 9), step, factor)


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
    phase_ids: tuple[str, ...] = ()
    voltage_v: float | None = None
    current_step_a: float | None = None
    min_charging_power_kw: float | None = None
    max_charging_power_kw: float | None = None
    fixed_current_a: float | None = None
    circuit_id: str | None = None
    circuit_limit_a: float | None = None

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
            self.min_current_a is not None and self.max_current_a is not None
            and self.min_current_a > self.max_current_a
        ):
            raise ValueError("variable current: min_current_a must be <= max_current_a")
        # Individual configured overrides are optional. The effective native
        # capability projection must complete the envelope before execution.
        if self.phase_ids and (
            len(self.phase_ids) != len(set(self.phase_ids))
            or any(x not in ("L1", "L2", "L3") for x in self.phase_ids)
            or self.phase_count != len(self.phase_ids)
        ):
            raise ValueError("charger phase identifiers must match phase count")
        for field in ("voltage_v", "current_step_a", "fixed_current_a", "circuit_limit_a"):
            _positive(getattr(self, field), field)
        if self.circuit_limit_a is not None and not self.circuit_id:
            raise ValueError("circuit limit requires an identified circuit")
        for field in ("min_charging_power_kw", "max_charging_power_kw"):
            _positive(getattr(self, field), field)
        if (self.min_charging_power_kw is not None
                or self.max_charging_power_kw is not None):
            if self.control_kind != "variable_current":
                raise ValueError("fixed on/off charger cannot modulate kW")
            if (self.min_charging_power_kw is not None
                    and self.max_charging_power_kw is not None
                    and self.min_charging_power_kw > self.max_charging_power_kw):
                raise ValueError("charger user minimum exceeds maximum")
        if self.fixed_current_a is not None and self.control_kind != "on_off":
            raise ValueError("fixed current only valid for on/off")
        if self.current_step_a is not None and self.control_kind != "variable_current":
            raise ValueError("setpoint step only valid for adjustable charger")


    def operating_grid(self):
        """The same static executable envelope used by native controls."""
        if self.control_kind != "variable_current":
            return None
        return operating_current_grid(
            self.min_current_a, self.max_current_a, self.current_step_a,
            self.phase_count, self.voltage_v, self.rated_power_kw,
            self.min_charging_power_kw, self.max_charging_power_kw,
            self.circuit_limit_a,
        )


@dataclass(frozen=True, kw_only=True)
class ChargeController:
    """One coordinated planner, not a whole-house EMS."""

    uid: str
    name: str
    max_parallel: int = 1
    max_group_power_kw: float | None = None
    phase_limits_a: Mapping[str, float] | None = None

    def __post_init__(self) -> None:
        if not self.uid.strip() or not self.name.strip():
            raise ValueError("controller identity is required")
        if self.max_parallel < 1:
            raise ValueError("max_parallel must be >= 1")
        _positive(self.max_group_power_kw, "max_group_power_kw")
        if self.phase_limits_a is not None:
            if not self.phase_limits_a or any(
                key not in ("L1", "L2", "L3") for key in self.phase_limits_a
            ):
                raise ValueError("phase limit keys must be L1/L2/L3")
            for current in self.phase_limits_a.values():
                _positive(current, "phase current limit")
