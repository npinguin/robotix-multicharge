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

from multicharge_source_test.source_evidence import (  # noqa: E402 - isolated bootstrap
    binding, connection, intervals, number, session_status, live_power, live_price,
)

NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)


def state(value, unit=None, observed=NOW, **attributes):
    attrs = dict(attributes)
    if unit is not None:
        attrs["unit_of_measurement"] = unit
    return SimpleNamespace(state=value, attributes=attrs, last_updated=observed)


def hass(data):
    return SimpleNamespace(states=SimpleNamespace(get=data.get))


class EvidenceTests(unittest.TestCase):
    def test_native_live_power_and_price_are_unit_and_freshness_qualified(self):
        source = hass({
            "sensor.pv": state("2200", "W"),
            "sensor.home": state("1.2", "kW"),
            "sensor.grid": state("-1200", "W"),
            "sensor.surplus": state("0", "W"),
            "sensor.negative_pv": state("-100", "W"),
            "sensor.energy_not_power": state("3.2", "kWh"),
            "sensor.stale": state("1", "kW", observed=NOW-timedelta(minutes=5)),
            "sensor.price": state("-0.11", "€/kWh"),
            "sensor.price_mwh": state("100", "EUR/MWh"),
            "sensor.price_unknown": state("0.05", "USD"),
        })
        self.assertEqual(live_power(source, "sensor.pv", NOW).value, 2.2)
        self.assertEqual(live_power(source, "sensor.home", NOW).value, 1.2)
        self.assertEqual(live_power(source, "sensor.grid", NOW, signed=True).value, -1.2)
        self.assertEqual(live_power(source, "sensor.surplus", NOW).value, 0)
        self.assertEqual(live_power(source, "sensor.grid", NOW).quality, "invalid")
        self.assertEqual(live_power(source, "sensor.negative_pv", NOW).quality, "invalid")
        self.assertEqual(live_power(source, "sensor.energy_not_power", NOW).reason,
                         "POWER_UNIT_UNVERIFIED")
        self.assertEqual(live_power(source, "sensor.stale", NOW).quality, "stale")
        price, currency = live_price(source, "sensor.price", NOW)
        self.assertEqual((price.value, currency), (-0.11, "EUR"))
        eur_mwh, currency = live_price(source, "sensor.price_mwh", NOW)
        self.assertEqual((eur_mwh.value, currency), (0.1, "EUR"))
        invalid, currency = live_price(source, "sensor.price_unknown", NOW)
        self.assertEqual(invalid.quality, "invalid")
        self.assertIsNone(currency)

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

    def test_fresh_native_source_can_confirm_unchanged_semantic_cable(self):
        stale = NOW - timedelta(hours=2)
        native = state("Available", observed=stale)
        native.last_reported = NOW
        semantic = state(
            "disconnected", observed=stale,
            source_type="native_charger_status",
            source_entity_id="sensor.native_connector",
            raw_status="Available",
        )
        src = hass({
            "sensor.native_connector": native,
            "sensor.semantic_cable": semantic,
        })
        observed = connection(src, "sensor.semantic_cable", NOW)
        self.assertEqual(observed.quality, "ok")
        self.assertIs(observed.value, False)
        self.assertEqual(observed.observed_at, NOW)
        # The semantic data must still match the real native report.
        native.state = "Charging"
        mismatch = connection(src, "sensor.semantic_cable", NOW)
        self.assertEqual(mismatch.reason, "BRIDGE_SOURCE_STATUS_DIVERGED")
        self.assertIsNone(mismatch.value)
        # A stopped native heartbeat never makes the cable fresh by proxy.
        native.state = "Available"
        native.last_reported = NOW - timedelta(hours=1)
        self.assertEqual(connection(src, "sensor.semantic_cable", NOW).quality,
                         "stale")
        # No manual utility presence/helper may masquerade as native evidence.
        semantic.attributes["source_type"] = "manual_confirmation"
        native.last_reported = NOW
        self.assertEqual(connection(src, "sensor.semantic_cable", NOW).quality,
                         "stale")

    def test_switch_on_is_not_physical_connection(self):
        obj = hass({
            "switch.plug": state("on"),
            "binary_sensor.cable": state("on"),
            "sensor.cable": state("connected"),
        })
        self.assertIsNone(connection(obj, "switch.plug", NOW).value)
        self.assertTrue(connection(obj, "binary_sensor.cable", NOW).value)
        self.assertTrue(connection(obj, "sensor.cable", NOW).value)

    def test_explicit_native_enum_charger_connection_mapping_is_quality_gated(self):
        observations = hass({
            "sensor.charger": state("Charging"),
            "sensor.available": state("Available"),
            "sensor.other": state("Faulted"),
            "switch.fake_cable": state("on"),
            "sensor.stale": state("Charging", observed=NOW - timedelta(hours=1)),
        })
        selected = ["Charging", "Preparing", "SuspendedEVSE"]
        empty = ["Available"]
        self.assertIs(connection(
            observations, "sensor.charger", NOW,
            connected_states=selected, disconnected_states=empty,
        ).value, True)
        self.assertIs(connection(
            observations, "sensor.available", NOW,
            connected_states=selected, disconnected_states=empty,
        ).value, False)
        unknown = connection(
            observations, "sensor.other", NOW,
            connected_states=selected, disconnected_states=empty,
        )
        self.assertIsNone(unknown.value)
        self.assertEqual(unknown.reason, "CONNECTION_AMBIGUOUS")
        self.assertEqual(connection(
            observations, "sensor.stale", NOW,
            connected_states=selected, disconnected_states=empty,
        ).quality, "stale")
        denied = connection(
            observations, "switch.fake_cable", NOW,
            connected_states=["on"], disconnected_states=["off"],
        )
        self.assertEqual(denied.reason, "CONNECTION_MAPPING_INVALID")
        overlap = connection(
            observations, "sensor.charger", NOW,
            connected_states=["charging"], disconnected_states=["CHARGING"],
        )
        self.assertEqual(overlap.reason, "CONNECTION_MAPPING_AMBIGUOUS")

    def test_session_status_is_only_read_only_source_evidence(self):
        obj = hass({
            "sensor.session": state("Charging"),
            "binary_sensor.session": state("on"),
            "sensor.invalid": state("1"),
            "sensor.stale": state(
                "paused", observed=NOW - timedelta(hours=1)
            ),
        })
        self.assertEqual(session_status(obj, "sensor.session", NOW).value,
                         "charging")
        self.assertEqual(session_status(obj, "binary_sensor.session", NOW).value,
                         "active")
        self.assertIsNone(session_status(obj, "sensor.invalid", NOW).value)
        self.assertEqual(session_status(obj, "sensor.invalid", NOW).quality,
                         "invalid")
        self.assertEqual(session_status(obj, "sensor.stale", NOW).quality,
                         "stale")
        self.assertEqual(session_status(obj, None, NOW).quality, "unknown")
        # Session-active is not physical cable identity, measured energy or
        # a permission to actuate a provider-owned EVSE.
        self.assertIsNone(connection(obj, "sensor.session", NOW).value)

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

    def test_native_spot_price_intervals_work_without_template_or_robotix_packages(self):
        """Provider-owned raw intervals qualify Economy, never all-in billing."""
        raw = [
            {"start": NOW.isoformat(),
             "end": (NOW + timedelta(minutes=15)).isoformat(),
             "value": -0.03},
            {"start": (NOW + timedelta(minutes=15)).isoformat(),
             "end": (NOW + timedelta(minutes=30)).isoformat(),
             "value": 0.08},
        ]
        obj = hass({
            "sensor.native_prices": state(
                "-0.03", unit="EUR/kWh", raw_today=raw, raw_tomorrow=[],
            ),
            "sensor.wholesale": state(
                "-30", unit="EUR/MWh", raw_today=raw, raw_tomorrow=[],
            ),
        })
        values, status = intervals(obj, "sensor.native_prices", "price", NOW)
        self.assertEqual(status, "OK")
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0].effective_price_per_kwh, -0.03)
        self.assertEqual(values[0].basis, "spot")
        self.assertEqual(values[0].currency, "EUR")
        mwh, status = intervals(obj, "sensor.wholesale", "price", NOW)
        self.assertEqual(status, "OK")
        self.assertAlmostEqual(mwh[0].effective_price_per_kwh, -0.00003)
        self.assertEqual(mwh[0].basis, "spot")

    def test_native_spot_never_infers_currency_unit_or_rewrites_bad_intervals(self):
        row = {"start": NOW.isoformat(),
               "end": (NOW + timedelta(minutes=15)).isoformat(),
               "value": 0.1}
        sources = hass({
            "sensor.missing_unit": state("0.1", raw_today=[row]),
            "sensor.wrong_unit": state("0.1", unit="EUR", raw_today=[row]),
            "sensor.mismatch": state(
                "0.1", unit="EUR/kWh", currency="USD", raw_today=[row]
            ),
            "sensor.overlap": state(
                "0.1", unit="EUR/kWh", raw_today=[row, row]
            ),
            "sensor.stale": state(
                "0.1", unit="EUR/kWh", raw_today=[row],
                observed=NOW - timedelta(hours=25),
            ),
            "sensor.no_future": state(
                "0.1", unit="EUR/kWh", raw_today=[{
                    "start": (NOW - timedelta(hours=2)).isoformat(),
                    "end": (NOW - timedelta(hours=1)).isoformat(), "value": 0.1,
                }],
            ),
        })
        for entity in ("missing_unit", "wrong_unit", "mismatch"):
            self.assertEqual(
                intervals(sources, f"sensor.{entity}", "price", NOW)[1],
                "INTERVAL_CURRENCY_OR_UNIT_UNVERIFIED",
            )
        self.assertEqual(
            intervals(sources, "sensor.overlap", "price", NOW)[1],
            "INTERVAL_OVERLAP",
        )
        self.assertEqual(
            intervals(sources, "sensor.stale", "price", NOW)[1],
            "SOURCE_STALE",
        )
        self.assertEqual(
            intervals(sources, "sensor.no_future", "price", NOW)[1],
            "INTERVAL_SOURCE_EXPIRED",
        )

    def test_native_spot_dst_25_hour_day_has_no_phantom_local_time(self):
        from zoneinfo import ZoneInfo

        brussels = ZoneInfo("Europe/Brussels")
        beginning = datetime(2026, 10, 24, 22, tzinfo=timezone.utc)
        rows = [{
            "start": (beginning + timedelta(hours=i)).astimezone(brussels),
            "end": (beginning + timedelta(hours=i + 1)).astimezone(brussels),
            "value": 0.1 if i % 2 else -0.01,
        } for i in range(25)]
        at = beginning + timedelta(hours=7)
        source = hass({"sensor.native": state(
            "0.1", unit="EUR/kWh", observed=at,
            raw_today=rows,
        )})
        slots, quality = intervals(source, "sensor.native", "price", at)
        self.assertEqual(quality, "OK")
        self.assertEqual(len(slots), 25)
        self.assertEqual(slots[0].start.utcoffset(), timedelta(0))
        self.assertEqual(slots[-1].end, beginning + timedelta(hours=25))
        self.assertEqual(slots[0].basis, "spot")

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
