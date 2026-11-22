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

    def test_forged_yaml_extra_keys_fails(self):
        cfg = default_configuration()
        cfg["controller"]["private_writer"] = True
        with self.assertRaises(ValueError):
            validate_configuration(cfg)


if __name__ == "__main__":
    unittest.main()
