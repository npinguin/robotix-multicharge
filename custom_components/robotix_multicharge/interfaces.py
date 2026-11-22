"""Minimal provider and actuator interfaces; no concrete source dependencies."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .contracts import ChargePlan, PowerEnvelope, PriceSlot


class PriceProvider(Protocol):
    async def prices(self, start: datetime, end: datetime) -> tuple[PriceSlot, ...]: ...


class AssetProvider(Protocol):
    async def state_of_charge(self, asset_uid: str) -> tuple[float | None, datetime | None]: ...


class ChargerProvider(Protocol):
    async def observed_power_kw(self, charger_uid: str) -> tuple[float | None, datetime | None]: ...


class PowerProvider(Protocol):
    async def allocation(self, start: datetime, end: datetime) -> PowerEnvelope | None: ...


class ChargeActuator(Protocol):
    async def request_charge_power(self, charger_uid: str, power_kw: float) -> str:
        """Return request ID, never physical readback."""
        ...


class PlanConsumer(Protocol):
    async def proposed_plan(self, plan: ChargePlan) -> None:
        """Read-only plan consumer; cannot become a second charger writer."""
        ...
