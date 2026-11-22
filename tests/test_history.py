"""Native measured history integration arithmetic and source-quality checks."""
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
measured_quarters = mod.measured_quarters
NOW = datetime(2026, 11, 22, 13, tzinfo=timezone.utc)


def recorded(at, value, units="W"):
    return SimpleNamespace(state=value, last_updated=at,
                           attributes={"unit_of_measurement": units})


class NativeMeasuredHistoryTests(unittest.TestCase):
    def test_real_meter_integrates_partial_power_changes(self):
        start = NOW - timedelta(minutes=15)
        result = measured_quarters([
            recorded(start, 2000),
            recorded(start + timedelta(minutes=10), 1000),
        ], start, NOW, NOW)[0]
        self.assertEqual(result["coverage"], "COMPLETE")
        self.assertAlmostEqual(result["actual_energy_kwh"], 25/60)
        self.assertAlmostEqual(result["actual_power_kw"], 25/15)

    def test_measured_zero_does_not_become_unknown(self):
        start = NOW - timedelta(minutes=15)
        row = measured_quarters([recorded(start, 0)], start, NOW, NOW)[0]
        self.assertEqual((row["coverage"], row["actual_energy_kwh"]),
                         ("COMPLETE", 0))

    def test_missing_start_or_stale_meter_is_unknown_not_zero(self):
        start = NOW - timedelta(minutes=15)
        row = measured_quarters([
            recorded(start + timedelta(minutes=5), 1500)
        ], start, NOW, NOW)[0]
        self.assertIsNone(row["actual_energy_kwh"])
        self.assertEqual(row["coverage"], "PARTIAL")
        start = NOW - timedelta(hours=1)
        samples = measured_quarters([recorded(start, 1000)], start, NOW, NOW)
        self.assertEqual(samples[0]["coverage"], "COMPLETE")
        self.assertIsNone(samples[2]["actual_energy_kwh"])

    def test_future_and_invalid_units_are_never_invented(self):
        data = measured_quarters(
            [recorded(NOW - timedelta(minutes=15), 8, "A")],
            NOW - timedelta(minutes=15), NOW + timedelta(minutes=15), NOW,
        )
        self.assertIsNone(data[0]["actual_power_kw"])
        self.assertEqual(data[1]["coverage"], "FUTURE")

    def test_spring_and_autumn_local_days_have_92_and_100_quarters(self):
        zone = ZoneInfo("Europe/Brussels")
        for (y,m,d),n in (((2026,3,29),92), ((2026,10,25),100)):
            first = datetime(y,m,d,tzinfo=zone).astimezone(timezone.utc)
            last = (datetime(y,m,d,tzinfo=zone)+timedelta(days=1)).astimezone(timezone.utc)
            rows = measured_quarters((), first, last, last)
            self.assertEqual(len(rows), n)
            self.assertTrue(all(x["actual_energy_kwh"] is None for x in rows))


if __name__ == "__main__":
    unittest.main()
