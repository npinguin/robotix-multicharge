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
    def test_real_meter_integrates_recorded_power_changes(self):
        start = NOW - timedelta(minutes=15)
        row = actual_quarters([
            recorded(start, 2000),
            recorded(start + timedelta(minutes=10), 1000),
        ], start, NOW, NOW)[0]
        self.assertEqual(row["quality"], "measured_power_integral")
        self.assertAlmostEqual(row["actual_energy_kwh"], 25 / 60, places=6)
        self.assertAlmostEqual(row["actual_power_kw"], 25 / 15)

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
