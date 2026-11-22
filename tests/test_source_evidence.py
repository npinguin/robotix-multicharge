"""Pure source-quality regression without a Home Assistant installation."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

PKG = Path(__file__).resolve().parents[1] / "custom_components" / "robotix_multicharge"
ROOT = "multicharge_source_test"
package = type(sys)(ROOT)
package.__path__ = [str(PKG)]
sys.modules[ROOT] = package
for name in ("contracts", "source_evidence"):
    spec = importlib.util.spec_from_file_location(f"{ROOT}.{name}", PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from multicharge_source_test.source_evidence import binding, connection, intervals, number  # noqa: E402 - imported after isolated pure-module bootstrap

NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)


def state(value, unit=None, observed=NOW, **attributes):
    attrs = dict(attributes)
    if unit is not None:
        attrs["unit_of_measurement"] = unit
    return SimpleNamespace(state=value, attributes=attrs, last_updated=observed)


def hass(data):
    return SimpleNamespace(states=SimpleNamespace(get=data.get))


class EvidenceTests(unittest.TestCase):
    def test_measured_zero_and_units_are_not_guessed(self):
        obj = hass({
            "sensor.power": state("0", "W"),
            "sensor.soc": state("0", "%"),
            "sensor.wrong": state("123", "MW"),
        })
        self.assertEqual(number(obj, "sensor.power", "power", NOW).value, 0)
        self.assertEqual(number(obj, "sensor.soc", "soc", NOW).value, 0)
        self.assertEqual(number(obj, "sensor.wrong", "power", NOW).quality, "invalid")

    def test_stale_missing_unknown_not_zero(self):
        obj = hass({
            "sensor.old": state("30", "%", observed=NOW - timedelta(hours=3)),
            "sensor.unknown": state("unknown", "%"),
        })
        self.assertEqual(number(obj, "sensor.old", "soc", NOW).quality, "stale")
        self.assertIsNone(number(obj, "sensor.missing", "soc", NOW).value)
        self.assertIsNone(number(obj, "sensor.unknown", "soc", NOW).value)

    def test_repeated_unchanged_native_reports_preserve_freshness(self):
        cable = state("on", observed=NOW - timedelta(hours=4))
        meter = state("150", "W", observed=NOW - timedelta(hours=4))
        cable.last_reported = NOW
        meter.last_reported = NOW
        source = hass({
            "binary_sensor.cable": cable,
            "sensor.actual": meter,
        })
        self.assertEqual(connection(source, "binary_sensor.cable", NOW).quality, "ok")
        self.assertEqual(number(source, "sensor.actual", "power", NOW).value, 0.15)
        # If the provider stops reporting altogether, a stale source is not
        # silently recast as healthy merely because its HA state is unchanged.
        cable.last_reported = NOW - timedelta(hours=1)
        self.assertEqual(connection(source, "binary_sensor.cable", NOW).quality, "stale")

    def test_switch_on_is_not_physical_connection(self):
        obj = hass({
            "switch.plug": state("on"),
            "binary_sensor.cable": state("on"),
            "sensor.cable": state("connected"),
        })
        self.assertIsNone(connection(obj, "switch.plug", NOW).value)
        self.assertTrue(connection(obj, "binary_sensor.cable", NOW).value)
        self.assertTrue(connection(obj, "sensor.cable", NOW).value)

    def test_price_requires_explicit_effective_basis(self):
        slots = [{
            "start": NOW.isoformat(),
            "end": (NOW + timedelta(minutes=15)).isoformat(),
            "value": -0.1,
        }]
        obj = hass({
            "sensor.prices": state(
                "ok", kind="effective_price_kwh", currency="EUR",
                valid_until=(NOW + timedelta(hours=1)).isoformat(),
                intervals=slots,
            ),
            "sensor.spot": state(
                "ok", kind="spot_eur_mwh",
                valid_until=(NOW + timedelta(hours=1)).isoformat(),
                intervals=slots,
            ),
        })
        accepted, status = intervals(obj, "sensor.prices", "price", NOW)
        self.assertEqual(status, "OK")
        self.assertEqual(accepted[0].effective_price_per_kwh, -0.1)
        self.assertEqual(intervals(obj, "sensor.spot", "price", NOW)[0], ())

    def test_binding_requires_fresh_authoritative_intervals(self):
        attrs = {
            "kind": "binding_power_envelope", "authority": "binding",
            "provider_id": "site-energy", "revision": "r17",
            "issued_at": NOW.isoformat(),
            "valid_until": (NOW + timedelta(hours=1)).isoformat(),
            "intervals": [{
                "start": NOW.isoformat(),
                "end": (NOW + timedelta(minutes=15)).isoformat(),
                "max_charging_kw": 0,
            }],
        }
        obj = hass({"sensor.binding": state("active", **attrs)})
        envelope, status = binding(obj, "sensor.binding", NOW)
        self.assertEqual(status, "OK")
        self.assertEqual(envelope.slots[0].max_charging_kw, 0)
        bad = hass({"sensor.binding": state(
            "active", **{**attrs, "authority": "advisory"}
        )})
        self.assertIsNone(binding(bad, "sensor.binding", NOW)[0])
        self.assertIsNone(binding(obj, "sensor.binding", NOW + timedelta(hours=2))[0])

    def test_price_without_currency_is_not_qualified(self):
        row = {
            "start": NOW.isoformat(),
            "end": (NOW + timedelta(minutes=15)).isoformat(),
            "value": -0.2,
        }
        obj = hass({"sensor.price": state(
            "ready", kind="effective_price_kwh",
            valid_until=(NOW + timedelta(hours=1)).isoformat(),
            intervals=[row],
        )})
        self.assertEqual(
            intervals(obj, "sensor.price", "price", NOW),
            ((), "INTERVAL_PAYLOAD_INVALID"),
        )

    def test_price_slot_cannot_outlive_source_validity(self):
        row = {
            "start": NOW.isoformat(),
            "end": (NOW + timedelta(hours=2)).isoformat(),
            "value": 0.12,
        }
        obj = hass({"sensor.price": state(
            "ready", kind="effective_price_kwh", currency="USD",
            valid_until=(NOW + timedelta(minutes=30)).isoformat(),
            intervals=[row],
        )})
        slots, reason = intervals(obj, "sensor.price", "price", NOW)
        self.assertEqual(slots, ())
        self.assertEqual(reason, "INTERVAL_EXCEEDS_VALIDITY")

    def test_overlapping_solar_and_expiry_rejected(self):
        row = {
            "start": NOW.isoformat(),
            "end": (NOW + timedelta(minutes=15)).isoformat(),
            "value": 2,
        }
        obj = hass({
            "sensor.solar": state(
                "ok", kind="solar_limit_kw",
                valid_until=(NOW + timedelta(hours=1)).isoformat(),
                intervals=[row, row],
            ),
        })
        self.assertEqual(intervals(obj, "sensor.solar", "solar", NOW)[1], "INTERVAL_OVERLAP")
        self.assertEqual(
            intervals(obj, "sensor.solar", "solar", NOW + timedelta(hours=2))[0],
            (),
        )


if __name__ == "__main__":
    unittest.main()
