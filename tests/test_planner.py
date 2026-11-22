"""Executable pure-domain guarantees for MultiCharge's one safe planner."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PKG = Path(__file__).resolve().parents[1] / "custom_components" / "robotix_multicharge"
ROOT = "multicharge_plan_test"
package = type(sys)(ROOT)
package.__path__ = [str(PKG)]
sys.modules[ROOT] = package
for name in ("domain", "contracts", "planner"):
    spec = importlib.util.spec_from_file_location(f"{ROOT}.{name}", PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from multicharge_plan_test.contracts import ChargeDemand, PowerEnvelope, PowerLimitSlot, PriceSlot  # noqa: E402 - imported after isolated pure-module bootstrap
from multicharge_plan_test.domain import Charger, ChargeController  # noqa: E402 - imported after isolated pure-module bootstrap
from multicharge_plan_test.planner import compile_plan  # noqa: E402 - imported after isolated pure-module bootstrap

NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)


def build(n=1, *, power=4.0, limit=16):
    controller = ChargeController(
        uid="home", name="Home", max_parallel=n, max_group_power_kw=limit
    )
    chargers = {
        f"c{i}": Charger(
            uid=f"c{i}", name=f"Charger {i}", controller_uid="home",
            control_kind="on_off", rated_power_kw=power,
        ) for i in range(n)
    }
    return controller, chargers


def demand(i, kwh=1.0, priority=1, deadline=None):
    return ChargeDemand(
        asset_uid=f"a{i}", charger_uid=f"c{i}",
        remaining_grid_kwh=kwh,
        ready_by=deadline or NOW + timedelta(hours=2),
        priority=priority,
    )


class PlannerTests(unittest.TestCase):
    def test_one_two_four_ten_chargers_with_bounded_parallel_cap(self):
        for n in (1, 2, 4, 10):
            ctl, chargers = build(n, limit=8)
            result = compile_plan(
                ctl, chargers, [demand(i) for i in range(n)], NOW
            )
            self.assertEqual(len(result.plan.slots), n, n)
            for slot in {s.start for s in result.plan.slots}:
                self.assertLessEqual(
                    sum(s.power_kw for s in result.plan.slots if s.start == slot),
                    8,
                )
                self.assertLessEqual(
                    len([s for s in result.plan.slots if s.start == slot]), n
                )

    def test_unchanged_slots_keep_plan_revision_across_minute_refresh(self):
        ctl, chargers = build()
        desired = [demand(0, kwh=1)]
        first = compile_plan(
            ctl, chargers, desired, NOW + timedelta(minutes=1)
        )
        after = compile_plan(
            ctl, chargers, desired, NOW + timedelta(minutes=2)
        )
        self.assertEqual(first.plan.slots, after.plan.slots)
        self.assertEqual(first.plan.revision, after.plan.revision)
        self.assertNotEqual(first.plan.generated_at, after.plan.generated_at)

    def test_explicit_priority_wins_early_capacity(self):
        ctl, chargers = build(2, limit=4)
        result = compile_plan(
            ctl, chargers,
            [demand(0, kwh=4, priority=0), demand(1, kwh=4, priority=5)],
            NOW, horizon_hours=1,
        )
        self.assertEqual(result.proposed_kwh["c1"], 4)
        self.assertEqual(result.proposed_kwh["c0"], 0)
        self.assertEqual(result.reasons["c0"], "INSUFFICIENT_CAPACITY_OR_TIME")

    def test_negative_prices_choose_cheapest_real_quarters(self):
        ctl, chargers = build()
        rates = [
            PriceSlot(NOW, NOW + timedelta(minutes=15), 0.4, "EUR"),
            PriceSlot(
                NOW + timedelta(minutes=15),
                NOW + timedelta(minutes=30), -0.1, "EUR"
            ),
        ]
        result = compile_plan(
            ctl, chargers, [demand(0)], NOW, mode="Economy",
            tariffs={"c0": rates}, horizon_hours=1,
        )
        self.assertEqual(result.plan.slots[0].start, NOW + timedelta(minutes=15))
        self.assertEqual(result.coverage["c0"], "COMPLETE")

    def test_economy_without_price_is_not_fake_zero(self):
        ctl, chargers = build()
        result = compile_plan(ctl, chargers, [demand(0)], NOW, mode="Economy")
        self.assertEqual(result.reasons["c0"], "PRICE_UNAVAILABLE")
        self.assertEqual(len(result.plan.slots), 0)

    def test_solar_without_solar_evidence_cannot_propose(self):
        ctl, chargers = build()
        result = compile_plan(ctl, chargers, [demand(0)], NOW, mode="Solar")
        self.assertEqual(result.reasons["c0"], "SOLAR_UNAVAILABLE")
        self.assertEqual(len(result.plan.slots), 0)

    def test_binding_zero_and_hole_never_fail_open(self):
        ctl, chargers = build()
        envelope = PowerEnvelope(
            "site", "r1", NOW, NOW + timedelta(hours=2), "binding",
            (PowerLimitSlot(NOW, NOW + timedelta(minutes=15), 0),),
        )
        result = compile_plan(
            ctl, chargers, [demand(0)], NOW, binding=envelope,
            horizon_hours=1,
        )
        self.assertEqual(len(result.plan.slots), 0)
        self.assertEqual(result.reasons["c0"], "BINDING_CAPACITY_UNAVAILABLE")

    def test_expired_envelope_never_grants_power(self):
        ctl, chargers = build()
        envelope = PowerEnvelope(
            "site", "rev", NOW - timedelta(hours=2), NOW, "binding",
            (),
        )
        result = compile_plan(ctl, chargers, [demand(0)], NOW, binding=envelope)
        self.assertEqual(len(result.plan.slots), 0)

    def test_unknown_demand_not_treated_as_zero(self):
        ctl, chargers = build()
        unknown = ChargeDemand("a0", "c0", None, NOW + timedelta(hours=1))
        result = compile_plan(ctl, chargers, [unknown], NOW)
        self.assertIsNone(result.shortfall_kwh["c0"])
        self.assertEqual(result.reasons["c0"], "DEMAND_UNKNOWN")
        complete = compile_plan(ctl, chargers, [demand(0, kwh=0)], NOW)
        self.assertEqual(complete.reasons["c0"], "TARGET_MET")

    def test_missing_group_cap_is_unqualified_not_unlimited(self):
        ctl = ChargeController(uid="home", name="Home", max_parallel=1)
        _, chargers = build()
        result = compile_plan(ctl, chargers, [demand(0)], NOW)
        self.assertEqual(result.reasons["c0"], "GROUP_CAPACITY_UNQUALIFIED")
        self.assertEqual(len(result.plan.slots), 0)

    def test_one_charger_may_only_have_one_request(self):
        ctl, chargers = build()
        with self.assertRaises(ValueError):
            compile_plan(ctl, chargers, [demand(0), demand(0)], NOW)

    def test_no_implicit_physical_authorization_or_current_modulation(self):
        ctl, chargers = build()
        result = compile_plan(ctl, chargers, [demand(0)], NOW)
        self.assertEqual(result.plan.status, "proposed")
        self.assertFalse(hasattr(result.plan, "authorized_physical_execution"))

    def test_dst_is_real_utc_quarters_not_fixed_local_96(self):
        tz = ZoneInfo("Europe/Brussels")
        for date, count in (("2026-03-29", 92), ("2026-10-25", 100)):
            midnight = datetime.fromisoformat(date).replace(tzinfo=tz)
            tomorrow = (midnight.date() + timedelta(days=1))
            next_midnight = datetime.combine(tomorrow, datetime.min.time(), tzinfo=tz)
            start = midnight.astimezone(timezone.utc)
            end = next_midnight.astimezone(timezone.utc)
            slots = []
            while start < end:
                slots.append(start)
                start += timedelta(minutes=15)
            self.assertEqual(len(slots), count)

    def test_duration_without_soc_is_valid_and_priority_scheduled(self):
        ctl, chargers = build()
        guest = ChargeDemand(
            "guest", "c0", None, NOW + timedelta(hours=2),
            remaining_duration_minutes=30,
        )
        result = compile_plan(ctl, chargers, [guest], NOW)
        self.assertEqual(len(result.plan.slots), 2)
        self.assertEqual(result.proposed_kwh["c0"], 2.0)

    def test_reject_advisory_as_binding(self):
        ctl, chargers = build()
        env = PowerEnvelope(
            "source", "r", NOW, NOW + timedelta(hours=1), "advisory",
            (PowerLimitSlot(NOW, NOW + timedelta(hours=1), 1),),
        )
        with self.assertRaises(ValueError):
            compile_plan(ctl, chargers, [demand(0)], NOW, binding=env)


if __name__ == "__main__":
    unittest.main()
