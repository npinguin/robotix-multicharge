"""Runtime observation and plan behavior with injected native HA states."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

PKG = Path(__file__).resolve().parents[1] / "custom_components" / "robotix_multicharge"
ROOT = "multicharge_runtime_test"
package = type(sys)(ROOT)
package.__path__ = [str(PKG)]
sys.modules[ROOT] = package
for name in ("domain", "contracts", "configuration", "planner",
             "source_evidence", "runtime", "const", "diagnostics"):
    spec = importlib.util.spec_from_file_location(f"{ROOT}.{name}", PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from multicharge_runtime_test.configuration import default_configuration, validate_configuration  # noqa: E402 - imported after isolated pure-module bootstrap
from multicharge_runtime_test.runtime import MultiChargeRuntime as _ProductionRuntime  # noqa: E402


MultiChargeRuntime = _ProductionRuntime

NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)


def state(value, unit=None):
    return SimpleNamespace(
        state=value,
        attributes={"unit_of_measurement": unit} if unit else {},
        last_updated=NOW,
        last_changed=NOW,
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
        "power_entity": "sensor.power", "control_owner": "multicharge",
        "control_entity": "switch.drive",
    }]
    return validate_configuration(cfg)


class RuntimeTests(unittest.TestCase):
    def test_only_unaliased_display_meter_updates_can_skip_planning(self):
        from multicharge_runtime_test.runtime import display_only_power_sources
        cfg = sample()
        cfg["controller"].update(home_power_entity="sensor.house", solar_power_entity="sensor.pv")
        states = {"sensor.soc": state("65", "%"), "sensor.power": state("0", "W"),
                  "binary_sensor.cable": state("on"), "sensor.house": state("100", "W"),
                  "sensor.pv": state("500", "W")}
        rt = MultiChargeRuntime(SimpleNamespace(states=SimpleNamespace(get=states.get)), cfg)
        rt.refresh(NOW)
        original = rt.assessment
        self.assertEqual(display_only_power_sources(cfg), {"sensor.house", "sensor.pv"})
        states["sensor.pv"].state = "900"
        rt.refresh_display_power(NOW)
        self.assertIs(rt.assessment, original)
        self.assertEqual(rt.observations["sources"]["solar_power"]["value"], 0.9)
        measured = rt.performance_snapshot()
        self.assertEqual(measured["full_refresh"]["count"], 1)
        self.assertEqual(measured["display_refresh"]["count"], 1)
        self.assertGreaterEqual(measured["full_refresh"]["p95_ms"], 0)
        cfg["controller"]["grid_power_entity"] = "sensor.pv"
        self.assertEqual(display_only_power_sources(cfg), {"sensor.house"})
        cfg["chargers"][0]["power_entity"] = "sensor.house"
        self.assertFalse(display_only_power_sources(cfg))

    def test_assigned_vehicle_plans_on_fresh_connection_without_extra_confirmation(self):
        config = sample()
        observations = {"sensor.soc": state("65", "%"),
                        "sensor.power": state("0", "W"),
                        "binary_sensor.cable": state("on")}
        rt = _ProductionRuntime(SimpleNamespace(states=SimpleNamespace(get=observations.get)), config)
        rt.refresh(NOW)
        self.assertTrue(rt.assessment.plan.slots)
        self.assertFalse(rt.goal_assessments["drive"]["conditional"])
        observations["binary_sensor.cable"].state = "off"
        rt.refresh(NOW)
        self.assertFalse(rt.assessment.plan.slots)
        observations["binary_sensor.cable"].state = "on"
        observations["binary_sensor.cable"].last_changed = NOW + timedelta(seconds=2)
        rt.refresh(NOW + timedelta(seconds=3))
        self.assertTrue(rt.assessment.plan.slots)
        restarted = _ProductionRuntime(SimpleNamespace(states=SimpleNamespace(get=observations.get)), config)
        restarted.refresh(NOW + timedelta(seconds=3))
        self.assertTrue(restarted.assessment.plan.slots)

    def test_resident_status_is_derived_from_backend_evidence(self):
        cfg = sample()
        cfg["controller"]["mode"] = "Automatic"
        data = {"sensor.soc": state("80", "%"), "sensor.power": state("0", "W"),
                "binary_sensor.cable": state("on"), "switch.drive": state("off")}
        rt = MultiChargeRuntime(SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg)
        rt.refresh(NOW)
        row = rt.charger_states()["drive"]
        self.assertEqual(row["asset_operational_status"]["status"], "ready")
        self.assertEqual(row["asset_operational_status"]["reason"], "TARGET_MET")
        data.pop("switch.drive")
        rt.refresh(NOW)
        row = rt.charger_states()["drive"]
        self.assertEqual(row["asset_operational_status"]["status"], "problem")
        self.assertEqual(row["operational_status"]["status"], "problem")

    def test_inactive_adjustable_kw_preview_without_guessed_current(self):
        cfg = sample()
        cfg["controller"]["mode"] = "Automatic"
        cfg["assets"][0].pop("ready_by")
        cfg["chargers"][0].update(kind="variable_current", control_owner="external",
                                  physical_commissioned=False, rated_power_kw=11)
        data = {"sensor.soc": state("65", "%"), "sensor.power": state("0", "W"),
                "binary_sensor.cable": state("on")}
        rt = MultiChargeRuntime(SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg)
        rt.refresh(NOW)
        self.assertFalse(rt.assessment.plan.slots)
        self.assertTrue(rt.forecast_assessment.plan.slots)
        self.assertTrue(all(s.current_a is None and s.power_kw <= 4 for s in rt.forecast_assessment.plan.slots))
        cfg["assets"][0].pop("capacity_kwh")
        rt.refresh(NOW)
        self.assertIsNone(rt.forecast_assessment)
        self.assertEqual(rt.forecast_excluded["drive"], "BATTERY_CAPACITY_NOT_CONFIGURED")

    def test_active_confirmed_variable_charger_retains_nonbinding_kw_preview(self):
        cfg = sample()
        cfg["controller"]["mode"] = "Automatic"
        cfg["chargers"][0].update(kind="variable_current", rated_power_kw=3.6)
        data = {"sensor.soc": state("65", "%"), "sensor.power": state("0", "W"),
                "binary_sensor.cable": state("on")}
        rt = MultiChargeRuntime(SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg)
        rt.refresh(NOW)
        self.assertEqual(rt.excluded["drive"], "VARIABLE_CURRENT_CAPABILITY_UNVERIFIED")
        self.assertFalse(rt.assessment.plan.slots)
        self.assertTrue(rt.forecast_assessment.plan.slots)
        self.assertEqual(rt.goal_assessments["drive"]["status"], "cannot_assess")
        self.assertIsNone(rt.goal_assessments["drive"]["shortfall_grid_kwh"])
        self.assertFalse(rt.goal_assessments["drive"]["power_capability_verified"])
        self.assertEqual(rt.goal_assessments["drive"]["assumption"], "IF_CAPABILITY_VERIFIED")
        self.assertTrue(all(slot.current_a is None for slot in rt.forecast_assessment.plan.slots))
        cfg["controller"]["phase_limits_a"] = {"L1": 16}
        rt.refresh(NOW)
        self.assertFalse(rt.forecast_assessment.plan.slots)
        self.assertEqual(rt.goal_assessments["drive"]["status"], "cannot_assess")

    def test_assignment_cannot_mask_unverified_power(self):
        cfg = sample()
        cfg["controller"]["mode"] = "Automatic"
        cfg["chargers"][0].update(kind="variable_current", rated_power_kw=3.6)
        data = {"sensor.soc": state("65", "%"), "sensor.power": state("0", "W"),
                "binary_sensor.cable": state("on")}
        rt = _ProductionRuntime(SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg)
        rt.refresh(NOW)
        goal = rt.goal_assessments["drive"]
        self.assertEqual(rt.excluded["drive"], "VARIABLE_CURRENT_CAPABILITY_UNVERIFIED")
        self.assertTrue(rt.forecast_assessment.plan.slots)
        self.assertFalse(goal["power_capability_verified"])
        self.assertAlmostEqual(goal["minimum_planning_power_kw"], 1.38)
        self.assertTrue(all(s.power_kw == 1.38 for s in rt.forecast_assessment.plan.slots))
        self.assertEqual(goal["status"], "cannot_assess")
        self.assertIsNone(goal["shortfall_grid_kwh"])
        self.assertEqual(goal["reason"], "VARIABLE_CURRENT_CAPABILITY_UNVERIFIED")

    def test_goal_feasibility_uses_full_plan_not_chart_visibility(self):
        cfg = sample()
        cfg["controller"].update(mode="Automatic", max_power_kw=3.6,
                                 show_indicative_forecast=False)
        cfg["assets"][0].update(target_soc=95, capacity_kwh=20, charge_efficiency=0.9,
                               ready_by=(NOW+timedelta(hours=2)).isoformat())
        cfg["chargers"][0].update(control_owner="external", physical_commissioned=False,
                                  rated_power_kw=3.6)
        data = {"sensor.soc": state("88", "%"), "sensor.power": state("0", "W"),
                "binary_sensor.cable": state("on")}
        rt = _ProductionRuntime(SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg)
        rt.refresh(NOW)
        result = rt.read_plan(NOW, NOW+timedelta(minutes=15))
        self.assertEqual(result["slots"], [])
        self.assertEqual(result["forecast_slots"], [])
        goal = result["goal_assessments"]["drive"]
        self.assertEqual(goal["status"], "achievable")
        self.assertTrue(goal["conditional"])
        self.assertAlmostEqual(goal["required_grid_kwh"], 1.4/0.9)
        self.assertEqual(goal["shortfall_grid_kwh"], 0)
        cfg["assets"][0]["ready_by"] = (NOW+timedelta(minutes=15)).isoformat()
        rt.refresh(NOW)
        self.assertEqual(rt.goal_assessments["drive"]["status"], "shortfall")
        self.assertGreater(rt.goal_assessments["drive"]["shortfall_grid_kwh"], 0)
        cfg["assets"][0].pop("capacity_kwh")
        rt.refresh(NOW)
        self.assertEqual(rt.goal_assessments["drive"]["status"], "cannot_assess")
        self.assertEqual(rt.goal_assessments["drive"]["reason"], "BATTERY_CAPACITY_NOT_CONFIGURED")
        data["sensor.soc"] = state("96", "%")
        data["binary_sensor.cable"] = state("off")
        cfg["controller"]["mode"] = "Off"
        rt.refresh(NOW)
        self.assertEqual(rt.goal_assessments["drive"]["status"], "target_met")
        self.assertEqual(rt.goal_assessments["drive"]["required_grid_kwh"], 0)

    def test_field_shaped_daily_goal_with_192_reference_price_quarters(self):
        # Representative test data, not the physical vehicle's battery spec.
        zone = ZoneInfo("Europe/Brussels")
        at = datetime(2026, 11, 24, 20, 45, tzinfo=zone).astimezone(timezone.utc)
        cfg = sample()
        cfg["controller"].update(mode="Automatic", max_power_kw=3.6,
                                 current_price_entity="sensor.price")
        cfg["assets"][0].update(target_soc=95, capacity_kwh=20, charge_efficiency=0.9,
            ready_by=datetime(2026, 11, 24, 6, tzinfo=zone).isoformat(),
            ready_by_repeat="daily")
        cfg["chargers"][0].update(kind="variable_current", control_owner="external",
                                  physical_commissioned=False, rated_power_kw=3.6)
        data = {"sensor.soc": state("88", "%"), "sensor.power": state("0", "W"),
                "binary_sensor.cable": state("on"), "sensor.price": state("0.39", "EUR/kWh")}
        first = datetime(2026, 11, 24, tzinfo=zone).astimezone(timezone.utc)
        for source in data.values():
            source.last_updated = source.last_changed = at
        data["sensor.price"].attributes.update(
            prices_today=[{"time": (first+timedelta(minutes=15*i)).isoformat(), "price": 0.39}
                          for i in range(96)],
            prices_tomorrow=[{"time": (first+timedelta(days=1, minutes=15*i)).isoformat(),
                              "price": 0.05 if 8 <= i < 12 else 0.30}
                             for i in range(96)],
        )
        rt = _ProductionRuntime(SimpleNamespace(states=SimpleNamespace(get=data.get),
                      config=SimpleNamespace(time_zone="Europe/Brussels")), cfg)
        rt.refresh(at)
        self.assertEqual(len(rt.price_slots), 192)
        result = rt.read_plan(first, first+timedelta(days=2))
        self.assertEqual(result["slots"], [])
        self.assertTrue(result["forecast_slots"])
        goal = result["goal_assessments"]["drive"]
        self.assertEqual(goal["status"], "cannot_assess")
        self.assertTrue(goal["conditional"])
        self.assertAlmostEqual(goal["required_grid_kwh"], 1.4/0.9)
        self.assertIsNone(goal["shortfall_grid_kwh"])
        self.assertTrue(all(s["indicative_power_kw"] == 1.38 for s in result["forecast_slots"]))
        self.assertTrue(any(datetime.fromisoformat(s["start"]).astimezone(zone).hour == 2
                            for s in result["forecast_slots"]))
        self.assertLessEqual(datetime.fromisoformat(goal["planned_finish_at"]),
                             datetime.fromisoformat(goal["deadline"]))
        self.assertTrue(goal["timeline_windows"])
        self.assertEqual(goal["timeline_windows"][0]["start"], goal["next_charge_at"])
        self.assertEqual(goal["timeline_windows"][-1]["end"], goal["planned_finish_at"])
        self.assertEqual(rt.read_plan(first, first+timedelta(days=1))["goal_assessments"]["drive"]["timeline_windows"],
                         goal["timeline_windows"])
        self.assertTrue(all(not s["may_execute"] and s["indicative_current_a"] is None
                            for s in result["forecast_slots"]))
        cfg["assets"][0]["capacity_kwh"] = 1000
        rt.refresh(at)
        self.assertEqual(rt.goal_assessments["drive"]["status"], "cannot_assess")
        self.assertIsNone(rt.goal_assessments["drive"]["shortfall_grid_kwh"])
        self.assertGreater(rt.forecast_assessment.shortfall_kwh["drive"], 0)
        self.assertFalse(rt.assessment.plan.slots)

    def test_prior_session_draw_forecast_matches_goal_energy(self):
        cfg = sample()
        charger = cfg["chargers"][0]
        charger.update(kind="variable_current", rated_power_kw=3.68,
                       voltage_v=230, phase_count=1, min_current_a=6,
                       max_current_a=16, current_step_a=1,
                       current_control_entity="number.charge_limit",
                       current_readback_entity="sensor.amps")
        asset = cfg["assets"][0]
        data = {"sensor.soc": state("65", "%"), "sensor.power": state("0", "W"),
                "binary_sensor.cable": state("off"), "switch.drive": state("off"),
                "sensor.amps": state("0", "A"), "number.charge_limit": state("6", "A")}
        data["number.charge_limit"].attributes.update(min=6, max=16, step=1)
        rt = _ProductionRuntime(SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg)
        stamp = NOW-timedelta(days=1)
        draw = {"power_kw": 1.1, "setpoint_kw": 3.68, "current_a": 16,
                "soc_min": 64, "soc_max": 66, "observed_at": stamp.isoformat(),
                "sample_count": 4, "basis": "sustained_current_session",
                "binding": rt.executor._draw_binding(rt.executor.effective_charger(charger), asset)}
        snapshot = rt.executor.export_state()
        snapshot["sessions"] = [{"charger_id": "drive", "asset_id": "car",
                                "started_at": (stamp-timedelta(minutes=6)).isoformat(),
                                "ended_at": (stamp+timedelta(minutes=1)).isoformat(),
                                "physical_stop_confirmed": True, "draw_evidence": draw}]
        rt.executor.restore_state(snapshot)
        rt.refresh(NOW)
        result = rt.read_plan(NOW, NOW+timedelta(hours=2))
        self.assertEqual(result["slots"], [])
        self.assertEqual(rt.observations["chargers"]["drive"]["session_draw_estimate"]["basis"],
                         "qualified_prior_session")
        slots = result["forecast_slots"]
        self.assertTrue(slots)
        self.assertTrue(all(s["indicative_power_kw"] <= 1.1 and not s["reserves_capacity"]
                            for s in slots))
        self.assertAlmostEqual(sum(s["indicative_energy_kwh"] for s in slots),
                               result["goal_assessments"]["drive"]["planned_grid_kwh"], places=4)

    def test_stale_solar_last_report_is_display_only(self):
        cfg = sample()
        cfg["controller"].update(solar_power_entity="sensor.pv",
                                 solar_source_kind="direct_surplus",
                                 solar_surplus_entity="sensor.pv")
        pv = state("0", "W")
        pv.last_updated = NOW - timedelta(minutes=5)
        data = {"sensor.pv": pv}
        rt = MultiChargeRuntime(SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg)
        rt.refresh(NOW)
        reading = rt.observations["sources"]["solar_power"]
        self.assertEqual(reading["quality"], "stale")
        self.assertIsNone(reading["value"])
        self.assertEqual(reading["last_reported_value"], 0)
        self.assertEqual(rt.native_surplus_power(NOW), (None, "SOURCE_STALE"))

    def test_inactive_demand_never_displaces_active_charger(self):
        cfg = sample()
        cfg["controller"]["max_parallel"] = 1
        cfg["assets"].append({**cfg["assets"][0], "id": "other", "name": "Other", "priority": 100})
        cfg["chargers"].append({**cfg["chargers"][0], "id": "inactive", "name": "Inactive",
                                "asset": "other", "control_owner": "external",
                                "physical_commissioned": False, "connected_entity": "binary_sensor.other",
                                "power_entity": "sensor.other_power", "control_entity": "switch.other"})
        data = {"sensor.soc": state("65", "%"), "sensor.power": state("0", "W"),
                "sensor.other_power": state("0", "W"), "binary_sensor.cable": state("on"),
                "binary_sensor.other": state("on")}
        rt = MultiChargeRuntime(SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg)
        rt.refresh(NOW)
        self.assertTrue(rt.assessment.plan.slots)
        self.assertEqual({slot.charger_uid for slot in rt.assessment.plan.slots}, {"drive"})
        self.assertEqual(rt.excluded["inactive"], "CHARGER_INACTIVE")

    def test_selected_current_price_can_supply_native_interval_forecast(self):
        cfg = sample()
        cfg["controller"]["current_price_entity"] = "sensor.price"
        quote = state("0.3", "EUR/kWh")
        quote.attributes.update(kind="effective_price_kwh", currency="EUR",
            valid_until=(NOW + timedelta(hours=2)).isoformat(),
            intervals=[{"start": NOW.isoformat(), "end": (NOW + timedelta(hours=2)).isoformat(), "value": 0.3}])
        rt = MultiChargeRuntime(SimpleNamespace(states=SimpleNamespace(get={"sensor.price": quote}.get)), cfg)
        rt.refresh(NOW)
        self.assertEqual(rt.observations["sources"]["tariff_quality"], "OK")
        self.assertTrue(rt.price_slots)

    def test_current_import_price_remains_separate_from_forecast(self):
        cfg = sample()
        cfg["controller"].update(current_price_entity="sensor.import_price",
                                 price_entity="sensor.forecast_price")
        forecast = state("0.11", "EUR/kWh")
        zone = ZoneInfo("Europe/Brussels")
        first = NOW.astimezone(zone).replace(hour=0, minute=0, second=0).astimezone(timezone.utc)
        forecast.attributes.update(
            prices_today=[{"time": (first+timedelta(hours=i)).isoformat(), "price": 0.11}
                          for i in range(24)],
            prices_tomorrow=[{"time": (first+timedelta(days=1)).isoformat(), "price": 0.2}],
        )
        data = {"sensor.import_price": state("0.32", "EUR/kWh"),
                "sensor.forecast_price": forecast}
        rt = MultiChargeRuntime(SimpleNamespace(states=SimpleNamespace(get=data.get),
                                                config=SimpleNamespace(time_zone="Europe/Brussels")), cfg)
        rt.refresh(NOW)
        sources = rt.observations["sources"]
        self.assertEqual(sources["current_price"], {
            "quality": "ok", "value": 0.32, "currency": "EUR", "basis": "current_only",
        })
        self.assertEqual(sources["tariff_quality"], "OK")
        self.assertEqual(sources["tariff_tomorrow_quality"], "INTERVAL_COVERAGE_INCOMPLETE")
        self.assertEqual(len(rt.price_slots), 24)
        self.assertTrue(all(s.effective_price_per_kwh == 0.11 and
                            s.basis == "variable_reference" for s in rt.price_slots))
        data["sensor.import_price"] = state("unavailable", "EUR/kWh")
        rt.refresh(NOW)
        self.assertIsNone(rt.observations["sources"]["current_price"]["value"])
        self.assertEqual(rt.observations["sources"]["current_price"]["quality"], "unavailable")
        self.assertEqual(len(rt.price_slots), 24)
        cfg["controller"].pop("current_price_entity")
        rt.refresh(NOW)
        self.assertEqual(rt.observations["sources"]["current_price"]["value"], 0.11)
        self.assertEqual(rt.observations["sources"]["current_price"]["basis"], "variable_reference")

    def test_native_diagnostics_capture_errors_without_leaking_names(self):
        import json
        from multicharge_runtime_test.diagnostics import build_diagnostics

        cfg = sample()
        cfg["controller"]["name"] = "Private test home"
        cfg["controller"]["current_price_entity"] = "sensor.private_tariff"
        cfg["assets"][0]["name"] = "Personal vehicle"
        states = {
            "sensor.soc": state("65", "%"),
            "sensor.private_tariff": state("0.2", "EUR/kWh"),
            "sensor.power": state("unavailable", "W"),
            "binary_sensor.cable": state("on"),
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=states.get)), cfg
        )
        rt.refresh(NOW)
        result = build_diagnostics(
            rt, SimpleNamespace(source="user", version=1), captured_at=NOW
        )
        rendered = json.dumps(result)
        self.assertEqual(result["schema_major"], 1)
        self.assertEqual(result["observations"]["chargers"][
            next(iter(result["observations"]["chargers"]))
        ]["power_kw"]["quality"], "unavailable")
        self.assertIn("source", rendered)
        self.assertEqual(result["observations"]["sources"]["tariff_source"],
                         result["controller"]["bindings"]["current_price_entity"])
        for sensitive in ("Private test home", "Personal vehicle",
                          "sensor.soc", "sensor.power", "binary_sensor.cable",
                          "sensor.private_tariff",
                          '"asset_id": "car"', '"charger_id": "drive"'):
            self.assertNotIn(sensitive, rendered)
        self.assertIsNone(rt.live_state()["actual_power_kw"])
        self.assertEqual(result["execution"]["action_health"], "idle")
        self.assertEqual(result["performance"]["full_refresh"]["count"], 1)
        rt.executor._inflight["car"] = "private-intent-fingerprint"
        held = build_diagnostics(rt, SimpleNamespace(source="user", version=1), captured_at=NOW)
        self.assertEqual(held["execution"]["inflight_intent_count"], 1)
        self.assertEqual(held["execution"]["intent_holds_without_checkpoint"],
                         [held["assets"][0]["id"]])
        self.assertNotIn("private-intent-fingerprint", json.dumps(held))

    def test_performance_samples_remain_bounded(self):
        from time import perf_counter
        rt = MultiChargeRuntime(SimpleNamespace(states=SimpleNamespace(get=lambda _: None)), sample())
        for _ in range(300):
            rt._record_performance("full_refresh", perf_counter())
        measured = rt.performance_snapshot()["full_refresh"]
        self.assertEqual(measured["count"], 300)
        self.assertEqual(measured["sample_count"], 256)
        self.assertGreaterEqual(measured["max_sample_ms"], measured["p95_ms"])

    def test_controller_live_projection_is_source_qualified_not_guessed(self):
        cfg = sample()
        cfg["controller"]["mode"] = "Off"
        data = {
            "sensor.soc": state("65", "%"),
            "sensor.power": state("0", "W"),
            "binary_sensor.cable": state("off"),
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg
        )
        rt.refresh(NOW)
        live = rt.live_state()
        self.assertEqual(live["connected_chargers"], 0)
        self.assertEqual(live["charging_chargers"], 0)
        self.assertEqual(live["actual_power_kw"], 0)
        self.assertEqual(live["mode"], "Off")
        self.assertEqual(live["action_health"], "idle")
        self.assertIsNone(live["last_action"])
        self.assertEqual(rt.read_plan(NOW, NOW+timedelta(hours=1))["live"], live)
        data["sensor.power"].state = "unavailable"
        rt.refresh(NOW)
        incomplete = rt.live_state()
        self.assertIsNone(incomplete["charging_chargers"])
        self.assertIsNone(incomplete["actual_power_kw"])
        self.assertEqual(incomplete["power_quality"], "unknown")
        self.assertEqual(incomplete["connected_chargers"], 0)

    def test_restored_unresolved_intent_is_controller_hold_not_idle(self):
        cfg = sample()
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get={}.get)), cfg
        )
        rt.executor._inflight["car"] = "unresolved-intent"
        self.assertEqual(rt.live_state()["action_health"], "hold")
        rt.executor._inflight.clear()
        rt.executor._persistence_verified = False
        self.assertEqual(rt.live_state()["action_health"], "hold")

    def test_multiple_chargers_unknown_connection_must_not_fake_aggregate_count(self):
        cfg = sample()
        cfg["chargers"].append({
            "id": "other", "name": "Other", "kind": "on_off",
            "rated_power_kw": 1.5, "connected_entity": "binary_sensor.other",
            "power_entity": "sensor.other_power",
        })
        data = {
            "sensor.soc": state("65", "%"),
            "sensor.power": state("2300", "W"),
            "binary_sensor.cable": state("on"),
            "sensor.other_power": state("0", "W"),
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg
        )
        rt.refresh(NOW)
        live = rt.live_state()
        self.assertIsNone(live["connected_chargers"])
        self.assertEqual(live["charging_chargers"], 1)
        self.assertEqual(live["actual_power_kw"], 2.3)

    def test_rejected_settings_action_is_never_confirmed_by_matching_revision(self):
        cfg = sample()
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get={}.get)), cfg
        )
        from multicharge_runtime_test.configuration import configuration_revision
        rt.record_settings_action(
            "controller", cfg["controller"]["id"], "save",
            {"mode": "Economy"}, configuration_revision(cfg),
            status="rejected", reason="SETTINGS_VALIDATION_OR_SAFETY_HOLD",
        )
        action = rt.live_state()["settings_action"]
        self.assertEqual(action["status"], "rejected")
        self.assertEqual(action["reason"], "SETTINGS_VALIDATION_OR_SAFETY_HOLD")

    def test_controller_settings_receipt_is_not_confirmed_before_config_reload(self):
        from multicharge_runtime_test.configuration import (
            apply_settings_change, configuration_revision
        )
        cfg = sample()
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get={}.get)), cfg
        )
        updated = apply_settings_change(cfg, "controller", cfg["controller"]["id"], {
            "mode": "Economy",
        })
        expected = configuration_revision(updated)
        notifications = []
        rt.subscribe(lambda: notifications.append(rt.live_state()["settings_action"]))
        rt.record_settings_action("controller", cfg["controller"]["id"], "save", {
            "mode": "Economy"
        }, expected)
        pending = rt.live_state()["settings_action"]
        self.assertEqual(pending["status"], "accepted_unconfirmed")
        self.assertEqual(pending["fields"], ["mode"])
        self.assertEqual(notifications[-1]["status"], "accepted_unconfirmed")
        saved = {**rt.executor.export_state(), "settings_action": rt._settings_action}
        new = MultiChargeRuntime(rt.hass, updated)
        new.attach_control_store(None, saved)
        self.assertEqual(new.live_state()["settings_action"]["status"], "confirmed")
        self.assertEqual(new.live_state()["mode"], "Economy")
        unchanged = MultiChargeRuntime(rt.hass, cfg)
        unchanged.attach_control_store(None, saved)
        self.assertEqual(unchanged.live_state()["settings_action"]["status"],
                         "accepted_unconfirmed")

    def test_two_calendar_days_cover_dst_47_and_49_hours(self):
        """Basic-style 48h means two civil days, not always 48 UTC hours."""
        cfg = sample()
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get={}.get)), cfg
        )
        zone = ZoneInfo("Europe/Brussels")
        for start_day, end_day, hours in (
            (datetime(2026, 3, 28, tzinfo=zone),
             datetime(2026, 3, 30, tzinfo=zone), 47),
            (datetime(2026, 10, 24, tzinfo=zone),
             datetime(2026, 10, 26, tzinfo=zone), 49),
        ):
            with self.subTest(day=start_day.date()):
                self.assertEqual(
                    (end_day.astimezone(timezone.utc)
                     - start_day.astimezone(timezone.utc)).total_seconds(),
                    hours * 3600,
                )
                result = rt.read_plan(start_day, end_day)
                self.assertEqual(result["start"],
                                 start_day.astimezone(timezone.utc).isoformat())
                self.assertEqual(result["end"],
                                 end_day.astimezone(timezone.utc).isoformat())
        with self.assertRaisesRegex(ValueError, "49h"):
            rt.read_plan(
                datetime(2026, 10, 24, tzinfo=zone),
                datetime(2026, 10, 26, tzinfo=zone)+timedelta(minutes=15),
            )

    def test_plan_query_uses_single_config_palette(self):
        from multicharge_runtime_test.configuration import PLAN_COLORS
        cfg = sample()
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get={}.get)), cfg
        )
        rt.refresh(NOW)
        plan = rt.read_plan(NOW, NOW + timedelta(hours=1))
        self.assertEqual(plan["plan_palette"], PLAN_COLORS)
        self.assertIn(plan["configuration"]["assets"][0]["plan_color"], PLAN_COLORS)
        self.assertIn(plan["configuration"]["chargers"][0]["plan_color"], PLAN_COLORS)

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
        self.assertEqual(
            rt.summary()["strategy_by_charger"]["drive"], "Ready By"
        )
        self.assertFalse(rt.summary()["physical_actuation_authorized"])

    def test_asset_charging_power_requires_live_confirmed_assignment(self):
        cfg = sample()
        data = {
            "sensor.soc": state("50", "%"),
            "sensor.power": state("2300", "W"),
            "binary_sensor.cable": state("on"),
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg
        )
        rt.refresh(NOW)
        self.assertIsNone(
            rt.observations["assets"]["car"]["effective_power_kw"].value
        )
        self.assertEqual(
            rt.observations["chargers"]["drive"]["power_kw"].value, 2.3
        )
        rt.executor._sessions["drive"] = {
            "asset_id": "car", "started_at": NOW
        }
        rt.refresh(NOW)
        reading = rt.observations["assets"]["car"]["effective_power_kw"]
        self.assertEqual(reading.value, 2.3)
        self.assertIs(reading, rt.observations["chargers"]["drive"]["power_kw"])
        view = rt.read_plan(NOW, NOW + timedelta(hours=1))
        self.assertEqual(
            view["observations"]["assets"]["car"]["effective_power_kw"]["value"],
            2.3
        )
        data["binary_sensor.cable"].state = "off"
        rt.refresh(NOW)
        self.assertIsNone(
            rt.observations["assets"]["car"]["effective_power_kw"].value
        )
        data["binary_sensor.cable"].state = "on"
        data["sensor.power"].state = "unavailable"
        rt.refresh(NOW)
        self.assertIsNone(
            rt.observations["assets"]["car"]["effective_power_kw"].value
        )
        data["sensor.power"].state = "0"
        rt.executor._sessions["drive"]["asset_id"] = "other"
        rt.refresh(NOW)
        self.assertIsNone(
            rt.observations["assets"]["car"]["effective_power_kw"].value
        )

    def test_all_asset_types_share_one_planner_without_soc(self):
        plans = []
        for kind in ("car", "bicycle", "motorcycle", "scooter", "other"):
            cfg = sample()
            asset = cfg["assets"][0]
            for field in ("soc_entity", "target_soc", "capacity_kwh",
                          "charge_efficiency"):
                asset.pop(field, None)
            asset["requested_kwh"] = 2.0
            asset["kind"] = kind
            cfg = validate_configuration(cfg)
            data = {
                "sensor.power": state("0", "W"),
                "binary_sensor.cable": state("on"),
            }
            rt = MultiChargeRuntime(
                SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg
            )
            rt.refresh(NOW)
            self.assertTrue(rt.assessment.plan.slots, kind)
            self.assertFalse(rt.summary()["physical_actuation_authorized"])
            plans.append(tuple(
                (slot.start, slot.end, slot.power_kw, slot.asset_uid)
                for slot in rt.assessment.plan.slots
            ))
        for result in plans[1:]:
            self.assertEqual(result, plans[0])

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

    def test_true_negative_effective_tariff_reaches_native_view_without_fake_cost(self):
        cfg = sample()
        cfg["controller"]["price_entity"] = "sensor.effective_tariff"
        price_state = state("ready")
        price_state.attributes = {
            "kind": "effective_price_kwh",
            "currency": "EUR",
            "valid_until": (NOW + timedelta(hours=1)).isoformat(),
            "intervals": [{
                "start": NOW.isoformat(),
                "end": (NOW + timedelta(minutes=30)).isoformat(),
                "value": -0.05,
            }],
        }
        data = {
            "sensor.soc": state("50", "%"),
            "binary_sensor.cable": state("on"),
            "sensor.power": state("1200", "W"),
            "sensor.effective_tariff": price_state,
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg
        )
        rt.refresh(NOW)
        response = rt.read_plan(NOW, NOW + timedelta(minutes=45))
        self.assertEqual(response["observations"]["sources"]["current_price"], {
            "quality": "ok", "value": -0.05, "currency": "EUR", "basis": "effective"
        })
        self.assertEqual(response["price_slots"][0]["currency"], "EUR")
        self.assertEqual(response["price_slots"][0]["price_per_kwh"], -0.05)
        self.assertTrue(response["read_only"])
        self.assertIsNone(response["slots"][0]["actual_energy_kwh"])

    def test_expired_guest_is_excluded_from_charging_proposals(self):
        cfg = sample()
        cfg["assets"][0]["temporary"] = True
        cfg["assets"][0]["expires_at"] = (NOW - timedelta(minutes=1)).isoformat()
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get={
                "sensor.soc": state("45", "%"),
                "binary_sensor.cable": state("on"),
                "sensor.power": state("0", "W"),
            }.get)), cfg
        )
        rt.refresh(NOW)
        self.assertEqual(rt.assessment.plan.slots, ())
        self.assertEqual(rt.excluded["drive"], "TEMPORARY_ASSET_EXPIRED")

    def test_unplugged_vehicle_is_indicative_only_never_in_executable_plan(self):
        cfg = sample()
        cfg["controller"]["max_power_kw"] = 4.0
        data = {
            "sensor.soc": state("50", "%"),
            "binary_sensor.cable": state("off"),
            "sensor.power": state("0", "W"),
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg
        )
        rt.refresh(NOW)
        self.assertFalse(rt.assessment.plan.slots)
        self.assertTrue(rt.forecast_assessment.plan.slots)
        view = rt.read_plan(NOW, NOW + timedelta(hours=2))
        self.assertEqual(view["slots"], [])
        self.assertTrue(view["forecast_slots"])
        self.assertEqual(view["forecast_slots"][0]["status"], "indicative_only")
        summary = rt.summary()
        self.assertIn("drive", summary["forecast_kwh_by_charger"])
        self.assertNotIn("drive", summary["planned_kwh_by_charger"])
        self.assertFalse(view["forecast_slots"][0]["may_execute"])
        self.assertFalse(view["forecast_slots"][0]["reserves_capacity"])
        self.assertEqual(view["forecast_assumptions"]["drive"]["assumption"],
                         "IF_CONNECTED_NOW")
        data["binary_sensor.cable"].state = "unavailable"
        rt.refresh(NOW)
        self.assertFalse(rt.forecast_assessment)
        self.assertEqual(rt.forecast_excluded["drive"], "CONNECTION_UNCONFIRMED")

    def test_forecast_expected_connection_time_and_off_mode(self):
        cfg = sample()
        cfg["controller"]["max_power_kw"] = 4.0
        cfg["assets"][0]["expected_connection_at"] = (
            NOW + timedelta(hours=1)).isoformat()
        data = {
            "sensor.soc": state("50", "%"),
            "binary_sensor.cable": state("off"),
            "sensor.power": state("0", "W"),
        }
        rt = MultiChargeRuntime(
            SimpleNamespace(states=SimpleNamespace(get=data.get)), cfg
        )
        rt.refresh(NOW)
        self.assertTrue(rt.forecast_assessment.plan.slots)
        self.assertTrue(all(
            s.start >= NOW + timedelta(hours=1)
            for s in rt.forecast_assessment.plan.slots
        ))
        cfg["controller"]["mode"] = "Off"
        rt.refresh(NOW)
        self.assertEqual(rt.forecast_assessment.plan.slots, ())
        self.assertFalse(rt.assessment.plan.slots)

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
            "control_owner": "multicharge", "control_entity": "switch.plug",
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
        self.assertEqual(result["configuration"]["controller"]["id"], "home")
        self.assertEqual(result["observations"]["assets"]["car"]["soc"]["value"], 50.0)
        self.assertEqual(result["observations"]["chargers"]["drive"]["power_kw"]["value"], 2.3)
        self.assertEqual(result["observations"]["chargers"]["drive"]["connected"]["value"], True)
        self.assertEqual(result["observations"]["sources"]["binding_quality"], "NOT_CONFIGURED")

    def test_plan_read_rejects_unknown_and_oversized_ranges(self):
        rt = MultiChargeRuntime(None, sample())
        with self.assertRaises(ValueError):
            rt.read_plan(NOW, NOW + timedelta(hours=49, minutes=15))
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


class CostArchiveRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_civil_timezone_change_invalidates_cached_days_not_pending_utc_writes(self):
        from unittest.mock import AsyncMock, patch
        from multicharge_runtime_test import runtime as module
        rt = _ProductionRuntime(None, sample())
        rt.hass = SimpleNamespace(config=SimpleNamespace(time_zone="Europe/Brussels"))
        now = datetime.now(timezone.utc)
        old_days = module.civil_cost_days(now, "Europe/Brussels")
        day = list(old_days)[-2]
        old_bounds = old_days[day]
        rt._cost_time_zone = "Europe/Brussels"
        rt._daily_costs[day] = {"old": "projection"}
        rt._archive_checked_days.add(day)
        rt._closed_cost_days.add(day)
        rt._archive_partial[day] = {"old": "partial"}
        rt._archive_pending[day] = {"start": old_bounds[0], "end": old_bounds[1],
                                    "projections": {}}
        original = rt._archive_pending[day].copy()
        identity = rt._current_session_cost_identity()
        rt.hass.config.time_zone = "Asia/Kolkata"
        self.assertNotEqual(identity, rt._current_session_cost_identity())
        with patch.object(module, "read_actual_history",
                          new=AsyncMock(return_value=([], "RECORDER_NOT_LOADED", {}, [], {}, {}))), \
                patch.object(module, "read_archive", new=AsyncMock(return_value=None)) as reader:
            await rt.refresh_session_costs()
        self.assertNotIn(day, rt._daily_costs)
        self.assertNotIn(day, rt._archive_checked_days)
        self.assertNotIn(day, rt._closed_cost_days)
        self.assertNotIn(day, rt._archive_partial)
        self.assertEqual(rt._archive_pending[day], original)
        self.assertEqual(reader.call_args.args[2], {day: old_bounds})
        self.assertEqual(reader.call_args.kwargs["exact_keys"], tuple(original["projections"]))

    async def test_archive_conflicting_readback_retains_original_and_missing_coverage(self):
        from copy import deepcopy
        from unittest.mock import AsyncMock, patch
        from multicharge_runtime_test import runtime as module
        from multicharge_runtime_test.history import _cost_bucket
        rt = _ProductionRuntime(None, sample())
        first = NOW.replace(hour=0)
        last = first+timedelta(hours=2)
        day = first.date().isoformat()
        days = {day: (first, last)}
        keys = list(module.hour_slices(first, last))
        bucket = _cost_bucket()
        bucket.update(expected_seconds=3600, observed_seconds=3600, observed_energy_kwh=1)
        bucket["valuations"][("EUR", "effective")] = [0.25, 1]
        original = {"controller": {"site": bucket}, "charger": {}, "asset": {}}
        conflict = deepcopy(original)
        conflict["controller"]["site"]["valuations"][("EUR", "effective")][0] = 0.50
        rt._archive_pending[day] = {"start": first, "end": last,
                                    "projections": {keys[0]: original}}
        rt._closed_cost_days.add(day)
        identity = rt._current_session_cost_identity()
        with patch.object(module, "read_archive",
                          new=AsyncMock(return_value={keys[0]: conflict})), \
                patch.object(module, "write_archive") as writer:
            await rt._retry_cost_archive(days, rt.configuration, [], identity)
        writer.assert_not_called()
        self.assertEqual(rt._archive_pending[day]["projections"], {keys[0]: original})
        self.assertNotIn(day, rt._closed_cost_days)
        self.assertIsNone(module.civil_period_costs(
            days, rt._daily_costs)["controller"]["site"]["today"]["cost"])
        self.assertEqual(rt._daily_costs[day]["controller"]["site"]["observed_seconds"], 0)

    async def test_readback_retries_only_original_missing_slices(self):
        from unittest.mock import AsyncMock, patch
        from multicharge_runtime_test import runtime as module

        rt = _ProductionRuntime(None, sample())
        rt.statistics_namespace = "entry"
        first = NOW.replace(hour=0)
        last = first+timedelta(hours=2)
        day = first.date().isoformat()
        days = {day: (first, last)}
        keys = list(module.hour_slices(first, last))
        from multicharge_runtime_test.history import _cost_bucket
        def sample_slice(value):
            bucket = _cost_bucket()
            bucket.update(expected_seconds=3600, observed_seconds=3600,
                          observed_energy_kwh=value)
            bucket["valuations"][("EUR", "effective")] = [value*0.25, value]
            return {"controller": {"site": bucket}, "charger": {}, "asset": {}}
        original = {keys[0]: sample_slice(1), keys[1]: sample_slice(2)}
        rt._archive_pending[day] = {"start": first, "end": last, "projections": original}
        identity = rt._current_session_cost_identity()
        with patch.object(module, "read_archive", new=AsyncMock(side_effect=[
                None, {keys[0]: original[keys[0]]}, dict(original)])), \
                patch.object(module, "write_archive") as writer:
            await rt._retry_cost_archive(days, rt.configuration, [], identity)
            self.assertEqual(rt._archive_pending[day]["projections"], original)
            writer.assert_not_called()
            await rt._retry_cost_archive(days, rt.configuration, [], identity)
            self.assertEqual(rt._archive_pending[day]["projections"], {keys[1]: original[keys[1]]})
            self.assertEqual(writer.call_args.args[-1], {keys[1]: original[keys[1]]})
            await rt._retry_cost_archive(days, rt.configuration, [], identity)
            self.assertFalse(rt._archive_pending)
            self.assertEqual(writer.call_count, 1)

    async def test_pending_cost_archive_survives_store_restart_and_year_rollover(self):
        import json
        from unittest.mock import AsyncMock, patch
        from multicharge_runtime_test import runtime as module
        from multicharge_runtime_test.history import _cost_bucket
        first = datetime(2025, 12, 31, 23, tzinfo=timezone.utc)
        last = first+timedelta(hours=1)
        day = "2025-12-31"
        key = first.isoformat()
        bucket = _cost_bucket()
        bucket.update(expected_seconds=3600, observed_seconds=3600,
                      observed_energy_kwh=2)
        bucket["valuations"][("EUR", "effective")] = [-0.1, 2]
        original = {key: {"controller": {"site": bucket}, "charger": {}, "asset": {}}}
        rt = _ProductionRuntime(None, sample())
        store = SimpleNamespace(async_save=AsyncMock())
        rt.attach_control_store(store, None)
        rt._archive_pending[day] = {"start": first, "end": last, "projections": original}
        self.assertTrue(await rt.persist_control_state())
        snapshot = json.loads(json.dumps(store.async_save.call_args.args[0]))
        restarted = _ProductionRuntime(None, sample())
        restarted.attach_control_store(store, snapshot)
        self.assertEqual(restarted._archive_pending, rt._archive_pending)
        identity = restarted._current_session_cost_identity()
        with patch.object(module, "read_archive", new=AsyncMock(side_effect=[{}, original, original])), \
                patch.object(module, "write_archive") as writer:
            # Native write failure does not discard the durable receipt.
            writer.side_effect = RuntimeError("recorder failed")
            await restarted._retry_cost_archive({}, restarted.configuration, [], identity)
            self.assertEqual(writer.call_args.args[-1], original)
            self.assertIn(day, restarted._archive_pending)
            # Acknowledgement alone is not sufficient if Store cleanup fails.
            store.async_save.side_effect = OSError("store failed")
            await restarted._retry_cost_archive({}, restarted.configuration, [], identity)
            self.assertIn(day, restarted._archive_pending)
            store.async_save.side_effect = None
            await restarted._retry_cost_archive({}, restarted.configuration, [], identity)
            self.assertFalse(restarted._archive_pending)
            self.assertEqual(writer.call_count, 1)
            self.assertEqual(store.async_save.call_args.args[0]["pending_cost_archive"], {})


if __name__ == "__main__":
    unittest.main()
