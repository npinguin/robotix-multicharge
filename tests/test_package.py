"""Static package and source-level safety checks; no Home Assistant runtime."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "robotix_multicharge"


class PackageTest(unittest.TestCase):
    def test_manifest_key_order_for_hassfest(self):
        text = (COMPONENT / "manifest.json").read_text(encoding="utf8")
        obj = json.loads(text)
        self.assertEqual(
            list(obj), ["domain", "name", *sorted(set(obj) - {"domain", "name"})]
        )

    def test_guided_five_step_onboarding_is_not_a_one_page_form(self):
        source = (COMPONENT / "config_flow.py").read_text(encoding="utf8")
        for step in ("user", "charger", "asset", "sources", "verify"):
            self.assertIn("async_step_" + step, source)
        self.assertIn("self._draft = validate_configuration(trial)", source)
        self.assertIn('user_input.get("confirm") is not True', source)
        self.assertIn('data={"source": "ui", "configuration": cfg}', source)
        self.assertNotIn("services.async_call(", source)

    def test_native_five_view_frontend_is_bundled(self):
        source = (COMPONENT / "frontend" / "robotix-multicharge.js").read_text(
            encoding="utf8"
        )
        for title in (
            "Overview", "Charging Plan", "Chargeable Assets", "Chargers",
            "Settings", "Charging site", "Sources & bindings",
            "Charging strategy", "Safety & limits", "Integrations",
            "Advanced & YAML",
        ):
            self.assertIn(title, source)
        self.assertIn("robotix-multicharge-card", source)
        self.assertIn('type:"robotix_multicharge/get_plan"', source)
        self.assertNotIn("hass.callService", source)
        self.assertNotIn(".innerHTML", source)

    def test_plan_query_is_importable_with_declared_ha_dependencies(self):
        text = (COMPONENT / "plan_query.py").read_text(encoding="utf8")
        self.assertIn("import voluptuous as vol", text)
        self.assertNotIn("import probatio", text)

    def test_manifest_is_standalone(self):
        m = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf8"))
        self.assertEqual(m["domain"], "robotix_multicharge")
        self.assertTrue(m["config_flow"])
        self.assertEqual(m["dependencies"], [])
        self.assertEqual(m["requirements"], [])

    def test_translation_source_consistency(self):
        self.assertEqual(
            json.loads((COMPONENT / "strings.json").read_text(encoding="utf8")),
            json.loads((COMPONENT / "translations/en.json").read_text(encoding="utf8")),
        )

    def test_no_physical_executor_in_bootstrap(self):
        for name in ("__init__.py", "sensor.py", "config_flow.py"):
            source = (COMPONENT / name).read_text(encoding="utf8")
            self.assertNotIn("services.async_call(", source)
            self.assertNotIn("async_track_state_change", source)

    def test_logical_devices_not_reparented(self):
        source = (COMPONENT / "sensor.py").read_text(encoding="utf8")
        self.assertNotIn("via_device", source)

    def test_native_read_only_property_surfaces(self):
        sensor = (COMPONENT / "sensor.py").read_text(encoding="utf8")
        self.assertIn("Actual power", sensor)
        self.assertIn("Battery level", sensor)
        self.assertIn("Connection", sensor)
        self.assertNotIn("services.async_call(", sensor)

    def test_no_legacy_setup_or_alias_entities(self):
        source = (COMPONENT / "sensor.py").read_text(encoding="utf8")
        self.assertIn(":readiness", source)
        self.assertNotIn("Setup status", source)
        self.assertNotIn(":setup", source)
        for name in ("legacy_", "evsc_", "vehicle_bridge"):
            self.assertNotIn(name, source)

    def test_no_legacy_runtime_import(self):
        for path in COMPONENT.glob("*.py"):
            self.assertNotIn("ev_" + "smart_charging", path.read_text(encoding="utf8"))


if __name__ == "__main__":
    unittest.main()
