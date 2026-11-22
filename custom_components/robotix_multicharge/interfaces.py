"""Minimal provider and actuator interfaces; no concrete source dependencies."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .contracts import (
    AssetObservation, ChargePlan, ChargerObservation, CommandOutcome,
    PowerEnvelope, PriceSlot,
)


class PriceProvider(Protocol):
    async def prices(self, start: datetime, end: datetime) -> tuple[PriceSlot, ...]: ...


class AssetProvider(Protocol):
    async def state_of_charge(self, asset_uid: str) -> AssetObservation: ...


class ChargerProvider(Protocol):
    async def observation(self, charger_uid: str) -> ChargerObservation: ...


class PowerProvider(Protocol):
    async def allocation(self, start: datetime, end: datetime) -> PowerEnvelope | None: ...


class ChargeActuator(Protocol):
    async def request_charge_power(self, charger_uid: str, power_kw: float) -> CommandOutcome:
        """Only the explicit physical owner may execute; no optimistic success."""
        ...


class PlanConsumer(Protocol):
    async def proposed_plan(self, plan: ChargePlan) -> None:
        """Read-only plan consumer; cannot become a second charger writer."""
        ...
