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
