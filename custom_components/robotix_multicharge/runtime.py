"""Source-neutral HA planning runtime and the guarded one-writer command owner.

Planning never authorizes a physical command. Explicit manual on/off requests
use the native executor, with distinct source observations and command outcomes.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .contracts import ChargeDemand, PowerEnvelope
from .configuration import configuration_revision
from .domain import ChargeController, Charger
from .planner import compile_plan, resolve_recurring_ready_by
from .source_evidence import binding, connection, intervals, number
from .execution import NativeSwitchExecutor

_LOGGER = logging.getLogger(__name__)


def _evidence(value):
    """Public JSON-shaped observation, never an implicit successful reading."""
    if value is None:
        return {"value": None, "quality": "unknown", "reason": "NOT_OBSERVED",
                "observed_at": None}
    return {"value": value.value, "quality": value.quality,
            "reason": value.reason,
            "observed_at": value.observed_at.isoformat() if value.observed_at else None}


class MultiChargeRuntime:
    def __init__(self, hass, configuration):
        self.hass = hass
        self.configuration = configuration
        self.assessment = None
        self.observations = {"chargers": {}, "assets": {}, "sources": {}}
        self.excluded = {}
        self.price_slots = ()
        self.executor = NativeSwitchExecutor(self)
        self._control_store = None
        self._save_lock = asyncio.Lock()
        self._listeners = set()
        self._unsubscribers = []
        self.active = True

    def attach_control_store(self, store, snapshot):
        self._control_store = store
        self.executor.restore_state(snapshot)

    async def persist_control_state(self):
        if self._control_store is None:
            return True  # isolated developer tests, never a production HA fallback
        try:
            async with self._save_lock:
                await self._control_store.async_save(self.executor.export_state())
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
        for listener in tuple(self._listeners):
            listener()

    def stop(self):
        self.active = False
        self.executor.detach()
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        self._listeners.clear()

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
        self.observations = {"chargers": {}, "assets": {}, "sources": {}}
        self.excluded = {}
        # Observe every logical asset, including unassigned assets and explicit
        # kWh/duration intents. Do not reconstruct a second OEM/vehicle truth.
        for asset in cfg["assets"]:
            self.observations["assets"][asset["id"]] = {
                "soc": number(self.hass, asset.get("soc_entity"), "soc", at)
            }
        for raw in cfg["chargers"]:
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
                fixed_current_a=raw.get("fixed_current_a"),
                circuit_id=raw.get("circuit_id"),
                circuit_limit_a=raw.get("circuit_limit_a"),
            )
            cable = connection(self.hass, raw.get("connected_entity"), at)
            power = number(self.hass, raw.get("power_entity"), "power", at)
            self.observations["chargers"][uid] = {
                "connected": cable, "power_kw": power
            }
            if cable.value is not True or cable.quality != "ok":
                self.excluded[uid] = (
                    "DISCONNECTED" if cable.value is False else "CONNECTION_UNCONFIRMED"
                )
                continue
            asset = assets.get(raw.get("asset"))
            if asset is None:
                self.excluded[uid] = "NO_CHARGEABLE_ASSET"
                continue
            amount = asset.get("requested_kwh")
            minutes = asset.get("requested_duration_minutes")
            if amount is None and minutes is None:
                reading = self.observations["assets"][asset["id"]]["soc"]
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
            ready = asset.get("ready_by")
            deadline = datetime.fromisoformat(ready) if ready else None
            repeat = asset.get("ready_by_repeat", "none")
            if deadline is not None and repeat != "none":
                zone = getattr(getattr(self.hass, "config", None),
                               "time_zone", "UTC")
                deadline, reason = resolve_recurring_ready_by(
                    deadline, at, repeat, zone
                )
                if deadline is None:
                    self.excluded[uid] = reason
                    continue
            if (self.executor.intent_completed(asset, raw, deadline)
                    and (amount is not None or minutes is not None)):
                amount, minutes = 0.0, None
            demands.append(ChargeDemand(
                asset_uid=asset["id"], charger_uid=uid,
                remaining_grid_kwh=amount, ready_by=deadline,
                priority=asset.get("priority", 0),
                remaining_duration_minutes=minutes,
                max_power_kw=asset.get("max_charge_kw"),
            ))
        tariff, tariff_quality = intervals(
            self.hass, setting.get("price_entity"), "price", at
        )
        solar, solar_quality = intervals(
            self.hass, setting.get("solar_entity"), "solar", at
        )
        self.price_slots = tuple(tariff)
        current = [row for row in tariff if row.start <= at < row.end]
        current_price = (
            {"quality": "ok", "value": current[0].effective_price_per_kwh,
             "currency": current[0].currency}
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
        self.observations["sources"] = {
            "tariff_quality": tariff_quality, "solar_quality": solar_quality,
            "binding_quality": binding_quality,
            "current_price": current_price,
        }
        try:
            self.assessment = compile_plan(
                controller, chargers, demands, at, mode=setting["mode"],
                tariffs={uid: tariff for uid in chargers}, solar=solar,
                binding=external_binding,
            )
        except (ValueError, TypeError, OverflowError) as exc:
            _LOGGER.warning("MultiCharge proposal unavailable: %s", exc)
            self.assessment = None
            self.excluded["controller"] = "INVALID_PLANNING_INPUT"
        self.notify()

    def summary(self):
        assessment = self.assessment
        if assessment is None:
            return {"status": "unavailable", "reason": "INVALID_PLANNING_INPUT"}
        return {
            "status": assessment.plan.status,
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
                for x in self.executor.capabilities().values()
            ),
            "command_outcomes": self.executor.snapshot(),
            "active_sessions": self.executor.session_snapshot(),
            "completed_sessions": self.executor.completed_sessions(),
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
        if not first < last or last - first > timedelta(hours=48):
            raise ValueError("plan query must be a positive interval <=48h")
        if charger_id is not None and not any(
            c["id"] == charger_id for c in self.configuration["chargers"]
        ):
            raise ValueError("unknown charger")
        if asset_id is not None and not any(
            a["id"] == asset_id for a in self.configuration["assets"]
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
                    "proposed_power_kw": slot.power_kw,
                    "proposed_current_a": slot.current_a,
                    "proposed_energy_kwh": round(
                        slot.power_kw * (slot.end - slot.start).total_seconds() / 3600, 6
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
        slots.sort(key=lambda row: (row["start"], row["charger_id"]))
        history = [
            receipt for receipt in self.executor.completed_sessions()
            if datetime.fromisoformat(receipt["started_at"]) < last
            and datetime.fromisoformat(receipt["ended_at"]) >= first
            and (charger_id is None or receipt["charger_id"] == charger_id)
            and (asset_id is None or receipt["asset_id"] == asset_id)
        ]
        return {
            "schema_major": 1,
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
            "command_outcomes": self.executor.snapshot(),
            "command_capabilities": self.executor.capabilities(),
            "active_sessions": self.executor.session_snapshot(),
            "completed_sessions": history,
            "price_slots": [
                {"start": row.start.isoformat(), "end": row.end.isoformat(),
                 "price_per_kwh": row.effective_price_per_kwh,
                 "currency": row.currency}
                for row in self.price_slots
                if row.start < last and row.end > first
            ],
            "configuration": self.configuration,
            "observations": {
                "assets": {
                    uid: {"soc": _evidence(readings.get("soc"))}
                    for uid, readings in self.observations.get("assets", {}).items()
                },
                "chargers": {
                    uid: {
                        "connected": _evidence(readings.get("connected")),
                        "power_kw": _evidence(readings.get("power_kw")),
                    }
                    for uid, readings in self.observations.get("chargers", {}).items()
                },
                "sources": dict(self.observations.get("sources", {})),
            },
            "read_only": True,
            "physical_actuation_authorized": any(
                x["start_allowed"] or x["stop_allowed"]
                for x in self.executor.capabilities().values()
            ),
        }
