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
            "quality": "ok", "value": -0.05, "currency": "EUR"
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
        self.assertEqual(result["configuration"]["controller"]["id"], "home")
        self.assertEqual(result["observations"]["assets"]["car"]["soc"]["value"], 50.0)
        self.assertEqual(result["observations"]["chargers"]["drive"]["power_kw"]["value"], 2.3)
        self.assertEqual(result["observations"]["chargers"]["drive"]["connected"]["value"], True)
        self.assertEqual(result["observations"]["sources"]["binding_quality"], "NOT_CONFIGURED")

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
