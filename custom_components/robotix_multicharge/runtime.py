"""One source-neutral, read-only Home Assistant charging planning runtime.

The engine makes no HA service calls and has no EVSE write ownership. Future
physical command authorization and independent readback are separate gates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from .contracts import ChargeDemand
from .domain import ChargeController, Charger
from .planner import compile_plan
from .source_evidence import connection, intervals, number

_LOGGER = logging.getLogger(__name__)


class MultiChargeRuntime:
    def __init__(self, hass, configuration):
        self.hass = hass
        self.configuration = configuration
        self.assessment = None
        self.observations = {"chargers": {}, "assets": {}, "sources": {}}
        self.excluded = {}
        self._listeners = set()
        self._unsubscribe_tick = None

    def set_unsubscribe(self, unsubscribe):
        self._unsubscribe_tick = unsubscribe

    def subscribe(self, callback):
        self._listeners.add(callback)
        return lambda: self._listeners.discard(callback)

    def stop(self):
        if self._unsubscribe_tick is not None:
            self._unsubscribe_tick()
            self._unsubscribe_tick = None
        self._listeners.clear()

    def refresh(self, at=None):
        at = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        cfg = self.configuration
        setting = cfg["controller"]
        controller = ChargeController(
            uid=setting["id"], name=setting["name"],
            max_parallel=setting["max_parallel"],
            max_group_power_kw=setting.get("max_power_kw"),
        )
        assets = {a["id"]: a for a in cfg["assets"]}
        chargers = {}
        demands = []
        self.observations = {"chargers": {}, "assets": {}, "sources": {}}
        self.excluded = {}
        for raw in cfg["chargers"]:
            uid = raw["id"]
            chargers[uid] = Charger(
                uid=uid, name=raw["name"], controller_uid=controller.uid,
                control_kind=raw["kind"], rated_power_kw=raw["rated_power_kw"],
                phase_count=raw.get("phase_count"),
                min_current_a=raw.get("min_current_a"),
                max_current_a=raw.get("max_current_a"),
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
                reading = number(self.hass, asset.get("soc_entity"), "soc", at)
                self.observations["assets"][asset["id"]] = {"soc": reading}
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
            demands.append(ChargeDemand(
                asset_uid=asset["id"], charger_uid=uid,
                remaining_grid_kwh=amount, ready_by=deadline,
                priority=asset.get("priority", 0),
                remaining_duration_minutes=minutes,
            ))
        tariff, tariff_quality = intervals(
            self.hass, setting.get("price_entity"), "price", at
        )
        solar, solar_quality = intervals(
            self.hass, setting.get("solar_entity"), "solar", at
        )
        self.observations["sources"] = {
            "tariff_quality": tariff_quality, "solar_quality": solar_quality
        }
        try:
            self.assessment = compile_plan(
                controller, chargers, demands, at, mode=setting["mode"],
                tariffs={uid: tariff for uid in chargers}, solar=solar,
            )
        except (ValueError, TypeError, OverflowError) as exc:
            _LOGGER.warning("MultiCharge proposal unavailable: %s", exc)
            self.assessment = None
            self.excluded["controller"] = "INVALID_PLANNING_INPUT"
        for listener in tuple(self._listeners):
            listener()

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
            "read_only": True,
            "physical_actuation_authorized": False,
        }
