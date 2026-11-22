"""Runtime observation and plan behavior with injected native HA states."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

PKG = Path(__file__).resolve().parents[1] / "custom_components" / "robotix_multicharge"
ROOT = "multicharge_runtime_test"
package = type(sys)(ROOT)
package.__path__ = [str(PKG)]
sys.modules[ROOT] = package
for name in ("domain", "contracts", "configuration", "planner",
             "source_evidence", "runtime"):
    spec = importlib.util.spec_from_file_location(f"{ROOT}.{name}", PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from multicharge_runtime_test.configuration import default_configuration, validate_configuration  # noqa: E402 - imported after isolated pure-module bootstrap
from multicharge_runtime_test.runtime import MultiChargeRuntime  # noqa: E402 - imported after isolated pure-module bootstrap

NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)


def state(value, unit=None):
    return SimpleNamespace(
        state=value,
        attributes={"unit_of_measurement": unit} if unit else {},
        last_updated=NOW,
    )


def sample():
    cfg = default_configuration()
    cfg["controller"].update(max_power_kw=4, mode="Ready By")
    cfg["assets"] = [{
        "id": "car", "name": "Car", "soc_entity": "sensor.soc",
        "target_soc": 80, "capacity_kwh": 20, "charge_efficiency": 1,
        "ready_by": (NOW + timedelta(hours=2)).isoformat(),
    }]
    cfg["chargers"] = [{
        "id": "drive", "name": "Drive", "kind": "on_off", "rated_power_kw": 4,
        "asset": "car", "connected_entity": "binary_sensor.cable",
        "power_entity": "sensor.power",
    }]
    return validate_configuration(cfg)


class RuntimeTests(unittest.TestCase):
    def test_real_source_soc_produces_read_only_plan(self):
        data = {
            "sensor.soc": state("50", "%"),
            "sensor.power": state("2300", "W"),
            "binary_sensor.cable": state("on"),
        }
        hass = SimpleNamespace(states=SimpleNamespace(get=data.get))
        rt = MultiChargeRuntime(hass, sample())
        rt.refresh(NOW)
        self.assertEqual(len(rt.assessment.plan.slots), 6)
        self.assertEqual(rt.observations["chargers"]["drive"]["power_kw"].value, 2.3)
        self.assertEqual(rt.summary()["status"], "proposed")
        self.assertFalse(rt.summary()["physical_actuation_authorized"])

    def test_unassigned_asset_still_exposes_source_observation(self):
        cfg = sample()
        cfg["assets"].append({
            "id": "bike", "name": "Bike", "soc_entity": "sensor.bike",
        })
        readings = {
            "sensor.soc": state("50", "%"),
            "sensor.bike": state("0", "%"),
            "binary_sensor.cable": state("on"),
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=readings.get)), cfg
        )
        rt.refresh(NOW)
        self.assertEqual(rt.observations["assets"]["bike"]["soc"].value, 0)
        self.assertEqual(rt.observations["assets"]["bike"]["soc"].quality, "ok")

    def test_no_connection_never_proposes_charging(self):
        cfg = sample()
        rt = MultiChargeRuntime(SimpleNamespace(
            states=SimpleNamespace(get=lambda _: None)), cfg)
        rt.refresh(NOW)
        self.assertEqual(rt.excluded["drive"], "CONNECTION_UNCONFIRMED")
        self.assertEqual(rt.assessment.plan.slots, ())

    def test_no_soc_with_explicit_energy_is_supported(self):
        cfg = default_configuration()
        cfg["controller"].update(max_power_kw=2, mode="Ready By")
        cfg["assets"] = [{
            "id": "bike", "name": "Bike", "requested_kwh": 1,
            "ready_by": (NOW + timedelta(hours=1)).isoformat(),
        }]
        cfg["chargers"] = [{
            "id": "plug", "name": "Plug", "kind": "on_off", "rated_power_kw": 2,
            "asset": "bike", "connected_entity": "sensor.plug_connected",
        }]
        data = {"sensor.plug_connected": state("connected")}
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=data.get)),
            validate_configuration(cfg),
        )
        rt.refresh(NOW)
        self.assertEqual(len(rt.assessment.plan.slots), 2)
        self.assertEqual(rt.assessment.proposed_kwh["plug"], 1)

    def test_bounded_plan_read_does_not_fake_actual_energy(self):
        data = {
            "sensor.soc": state("50", "%"),
            "sensor.power": state("2300", "W"),
            "binary_sensor.cable": state("on"),
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=data.get)), sample()
        )
        rt.refresh(NOW)
        result = rt.read_plan(NOW, NOW + timedelta(hours=2), charger_id="drive")
        self.assertEqual(result["schema_major"], 1)
        self.assertEqual(result["timezone"], "UTC")
        self.assertIn("binding_quality", result["quality"])
        self.assertEqual(
            result["valid_until"],
            (NOW + timedelta(minutes=2)).isoformat(),
        )
        self.assertEqual(len(result["slots"]), 6)
        self.assertIsNone(result["slots"][0]["actual_power_kw"])
        self.assertIsNone(result["slots"][0]["accepted_power_kw"])
        self.assertFalse(result["physical_actuation_authorized"])

    def test_plan_read_rejects_unknown_and_oversized_ranges(self):
        rt = MultiChargeRuntime(None, sample())
        with self.assertRaises(ValueError):
            rt.read_plan(NOW, NOW + timedelta(hours=49))
        with self.assertRaises(ValueError):
            rt.read_plan(NOW.replace(tzinfo=None), NOW + timedelta(hours=1))
        with self.assertRaises(ValueError):
            rt.read_plan(NOW, NOW + timedelta(hours=1), charger_id="not-real")

    def test_selected_site_capacity_never_silently_ignored(self):
        cfg = sample()
        cfg["controller"]["site_power_entity"] = "sensor.available"
        readings = {
            "sensor.soc": state("50", "%"),
            "binary_sensor.cable": state("on"),
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=readings.get)), cfg
        )
        rt.refresh(NOW)
        self.assertEqual(rt.assessment.plan.slots, ())
        self.assertEqual(rt.excluded["controller"], "BINDING_CAPACITY_UNAVAILABLE")

    def test_selected_but_unavailable_ems_never_becomes_unlimited(self):
        cfg = sample()
        cfg["controller"]["binding_entity"] = "sensor.supervision"
        # The runtime works on already-validated structured configuration.
        data = {
            "sensor.soc": state("50", "%"),
            "binary_sensor.cable": state("on"),
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg
        )
        rt.refresh(NOW)
        self.assertEqual(rt.assessment.plan.slots, ())
        self.assertEqual(rt.excluded["controller"], "BINDING_CAPACITY_UNAVAILABLE")

    def test_no_silent_energization_after_unload(self):
        rt = MultiChargeRuntime(None, sample())
        events = []
        rt.set_unsubscribe(lambda: events.append("unsubscribed"))
        rt.subscribe(lambda: events.append("notified"))
        rt.stop()
        self.assertEqual(events, ["unsubscribed"])
        self.assertEqual(rt._listeners, set())


if __name__ == "__main__":
    unittest.main()
