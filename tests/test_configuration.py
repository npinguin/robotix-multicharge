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

from multicharge_configuration_tests.configuration import (  # noqa: E402 - imported after isolated pure-module bootstrap
    default_configuration, effective_configuration, validate_configuration
)


class ConfigurationTests(unittest.TestCase):
    def test_plan_display_preferences_cannot_change_physical_runtime(self):
        from multicharge_configuration_tests.configuration import (
            is_plan_presentation_only_change, apply_settings_change,
        )
        original = validate_configuration(default_configuration())
        visual = apply_settings_change(
            original, "controller", "home", {
                "plan_label_mode": "charger",
                "plan_color_by": "charger",
                "show_indicative_forecast": False,
            }
        )
        self.assertTrue(is_plan_presentation_only_change(original, visual))
        self.assertFalse(is_plan_presentation_only_change(original, original))
        physical = apply_settings_change(
            visual, "controller", "home", {"mode": "Economy"}
        )
        self.assertFalse(is_plan_presentation_only_change(visual, physical))
        self.assertFalse(is_plan_presentation_only_change(original, physical))

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

    def test_atomic_preferences_and_stable_revision(self):
        from multicharge_configuration_tests.configuration import (
            apply_settings_change, configuration_revision,
        )
        cfg = validate_configuration(default_configuration())
        revised = apply_settings_change(cfg, "controller", "home", {
            "mode": "Economy", "max_power_kw": 7.4,
        })
        self.assertEqual(cfg["controller"]["mode"], "Off")
        self.assertEqual(revised["controller"]["mode"], "Economy")
        self.assertNotEqual(configuration_revision(cfg), configuration_revision(revised))
        self.assertEqual(configuration_revision(revised),
                         configuration_revision(validate_configuration(revised)))

    def test_preferences_cannot_commission_or_replace_physical_writer(self):
        from multicharge_configuration_tests.configuration import apply_settings_change
        cfg = validate_configuration(default_configuration())
        for field in ("physical_commissioned", "control_owner", "control_entity"):
            with self.assertRaises(ValueError):
                apply_settings_change(cfg, "charger", "drive", {field: True})
        with self.assertRaises(ValueError):
            apply_settings_change(cfg, "controller", "home", {"unknown": 7})

    def test_asset_preference_lifecycle_requires_integrity(self):
        from multicharge_configuration_tests.configuration import apply_settings_change
        cfg = validate_configuration(default_configuration())
        created = apply_settings_change(cfg, "asset", "guest", {
            "name": "Guest", "kind": "car", "requested_kwh": 3.0
        }, "create")
        self.assertEqual(created["assets"][0]["id"], "guest")
        revised = apply_settings_change(created, "asset", "guest", {
            "requested_kwh": None, "requested_duration_minutes": 45,
        })
        self.assertNotIn("requested_kwh", revised["assets"][0])
        self.assertEqual(revised["assets"][0]["requested_duration_minutes"], 45)
        with self.assertRaises(ValueError):
            apply_settings_change(revised, "asset", "guest", {"name": ""})
        self.assertEqual(apply_settings_change(revised, "asset", "guest",
                                               {"name": "placeholder"}, "delete")["assets"], [])

    def test_guest_expiry_requires_timezone_and_is_not_ignored(self):
        cfg = default_configuration()
        cfg["assets"] = [{"id": "guest", "name": "Guest", "kind": "car",
                          "temporary": True, "expires_at": "2026-11-23T15:00:00+01:00",
                          "requested_kwh": 2}]
        normalized = validate_configuration(cfg)
        self.assertTrue(normalized["assets"][0]["temporary"])
        self.assertEqual(normalized["assets"][0]["expires_at"],
                         "2026-11-23T15:00:00+01:00")
        cfg["assets"][0].pop("expires_at")
        with self.assertRaisesRegex(ValueError, "expiry required"):
            validate_configuration(cfg)
        cfg["assets"][0]["expires_at"] = "2026-11-23T15:00:00"
        with self.assertRaisesRegex(ValueError, "timezone required"):
            validate_configuration(cfg)

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

    def test_conflicting_power_sources_fail_closed(self):
        cfg = default_configuration()
        cfg["controller"]["site_power_entity"] = "sensor.site_power"
        cfg["controller"]["binding_entity"] = "sensor.energy_envelope"
        with self.assertRaisesRegex(ValueError, "one authoritative"):
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

    def test_recurrence_requires_a_real_ready_by_anchor(self):
        cfg = default_configuration()
        cfg["assets"] = [{"id": "guest", "name": "Guest",
                          "ready_by_repeat": "weekly"}]
        with self.assertRaisesRegex(ValueError, "anchor required"):
            validate_configuration(cfg)

    def test_ready_by_requires_aware_instant(self):
        cfg = default_configuration()
        cfg["assets"] = [{
            "id": "guest", "name": "Guest", "requested_kwh": 3,
            "ready_by": "2026-12-01T08:00:00",
        }]
        with self.assertRaises(ValueError):
            validate_configuration(cfg)


    def test_owned_adjustable_charger_requires_verified_distinct_readback(self):
        cfg = default_configuration()
        cfg["assets"] = [{"id": "car", "name": "Car", "requested_kwh": 2}]
        cfg["controller"]["phase_limits_a"] = {"L1": 16, "L2": 16, "L3": 16}
        c = {"id": "drive", "name": "Drive", "kind": "variable_current",
             "rated_power_kw": 11, "asset": "car", "control_owner": "multicharge",
             "control_entity": "switch.drive", "connected_entity": "binary_sensor.plug",
             "power_entity": "sensor.power", "phase_count": 3,
             "phase_ids": ["L1", "L2", "L3"], "voltage_v": 230,
             "min_current_a": 6, "max_current_a": 16, "current_step_a": 1,
             "circuit_id": "drive", "circuit_limit_a": 16,
             "current_control_entity": "number.charge_limit",
             "current_readback_entity": "sensor.actual_current"}
        cfg["chargers"] = [c]
        self.assertEqual(validate_configuration(cfg)["chargers"][0]["phase_ids"],
                         ["L1", "L2", "L3"])
        c["current_readback_entity"] = "number.charge_limit"
        with self.assertRaisesRegex(ValueError, "independent current sensor"):
            validate_configuration(cfg)

    def test_phase_circuit_conflicts_are_rejected(self):
        cfg = default_configuration()
        cfg["controller"]["phase_limits_a"] = {"L1": 16}
        cfg["chargers"] = [
            {"id": "a", "name": "A", "kind": "on_off", "rated_power_kw": 2,
             "phase_count": 1, "phase_ids": ["L1"], "voltage_v": 230,
             "fixed_current_a": 10, "circuit_id": "common", "circuit_limit_a": 16},
            {"id": "b", "name": "B", "kind": "on_off", "rated_power_kw": 2,
             "phase_count": 1, "phase_ids": ["L1"], "voltage_v": 230,
             "fixed_current_a": 10, "circuit_id": "common", "circuit_limit_a": 10},
        ]
        with self.assertRaisesRegex(ValueError, "sharing a circuit"):
            validate_configuration(cfg)

    def test_forged_yaml_extra_keys_fails(self):
        cfg = default_configuration()
        cfg["controller"]["private_writer"] = True
        with self.assertRaises(ValueError):
            validate_configuration(cfg)


if __name__ == "__main__":
    unittest.main()
