"""Static source checks that do not need a Home Assistant installation."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "robotix_multicharge"


class PackageTest(unittest.TestCase):
    def test_manifest_is_standalone(self):
        m = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf8"))
        self.assertEqual(m["domain"], "robotix_multicharge")
        self.assertTrue(m["config_flow"])
        self.assertEqual(m["dependencies"], [])
        self.assertEqual(m["requirements"], [])
        self.assertEqual(len(list((ROOT / "custom_components").iterdir())), 1)

    def test_translation_source_consistency(self):
        self.assertEqual(
            json.loads((COMPONENT / "strings.json").read_text(encoding="utf8")),
            json.loads((COMPONENT / "translations/en.json").read_text(encoding="utf8")),
        )

    def test_bootstrap_cannot_write_to_hardware(self):
        source = (COMPONENT / "__init__.py").read_text(encoding="utf8")
        self.assertNotIn("async_call(", source)
        self.assertNotIn("async_track_", source)
        self.assertNotIn("async_forward_entry", source)

    def test_no_legacy_runtime_import(self):
        for path in COMPONENT.glob("*.py"):
            self.assertNotIn("ev_" + "smart_charging", path.read_text(encoding="utf8"))


if __name__ == "__main__":
    unittest.main()
