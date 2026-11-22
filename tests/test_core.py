"""Source-level tests for the three concepts and safe contract semantics."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "custom_components" / "robotix_multicharge"
ROOT = "multicharge_test_core"
package = type(sys)(ROOT)
package.__path__ = [str(PKG)]
sys.modules[ROOT] = package
for name in ("domain", "contracts", "interfaces"):
    spec = importlib.util.spec_from_file_location(f"{ROOT}.{name}", PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from multicharge_test_core.domain import ChargeableAsset, Charger, ChargeController  # noqa: E402 - imported after isolated pure-module bootstrap
from multicharge_test_core.contracts import (  # noqa: E402 - imported after isolated pure-module bootstrap
    PowerEnvelope, PowerLimitSlot, PriceSlot, ChargePlan, ChargeDemand,
    AssetObservation, ChargerObservation, CommandOutcome,
)

NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)


class ConceptsTest(unittest.TestCase):
    def test_bicycle_and_car_share_generic_asset(self):
        self.assertEqual(ChargeableAsset(uid="a", name="City bike", kind="bicycle").kind, "bicycle")
        self.assertIsNone(ChargeableAsset(uid="b", name="Family car").target_soc_pct)

    def test_soc_zero_is_valid_but_unknown_remains_none(self):
        self.assertEqual(ChargeableAsset(uid="a", name="Bike", target_soc_pct=0).target_soc_pct, 0)
        with self.assertRaises(ValueError):
            ChargeableAsset(uid="a", name="Bike", target_soc_pct=120)

    def test_no_synthetic_charger_capability(self):
        with self.assertRaises(ValueError):
            Charger(uid="c", name="Socket", controller_uid="x", control_kind="variable_current", rated_power_kw=2)
        with self.assertRaises(ValueError):
            Charger(uid="c", name="Socket", controller_uid="x", control_kind="on_off", rated_power_kw=2, max_current_a=10)
        self.assertEqual(Charger(uid="c", name="Socket", controller_uid="x", control_kind="on_off", rated_power_kw=2).control_kind, "on_off")

    def test_controller_limits(self):
        with self.assertRaises(ValueError):
            ChargeController(uid="x", name="Home", max_parallel=0)
        with self.assertRaises(ValueError):
            ChargeController(uid="x", name="Home", max_group_power_kw=-1)

    def test_price_can_be_negative(self):
        self.assertEqual(PriceSlot(NOW, NOW + timedelta(minutes=15), -0.02, "USD").effective_price_per_kwh, -0.02)
        with self.assertRaises(ValueError):
            PriceSlot(NOW, NOW, 0, "EUR")

    def test_binding_supervision_expiry_and_explicit_zero(self):
        slot = PowerLimitSlot(NOW, NOW + timedelta(minutes=15), 0)
        env = PowerEnvelope("ems", "rev1", NOW, NOW + timedelta(hours=1), "binding", (slot,))
        self.assertTrue(env.current(NOW))
        self.assertFalse(env.current(NOW + timedelta(hours=1)))
        self.assertEqual(env.slots[0].max_charging_kw, 0)
        with self.assertRaises(ValueError):
            PowerLimitSlot(NOW, NOW + timedelta(minutes=15), -0.1)

    def test_plan_is_proposal_not_actual(self):
        plan = ChargePlan("home", "r1", NOW, "proposed", ())
        self.assertEqual(plan.status, "proposed")
        self.assertEqual(plan.slots, ())
        with self.assertRaises(ValueError):
            ChargePlan("home", "r1", NOW.replace(tzinfo=None), "accepted", ())


    def test_energy_and_duration_not_conflated(self):
        self.assertEqual(
            ChargeDemand("asset", "charger", 4.0, NOW).remaining_grid_kwh, 4.0
        )
        self.assertEqual(
            ChargeDemand("guest", None, None, NOW, remaining_duration_minutes=45)
            .remaining_duration_minutes, 45
        )
        with self.assertRaises(ValueError):
            ChargeDemand("guest", None, 4.0, NOW, remaining_duration_minutes=45)
        with self.assertRaises(ValueError):
            ChargeDemand("guest", None, None, NOW, remaining_duration_minutes=0)

    def test_soC_source_quality_and_zero_are_explicit(self):
        unknown = AssetObservation(asset_uid="car", soc_pct=None, observed_at=None, quality="unknown")
        self.assertIsNone(unknown.soc_pct)
        real_zero = AssetObservation(
            asset_uid="car", soc_pct=0, observed_at=NOW, quality="ok", provenance="oem"
        )
        self.assertEqual(real_zero.soc_pct, 0)
        with self.assertRaises(ValueError):
            AssetObservation(asset_uid="car", soc_pct=90, observed_at=NOW, quality="ok")
        with self.assertRaises(ValueError):
            AssetObservation(asset_uid="car", soc_pct=101, observed_at=NOW, quality="ok", provenance="oem")

    def test_physical_state_and_command_outcome_are_separate(self):
        reading = ChargerObservation(
            charger_uid="plug", observed_at=NOW, quality="ok",
            connected="unknown", charging="no", actual_power_kw=0
        )
        self.assertEqual(reading.actual_power_kw, 0)
        with self.assertRaises(ValueError):
            ChargerObservation(charger_uid="plug", observed_at=NOW, quality="stale", charging="yes")
        with self.assertRaises(ValueError):
            ChargerObservation(charger_uid="plug", observed_at=None, quality="ok", charging="yes")
        pending = CommandOutcome(
            charger_uid="plug", request_id="req-1", status="accepted_unconfirmed"
        )
        self.assertNotEqual(pending.status, "confirmed")
        with self.assertRaises(ValueError):
            CommandOutcome(charger_uid="plug", request_id="req-1", status="confirmed")
        confirmed = CommandOutcome(
            charger_uid="plug", request_id="req-1", status="confirmed", readback_at=NOW
        )
        self.assertEqual(confirmed.status, "confirmed")


if __name__ == "__main__":
    unittest.main()
