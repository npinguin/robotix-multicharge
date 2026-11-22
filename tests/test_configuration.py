"""Pure validation and configuration-contract regression without HA runtime."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "custom_components" / "robotix_multicharge"
ROOT = "multicharge_configuration_tests"
package = type(sys)(ROOT)
package.__path__ = [str(PKG)]
sys.modules[ROOT] = package
for name in ("domain", "configuration"):
    spec = importlib.util.spec_from_file_location(f"{ROOT}.{name}", PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from multicharge_configuration_tests.configuration import (
    default_configuration, effective_configuration, validate_configuration
)


class ConfigurationTests(unittest.TestCase):
    def test_default_is_valid(self):
        self.assertEqual(validate_configuration(default_configuration())["controller"]["id"], "home")

    def test_car_bicycle_and_different_chargers(self):
        cfg = default_configuration()
        cfg["assets"] = [
            {"id": "car", "name": "Car", "kind": "car", "target_soc": 80},
            {"id": "bike", "name": "Bike", "kind": "bicycle"},
        ]
        cfg["chargers"] = [
            {"id": "drive", "name": "Driveway", "kind": "variable_current",
             "rated_power_kw": 11, "min_current_a": 6, "max_current_a": 16,
             "power_entity": "sensor.drive_power", "asset": "car"},
            {"id": "plug", "name": "Bike plug", "kind": "on_off",
             "rated_power_kw": 0.5, "asset": "bike"},
        ]
        normalized = validate_configuration(cfg)
        self.assertEqual(len(normalized["chargers"]), 2)

    def test_no_guessed_entities(self):
        cfg = default_configuration()
        cfg["assets"] = [{"id": "car", "name": "Car", "soc_entity": "car-battery"}]
        with self.assertRaises(ValueError):
            validate_configuration(cfg)

    def test_unknown_asset_and_duplicate(self):
        cfg = default_configuration()
        cfg["chargers"] = [
            {"id": "a", "name": "Charger", "kind": "on_off",
             "rated_power_kw": 1, "asset": "unknown"}
        ]
        with self.assertRaises(ValueError):
            validate_configuration(cfg)
        cfg["chargers"][0].pop("asset")
        cfg["chargers"].append(dict(cfg["chargers"][0]))
        with self.assertRaises(ValueError):
            validate_configuration(cfg)

    def test_invalid_current_capability_rejected(self):
        cfg = default_configuration()
        cfg["chargers"] = [
            {"id": "a", "name": "A", "kind": "variable_current", "rated_power_kw": 11}
        ]
        with self.assertRaises(ValueError):
            validate_configuration(cfg)

    def test_unknown_and_zero_are_different(self):
        cfg = default_configuration()
        cfg["assets"] = [{"id": "bike", "name": "Bike", "target_soc": 0}]
        result = validate_configuration(cfg)["assets"][0]
        self.assertEqual(result["target_soc"], 0)
        self.assertNotIn("capacity_kwh", result)

    def test_options_have_single_config_authority(self):
        class Entry:
            data = {"configuration": default_configuration()}
            options = {"configuration": default_configuration("Edited via UI")}
        self.assertEqual(effective_configuration(Entry())["controller"]["name"], "Edited via UI")

    def test_two_chargers_cannot_share_a_physical_writer(self):
        cfg = default_configuration()
        cfg["chargers"] = [
            {"id": "white", "name": "White", "kind": "on_off",
             "rated_power_kw": 7, "control_entity": "switch.garage"},
            {"id": "black", "name": "Black", "kind": "on_off",
             "rated_power_kw": 7, "control_entity": "switch.garage"},
        ]
        with self.assertRaises(ValueError):
            validate_configuration(cfg)

    def test_two_chargers_cannot_double_count_one_energy_meter(self):
        cfg = default_configuration()
        cfg["chargers"] = [
            {"id": "white", "name": "White", "kind": "on_off",
             "rated_power_kw": 7, "energy_entity": "sensor.energy"},
            {"id": "black", "name": "Black", "kind": "on_off",
             "rated_power_kw": 7, "energy_entity": "sensor.energy"},
        ]
        with self.assertRaises(ValueError):
            validate_configuration(cfg)

    def test_binding_source_is_explicitly_preserved(self):
        cfg = default_configuration()
        cfg["controller"]["binding_entity"] = "sensor.site_envelope"
        cfg["controller"]["mode"] = "Solar"
        value = validate_configuration(cfg)["controller"]
        self.assertEqual(value["binding_entity"], "sensor.site_envelope")
        self.assertEqual(value["mode"], "Solar")

    def test_explicit_duration_and_energy_cannot_be_combined(self):
        cfg = default_configuration()
        cfg["assets"] = [{
            "id": "guest", "name": "Guest", "requested_kwh": 3.0,
            "requested_duration_minutes": 60,
        }]
        with self.assertRaises(ValueError):
            validate_configuration(cfg)

    def test_ready_by_requires_aware_instant(self):
        cfg = default_configuration()
        cfg["assets"] = [{
            "id": "guest", "name": "Guest", "requested_kwh": 3,
            "ready_by": "2026-12-01T08:00:00",
        }]
        with self.assertRaises(ValueError):
            validate_configuration(cfg)

    def test_forged_yaml_extra_keys_fails(self):
        cfg = default_configuration()
        cfg["controller"]["private_writer"] = True
        with self.assertRaises(ValueError):
            validate_configuration(cfg)


if __name__ == "__main__":
    unittest.main()
