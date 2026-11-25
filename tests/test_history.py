"""Native Recorder actual-quarter evidence; no fabricated values in production."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

path = Path(__file__).resolve().parents[1] / "custom_components/robotix_multicharge/history.py"
spec = importlib.util.spec_from_file_location("multicharge_history_test", path)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
actual_quarters = mod._quarter_actuals
NOW = datetime(2026, 11, 22, 13, tzinfo=timezone.utc)


def recorded(at, value, units="W"):
    return SimpleNamespace(state=value, last_updated=at,
                           attributes={"unit_of_measurement": units})


class NativeMeasuredHistoryTests(unittest.TestCase):
    def test_planned_cost_shared_owners_and_negative_prices(self):
        start = NOW
        mid = start + timedelta(minutes=15)
        end = mid + timedelta(minutes=15)
        def slot(uid, asset, a, b):
            return SimpleNamespace(
                charger_uid=uid, asset_uid=asset, start=a, end=b, power_kw=4)
        rows = [slot("a", "car_a", start, mid),
                slot("b", "car_b", mid, end)]
        prices = [self._price(start, mid, -0.10, basis="spot"),
                  self._price(mid, end, 0.30, basis="spot")]
        result = mod.planned_costs(rows, prices, start)
        self.assertAlmostEqual(result["controller"]["site"]["cost"], 0.2)
        self.assertAlmostEqual(result["asset"]["car_a"]["cost"], -0.1)
        self.assertAlmostEqual(result["charger"]["b"]["cost"], 0.3)
        partial = mod.planned_costs(rows, prices[:1], start)
        self.assertIsNone(partial["controller"]["site"]["cost"])
        self.assertEqual(partial["controller"]["site"]["quality"], "incomplete_tariff")
        clipped = mod.planned_costs(rows, prices, mid)
        self.assertAlmostEqual(clipped["controller"]["site"]["cost"], 0.3)
        bounded = mod.planned_costs(rows, prices, start, until=mid)
        self.assertAlmostEqual(bounded["controller"]["site"]["cost"], -0.1)


    def test_session_costs_do_not_reassign_external_or_duplicate_site(self):
        started = (NOW-timedelta(minutes=15)).isoformat()
        active = {"a": {"started_at": started, "asset_id": "car_a"}}
        metrics = {("a", started, None): {
            "estimated_cost": 0.3, "estimated_cost_currency": "EUR",
            "estimated_cost_basis": "spot", "observed_energy_kwh": 1.0}}
        observed = [{"charger_id": "b", "asset_id": "wrong", "started_at": started,
                     "ended_at": NOW.isoformat(), "ongoing": True,
                     "complete_observed_window": True, "estimated_cost": 0.6,
                     "estimated_cost_currency": "EUR", "estimated_cost_basis": "spot",
                     "observed_energy_kwh": 2.0}]
        result = mod.session_costs([], active, observed, {}, metrics)
        self.assertAlmostEqual(result["controller"]["site"]["active"]["cost"], 0.9)
        self.assertAlmostEqual(result["asset"]["car_a"]["active"]["cost"], 0.3)
        self.assertNotIn("wrong", result["asset"])
        self.assertAlmostEqual(result["charger"]["b"]["active"]["average_price_per_kwh"], 0.3)
        observed[0]["complete_observed_window"] = False
        result = mod.session_costs([], active, observed, {}, metrics)
        self.assertIsNone(result["controller"]["site"]["active"]["cost"])
        self.assertEqual(result["charger"]["b"]["active"]["quality"], "partial_observation")

    def test_tariff_remap_keeps_old_source_and_clips_forecast(self):
        first = NOW-timedelta(minutes=30)
        changed = NOW-timedelta(minutes=10)
        config = {"controller": {"current_price_entity": "sensor.old"}}
        before = mod.reconcile_tariff_bindings(None, config, first)
        config["controller"]["price_entity"] = "sensor.new"
        after = mod.reconcile_tariff_bindings(before, config, changed)
        self.assertEqual(mod._binding_for_interval(after["site"], first, changed), "sensor.old")
        self.assertEqual(mod._binding_for_interval(after["site"], changed, NOW), "sensor.new")
        self.assertIsNone(mod._binding_for_interval(after["site"], first, NOW))
        old = self._price(first, NOW, 0.2, basis="spot")
        new = self._price(first, NOW, 0.6, basis="spot")
        from unittest.mock import patch
        with patch.object(mod, "_historical_reference_quotes",
                          side_effect=lambda hass, historical, entity, current, a, b:
                          (old,) if entity == "sensor.old" else (new,)):
            quotes = mod._quotes_at_binding(None, {}, after["site"], "sensor.new",
                                            [new], first, NOW)
        self.assertEqual([(q.start, q.end, q.effective_price_per_kwh) for q in quotes],
                         [(first, changed, 0.2), (changed, NOW, 0.6)])
        result = mod._run_valuation([(first, NOW, 3.0)], quotes)
        self.assertAlmostEqual(result["estimated_cost"], 0.5)

    def test_unconfirmed_closed_session_cost_is_not_attributed_to_car(self):
        row = {"charger_id": "drive", "asset_id": "car",
               "started_at": (NOW-timedelta(minutes=15)).isoformat(),
               "ended_at": NOW.isoformat(), "physical_stop_confirmed": False}
        result = mod.session_costs([row], {}, [], {}, {})
        self.assertNotIn("car", result["asset"])
        self.assertIn("last", result["charger"]["drive"])

    def test_civil_day_costs_split_actual_session_and_tariff_boundaries(self):
        start = NOW-timedelta(minutes=30)
        mid = start+timedelta(minutes=10)
        remap = start+timedelta(minutes=20)
        config = {"chargers": [{"id": "a"}, {"id": "b"}],
                  "assets": [{"id": "old"}, {"id": "new"}]}
        bindings = {"a": [{"start": None, "entity": "sensor.a"}],
                    "b": [{"start": None, "entity": "sensor.b"}]}
        states = {"sensor.a": [recorded(start, 3000), recorded(mid, 6000), recorded(remap, 0)],
                  "sensor.b": [recorded(start, 0), recorded(remap, 3000)]}
        quotes = [self._price(start, remap, 0.2, basis="spot"),
                  self._price(remap, NOW, -0.1, basis="spot")]
        receipts = [{"charger_id": "a", "asset_id": "old", "started_at": start.isoformat(),
                     "ended_at": mid.isoformat(), "physical_stop_confirmed": True},
                    {"charger_id": "a", "asset_id": "new", "started_at": mid.isoformat(),
                     "ended_at": remap.isoformat(), "physical_stop_confirmed": True}]
        result = mod.daily_costs(states, bindings, config, start, NOW, quotes, receipts)
        key = ("EUR", "spot")
        self.assertAlmostEqual(result["charger"]["a"]["valuations"][key][0], 0.3)
        self.assertAlmostEqual(result["charger"]["b"]["valuations"][key][0], -0.05)
        self.assertAlmostEqual(result["controller"]["site"]["valuations"][key][0], 0.25)
        self.assertAlmostEqual(result["asset"]["old"]["valuations"][key][0], 0.1)
        self.assertAlmostEqual(result["asset"]["new"]["valuations"][key][0], 0.2)
        self.assertAlmostEqual(result["controller"]["site"]["unattributed_energy_kwh"], 0.5)
        days = {"2026-11-21": (start-timedelta(days=1), start),
                "2026-11-22": (start, NOW)}
        periods = mod.civil_period_costs(days, {"2026-11-22": result})
        site = periods["controller"]["site"]
        self.assertAlmostEqual(site["today"]["cost"], 0.25)
        self.assertAlmostEqual(site["today"]["average_price_per_kwh"], 0.125)
        self.assertIsNone(site["month"]["cost"])
        self.assertAlmostEqual(site["month"]["covered_cost"], 0.25)
        self.assertIsNone(periods["asset"]["old"]["today"]["cost"])
        self.assertAlmostEqual(periods["asset"]["old"]["today"]["covered_cost"], 0.1)

    def test_overlapping_historic_power_claim_is_not_double_counted(self):
        first = NOW-timedelta(minutes=30)
        middle = NOW-timedelta(minutes=15)
        configuration = {"chargers": [{"id": "a"}, {"id": "b"}], "assets": []}
        bindings = {"a": [{"start": None, "entity": "sensor.shared"}],
                    "b": [{"start": middle.isoformat(), "entity": "sensor.shared"}]}
        states = {"sensor.shared": [recorded(first, 4000), recorded(middle, 4000)]}
        result = mod.daily_costs(states, bindings, configuration, first, NOW,
                                 [self._price(first, NOW, 0.3)])
        site = result["controller"]["site"]
        self.assertAlmostEqual(site["observed_energy_kwh"], 1.0)
        self.assertEqual(site["observed_seconds"], 900)
        period = mod.civil_period_costs({"2026-11-22": (first, NOW)}, {"2026-11-22": result})
        self.assertIsNone(period["controller"]["site"]["today"]["cost"])
        self.assertAlmostEqual(period["controller"]["site"]["today"]["covered_cost"], 0.3)

    def test_civil_cost_zero_idle_is_not_missing_or_mixed_with_charged_basis(self):
        first = NOW-timedelta(minutes=15)
        configuration = {"chargers": [{"id": "a"}], "assets": []}
        bindings = {"a": [{"start": None, "entity": "sensor.a"}]}
        idle = mod.daily_costs({"sensor.a": [recorded(first, 0)]}, bindings,
                               configuration, first, NOW, [self._price(first, NOW, 0.4)])
        period = mod.civil_period_costs({"2026-11-22": (first, NOW)}, {"2026-11-22": idle})
        self.assertEqual(period["controller"]["site"]["today"]["cost"], 0)
        self.assertIsNone(period["controller"]["site"]["today"]["average_price_per_kwh"])

    def test_civil_cost_days_respect_dst_and_missing_measurements(self):
        at = datetime(2026, 10, 26, 11, tzinfo=timezone.utc)
        days = mod.civil_cost_days(at, "Europe/Brussels")
        start, end = days["2026-10-25"]
        self.assertEqual(end-start, timedelta(hours=25))
        self.assertEqual(days["2026-10-26"][1], at)
        config = {"chargers": [{"id": "a"}], "assets": []}
        binding = {"a": [{"start": None, "entity": "sensor.a"}]}
        result = mod.daily_costs({"sensor.a": [recorded(start, 2000)]}, binding,
                                 config, start, end, [self._price(start, end, 0.2)])
        day = result["controller"]["site"]
        self.assertEqual(day["observed_seconds"], 1800)
        self.assertEqual(day["expected_seconds"], 25*3600)
        self.assertAlmostEqual(day["valuations"][("EUR", "effective")][0], 0.2)
        period = mod.civil_period_costs({"2026-10-25": (start, end)}, {"2026-10-25": result})
        self.assertIsNone(period["controller"]["site"]["today"]["cost"])
        self.assertAlmostEqual(period["controller"]["site"]["today"]["covered_cost"], 0.2)

    def test_civil_costs_do_not_combine_currencies_or_missing_tariff(self):
        start = NOW-timedelta(minutes=30)
        mid = start+timedelta(minutes=15)
        config = {"chargers": [{"id": "a"}], "assets": []}
        bindings = {"a": [{"start": None, "entity": "sensor.a"}]}
        states = {"sensor.a": [recorded(start, 4000), recorded(mid, 4000)]}
        for quotes, quality in (
            ([self._price(start, mid, 0.2)], "partial_coverage"),
            ([self._price(start, mid, 0.2), self._price(mid, NOW, 0.3, currency="USD")],
             "mixed_price_basis_or_currency"),
        ):
            day = mod.daily_costs(states, bindings, config, start, NOW, quotes)
            result = mod.civil_period_costs({"2026-11-22": (start, NOW)}, {"2026-11-22": day})
            self.assertIsNone(result["controller"]["site"]["today"]["cost"])
            self.assertEqual(result["controller"]["site"]["today"]["quality"], quality)

    def test_historical_attribution_uses_session_at_time_not_new_assignment(self):
        beginning = NOW - timedelta(minutes=45)
        receipts = [{
            "charger_id": "drive", "asset_id": "old_car",
            "started_at": beginning.isoformat(),
            "ended_at": NOW.isoformat(),
            "physical_stop_confirmed": True,
        }]
        self.assertEqual(
            mod._session_asset_at_time(
                receipts, "drive", NOW-timedelta(minutes=30),
                NOW-timedelta(minutes=15),
            ), "old_car"
        )
        self.assertIsNone(mod._session_asset_at_time(
            receipts, "drive", NOW, NOW+timedelta(minutes=15)))
        self.assertIsNone(mod._session_asset_at_time(
            receipts, "new_charger", NOW-timedelta(minutes=30),
            NOW-timedelta(minutes=15)))
        self.assertIsNone(mod._session_asset_at_time(
            [], "drive", NOW-timedelta(minutes=30),
            NOW-timedelta(minutes=15)))

    def test_ambiguous_overlapping_session_receipts_do_not_guess_vehicle(self):
        when = NOW-timedelta(minutes=30)
        evidence = [
            {"charger_id":"drive","asset_id":id,
             "started_at":(when-timedelta(minutes=10)).isoformat(),
             "ended_at":NOW.isoformat(),"physical_stop_confirmed":True}
            for id in ("car_a","car_b")
        ]
        self.assertIsNone(mod._session_asset_at_time(
            evidence, "drive", when, when+timedelta(minutes=15)))

    def test_power_binding_epochs_survive_rebind_and_deletion(self):
        cfg = {"chargers": [{"id": "drive", "power_entity": "sensor.old"}]}
        before = mod.reconcile_power_bindings(None, cfg, NOW)
        change = NOW + timedelta(minutes=7)
        cfg["chargers"][0]["power_entity"] = "sensor.new"
        after = mod.reconcile_power_bindings(before, cfg, change)
        self.assertEqual(mod._binding_for_interval(after["drive"], NOW-timedelta(minutes=15), NOW),
                         "sensor.old")
        self.assertIsNone(mod._binding_for_interval(after["drive"], NOW, NOW+timedelta(minutes=15)))
        self.assertEqual(mod._binding_for_interval(after["drive"], NOW+timedelta(minutes=15),
                                                   NOW+timedelta(minutes=30)), "sensor.new")
        self.assertEqual(after, mod.reconcile_power_bindings(after, cfg, NOW+timedelta(hours=1)))
        deleted = mod.reconcile_power_bindings(after, {"chargers": []}, NOW+timedelta(hours=1))
        self.assertIsNone(mod._binding_for_interval(deleted["drive"], NOW+timedelta(hours=1),
                                                   NOW+timedelta(hours=2)))
        self.assertEqual(mod._binding_for_interval(deleted["drive"], NOW-timedelta(minutes=15), NOW),
                         "sensor.old")

    def test_external_run_energy_and_tariff_overlap_without_attribution(self):
        start = NOW - timedelta(minutes=30)
        mid = start + timedelta(minutes=15)
        first = start - timedelta(minutes=5)
        states = [recorded(first, 0), recorded(start, 2000),
                  recorded(mid, 4000), recorded(NOW, 0)]
        bindings = {"drive": [{"start": None, "entity": "sensor.power"}]}
        quotes = [self._price(start, mid, 0.20, basis="spot"),
                  self._price(mid, NOW, 0.32, basis="spot")]
        rows = mod._observed_session_rows(
            {"sensor.power": states}, bindings, ["drive"], first,
            NOW, NOW, [], {}, quotes)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["complete_observed_window"])
        self.assertTrue(row["end_known"])
        self.assertIsNone(row["asset_id"])
        self.assertAlmostEqual(row["observed_energy_kwh"], 1.5)
        self.assertAlmostEqual(row["average_power_kw"], 3)
        self.assertAlmostEqual(row["peak_power_kw"], 4)
        self.assertAlmostEqual(row["estimated_cost"], 0.42)
        self.assertEqual(row["estimated_cost_basis"], "spot")
        duplicate = mod._observed_session_rows(
            {"sensor.power": states}, bindings, ["drive"], first,
            NOW, NOW, [self._receipt(start, NOW)], {}, quotes)
        self.assertEqual(duplicate, [])
        # Partial ownership never discards the rest of a real external run.
        owned_start = start + timedelta(minutes=5)
        owned_end = NOW - timedelta(minutes=5)
        parts = mod._observed_session_rows(
            {"sensor.power": states}, bindings, ["drive"], first, NOW, NOW,
            [self._receipt(owned_start, owned_end)], {}, quotes)
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0]["ended_at"], owned_start.isoformat())
        self.assertEqual(parts[1]["started_at"], owned_end.isoformat())
        self.assertFalse(any(part["complete_observed_window"] for part in parts))
        self.assertAlmostEqual(sum(part["observed_energy_kwh"] for part in parts), 0.5)
        incomplete = mod._observed_session_rows(
            {"sensor.power": states}, bindings, ["drive"], first,
            NOW, NOW, [], {}, quotes[:1])
        self.assertIsNone(incomplete[0]["estimated_cost"])

    def test_stale_observed_run_does_not_invent_completion(self):
        start = NOW - timedelta(hours=2)
        runs = mod._observed_runs(
            [recorded(start-timedelta(minutes=5), 0), recorded(start, 2000)],
            start-timedelta(minutes=5), NOW, NOW)
        self.assertEqual(len(runs), 1)
        self.assertFalse(runs[0]["end_known"])
        self.assertFalse(runs[0]["ongoing"])
        self.assertEqual(runs[0]["segments"][0][1], start+mod.MAX_OBSERVATION_AGE)

    def test_cumulative_meter_delta_requires_monotonic_qualified_boundaries(self):
        start = NOW - timedelta(minutes=15)
        power = [recorded(start, 2000), recorded(NOW, 0)]
        meter = [recorded(start, 10, "kWh"), recorded(NOW, 10.5, "kWh")]
        self.assertAlmostEqual(mod._meter_delta(
            meter, power, start, NOW, NOW, False)["meter_energy_kwh"], 0.5)
        reset = [meter[0], recorded(NOW, 0.5, "kWh")]
        self.assertIsNone(mod._meter_delta(reset, power, start, NOW, NOW, False))

    def test_real_meter_integrates_recorded_power_changes(self):
        start = NOW - timedelta(minutes=15)
        row = actual_quarters([
            recorded(start, 2000),
            recorded(start + timedelta(minutes=10), 1000),
        ], start, NOW, NOW)[0]
        self.assertEqual(row["quality"], "measured_power_integral")
        self.assertAlmostEqual(row["actual_energy_kwh"], 25 / 60, places=6)
        self.assertAlmostEqual(row["actual_power_kw"], 25 / 15, places=6)

    def test_measured_zero_is_distinct_from_unknown(self):
        start = NOW - timedelta(minutes=15)
        row = actual_quarters([recorded(start, 0)], start, NOW, NOW)[0]
        self.assertEqual(row["quality"], "measured_power_integral")
        self.assertEqual(row["actual_energy_kwh"], 0)

    def test_missing_prefix_and_stale_measurements_do_not_invent_energy(self):
        start = NOW - timedelta(minutes=15)
        row = actual_quarters(
            [recorded(start + timedelta(minutes=5), 1500)],
            start, NOW, NOW,
        )[0]
        self.assertEqual(row["quality"], "unknown")
        self.assertIsNone(row["actual_energy_kwh"])
        start = NOW - timedelta(hours=1)
        items = actual_quarters([recorded(start, 1000)], start, NOW, NOW)
        self.assertEqual(items[0]["quality"], "measured_power_integral")
        self.assertIsNone(items[2]["actual_power_kw"])

    def test_unavailable_sensor_event_breaks_historical_coverage(self):
        start = NOW - timedelta(minutes=15)
        # The meter goes unavailable five minutes into the same quarter.
        # We must not forward-fill the last known positive reading.
        samples = [
            recorded(start, 2000),
            recorded(start + timedelta(minutes=5), "unavailable"),
        ]
        actual = actual_quarters(samples, start, NOW, NOW)[0]
        self.assertEqual(actual["quality"], "unknown")
        self.assertIsNone(actual["actual_energy_kwh"])

    def test_invalid_unit_and_future_never_claim_actual_power(self):
        start = NOW - timedelta(minutes=15)
        items = actual_quarters(
            [recorded(start, 8, "A")],
            start, NOW + timedelta(minutes=15), NOW,
        )
        self.assertEqual(len(items), 1)
        self.assertIsNone(items[0]["actual_energy_kwh"])

    @staticmethod
    def _receipt(start, end):
        return {
            "charger_id": "drive", "asset_id": "old_car",
            "started_at": start.isoformat(),
            "ended_at": end.isoformat(),
            "physical_stop_confirmed": True,
            "energy_quality": "measured",
            "actual_energy_kwh": 1.5,
        }

    @staticmethod
    def _price(start, end, price, *, currency="EUR", basis="effective"):
        return SimpleNamespace(
            start=start, end=end, effective_price_per_kwh=price,
            currency=currency, basis=basis,
        )

    def test_two_effective_tariff_intervals_use_actual_metered_power_timeline(self):
        start = NOW - timedelta(minutes=30)
        middle = start + timedelta(minutes=15)
        prices = [self._price(start, middle, 0.20),
                  self._price(middle, NOW, 0.32)]
        samples = [recorded(start, 2000), recorded(middle, 4000)]
        outcome = mod._estimated_session_variable_cost(
            samples, self._receipt(start, NOW), prices, NOW
        )
        self.assertIsNotNone(outcome)
        # 0.5 kWh @ 0.20 plus 1.0 kWh @ 0.32: never average session
        # kWh uniformly across two different tariffs.
        self.assertAlmostEqual(outcome["estimated_variable_cost"], 0.42)
        self.assertAlmostEqual(outcome["estimated_variable_cost_energy_kwh"], 1.5)
        self.assertEqual(outcome["estimated_variable_cost_currency"], "EUR")
        self.assertEqual(outcome["estimated_variable_cost_quality"],
                         "observed_power_integral_effective_tariff")
        self.assertEqual(outcome["estimated_variable_cost_basis"],
                         "indicative_variable_energy_only")

    def test_partial_boundary_uses_actual_power_not_prorated_meter_total(self):
        start = NOW - timedelta(minutes=30)
        middle = start + timedelta(minutes=7, seconds=30)
        outcome = mod._estimated_session_variable_cost(
            [recorded(start, 2000)],
            self._receipt(start, NOW),
            [self._price(start, middle, 0.2),
             self._price(middle, NOW, 0.4)],
            NOW,
        )
        self.assertAlmostEqual(outcome["estimated_variable_cost"], 0.35)
        self.assertAlmostEqual(outcome["estimated_variable_cost_energy_kwh"], 1.0)
        self.assertEqual(outcome["estimated_variable_cost_basis"],
                         "indicative_variable_energy_only")

    def test_native_variable_cost_fails_closed_for_missing_or_ambiguous_evidence(self):
        start = NOW - timedelta(minutes=30)
        middle = start + timedelta(minutes=15)
        good = [self._price(start, middle, 0.1),
                self._price(middle, NOW, 0.2)]
        samples = [recorded(start, 2000), recorded(middle, 1000)]
        receipt = self._receipt(start, NOW)
        cases = (
            (samples, receipt, [good[0]], "missing final tariff"),
            (samples, receipt, [good[0],
                self._price(middle + timedelta(seconds=1), NOW, 0.2)],
                "one second of missing price"),
            (samples, receipt, [good[0],
                self._price(middle - timedelta(seconds=1), NOW, 0.2)],
                "overlapping prices"),
            (samples, receipt, [good[0],
                self._price(middle, NOW, 0.2, currency="USD")],
                "mixed currency"),
            (samples, receipt, [good[0],
                self._price(middle, NOW, 0.2, basis="spot")],
                "spot quote cannot be billed"),
            ([recorded(start + timedelta(minutes=5), 2000)], receipt,
             good, "missing beginning power"),
            ([recorded(start, 2000), recorded(middle, "unavailable")],
             receipt, good, "provider became unavailable"),
            ([recorded(start, 2000), recorded(middle, -1000)],
             receipt, good, "unphysical negative power"),
            ([recorded(start - timedelta(minutes=40), 2000)],
             receipt, good, "stale physical measurement"),
            ([recorded(start, 2000), recorded(start, 4000)],
             receipt, good, "ambiguous native sample order"),
            (samples, {**receipt, "physical_stop_confirmed": False},
             good, "unconfirmed physical stop"),
            (samples, {**receipt, "energy_quality": "unknown"},
             good, "no independent energy receipt"),
            (samples, {**receipt, "actual_energy_kwh": None},
             good, "no measured delivered kWh"),
        )
        for readings, session, rates, label in cases:
            with self.subTest(label=label):
                self.assertIsNone(mod._estimated_session_variable_cost(
                    readings, session, rates, NOW
                ), label)

    def test_negative_effective_tariff_is_preserved_not_rounded_to_zero(self):
        start = NOW - timedelta(minutes=15)
        result = mod._estimated_session_variable_cost(
            [recorded(start, 2000)],
            self._receipt(start, NOW),
            [self._price(start, NOW, -0.2)],
            NOW,
        )
        self.assertAlmostEqual(result["estimated_variable_cost"], -0.1)

    def test_fall_dst_real_25_hour_utc_intervals_are_not_flattened(self):
        zone = ZoneInfo("Europe/Brussels")
        start = datetime(2026, 10, 24, 22, tzinfo=timezone.utc)
        end = start + timedelta(hours=25)
        steps = [recorded(start + timedelta(minutes=15*i), 1000)
                 for i in range(100)]
        prices = [self._price(
            (start + timedelta(hours=i)).astimezone(zone),
            (start + timedelta(hours=i+1)).astimezone(zone), 0.1
        ) for i in range(25)]
        outcome = mod._estimated_session_variable_cost(
            steps, self._receipt(start, end), prices, end,
        )
        self.assertIsNotNone(outcome)
        self.assertAlmostEqual(outcome["estimated_variable_cost"], 2.5)
        self.assertAlmostEqual(outcome["estimated_variable_cost_energy_kwh"], 25)

    def test_dst_days_are_92_and_100_real_utc_quarters(self):
        zone = ZoneInfo("Europe/Brussels")
        for (y, m, d), count in (
            ((2026, 3, 29), 92), ((2026, 10, 25), 100)
        ):
            start = datetime(y, m, d, tzinfo=zone).astimezone(timezone.utc)
            end = (
                datetime(y, m, d, tzinfo=zone) + timedelta(days=1)
            ).astimezone(timezone.utc)
            rows = actual_quarters((), start, end, end)
            self.assertEqual(len(rows), count)
            self.assertTrue(all(x["actual_energy_kwh"] is None for x in rows))


if __name__ == "__main__":
    unittest.main()
