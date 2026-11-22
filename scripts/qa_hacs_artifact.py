"""Verify the exact plain-source HACS TEST archive, not a mock package.

Run after `python scripts/dev.py package`, with the target Home Assistant
version installed. The archive is the same bytes attached to the GitHub
TEST release; HACS itself installs the matching immutable repository tag.
"""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

from dev import ROOT, archive_bytes, identity

PREFIX = "custom_components/robotix_multicharge/"


def main() -> None:
    manifest = identity()
    artifact = ROOT / "dist" / f"robotix_multicharge-{manifest['version']}.zip"
    content = artifact.read_bytes()
    if content != archive_bytes():
        raise ValueError("artifact differs from current complete source tree")
    with ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
        if (not names or len(names) != len(set(names))
                or any(not x.startswith(PREFIX) or x.endswith("/")
                       or ".." in Path(x).parts or x.endswith((".pyc", ".pyo"))
                       for x in names)):
            raise ValueError("unexpected archive path or duplicate")
        if PREFIX + "manifest.json" not in names:
            raise ValueError("integration manifest missing")
        shipped = json.loads(archive.read(PREFIX + "manifest.json"))
        if shipped != manifest:
            raise ValueError("shipped metadata disagrees with source")
        if (not any(x.endswith("robotix-multicharge.js") for x in names)
                or PREFIX + "diagnostics.py" not in names):
            raise ValueError("functional UX or diagnostics missing")
        with tempfile.TemporaryDirectory(prefix="multicharge-ha-artifact-") as tmp:
            archive.extractall(tmp)
            # Import the *shipped extracted files* under the pinned actual HA
            # API, not the development checkout. Not a live EVSE qualification.
            checks = """
import json
import pathlib
import sys
from homeassistant.components.diagnostics import async_redact_data
from homeassistant import __version__ as ha_version
from custom_components.robotix_multicharge import (
    config_flow, plan_query, command_query, sensor, button, select,
    number, datetime, text, binary_sensor, diagnostics, frontend,
)
root = pathlib.Path.cwd().resolve()
installed = pathlib.Path(diagnostics.__file__).resolve()
assert installed.is_relative_to(root), (installed, root)
assert hasattr(diagnostics, 'async_get_config_entry_diagnostics')
assert hasattr(button, '_ConfirmCurrentAssetButton')
assert hasattr(plan_query, 'websocket_get_plan')
print('Extracted HACS source Home Assistant API imports PASS: ' + str(ha_version))
"""
            subprocess.run([sys.executable, "-c", checks], cwd=tmp, check=True)
    print(f"Source artifact SHA256: {hashlib.sha256(content).hexdigest()}")
    print(f"Source artifact file count: {len(names)}")
    print("HACS source artifact + native HA module import PASS")
    print("Installed HA UI, EVSE physical readback and rollback remain separate TEST qualification")


if __name__ == "__main__":
    main()
