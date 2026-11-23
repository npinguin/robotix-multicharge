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
    default_configuration, effective_configuration, validate_configuration,
    normalize_expert_json, prepare_expert_yaml_revision,
)


class ConfigurationTests(unittest.TestCase):
    def test_energy_dashboard_suggestions_reuse_native_power_and_price_only(self):
        from multicharge_configuration_tests.configuration import (
            energy_dashboard_suggestions,
        )
        prefs = {"energy_sources": [
            {"type": "solar", "stat_energy_from": "sensor.solar_total_kwh",
             "stat_rate": "sensor.solar_instant_w"},
            {"type": "grid", "stat_energy_from": "sensor.grid_import_kwh",
             "stat_energy_to": "sensor.grid_export_kwh",
             "stat_rate": "sensor.grid_net_w",
             "entity_energy_price": "sensor.import_price",
             "entity_energy_price_export": "sensor.export_price"},
            {"type": "battery", "stat_rate": "sensor.battery_w"},
        ], "device_consumption": [
            {"stat_consumption": "sensor.fridge_kwh",
             "stat_rate": "sensor.fridge_w"},
        ]}
        self.assertEqual(energy_dashboard_suggestions(prefs), {
            "solar_power_entity": "sensor.solar_instant_w",
            "grid_power_entity": "sensor.grid_net_w",
            "current_price_entity": "sensor.import_price",
            "export_price_entity": "sensor.export_price",
        })
        # It is not safe to mistake a device for whole-home consumption,
        # battery discharge for solar export, or energy kWh for live kW.
        for excluded in ("home_power_entity", "solar_surplus_entity",
                         "solar_entity", "price_entity"):
            self.assertNotIn(excluded, energy_dashboard_suggestions(prefs))
        self.assertEqual(energy_dashboard_suggestions(None), {})
        prefs["energy_sources"].append({
            "type": "grid", "stat_rate": "sensor.other_net_power",
            "entity_energy_price": "sensor.other_price",
        })
        ambiguous = energy_dashboard_suggestions(prefs)
        self.assertNotIn("grid_power_entity", ambiguous)
        self.assertNotIn("current_price_entity", ambiguous)
        self.assertIn("solar_power_entity", ambiguous)

    def test_native_solar_power_and_energy_price_options_have_one_authority(self):
        from copy import deepcopy
        base = default_configuration()
        base["controller"].update({
            "solar_power_entity": "sensor.pv_power",
            "home_power_entity": "sensor.home_power",
            "grid_power_entity": "sensor.net_power",
            "current_price_entity": "sensor.electricity_price",
            "export_price_entity": "sensor.feed_in_price",
            "solar_source_kind": "grid_export",
            "grid_power_direction": "import_positive",
        })
        normalized = validate_configuration(base)
        for key in ("solar_power_entity", "home_power_entity",
                    "grid_power_entity", "current_price_entity",
                    "export_price_entity", "solar_source_kind",
                    "grid_power_direction"):
            self.assertEqual(normalized["controller"][key],
                             base["controller"][key])
        normalized["controller"]["name"] = "New home"
        self.assertEqual(
            validate_configuration(normalized)["controller"]["solar_source_kind"],
            "grid_export",
        )
        for badchange in (
            {"solar_source_kind": "unverified"},
            {"solar_source_kind": "direct_surplus"},
            {"grid_power_direction": "unknown"},
            {"grid_power_entity": "sensor.fake-kwh"},
            {"grid_power_entity": "switch.fake_grid"},
            {"solar_source_kind": "intervals"},
        ):
            bad = deepcopy(base)
            bad["controller"].update(badchange)
            with self.subTest(badchange=badchange), self.assertRaises(ValueError):
                validate_configuration(bad)

        direct = deepcopy(base)
        direct["controller"]["solar_source_kind"] = "direct_surplus"
        direct["controller"]["solar_surplus_entity"] = "sensor.surplus_w"
        self.assertEqual(
            validate_configuration(direct)["controller"]["solar_source_kind"],
            "direct_surplus",
        )

    def test_oem_soc_quality_flag_is_native_optional_and_requires_oem_sensor(self):
        from copy import deepcopy
        source = default_configuration()
        source["assets"] = [{
            "id": "vehicle", "name": "Vehicle", "kind": "car",
            "soc_entity": "sensor.vehicle_battery_pct",
            "soc_stale_entity": "binary_sensor.vehicle_data_stale",
        }]
        normalized = validate_configuration(source)
        self.assertEqual(normalized["assets"][0]["soc_stale_entity"],
                         "binary_sensor.vehicle_data_stale")
        for value in ("sensor.not_binary", "switch.not_binary", "missing"):
            bad = deepcopy(source)
            bad["assets"][0]["soc_stale_entity"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_configuration(bad)
        incomplete = deepcopy(source)
        del incomplete["assets"][0]["soc_entity"]
        with self.assertRaises(ValueError):
            validate_configuration(incomplete)

    def test_native_status_mapping_config_requires_disjoint_known_sensor_states(self):
        from copy import deepcopy

        basic = {
            "controller": {"id": "home", "name": "Home", "max_parallel": 1},
            "assets": [],
            "chargers": [{
                "id": "evse", "name": "EVSE", "kind": "on_off",
                "rated_power_kw": 3.6, "control_entity": "switch.evse",
                "connected_entity": "sensor.evse_status",
                "connected_states": ["Charging", "Preparing"],
                "disconnected_states": ["Available"],
            }],
        }
        resolved = validate_configuration(basic)
        self.assertEqual(resolved["chargers"][0]["connected_states"],
                         ["charging", "preparing"])
        self.assertEqual(resolved["chargers"][0]["disconnected_states"],
                         ["available"])
        for changes in (
            {"connected_states": ["charging", "CHARGING"]},
            {"connected_states": ["Available"]},
            {"disconnected_states": []},
            {"connected_states": [""]},
            {"connected_entity": "switch.evse"},
        ):
            bad = deepcopy(basic)
            bad["chargers"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_configuration(bad)
        missing = deepcopy(basic)
        del missing["chargers"][0]["disconnected_states"]
        with self.assertRaises(ValueError):
            validate_configuration(missing)

        expert = normalize_expert_json({
            "Controller": {"ID": "home", "Name": "Home"},
            "Charger": [{
                "Name": "EVSE",
                "Charging-startstop-entity": "switch.evse",
                "Charging-connected-sensor": "sensor.evse_status",
                "Charging-connected-states": ["Charging"],
                "Charging-disconnected-states": ["Available"],
            }],
        })
        self.assertEqual(expert["chargers"][0]["connected_states"], ["charging"])

    def test_new_car_defaults_to_80_without_overriding_existing_or_finite_goal(self):
        from multicharge_configuration_tests.configuration import (
            apply_settings_change, apply_new_asset_defaults,
        )
        base = validate_configuration(default_configuration())
        created = apply_settings_change(
            base, "asset", "new_car", {"name": "New car", "kind": "car"},
            action="create",
        )
        self.assertEqual(created["assets"][0]["target_soc"], 80)
        manually = apply_settings_change(
            created, "asset", "new_car", {"target_soc": 90}
        )
        self.assertEqual(manually["assets"][0]["target_soc"], 90)
        finite = apply_settings_change(
            base, "asset", "guest", {"name": "Guest", "kind": "car",
                                   "requested_kwh": 3.0}, action="create"
        )
        self.assertNotIn("target_soc", finite["assets"][0])
        bicycle = apply_new_asset_defaults({"name": "Bike", "kind": "bicycle"})
        self.assertNotIn("target_soc", bicycle)
        imported = default_configuration()
        imported["assets"] = [{"id": "legacy", "name": "Legacy car", "kind": "car"}]
        self.assertNotIn("target_soc", validate_configuration(imported)["assets"][0])

    def test_charger_user_power_envelope_is_hardware_bounded_and_native_editable(self):
        from multicharge_configuration_tests.configuration import (
            apply_settings_change, is_in_place_runtime_preference_change,
        )
        cfg = default_configuration()
        cfg["controller"]["phase_limits_a"] = {"L1": 16}
        cfg["chargers"] = [{
            "id": "drive", "name": "Driveway", "kind": "variable_current",
            "rated_power_kw": 3.68, "phase_count": 1, "phase_ids": ["L1"],
            "voltage_v": 230, "min_current_a": 6, "max_current_a": 16,
            "current_step_a": 1, "circuit_id": "drive", "circuit_limit_a": 16,
        }]
        original = validate_configuration(cfg)
        after_min = apply_settings_change(
            original, "charger", "drive", {"min_charging_power_kw": 2.0}
        )
        updated = apply_settings_change(
            after_min, "charger", "drive", {"max_charging_power_kw": 3.0}
        )
        self.assertTrue(is_in_place_runtime_preference_change(original, updated))
        self.assertEqual(updated["chargers"][0]["min_charging_power_kw"], 2.0)
        self.assertEqual(updated["chargers"][0]["max_charging_power_kw"], 3.0)
        for field, value in (
            ("min_charging_power_kw", 0.5),
            ("max_charging_power_kw", 4.0),
            ("min_charging_power_kw", 3.2),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                apply_settings_change(updated, "charger", "drive", {field: value})
        with self.assertRaisesRegex(ValueError, "no supported current step"):
            apply_settings_change(updated, "charger", "drive", {
                "min_charging_power_kw": 2.001,
                "max_charging_power_kw": 2.009,
            })
        fixed = default_configuration()
        fixed["chargers"] = [{"id": "plug", "name": "Plug",
                              "kind": "on_off", "rated_power_kw": 2.0,
                              "max_charging_power_kw": 1.0}]
        with self.assertRaises(ValueError):
            validate_configuration(fixed)

    def test_direct_expert_json_normalizes_charger_and_vehicle_without_wizard(self):
        """Owner's JSON fields are the complete input, not internal YAML keys."""
        data = {
            "Controller": {"Name": "Sample home", "ID": "home"},
            "Charger": [
                {"Name": "Garage A",
                 "Charging-Session-sensor": "sensor.white_session",
                 "Charging-startstop-entity": "switch.white_charge",
                 "Charging-amp-entity": "number.white_limit",
                 "ChargingAsset": "Family car"},
                {"Name": "Outdoor charger",
                 "Charging-startstop-entity": "switch.peblar_charge"},
            ],
            "ChargingAsset": [
                {"Name": "Family car", "Asset type": "Véhicule",
                 "Vehicle-Charging-startstop-entity": "switch.family_charge",
                 "Vehicle-Charging-amp-entity": "number.family_limit",
                 "Vehicle-soc-sensor": "sensor.family_soc"},
                {"Name": "Guest", "Asset type": "bicycle"},
            ],
        }
        cfg = normalize_expert_json(data)
        self.assertEqual(cfg["controller"]["name"], "Sample home")
        self.assertEqual(cfg["controller"]["mode"], "Off")
        self.assertEqual(cfg["controller"]["id"], "home")
        self.assertNotIn("max_power_kw", cfg["controller"])
        self.assertEqual(len(cfg["chargers"]), 2)
        self.assertEqual(cfg["chargers"][0]["id"], "garage_a")
        self.assertEqual(cfg["chargers"][0]["asset"], "family_car")
        self.assertEqual(cfg["chargers"][0]["session_entity"], "sensor.white_session")
        self.assertEqual(cfg["chargers"][0]["control_entity"], "switch.white_charge")
        self.assertEqual(cfg["chargers"][0]["current_control_entity"], "number.white_limit")
        self.assertEqual(cfg["chargers"][0]["control_owner"], "external")
        self.assertFalse(cfg["chargers"][0]["physical_commissioned"])
        self.assertEqual(cfg["assets"][0]["kind"], "car")
        self.assertEqual(cfg["assets"][0]["soc_entity"], "sensor.family_soc")
        self.assertEqual(cfg["assets"][0]["vehicle_control_entity"], "switch.family_charge")
        self.assertEqual(cfg["assets"][0]["vehicle_current_entity"], "number.family_limit")
        self.assertEqual(cfg["assets"][1]["kind"], "bicycle")
        self.assertNotIn("vehicle_control_entity", cfg["assets"][1])
        self.assertEqual(cfg, validate_configuration(cfg))

    def test_expert_json_single_objects_and_optional_inputs(self):
        cfg = normalize_expert_json({
            "Charger": {"Name": "Utility Plug",
                        "Charging-startstop-entity": "switch.utility"},
            "ChargingAsset": {"Name": "Second car", "Asset type": "Véhicule"},
        })
        self.assertEqual(len(cfg["chargers"]), 1)
        self.assertEqual(len(cfg["assets"]), 1)
        self.assertNotIn("soc_entity", cfg["assets"][0])
        self.assertEqual(cfg["chargers"][0]["rated_power_kw"], 3.6)
        self.assertEqual(cfg["controller"]["mode"], "Off")

    def test_expert_json_rejects_unknown_keys_and_invalid_entity_domains(self):
        sample = {"Charger": [{"Name": "Garage A",
                              "Charging-startstop-entity": "switch.white"}]}
        for field, value in (
            ("Charging-Session-sensor", "number.not_a_sensor"),
            ("Charging-amp-entity", "sensor.not_a_number"),
            ("Charging-startstop-entity", "button.not_a_switch"),
            ("unexpected", "foo"),
        ):
            row = {**sample["Charger"][0], field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                normalize_expert_json({"Charger": [row]})
        with self.assertRaisesRegex(ValueError, "required"):
            normalize_expert_json({"Charger": {"Name": "No physical control"}})
        with self.assertRaisesRegex(ValueError, "unsupported kind"):
            normalize_expert_json({
                "Charger": sample["Charger"],
                "ChargingAsset": [{"Name": "Other", "Asset type": "Spaceship"}],
            })
        with self.assertRaisesRegex(ValueError, "duplicate"):
            normalize_expert_json({
                "Charger": [sample["Charger"][0], dict(sample["Charger"][0])],
            })
        with self.assertRaisesRegex(ValueError, "another physical role"):
            normalize_expert_json({
                "Charger": sample["Charger"],
                "ChargingAsset": [{"Name": "Car",
                                   "Vehicle-Charging-startstop-entity": "switch.white"}],
            })

    def test_json_import_is_authority_not_historic_gui_settings(self):
        class Entry:
            data = {
                "source": "json",
                "configuration": normalize_expert_json({
                    "Charger": {"Name": "White",
                                "Charging-startstop-entity": "switch.white"}
                }),
            }
            options = {"configuration": default_configuration("Wizard leftovers")}
        self.assertEqual(
            effective_configuration(Entry())["chargers"][0]["name"], "White"
        )
        self.assertEqual(effective_configuration(Entry())["controller"]["mode"], "Off")

    def test_expert_json_can_prepare_full_charge_intent_and_site_budget(self):
        config = normalize_expert_json({
            "Controller": {
                "Name": "Home charging", "Mode": "Ready By",
                "Max-parallel": 2, "Max-power-kW": 7.0,
                "Phase-limits-A": {"L1": 20},
                "Plan-label-mode": "both",
                "Plan-color-by": "charger", "Show-indicative-forecast": True,
            },
            "ChargingAsset": {
                "ID": "car", "Name": "Car", "Asset type": "car",
                "Requested-kWh": 4.0, "Ready-by": "2026-11-30T08:00:00+01:00",
                "Ready-by-repeat": "daily", "Priority": 5,
                "Plan-color": "violet", "Target-SoC-percent": 80.0,
                "Usable-capacity-kWh": 14.0, "Charging-efficiency": 0.9,
                "Expected-connection-at": "2026-11-29T17:00:00+01:00",
            },
            "Charger": {
                "ID": "plug", "Name": "Plug", "Control-kind": "on_off",
                "Charging-startstop-entity": "switch.garage_plug",
                "Charging-connected-sensor": "binary_sensor.garage_connected",
                "Charging-power-sensor": "sensor.garage_power",
                "Charging-energy-sensor": "sensor.garage_energy",
                "Rated-power-kW": 0.5, "Phase-count": 1,
                "Phase-IDs": ["L1"], "Voltage-V": 230.0,
                "Fixed-current-A": 3.0, "Circuit-ID": "garage",
                "Circuit-limit-A": 10.0,
                "Control-owner": "multicharge",
                "Physical-commissioned": False,
                "ChargingAsset": "Car",
            },
        })
        self.assertEqual(config, validate_configuration(config))
        self.assertEqual(config["controller"]["mode"], "Ready By")
        self.assertEqual(config["controller"]["phase_limits_a"], {"L1": 20.0})
        self.assertEqual(config["controller"]["plan_color_by"], "charger")
        self.assertEqual(config["chargers"][0]["control_owner"], "multicharge")
        self.assertFalse(config["chargers"][0]["physical_commissioned"])
        self.assertEqual(config["chargers"][0]["asset"], "car")
        self.assertEqual(config["assets"][0]["requested_kwh"], 4.0)
        self.assertEqual(config["assets"][0]["ready_by_repeat"], "daily")

    def test_expert_json_variable_current_needs_verified_independent_readback(self):
        configured = {
            "Controller": {
                "Name": "Home", "Mode": "Automatic", "Max-power-kW": 12,
                "Phase-limits-A": {"L1": 24, "L2": 24, "L3": 24},
            },
            "Charger": {
                "Name": "Wallbox", "Control-owner": "multicharge",
                "Physical-commissioned": True,
                "Control-kind": "variable_current",
                "Rated-power-kW": 11, "Phase-count": 3,
                "Phase-IDs": ["L1", "L2", "L3"], "Voltage-V": 230,
                "Min-current-A": 6, "Max-current-A": 16,
                "Current-step-A": 1,
                "Circuit-ID": "garage", "Circuit-limit-A": 20,
                "Charging-startstop-entity": "switch.wallbox",
                "Charging-amp-entity": "number.wallbox_target",
                "Charging-current-readback-sensor": "sensor.wallbox_current",
                "Charging-connected-sensor": "binary_sensor.wallbox_cable",
                "Charging-power-sensor": "sensor.wallbox_power",
            },
        }
        cfg = normalize_expert_json(configured)
        self.assertEqual(cfg["chargers"][0]["kind"], "variable_current")
        self.assertTrue(cfg["chargers"][0]["physical_commissioned"])
        self.assertEqual(cfg["chargers"][0]["current_readback_entity"],
                         "sensor.wallbox_current")
        from copy import deepcopy
        without_readback = deepcopy(configured)
        without_readback["Charger"].pop("Charging-current-readback-sensor")
        with self.assertRaisesRegex(ValueError, "readback"):
            normalize_expert_json(without_readback)
        duplicate_readback = deepcopy(configured)
        duplicate_readback["Charger"]["Charging-current-readback-sensor"] = (
            "number.wallbox_target"
        )
        with self.assertRaisesRegex(ValueError, "expected sensor"):
            normalize_expert_json(duplicate_readback)

    def test_expert_json_cannot_claim_commissioning_without_complete_evidence(self):
        safe = {
            "Controller": {"Name": "Home"},
            "Charger": {
                "Name": "Plug",
                "Charging-startstop-entity": "switch.plug",
            },
        }
        self.assertEqual(normalize_expert_json(safe)["controller"]["mode"], "Off")
        self.assertEqual(normalize_expert_json(safe)["chargers"][0]["control_owner"],
                         "external")
        from copy import deepcopy
        unsafe = deepcopy(safe)
        unsafe["Charger"]["Control-owner"] = "multicharge"
        unsafe["Charger"]["Physical-commissioned"] = True
        with self.assertRaisesRegex(ValueError, "requires verified"):
            normalize_expert_json(unsafe)
        unsafe = deepcopy(safe)
        unsafe["Charger"]["Physical-commissioned"] = True
        with self.assertRaisesRegex(ValueError, "commissioning requires"):
            normalize_expert_json(unsafe)
        unsafe = deepcopy(safe)
        unsafe["Controller"]["Mode"] = "Force Charge"
        self.assertEqual(normalize_expert_json(unsafe)["chargers"][0]["control_owner"],
                         "external")
        unsafe = deepcopy(safe)
        unsafe["Controller"]["Phase-limits-A"] = {"L5": 16}
        with self.assertRaisesRegex(ValueError, "phase_limits_a"):
            normalize_expert_json(unsafe)

    def test_controller_only_expert_json_is_a_valid_empty_site(self):
        configured = normalize_expert_json({
            "Controller": {"ID": "home", "Name": "Home only", "Mode": "Off"},
        })
        self.assertEqual(configured["controller"]["name"], "Home only")
        self.assertEqual(configured["assets"], [])
        self.assertEqual(configured["chargers"], [])

    def test_expert_json_rejects_ambiguous_vehicle_names_and_non_numeric_limits(self):
        template = {
            "Charger": {
                "Name": "Plug", "Charging-startstop-entity": "switch.plug"
            },
            "ChargingAsset": [
                {"ID": "vehicle_1", "Name": "Duplicate"},
                {"ID": "vehicle_2", "Name": "Duplicate"},
            ],
        }
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            normalize_expert_json(template)
        template["ChargingAsset"][1]["Name"] = "Other"
        template["Charger"]["Rated-power-kW"] = "several"
        with self.assertRaisesRegex(ValueError, "expected a number"):
            normalize_expert_json(template)

    def test_idle_only_vehicle_rebind_is_in_place_not_physical_reload(self):
        from multicharge_configuration_tests.configuration import (
            apply_settings_change, is_in_place_runtime_preference_change,
        )
        config = default_configuration()
        config["assets"] = [
            {"id": "a", "name": "A", "requested_kwh": 3},
            {"id": "b", "name": "B", "requested_kwh": 4},
        ]
        config["chargers"] = [
            {"id": "c1", "name": "One", "kind": "on_off",
             "rated_power_kw": 3.5, "asset": "a"},
            {"id": "c2", "name": "Two", "kind": "on_off",
             "rated_power_kw": 3.5, "asset": "b"},
            {"id": "c3", "name": "Three", "kind": "on_off",
             "rated_power_kw": 3.5},
        ]
        before = validate_configuration(config)
        # A destination occupied by B must never silently discard B.
        with self.assertRaisesRegex(ValueError, "charger_occupied"):
            apply_settings_change(before, "charger", "c2", {"asset": "a"})
        after = apply_settings_change(before, "charger", "c3", {"asset": "a"})
        self.assertTrue(is_in_place_runtime_preference_change(before, after))
        self.assertNotIn("asset", after["chargers"][0])
        self.assertEqual(after["chargers"][1]["asset"], "b")
        self.assertEqual(after["chargers"][2]["asset"], "a")
        self.assertFalse(is_in_place_runtime_preference_change(before, before))
        structural = validate_configuration({**before, "chargers": [
            {**before["chargers"][0], "power_entity": "sensor.another"},
            *before["chargers"][1:],
        ]})
        self.assertFalse(is_in_place_runtime_preference_change(before, structural))

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

    def test_type_only_asset_edit_preserves_physical_runtime(self):
        from multicharge_configuration_tests.configuration import (
            is_plan_presentation_only_change, apply_settings_change,
        )
        cfg = default_configuration()
        cfg["assets"] = [{"id": "bike", "name": "Bike", "kind": "bicycle",
                          "requested_kwh": 2.0}]
        cfg["chargers"] = [{"id": "plug", "name": "Plug", "kind": "on_off",
                            "rated_power_kw": 0.5, "asset": "bike"}]
        original = validate_configuration(cfg)
        edited = apply_settings_change(original, "asset", "bike",
                                       {"kind": "scooter"})
        self.assertTrue(is_plan_presentation_only_change(original, edited))
        structural = apply_settings_change(edited, "asset", "bike",
                                           {"requested_kwh": 3.0})
        self.assertFalse(is_plan_presentation_only_change(edited, structural))

    def test_auto_palette_unique_per_owner_and_stable_across_reorder(self):
        from multicharge_configuration_tests.configuration import PLAN_COLORS
        cfg = default_configuration()
        cfg["assets"] = [
            {"id": f"vehicle_{i}", "name": f"Vehicle {i}", "kind": "car"}
            for i in range(10)
        ]
        cfg["chargers"] = [
            {"id": f"charger_{i}", "name": f"Charger {i}", "kind": "on_off",
             "rated_power_kw": 3.6} for i in range(10)
        ]
        first = validate_configuration(cfg)
        self.assertEqual(len({a["plan_color"] for a in first["assets"]}), 10)
        self.assertEqual(len({c["plan_color"] for c in first["chargers"]}), 10)
        self.assertTrue(all(a["plan_color"] in PLAN_COLORS for a in first["assets"]))
        cfg["assets"].reverse()
        cfg["chargers"].reverse()
        reordered = validate_configuration(cfg)
        self.assertEqual({a["id"]: a["plan_color"] for a in first["assets"]},
                         {a["id"]: a["plan_color"] for a in reordered["assets"]})
        changed = first["assets"][2]
        changed["plan_color"] = "wine"
        self.assertEqual(
            validate_configuration(first)["assets"][2]["plan_color"], "wine"
        )

    def test_plan_color_is_native_owner_only_and_display_change(self):
        from multicharge_configuration_tests.configuration import (
            apply_settings_change, is_plan_presentation_only_change,
        )
        cfg = default_configuration()
        cfg["assets"] = [{"id": "a", "name": "A", "kind": "car"}]
        cfg["chargers"] = [{"id": "c", "name": "C",
                            "kind": "on_off", "rated_power_kw": 2}]
        original = validate_configuration(cfg)
        updated = apply_settings_change(original, "asset", "a",
                                        {"plan_color": "pink"})
        updated = apply_settings_change(updated, "charger", "c",
                                        {"plan_color": "coral"})
        self.assertTrue(is_plan_presentation_only_change(original, updated))
        self.assertEqual(updated["assets"][0]["plan_color"], "pink")
        self.assertEqual(updated["chargers"][0]["plan_color"], "coral")
        with self.assertRaises(ValueError):
            apply_settings_change(updated, "controller", "home",
                                  {"plan_color": "blue"})

    def test_missing_energy_target_is_not_equivalent_to_zero(self):
        cfg = default_configuration()
        cfg["assets"] = [{"id": "car", "name": "Car", "kind": "car"}]
        result = validate_configuration(cfg)
        self.assertNotIn("requested_kwh", result["assets"][0])
        self.assertNotIn("target_soc", result["assets"][0])
        self.assertNotIn("requested_duration_minutes", result["assets"][0])
        self.assertEqual(result["assets"][0]["plan_color"], "blue")

    def test_owner_rename_and_color_do_not_reload_active_charger(self):
        from multicharge_configuration_tests.configuration import (
            apply_settings_change, is_plan_presentation_only_change,
        )
        base = validate_configuration(default_configuration())
        with_car = apply_settings_change(base, "asset", "car", {
            "name": "Car", "kind": "car"
        }, action="create")
        renamed = apply_settings_change(
            with_car, "asset", "car", {"name": "New car"}
        )
        self.assertTrue(is_plan_presentation_only_change(with_car, renamed))
        recolored = apply_settings_change(
            renamed, "asset", "car", {"plan_color": "orange"}
        )
        self.assertTrue(is_plan_presentation_only_change(renamed, recolored))
        new_controller = apply_settings_change(
            base, "controller", "home", {"name": "New site"}
        )
        self.assertTrue(is_plan_presentation_only_change(base, new_controller))
        self.assertEqual(renamed["assets"][0]["id"], "car")
        self.assertFalse(is_plan_presentation_only_change(
            base, apply_settings_change(base, "controller", "home", {
                "max_parallel": 2
            })
        ))

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

    def test_yaml_import_overrides_old_ui_options_and_preserves_truth(self):
        class Entry:
            data = {"source": "yaml", "configuration": default_configuration("Expert YAML")}
            options = {"configuration": default_configuration("Old wizard"),
                       "enable_ux": True}
        self.assertEqual(
            effective_configuration(Entry())["controller"]["name"],
            "Expert YAML",
        )
        # Switching to YAML must never resurrect stale wizard preferences.
        Entry.options["configuration"]["controller"]["mode"] = "Force Charge"
        self.assertEqual(effective_configuration(Entry())["controller"]["mode"], "Off")

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

    def test_native_specific_day_calendar_and_charging_window_validation(self):
        from copy import deepcopy
        from multicharge_configuration_tests.configuration import (
            apply_settings_change, is_in_place_runtime_preference_change,
        )
        source = default_configuration()
        source["assets"] = [{
            "id": "guest", "name": "Guest", "kind": "car",
            "ready_by_repeat": "specific_days",
            "ready_by_weekdays": {"mon": "06:45", "wed": "08:30", "fri": "17:15"},
            "charging_windows": {
                "mon": {"start": "22:00", "end": "06:00"},
                "wed": {"start": "11:00", "end": "15:00"},
            },
            "requested_duration_minutes": 30,
        }]
        canonical = validate_configuration(source)
        asset = canonical["assets"][0]
        self.assertEqual(asset["ready_by_weekdays"]["wed"], "08:30")
        self.assertEqual(asset["charging_windows"]["mon"]["end"], "06:00")
        revised = apply_settings_change(
            canonical, "asset", "guest",
            {"ready_by_weekdays": {"tue": "10:15"},
             "charging_windows": {"tue": {"start": "08:00", "end": "11:00"}}},
        )
        self.assertTrue(is_in_place_runtime_preference_change(canonical, revised))
        self.assertEqual(revised["assets"][0]["ready_by_weekdays"], {"tue": "10:15"})
        clean = apply_settings_change(revised, "asset", "guest",
                                      {"charging_windows": None})
        self.assertNotIn("charging_windows", clean["assets"][0])
        legacy = deepcopy(source)
        legacy["assets"][0].pop("ready_by_weekdays")
        legacy["assets"][0]["ready_by_repeat"] = "weekly"
        legacy["assets"][0]["ready_by"] = "2026-11-23T09:00:00+01:00"
        self.assertEqual(validate_configuration(legacy)["assets"][0]["ready_by_repeat"],
                         "weekly")  # Retained on disk until user edits; IDs preserved.
        for bad in (
            {"ready_by_weekdays": {}},
            {"ready_by_weekdays": {"hol": "08:00"}},
            {"ready_by_weekdays": {"mon": "24:00"}},
            {"charging_windows": {"mon": {"start": "07:00", "end": "07:00"}}},
            {"charging_windows": {"mon": {"start": "25:00", "end": "06:00"}}},
            {"charging_windows": {"sunday": {"start": "10:00", "end": "18:00"}}},
        ):
            example = deepcopy(source)
            example["assets"][0].update(bad)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_configuration(example)

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


class YamlEditorConfigurationTests(unittest.TestCase):
    """Same canonical schema for native reviewed YAML and ordinary settings."""

    @staticmethod
    def configured_site():
        cfg = default_configuration("Original")
        cfg["assets"] = [
            {"id": "family", "name": "Family", "kind": "car"},
            {"id": "guest", "name": "Guest", "kind": "car"},
        ]
        cfg["chargers"] = [
            {"id": "white", "name": "White", "kind": "on_off",
             "rated_power_kw": 3.6, "control_entity": "switch.white",
             "control_owner": "external", "physical_commissioned": False,
             "asset": "family"},
            {"id": "outside", "name": "Outside", "kind": "on_off",
             "rated_power_kw": 7.2, "control_entity": "switch.outside",
             "control_owner": "external", "physical_commissioned": False},
        ]
        return validate_configuration(cfg)

    def test_full_replacement_preserves_existing_id_and_rejects_owner_change(self):
        old = self.configured_site()
        updated = prepare_expert_yaml_revision(old, {
            "robotix_multicharge": {
                "controller": {**old["controller"], "name": "Home"},
                "assets": [{"id": "family", "name": "Family", "kind": "car"}],
                "chargers": [old["chargers"][0]],
            }
        }, "replace")
        self.assertEqual(updated["controller"]["id"], "home")
        self.assertEqual([c["id"] for c in updated["chargers"]], ["white"])
        self.assertEqual([a["id"] for a in updated["assets"]], ["family"])
        self.assertEqual(updated["chargers"][0]["control_owner"], "external")
        self.assertFalse(updated["chargers"][0]["physical_commissioned"])
        bad = {**old, "chargers": [{**old["chargers"][0],
                                  "control_owner": "multicharge",
                                  "connected_entity": "binary_sensor.white_plug",
                                  "power_entity": "sensor.white_power",
                                  "physical_commissioned": False}]}
        with self.assertRaisesRegex(ValueError, "cannot transfer"):
            prepare_expert_yaml_revision(old, bad, "replace")
        with self.assertRaisesRegex(ValueError, "cannot change"):
            prepare_expert_yaml_revision(old, {
                **old, "controller": {**old["controller"], "id": "other"},
            }, "replace")

    def test_scoped_merge_preserves_unmentioned_chargers_and_assets(self):
        old = self.configured_site()
        updated = prepare_expert_yaml_revision(old, {
            "controller": {"name": "Updated"},
            "assets": [{"id": "guest", "requested_kwh": 2.0}],
            "chargers": [{"id": "white", "name": "Garage White"}],
        }, "merge")
        self.assertEqual(updated["controller"]["name"], "Updated")
        self.assertEqual(len(updated["chargers"]), 2)
        self.assertEqual(len(updated["assets"]), 2)
        self.assertEqual(updated["chargers"][0]["asset"], "family")
        self.assertEqual(updated["chargers"][0]["name"], "Garage White")
        self.assertEqual(updated["assets"][1]["requested_kwh"], 2)
        self.assertEqual(old["chargers"][0]["name"], "White")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            prepare_expert_yaml_revision(old, {
                "chargers": [{"id": "white"}, {"id": "white"}],
            }, "merge")
        with self.assertRaisesRegex(ValueError, "requires controller"):
            prepare_expert_yaml_revision(old, {"chargers": []}, "replace")
        with self.assertRaisesRegex(ValueError, "Only robotix_multicharge"):
            prepare_expert_yaml_revision(old, {
                "robotix_multicharge": old, "template": []
            }, "replace")

    def test_expert_json_and_yaml_share_one_schema_but_no_writer_commissioning(self):
        old = default_configuration()
        result = prepare_expert_yaml_revision(old, {
            "Controller": {"ID": "home", "Name": "Home"},
            "Charger": [{"Name": "Garage", "Charging-startstop-entity": "switch.garage"}],
        }, "replace")
        self.assertEqual(result["controller"]["id"], "home")
        self.assertEqual(result["chargers"][0]["control_owner"], "external")
        self.assertFalse(result["chargers"][0]["physical_commissioned"])
        with self.assertRaisesRegex(ValueError, "requires replace"):
            prepare_expert_yaml_revision(old, {"Controller": {"Name": "Home"}}, "merge")


if __name__ == "__main__":
    unittest.main()
