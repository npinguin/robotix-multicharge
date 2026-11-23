"""Static package and source-level safety checks; no Home Assistant runtime."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "robotix_multicharge"


class PackageTest(unittest.TestCase):
    def test_canonical_functional_specification_keeps_every_approved_journey(self):
        """UC authority lives in docs, not in a long-running PR/issue body."""
        spec = (ROOT / "docs" / "FUNCTIONAL_SPECIFICATION.md").read_text(
            encoding="utf8"
        )
        for prefix, expression, count in (
            ("UC", r"^### UC(\d{2}) —", 29),
            ("FLEX", r"^\| FLEX-(\d{2}) \|", 21),
            ("FORECAST", r"^\| FORECAST-(\d{2}) \|", 12),
            ("UI-OWNER", r"^\| UI-OWNER-(\d{2}) \|", 10),
        ):
            indices = [int(x) for x in re.findall(expression, spec, re.M)]
            self.assertEqual(
                indices, list(range(1, count + 1)),
                f"{prefix}: every approved use case must remain traceable",
            )
        for block in re.split(r"(?=^### UC\d{2} —)", spec, flags=re.M)[1:]:
            for label in (
                "Persona / eigenaar", "GIVEN", "WHEN", "THEN",
                "Negatief / fail-closed", "Bewijs",
            ):
                self.assertIn(label, block)
        for path in ("README.md", "docs/ARCHITECTURE.md",
                     "docs/INTERFACES.md"):
            self.assertIn(
                "FUNCTIONAL_SPECIFICATION.md",
                (ROOT / path).read_text(encoding="utf8"),
                f"{path} must point to the single canonical UC authority",
            )

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
        ):
            self.assertIn(title, source)
        self.assertIn("robotix-multicharge-card", source)
        self.assertIn('type:"robotix_multicharge/get_plan"', source)
        # Dashboard operates *only* the MultiCharge-owned native HA entities.
        # The Charger Number delegates to the sole guarded physical executor;
        # no frontend ever calls a manufacturer's switch or Amp-setpoint.
        self.assertIn('this._hass.callService("select","select_option"', source)
        self.assertIn('this._hass.callService("number","set_value"', source)
        self.assertIn('const entity=this.ownerEntity(scope,uid,field);', source)
        self.assertNotIn('this._hass.callService("switch"', source)
        self.assertNotIn('c.current_control_entity', source)
        # The owner-scoped vehicle-confirmation button carries no actuation.
        self.assertIn('this._hass.callService("button","press"', source)
        self.assertIn('this.ownerEntity(scope,uid,field)', source)
        self.assertIn("this.ownerEntity(scope,uid,field)", source)
        self.assertNotIn(".innerHTML", source)

    def test_plan_query_is_importable_with_declared_ha_dependencies(self):
        text = (COMPONENT / "plan_query.py").read_text(encoding="utf8")
        self.assertIn("import voluptuous as vol", text)
        self.assertNotIn("import probatio", text)

    def test_resident_plan_is_readable_but_writes_require_admin(self):
        """Authenticated HA users can view the dashboard; writes stay admin-only."""
        read = (COMPONENT / "plan_query.py").read_text(encoding="utf8")
        writes = (COMPONENT / "command_query.py").read_text(encoding="utf8")
        self.assertIn('"robotix_multicharge/get_plan"', read)
        self.assertNotIn("@websocket_api.require_admin", read)
        self.assertIn('@websocket_api.websocket_command({', read)
        self.assertEqual(writes.count("@websocket_api.require_admin"), 2)

    def test_local_robotix_brand_is_packaged_as_real_pngs(self):
        """HA 2026.3+ and Marketplace use native local integration branding."""
        for name, size in (("icon.png", 256), ("icon@2x.png", 512),
                           ("logo.png", 256), ("logo@2x.png", 512)):
            path = COMPONENT / "brand" / name
            payload = path.read_bytes()
            with self.subTest(asset=name):
                self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(payload[12:16], b"IHDR")
                width = int.from_bytes(payload[16:20], "big")
                height = int.from_bytes(payload[20:24], "big")
                self.assertGreaterEqual(width, size)
                self.assertGreaterEqual(height, size)

    def test_optional_native_setup_and_yaml_takeover_contract(self):
        wizard = (COMPONENT / "config_flow.py").read_text(encoding="utf8")
        for name in ("charger", "charger_details", "charger_electrical",
                     "asset", "sources", "verify"):
            self.assertIn("async_step_" + name, wizard)
        self.assertIn('vol.Optional("control_entity")', wizard)
        self.assertIn('user_input.get("control_entity")', wizard)
        self.assertIn('selector.NumberSelectorMode.BOX', wizard)
        self.assertIn('data=next_data, options=next_options', wizard)
        self.assertIn('if key != "configuration"', wizard)
        self.assertIn('entry.entry_id not in self.hass.data.get(DOMAIN, {})', wizard)
        cards = (COMPONENT / "frontend" / "robotix-multicharge.js").read_text(
            encoding="utf8"
        )
        self.assertIn("configuration_managed_by_yaml", cards)
        self.assertIn("canEditSettings()", cards)
        for language in ("en", "nl", "fr", "da", "nb", "sv", "de", "es"):
            t = json.loads((COMPONENT / "translations" / (language + ".json")).read_text(
                encoding="utf8"
            ))
            for step in ("charger_details", "charger_electrical"):
                self.assertTrue(t["config"]["step"][step]["title"])
                self.assertTrue(t["config"]["step"][step]["description"])
            self.assertEqual(
                set(t["config"]["step"]["charger"]["data"]),
                {"action", "name", "control_entity", "configure_details", "add_another"}
            )

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

    def test_eight_locales_preserve_all_native_entity_keys(self):
        reference = json.loads((COMPONENT / "strings.json").read_text(encoding="utf8"))
        for lang in ("en", "nl", "fr", "da", "nb", "sv", "de", "es"):
            with self.subTest(language=lang):
                translated = json.loads(
                    (COMPONENT / "translations" / (lang + ".json")).read_text(
                        encoding="utf8"
                    )
                )
                for platform, entities in reference["entity"].items():
                    self.assertEqual(
                        set(entities), set(translated["entity"][platform])
                    )
                    for uid, original in entities.items():
                        item = translated["entity"][platform][uid]
                        self.assertTrue(item.get("name"))
                        self.assertEqual(
                            set(original.get("state", {})),
                            set(item.get("state", {}))
                        )
                        self.assertTrue(all(item.get("state", {}).values()))
                self.assertEqual(
                    translated["entity"]["select"]["kind"]["state"].keys(),
                    reference["entity"]["select"]["kind"]["state"].keys()
                )

    def test_effective_power_is_owner_projection_not_second_meter(self):
        runtime = (COMPONENT / "runtime.py").read_text(encoding="utf8")
        sensor = (COMPONENT / "sensor.py").read_text(encoding="utf8")
        self.assertIn('"effective_power_kw"', runtime)
        self.assertIn('"CHARGING_SESSION_UNCONFIRMED"', runtime)
        self.assertIn('sessions = self.executor.session_snapshot()', runtime)
        self.assertIn('self.observations["chargers"]', runtime)
        self.assertIn(
            '_LogicalEvidenceSensor("asset", asset, runtime, "power")', sensor
        )
        self.assertNotIn('effective_power_entity', runtime)

    def test_one_physical_writer_no_bypass_in_setup_sensors_or_gui(self):
        for name in ("__init__.py", "sensor.py", "config_flow.py", "runtime.py",
                     "command_query.py"):
            source = (COMPONENT / name).read_text(encoding="utf8")
            self.assertNotIn("services.async_call(", source)
        executor = (COMPONENT / "execution.py").read_text(encoding="utf8")
        self.assertIn("services.async_call(", executor)
        self.assertIn('"switch", "turn_on" if action == "start" else "turn_off"', executor)
        self.assertIn('"INDEPENDENT_POWER_READBACK"', executor)
        self.assertIn("async def supervise(", executor)
        native = (COMPONENT / "__init__.py").read_text(encoding="utf8")
        self.assertIn("async_track_state_change_event", native)
        self.assertIn("register_command_query(hass)", native)
        api = (COMPONENT / "command_query.py").read_text(encoding="utf8")
        self.assertIn("@websocket_api.require_admin", api)

    def test_logical_devices_not_reparented(self):
        source = (COMPONENT / "sensor.py").read_text(encoding="utf8")
        self.assertNotIn("via_device", source)

    def test_native_read_only_property_surfaces(self):
        sensor = (COMPONENT / "sensor.py").read_text(encoding="utf8")
        self.assertIn("Actual power", sensor)
        self.assertIn("Battery level", sensor)
        self.assertIn("Connection", sensor)
        self.assertNotIn("services.async_call(", sensor)

    def test_no_fourth_forecast_or_session_device(self):
        """HA entities attach to existing Controller, Charger or Asset."""
        platforms = (
            "sensor.py", "binary_sensor.py", "button.py", "select.py",
            "number.py", "datetime.py", "text.py",
        )
        for filename in platforms:
            source = (COMPONENT / filename).read_text(encoding="utf8")
            self.assertNotIn("via_device", source)
            self.assertNotIn('f"session/', source)
            self.assertNotIn('f"forecast/', source)
            self.assertIn('"identifiers"', source)
        root = (COMPONENT / "__init__.py").read_text(encoding="utf8")
        for filename in platforms:
            self.assertIn('"' + filename[:-3] + '"', root)
        text = (COMPONENT / "sensor.py").read_text(encoding="utf8")
        self.assertIn("class _AssetIntentSensor", text)
        self.assertIn("class _PlanStatusSensor", text)
        self.assertIn('field in ("connected_chargers", "charging_chargers")', text)

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
