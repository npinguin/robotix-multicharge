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
from multicharge_plan_test.planner import (  # noqa: E402 - imported after isolated pure-module bootstrap
    compile_plan, minimum_planning_power, resolve_recurring_ready_by, charging_window_allows,
)

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
    def test_sustained_session_draw_limits_expected_energy_not_electrical_reservation(self):
        ctl, chargers = build(power=3.6, limit=3.6)
        chargers["c0"] = Charger(uid="c0", name="Drive", controller_uid="home",
                                 control_kind="variable_current", rated_power_kw=3.6,
                                 min_current_a=6, max_current_a=16, phase_count=1,
                                 voltage_v=230, current_step_a=1)
        # An hour at 3.45 kW would nominally deliver 3.45 kWh;
        # observed 1.48 kW must not be treated as 3.45 kW.
        result = compile_plan(ctl, chargers, [ChargeDemand(
            asset_uid="car", charger_uid="c0", remaining_grid_kwh=3,
            ready_by=NOW+timedelta(hours=1), observed_session_draw_kw=1.48,
        )], NOW, mode="Ready By")
        self.assertEqual(result.coverage["c0"], "INCOMPLETE")
        self.assertAlmostEqual(result.proposed_kwh["c0"], 1.48)
        self.assertAlmostEqual(result.shortfall_kwh["c0"], 1.52)
        self.assertTrue(all(slot.expected_power_kw <= 1.48 and slot.power_kw <= 3.6
                            for slot in result.plan.slots))
        self.assertTrue(any(slot.power_kw > slot.expected_power_kw for slot in result.plan.slots))

    def test_curtailed_draw_does_not_cap_higher_verified_setpoints(self):
        ctl, chargers = build(power=3.6, limit=3.6)
        chargers["c0"] = Charger(uid="c0", name="Drive", controller_uid="home",
                                 control_kind="variable_current", rated_power_kw=3.6,
                                 min_current_a=6, max_current_a=16, phase_count=1,
                                 voltage_v=230, current_step_a=1)
        result = compile_plan(ctl, chargers, [ChargeDemand(
            asset_uid="car", charger_uid="c0", remaining_grid_kwh=3,
            ready_by=NOW+timedelta(hours=1), observed_session_draw_kw=1.1,
            observed_draw_setpoint_kw=1.38,
        )], NOW, mode="Ready By")
        self.assertTrue(any(slot.power_kw > 1.38 for slot in result.plan.slots))
        for slot in result.plan.slots:
            if slot.power_kw > 1.38:
                self.assertAlmostEqual(slot.expected_power_kw, slot.power_kw)
            else:
                self.assertLessEqual(slot.expected_power_kw, 1.1)

    def test_indicative_slots_use_residual_capacity_without_changing_firm_slots(self):
        controller, chargers = build(n=2, power=4.0, limit=4.0)
        at = NOW
        live = compile_plan(controller, chargers, [
            ChargeDemand(asset_uid="car0", charger_uid="c0",
                         remaining_grid_kwh=2.0, ready_by=at + timedelta(hours=2)),
        ], at, mode="Ready By")
        assert live.plan.slots
        preview = compile_plan(controller, chargers, [
            ChargeDemand(asset_uid="car1", charger_uid="c1",
                         remaining_grid_kwh=2.0, ready_by=at + timedelta(hours=3),
                         not_before=at + timedelta(hours=1)),
        ], at, mode="Ready By", reserved_slots=live.plan.slots)
        self.assertEqual(tuple(live.plan.slots),
                         tuple(compile_plan(controller, chargers, [
                             ChargeDemand(asset_uid="car0", charger_uid="c0",
                                          remaining_grid_kwh=2.0,
                                          ready_by=at + timedelta(hours=2)),
                         ], at, mode="Ready By").plan.slots))
        self.assertTrue(preview.plan.slots)
        firm_kw = {s.start: s.power_kw for s in live.plan.slots}
        for slot in preview.plan.slots:
            self.assertGreaterEqual(slot.start, at + timedelta(hours=1))
            self.assertLessEqual(slot.power_kw + firm_kw.get(slot.start, 0), 4.0000001)
        self.assertFalse(set((s.charger_uid, s.start) for s in live.plan.slots) &
                         set((s.charger_uid, s.start) for s in preview.plan.slots))

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

    def test_equal_priority_constrained_arrival_does_not_lose_only_slot(self):
        ctl, chargers = build(2, limit=4)
        due = NOW + timedelta(minutes=30)
        first = demand(0, deadline=due)
        second = ChargeDemand(asset_uid="a1", charger_uid="c1",
                              remaining_grid_kwh=1, ready_by=due, priority=1,
                              not_before=NOW+timedelta(minutes=15))
        prices = [
            PriceSlot(NOW, NOW+timedelta(minutes=15), 0.40, "EUR"),
            PriceSlot(NOW+timedelta(minutes=15), due, 0.10, "EUR"),
        ]
        result = compile_plan(ctl, chargers, [first, second], NOW,
                              mode="Economy", tariffs={"c0": prices, "c1": prices})
        self.assertEqual(result.coverage, {"c0": "COMPLETE", "c1": "COMPLETE"})
        self.assertEqual([(slot.charger_uid, slot.start) for slot in result.plan.slots],
                         [("c0", NOW), ("c1", NOW+timedelta(minutes=15))])

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

    def test_force_charge_accepts_explicit_demand_without_deadline(self):
        ctl, chargers = build()
        request = ChargeDemand("guest", "c0", 1.0, None)
        result = compile_plan(ctl, chargers, [request], NOW, mode="Force Charge")
        self.assertEqual(result.plan.status, "proposed")
        self.assertEqual(len(result.plan.slots), 1)
        self.assertEqual(result.strategy["c0"], "Force Charge")
        self.assertEqual(result.plan.slots[0].start, NOW)

    def test_off_without_deadline_is_a_safe_empty_proposal(self):
        ctl, chargers = build()
        request = ChargeDemand("guest", "c0", None, None)
        result = compile_plan(ctl, chargers, [request], NOW, mode="Off")
        self.assertEqual(result.plan.slots, ())
        self.assertEqual(result.reasons["c0"], "OFF")
        self.assertEqual(result.plan.status, "proposed")

    def test_automatic_uses_qualified_solar_before_positive_tariff(self):
        ctl, chargers = build()
        request = [demand(0, kwh=1)]
        tariff = [PriceSlot(NOW, NOW + timedelta(minutes=30), 0.3, "EUR")]
        solar = [
            PowerLimitSlot(
                NOW + timedelta(minutes=15), NOW + timedelta(minutes=30), 4
            )
        ]
        result = compile_plan(
            ctl, chargers, request, NOW, mode="Automatic",
            tariffs={"c0": tariff}, solar=solar,
        )
        self.assertEqual(result.plan.slots[0].start, NOW + timedelta(minutes=15))
        self.assertEqual(result.strategy["c0"], "solar")

    def test_automatic_explains_missing_price_and_solar_fallback(self):
        ctl, chargers = build()
        result = compile_plan(
            ctl, chargers, [demand(0)], NOW, mode="Automatic"
        )
        self.assertEqual(result.reasons["c0"], "PROPOSED")
        self.assertEqual(result.strategy["c0"], "ready_by_fallback")

    def test_automatic_prioritizes_real_negative_prices(self):
        ctl, chargers = build()
        tariffs = [
            PriceSlot(NOW, NOW + timedelta(minutes=15), -0.12, "EUR"),
            PriceSlot(NOW + timedelta(minutes=15),
                      NOW + timedelta(minutes=30), 0.11, "EUR"),
        ]
        solar = [
            PowerLimitSlot(NOW + timedelta(minutes=15),
                           NOW + timedelta(minutes=30), 4)
        ]
        result = compile_plan(
            ctl, chargers, [demand(0)], NOW, mode="Automatic",
            tariffs={"c0": tariffs}, solar=solar,
        )
        self.assertEqual(result.plan.slots[0].start, NOW)
        self.assertEqual(result.strategy["c0"], "negative_tariff")

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

    def test_unselected_group_cap_uses_declared_charger_capacity_and_parallelism(self):
        ctl = ChargeController(uid="home", name="Home", max_parallel=1)
        _, chargers = build(n=2)
        result = compile_plan(ctl, chargers, [demand(0), demand(1)], NOW)
        self.assertEqual(len(result.plan.slots), 2)
        self.assertEqual(len({row.start for row in result.plan.slots}), 2)
        self.assertTrue(all(row.power_kw == 4.0 for row in result.plan.slots))

    def test_asset_power_cap_blocks_unqualified_modulation(self):
        ctl, chargers = build(power=7.2, limit=11)
        request = ChargeDemand(
            "bike", "c0", 1.0, NOW + timedelta(hours=1),
            max_power_kw=2.0,
        )
        result = compile_plan(ctl, chargers, [request], NOW)
        self.assertEqual(result.plan.slots, ())
        self.assertEqual(
            result.reasons["c0"],
            "ASSET_POWER_LIMIT_REQUIRES_VERIFIED_MODULATION",
        )

    def test_prices_of_different_currencies_are_not_compared(self):
        ctl, chargers = build()
        prices = [
            PriceSlot(NOW, NOW + timedelta(minutes=15), -0.1, "EUR"),
            PriceSlot(NOW + timedelta(minutes=15),
                      NOW + timedelta(minutes=30), 0.1, "USD"),
        ]
        with self.assertRaisesRegex(ValueError, "mixed tariff currencies"):
            compile_plan(
                ctl, chargers, [demand(0)], NOW, mode="Economy",
                tariffs={"c0": prices},
            )

    def test_one_charger_may_only_have_one_request(self):
        ctl, chargers = build()
        with self.assertRaises(ValueError):
            compile_plan(ctl, chargers, [demand(0), demand(0)], NOW)

    def test_no_implicit_physical_authorization_or_current_modulation(self):
        ctl, chargers = build()
        result = compile_plan(ctl, chargers, [demand(0)], NOW)
        self.assertEqual(result.plan.status, "proposed")
        self.assertFalse(hasattr(result.plan, "authorized_physical_execution"))

    def test_recurring_ready_by_uses_site_wall_clock_across_spring_dst(self):
        zone = ZoneInfo("Europe/Brussels")
        anchor = datetime(2026, 3, 28, 8, tzinfo=zone)
        now = datetime(2026, 3, 29, 7, tzinfo=zone)
        deadline, reason = resolve_recurring_ready_by(
            anchor, now, "daily", "Europe/Brussels"
        )
        self.assertEqual(reason, "RECURRING")
        self.assertEqual(deadline.astimezone(timezone.utc).hour, 6)
        self.assertEqual(deadline.astimezone(zone).hour, 8)

    def test_recurring_ready_by_refuses_nonexistent_and_ambiguous_dst(self):
        zone = ZoneInfo("Europe/Brussels")
        for anchor, now in (
            (datetime(2026, 3, 28, 2, 30, tzinfo=zone),
             datetime(2026, 3, 29, 1, tzinfo=zone)),
            (datetime(2026, 10, 24, 2, 30, tzinfo=zone),
             datetime(2026, 10, 25, 1, tzinfo=zone)),
        ):
            deadline, reason = resolve_recurring_ready_by(
                anchor, now, "daily", "Europe/Brussels"
            )
            self.assertIsNone(deadline)
            self.assertEqual(reason, "DEADLINE_DST_UNRESOLVED")

    def test_weekly_ready_by_preserves_anchor_weekday(self):
        zone = ZoneInfo("Europe/Brussels")
        anchor = datetime(2026, 11, 23, 9, tzinfo=zone)
        now = datetime(2026, 11, 25, 12, tzinfo=zone)
        deadline, reason = resolve_recurring_ready_by(
            anchor, now, "weekly", "Europe/Brussels"
        )
        self.assertEqual(reason, "RECURRING")
        self.assertEqual(deadline.astimezone(zone).date().isoformat(), "2026-11-30")

    def test_zero_price_budget_also_has_cumulative_physical_time_ceiling(self):
        ctl, chargers = build()
        quotes = tuple(
            PriceSlot(
                NOW + i * timedelta(minutes=15),
                NOW + (i + 1) * timedelta(minutes=15),
                -0.08, "EUR", "effective",
            ) for i in range(192)
        )
        demand = ChargeDemand(
            "visitor", "c0", None, None,
            remaining_budget_amount=10.0, budget_currency="EUR",
            budget_remaining_minutes=30,
        )
        result = compile_plan(
            ctl, chargers, [demand], NOW, mode="Economy",
            tariffs={"c0": quotes},
        )
        self.assertEqual(len(result.plan.slots), 2)
        self.assertEqual(result.reasons["c0"], "BUDGET_DURATION_SAFETY_LIMIT")
        self.assertEqual(result.coverage["c0"], "INCOMPLETE")
        self.assertEqual(result.proposed_kwh["c0"], 2.0)
        full = compile_plan(
            ctl, chargers,
            [ChargeDemand("visitor", "c0", None, None,
                          remaining_budget_amount=10.0,
                          budget_currency="EUR")],
            NOW, mode="Economy", tariffs={"c0": quotes},
        )
        self.assertEqual(len(full.plan.slots), 96,
                         "Even free/negative quotes cannot reserve more than 24h")
        for minutes in (-1, 1441, float("nan")):
            with self.subTest(minutes=minutes), self.assertRaises(ValueError):
                ChargeDemand(
                    "visitor", "c0", None, None,
                    remaining_budget_amount=10.0, budget_currency="EUR",
                    budget_remaining_minutes=minutes,
                )

    def test_upstream_price_cap_minimum_soc_and_low_price_immediate(self):
        ctl, chargers = build()
        quotes = [0.30, 0.05, 0.10, 0.25, 0.03]
        tariffs = [
            PriceSlot(NOW + i * timedelta(minutes=15),
                      NOW + (i + 1) * timedelta(minutes=15), p, "EUR",
                      "spot")
            for i, p in enumerate(quotes)
        ]
        minimum = compile_plan(
            ctl, chargers,
            [ChargeDemand("car", "c0", 3.0, NOW + timedelta(hours=2),
                          minimum_priority_kwh=1.0,
                          maximum_price_per_kwh=0.20,
                          price_currency="EUR")],
            NOW, mode="Economy", tariffs={"c0": tariffs})
        self.assertEqual(
            [x.start for x in minimum.plan.slots],
            [NOW, NOW + timedelta(minutes=15),
             NOW + timedelta(hours=1)],
            "One earliest expensive SoC-minimum quarter followed by lowest "
            "available price-limited slots",
        )
        without_minimum = compile_plan(
            ctl, chargers,
            [ChargeDemand("car", "c0", 3.0, NOW + timedelta(hours=2),
                          maximum_price_per_kwh=0.20, price_currency="EUR")],
            NOW, mode="Economy", tariffs={"c0": tariffs})
        self.assertFalse(any(s.start == NOW for s in without_minimum.plan.slots))
        urgent_low_soc = compile_plan(
            ctl, chargers,
            [ChargeDemand("car", "c0", 1.0, NOW + timedelta(hours=2),
                          low_soc_priority_kwh=1.0)],
            NOW, mode="Economy", tariffs={"c0": tariffs})
        self.assertEqual(urgent_low_soc.plan.slots[0].start, NOW)
        low_price = compile_plan(
            ctl, chargers,
            [ChargeDemand("car", "c0", 1.0, NOW + timedelta(hours=2),
                          low_price_trigger_per_kwh=0.31,
                          price_currency="EUR")],
            NOW, mode="Economy", tariffs={"c0": tariffs})
        self.assertEqual(low_price.plan.slots[0].start, NOW,
                         "User explicitly allows immediate rate at/below threshold")
        no_source = compile_plan(
            ctl, chargers,
            [ChargeDemand("car", "c0", 1.0, NOW + timedelta(hours=2),
                          maximum_price_per_kwh=0.20, price_currency="EUR")],
            NOW, mode="Ready By")
        self.assertFalse(no_source.plan.slots)
        self.assertEqual(no_source.reasons["c0"], "PRICE_SOURCE_UNAVAILABLE")
        wrong_currency = compile_plan(
            ctl, chargers,
            [ChargeDemand("car", "c0", 1.0, NOW + timedelta(hours=2),
                          maximum_price_per_kwh=0.20, price_currency="USD")],
            NOW, mode="Economy", tariffs={"c0": tariffs})
        self.assertFalse(wrong_currency.plan.slots)

    def test_upstream_opportunistic_type1_and_type2_qualified(self):
        ctl, chargers = build()
        source = [0.15, 0.08, 0.02]
        tariffs = [
            PriceSlot(NOW + i * timedelta(minutes=15),
                      NOW + (i + 1) * timedelta(minutes=15), p, "EUR",
                      "spot")
            for i, p in enumerate(source)
        ]
        for kind, level, expected in (
            ("type1", 50, NOW + timedelta(minutes=30)),
            ("type2", 90, NOW),
        ):
            qualified = tariffs if kind == "type1" else [
                PriceSlot(row.start, row.end,
                          (0.015 if index == 0 else row.effective_price_per_kwh),
                          row.currency, row.basis)
                for index, row in enumerate(tariffs)
            ]
            result = compile_plan(
                ctl, chargers,
                [ChargeDemand("car", "c0", 1.0, NOW + timedelta(hours=1),
                              maximum_price_per_kwh=0.20,
                              price_currency="EUR",
                              opportunistic_kind=kind,
                              opportunistic_level_pct=level)],
                NOW, mode="Economy", tariffs={"c0": qualified})
            self.assertEqual([s.start for s in result.plan.slots], [expected])
        with self.assertRaises(ValueError):
            ChargeDemand("car", "c0", 1.0, None,
                         opportunistic_kind="type2")
        unavailable = compile_plan(
            ctl, chargers,
            [ChargeDemand("car", "c0", 1.0, NOW + timedelta(hours=1),
                          maximum_price_per_kwh=0.20,
                          price_currency="EUR",
                          opportunistic_kind="type2")],
            NOW, mode="Economy")
        self.assertEqual(unavailable.reasons["c0"], "PRICE_SOURCE_UNAVAILABLE")
        self.assertFalse(unavailable.plan.slots)

    def test_upstream_continuous_and_non_contiguous_cheapest_quarters(self):
        ctl, chargers = build()
        prices = [0.05, 0.90, 0.05, 0.90, 0.05, 0.05]
        tariff = [PriceSlot(NOW + i * timedelta(minutes=15),
                            NOW + (i + 1) * timedelta(minutes=15),
                            price, "EUR") for i, price in enumerate(prices)]
        flexible = compile_plan(
            ctl, chargers,
            [ChargeDemand("car", "c0", 2.0, NOW + timedelta(hours=2))],
            NOW, mode="Economy", tariffs={"c0": tariff})
        self.assertEqual(
            [x.start for x in flexible.plan.slots],
            [NOW, NOW + timedelta(minutes=30)],
        )
        contiguous = compile_plan(
            ctl, chargers,
            [ChargeDemand("car", "c0", 2.0, NOW + timedelta(hours=2),
                          continuous_charging=True)],
            NOW, mode="Economy", tariffs={"c0": tariff})
        self.assertEqual(
            [x.start for x in contiguous.plan.slots],
            [NOW + timedelta(hours=1),
             NOW + timedelta(hours=1, minutes=15)],
        )
        self.assertEqual(contiguous.coverage["c0"], "COMPLETE")
        with self.assertRaises(ValueError):
            ChargeDemand("car", "c0", 2, None, continuous_charging="true")
        unfillable = compile_plan(
            ctl, chargers,
            [ChargeDemand("car", "c0", 2.0, NOW + timedelta(hours=2),
                          continuous_charging=True)],
            NOW, mode="Economy",
            tariffs={"c0": [tariff[0], tariff[2], tariff[4]]})
        self.assertEqual(unfillable.reasons["c0"],
                         "CONTIGUOUS_WINDOW_UNAVAILABLE")
        self.assertFalse(unfillable.plan.slots)

    def test_money_budget_only_effective_tariffs_and_full_quarter_caps(self):
        ctl, chargers = build()
        tariff = [
            PriceSlot(NOW, NOW + timedelta(minutes=15), 2.0, "EUR",
                      basis="effective"),
            PriceSlot(NOW + timedelta(minutes=15),
                      NOW + timedelta(minutes=30), 0.5, "EUR",
                      basis="effective"),
            PriceSlot(NOW + timedelta(minutes=30),
                      NOW + timedelta(minutes=45), 3.0, "EUR",
                      basis="effective"),
        ]
        request = ChargeDemand(
            "guest", "c0", None, NOW + timedelta(hours=1),
            remaining_budget_amount=1.5, budget_currency="EUR",
        )
        plan = compile_plan(ctl, chargers, [request], NOW,
                            mode="Economy", tariffs={"c0": tariff})
        self.assertEqual([s.start for s in plan.plan.slots],
                         [NOW + timedelta(minutes=15)])
        self.assertLessEqual(plan.proposed_kwh["c0"], 1.0)
        # Wholesale spot or unqualified variable reference cannot authorize
        # physically executable EUR-budget demand.
        for basis in ("spot", "variable_reference"):
            actual = [PriceSlot(p.start, p.end,
                                p.effective_price_per_kwh, "EUR", basis=basis)
                      for p in tariff]
            refused = compile_plan(ctl, chargers, [request], NOW,
                                   mode="Economy", tariffs={"c0": actual})
            self.assertFalse(refused.plan.slots)
            self.assertEqual(refused.reasons["c0"],
                             "BUDGET_EFFECTIVE_TARIFF_UNAVAILABLE")
        wrong = compile_plan(ctl, chargers, [request], NOW, mode="Economy",
                             tariffs={"c0": [
                                 PriceSlot(p.start, p.end,
                                           p.effective_price_per_kwh, "USD")
                                 for p in tariff]})
        self.assertFalse(wrong.plan.slots)
        with self.assertRaises(ValueError):
            ChargeDemand("guest", "c0", 2.0, None,
                         remaining_budget_amount=10.0,
                         budget_currency="EUR")

    def test_specific_weekdays_replace_single_weekly(self):
        zone = ZoneInfo("Europe/Brussels")
        monday = datetime(2026, 11, 23, 7, tzinfo=zone)
        deadline, status = resolve_recurring_ready_by(
            None, monday, "specific_days", "Europe/Brussels",
            {"mon": "06:45", "wed": "08:30", "fri": "17:15"},
        )
        self.assertEqual(status, "RECURRING")
        self.assertEqual(deadline.astimezone(zone).strftime("%a %H:%M"), "Wed 08:30")
        friday = datetime(2026, 11, 27, 18, tzinfo=zone)
        deadline, _ = resolve_recurring_ready_by(
            None, friday, "specific_days", "Europe/Brussels",
            {"mon": "06:45", "wed": "08:30", "fri": "17:15"},
        )
        self.assertEqual(deadline.astimezone(zone).strftime("%a %H:%M"), "Mon 06:45")
        deadline, reason = resolve_recurring_ready_by(
            None, monday, "specific_days", "Europe/Brussels", {},
        )
        self.assertIsNone(deadline)
        self.assertEqual(reason, "DEADLINE_UNAVAILABLE")

    def test_specific_days_dst_uses_real_future_instants(self):
        spring = datetime(2027, 3, 27, 20, tzinfo=timezone.utc)
        got, reason = resolve_recurring_ready_by(
            None, spring, "specific_days", "Europe/Brussels",
            {"sun": "02:30"},
        )
        self.assertEqual(reason, "RECURRING")
        self.assertEqual(got, datetime(2027, 3, 28, 1, tzinfo=timezone.utc))
        fall = datetime(2026, 10, 25, 0, 15, tzinfo=timezone.utc)
        got, reason = resolve_recurring_ready_by(
            None, fall, "specific_days", "Europe/Brussels",
            {"sun": "02:30"},
        )
        self.assertEqual(reason, "RECURRING")
        self.assertEqual(got, datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc))

    def test_weekday_charging_windows_are_binding_in_one_planner(self):
        zone = "Europe/Brussels"
        window = {"mon": {"start": "22:00", "end": "06:00"}}
        for local, expected in (
            (datetime(2026, 11, 23, 22, 0, tzinfo=ZoneInfo(zone)), True),
            (datetime(2026, 11, 24, 5, 45, tzinfo=ZoneInfo(zone)), True),
            (datetime(2026, 11, 24, 6, 0, tzinfo=ZoneInfo(zone)), False),
            (datetime(2026, 11, 28, 23, 0, tzinfo=ZoneInfo(zone)), False),
        ):
            self.assertEqual(
                charging_window_allows(window, local, timedelta(minutes=15), zone),
                expected,
            )
        ctl, chargers = build()
        plan = compile_plan(
            ctl, chargers,
            [ChargeDemand("a0", "c0", 4.0,
                          datetime(2026, 11, 24, 8, tzinfo=timezone.utc))],
            datetime(2026, 11, 23, 19, tzinfo=timezone.utc),
            mode="Ready By", horizon_hours=18,
            charging_windows={"c0": window}, site_time_zone=zone,
        )
        self.assertTrue(plan.plan.slots)
        self.assertTrue(all(
            charging_window_allows(window, slot.start, timedelta(minutes=15), zone)
            for slot in plan.plan.slots
        ))
        blocked = compile_plan(
            ctl, chargers,
            [ChargeDemand("a0", "c0", 1.0,
                          datetime(2026, 11, 23, 20, tzinfo=timezone.utc))],
            datetime(2026, 11, 23, 12, tzinfo=timezone.utc),
            mode="Ready By",
            charging_windows={"c0": window}, site_time_zone=zone,
        )
        self.assertFalse(blocked.plan.slots)
        self.assertEqual(blocked.reasons["c0"], "CHARGING_WINDOW_LIMITED")

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


    def test_variable_current_respects_site_phase_and_circuit(self):
        controller = ChargeController(
            uid="site", name="Site", max_parallel=2, max_group_power_kw=12,
            phase_limits_a={"L1": 20, "L2": 20, "L3": 20},
        )
        chargers = {
            "a": Charger(uid="a", name="A", controller_uid="site",
                control_kind="variable_current", rated_power_kw=11,
                phase_count=3, phase_ids=("L1", "L2", "L3"), voltage_v=230,
                min_current_a=6, max_current_a=16, current_step_a=1,
                circuit_id="shared", circuit_limit_a=20),
            "b": Charger(uid="b", name="B", controller_uid="site",
                control_kind="variable_current", rated_power_kw=11,
                phase_count=3, phase_ids=("L1", "L2", "L3"), voltage_v=230,
                min_current_a=6, max_current_a=16, current_step_a=1,
                circuit_id="shared", circuit_limit_a=20),
        }
        demand = [ChargeDemand("car-a", "a", 5, NOW, priority=10),
                  ChargeDemand("car-b", "b", 5, NOW)]
        result = compile_plan(controller, chargers, demand, NOW, mode="Force Charge")
        for slot in {s.start for s in result.plan.slots}:
            selected = [s for s in result.plan.slots if s.start == slot]
            self.assertLessEqual(sum(s.current_a for s in selected), 20)
            self.assertLessEqual(sum(s.power_kw for s in selected), 12)
        self.assertTrue(any(s.current_a < 16 for s in result.plan.slots
                            if s.charger_uid == "b"))

    def test_ac_minimum_energy_planning_and_unverified_defaults(self):
        controller = ChargeController(uid="site", name="Site", max_group_power_kw=3.6)
        base = dict(uid="c", name="C", controller_uid="site",
                    control_kind="variable_current", rated_power_kw=3.6)
        demand = [ChargeDemand("car", "c", 3, NOW+timedelta(hours=2))]
        unknown = Charger(**base)
        self.assertAlmostEqual(minimum_planning_power(unknown), 1.38)
        self.assertAlmostEqual(minimum_planning_power(Charger(**base, phase_count=2)), 2.76)
        self.assertAlmostEqual(minimum_planning_power(Charger(**base, phase_count=3)), 4.14)
        preview = compile_plan(controller, {"c": unknown}, demand, NOW,
                               mode="Automatic", indicative_only=True)
        self.assertTrue(preview.plan.slots)
        self.assertTrue(all(s.power_kw == 1.38 and s.current_a is None
                            for s in preview.plan.slots))
        self.assertAlmostEqual(preview.shortfall_kwh["c"], 0.24)
        known = Charger(**base, phase_count=1, voltage_v=230,
                        min_current_a=6, max_current_a=16, current_step_a=1)
        covered = [ChargeDemand("car", "c", 2, NOW+timedelta(hours=2))]
        plan = compile_plan(controller, {"c": known}, covered, NOW, mode="Automatic")
        self.assertTrue(plan.plan.slots)
        self.assertTrue(all(s.expected_power_kw == 1.38 and s.current_a == 15
                            and s.power_kw == 3.45 for s in plan.plan.slots))
        self.assertEqual(len(plan.plan.slots), 6)
        self.assertAlmostEqual(plan.proposed_kwh["c"], 2.07)
        self.assertEqual(plan.shortfall_kwh["c"], 0)
        recovered = compile_plan(controller, {"c": known}, demand, NOW, mode="Automatic")
        self.assertEqual(recovered.shortfall_kwh["c"], 0)
        self.assertEqual(recovered.strategy["c"], "deadline_recovery")
        self.assertEqual(recovered.plan.slots[0].start, NOW)
        self.assertTrue(all(s.current_a > 6 and s.power_kw <= 3.6 for s in recovered.plan.slots))
        custom = Charger(**base, phase_count=1, voltage_v=230, min_current_a=6,
                         max_current_a=16, current_step_a=1, min_charging_power_kw=1.8)
        self.assertAlmostEqual(minimum_planning_power(custom), 1.84)
        plan = compile_plan(controller, {"c": custom}, demand, NOW, mode="Ready By")
        self.assertTrue(all(s.expected_power_kw == 1.84 and s.current_a == 15
                            for s in plan.plan.slots))
        self.assertEqual(plan.shortfall_kwh["c"], 0)
        forced = compile_plan(controller, {"c": known}, demand, NOW, mode="Force Charge")
        self.assertTrue(any(s.current_a > 6 for s in forced.plan.slots))
        limited = ChargeController(uid="site", name="Site", max_group_power_kw=1)
        self.assertFalse(compile_plan(limited, {"c": unknown}, demand, NOW,
                                     mode="Automatic", indicative_only=True).plan.slots)

    def test_boost_respects_other_minimum_allocations_and_solar(self):
        ctl = ChargeController(uid="site", name="Site", max_parallel=2,
                               max_group_power_kw=3.6, phase_limits_a={"L1": 15})
        chargers = {uid: Charger(uid=uid, name=uid, controller_uid="site",
                    control_kind="variable_current", rated_power_kw=3.6,
                    phase_count=1, phase_ids=("L1",), voltage_v=230,
                    min_current_a=6, max_current_a=16, current_step_a=1)
                    for uid in ("a", "b")}
        demands = [ChargeDemand(uid, uid, 0.6, NOW+timedelta(hours=1))
                   for uid in chargers]
        result = compile_plan(ctl, chargers, demands, NOW, mode="Ready By")
        self.assertEqual(result.coverage, {"a": "COMPLETE", "b": "COMPLETE"})
        self.assertEqual(len(result.plan.slots), 4)
        for start in {s.start for s in result.plan.slots}:
            rows = [s for s in result.plan.slots if s.start == start]
            self.assertEqual(len(rows), 2)
            self.assertEqual(sum(s.current_a for s in rows), 15)
            self.assertTrue(all(s.expected_power_kw == 1.38 for s in rows))
        solar = tuple(PowerLimitSlot(NOW+timedelta(minutes=i*15),
                    NOW+timedelta(minutes=(i+1)*15), 2.76) for i in range(4))
        result = compile_plan(ctl, chargers, demands, NOW, mode="Solar", solar=solar)
        self.assertTrue(all(s.current_a == 6 for s in result.plan.slots))

    def test_variable_current_without_verified_wiring_cannot_be_planned(self):
        controller = ChargeController(uid="site", name="Site", max_group_power_kw=11)
        charger = Charger(uid="c", name="C", controller_uid="site",
            control_kind="variable_current", rated_power_kw=11, phase_count=3,
            min_current_a=6, max_current_a=16)
        result = compile_plan(controller, {"c": charger},
            [ChargeDemand("car", "c", 2, NOW + timedelta(hours=1))],
            NOW, mode="Automatic")
        self.assertEqual(result.reasons["c"], "VARIABLE_CURRENT_CAPABILITY_UNVERIFIED")

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
