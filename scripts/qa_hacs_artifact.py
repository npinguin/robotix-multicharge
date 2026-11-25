"""Verify the exact plain-source HACS TEST archive, not a mock package.

Run after `python scripts/dev.py package`, with the target Home Assistant
version installed. The archive is the same bytes attached to the GitHub
TEST release; HACS itself installs the matching immutable repository tag.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

from dev import ROOT, archive_bytes, identity

PREFIX = "custom_components/robotix_multicharge/"

# Each invocation imports its own immutable/extracted code in a separate
# interpreter, using actual native Home Assistant Store I/O. These are isolated
# component checkpoint tests, not a replacement for full HA backup/restore.
CHECKPOINT_TEST = r"""
import asyncio
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from custom_components.robotix_multicharge.configuration import validate_configuration
from custom_components.robotix_multicharge.runtime import MultiChargeRuntime

root = pathlib.Path.cwd()
mode, config_dir, version = sys.argv[1:]
directory = pathlib.Path(config_dir)
assert pathlib.Path(sys.modules[MultiChargeRuntime.__module__].__file__).is_relative_to(root)
assert json.loads((root / "custom_components/robotix_multicharge/manifest.json").read_text())["version"] == version
config_path = directory / "fixture_configuration.json"
expected_path = directory / "fixture_receipts.json"

async def run():
    hass = HomeAssistant(str(directory))
    store = Store(hass, 1, "robotix_multicharge_test-entry_control")
    if mode == "seed":
        cfg = validate_configuration({
            "controller": {"id": "home", "name": "Home", "mode": "Off"},
            "assets": [{"id": "car", "name": "Car", "requested_duration_minutes": 15}],
            "chargers": [{"id": "drive", "name": "Drive", "kind": "on_off",
                          "rated_power_kw": 3.6, "asset": "car",
                          "control_entity": "switch.drive",
                          "connected_entity": "binary_sensor.plug",
                          "power_entity": "sensor.power",
                          "control_owner": "external"}],
        })
        runtime = MultiChargeRuntime(hass, cfg)
        stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
        receipts = [
            {"charger_id": "drive", "asset_id": "car",
             "started_at": (stamp+timedelta(minutes=i*2)).isoformat(),
             "ended_at": (stamp+timedelta(minutes=i*2+1)).isoformat(),
             "actual_energy_kwh": 0.05, "physical_stop_confirmed": True}
            for i in range(200)
        ]
        snapshot = {**runtime.executor.export_state(), "sessions": receipts,
                    "paused": ["drive"], "completed": {"car": "old-completed"},
                    "inflight": {"car": "old-unresolved"}}
        runtime.attach_control_store(store, snapshot)
        assert runtime.executor._persistence_verified
        assert await runtime.persist_control_state()
        config_path.write_text(json.dumps(cfg))
        expected_path.write_text(json.dumps(receipts))
        return
    raw = json.loads(config_path.read_text())
    receipts = json.loads(expected_path.read_text())
    original = await store.async_load()
    if mode == "reject_direct":
        try:
            validate_configuration(raw)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected old validator to reject new configuration")
        # Exercise the old control reader independently using the original
        # supported subset, but never invoke its writer on the upgraded data.
        raw["controller"].pop("power_adjustment_interval_minutes", None)
        raw["chargers"][0].pop("dedicated_asset_id", None)
        runtime = MultiChargeRuntime(hass, validate_configuration(raw))
        runtime.attach_control_store(store, original)
        assert not runtime.executor._persistence_verified
        assert await Store(hass, 1, "robotix_multicharge_test-entry_control").async_load() == original
        return
    cfg = validate_configuration(raw)
    runtime = MultiChargeRuntime(hass, cfg)
    runtime.attach_control_store(store, original)
    assert runtime.executor._persistence_verified
    assert runtime.executor.export_state()["sessions"] == receipts
    assert runtime.executor.export_state()["paused"] == ["drive"]
    assert runtime.executor.export_state()["completed"] == {"car": "old-completed"}
    assert runtime.executor.export_state()["inflight"] == {"car": "old-unresolved"}
    assert not runtime.executor.session_snapshot()
    assert (cfg["controller"]["id"], cfg["assets"][0]["id"],
            cfg["chargers"][0]["id"]) == ("home", "car", "drive")
    if mode == "upgrade":
        cfg["controller"]["power_adjustment_interval_minutes"] = 7
        cfg["chargers"][0]["dedicated_asset_id"] = "car"
        cfg = validate_configuration(cfg)
        runtime.configuration = cfg
        stamp = datetime(2026, 1, 2, tzinfo=timezone.utc)
        receipts.append({"charger_id": "drive", "asset_id": "car",
                         "started_at": stamp.isoformat(),
                         "ended_at": (stamp+timedelta(minutes=1)).isoformat(),
                         "actual_energy_kwh": 0.07, "physical_stop_confirmed": True})
        runtime.executor.restore_state({**runtime.executor.export_state(), "sessions": receipts})
        assert runtime.executor._persistence_verified
        assert await runtime.persist_control_state()
        config_path.write_text(json.dumps(cfg))
        expected_path.write_text(json.dumps(receipts))
    elif mode == "forward":
        assert len(receipts) == 201
        assert cfg["controller"]["power_adjustment_interval_minutes"] == 7
        assert cfg["chargers"][0]["dedicated_asset_id"] == "car"
        assert "tariff_bindings" in original and "pending_cost_archive" in original
    else:
        assert mode == "rollback"
        assert len(receipts) == 200
        assert await runtime.persist_control_state()
        assert (await Store(hass, 1, "robotix_multicharge_test-entry_control").async_load())["sessions"] == receipts

asyncio.run(run())
print("Native artifact checkpoint", mode, version, "PASS")
"""


# Invoke the native HA Core archive writer and startup restoration on
# disposable test directories only. No production .storage access.
BACKUP_TEST = r"""
import asyncio
import json
from pathlib import Path
import sys
from homeassistant.backup_restore import restore_backup, RESTORE_BACKUP_FILE
from homeassistant.components.backup.manager import CoreBackupReaderWriter
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant

action, config, archive = sys.argv[1:]
config = Path(config)
archive = Path(archive)
assert config.is_dir() and archive.parent != config
if action == "backup":
    async def run():
        hass = HomeAssistant(str(config))
        writer = CoreBackupReaderWriter(hass)
        metadata = {
            "compressed": True, "date": "2026-11-25T00:00:00+00:00",
            "extra": {}, "homeassistant": {
                "exclude_database": False, "version": HA_VERSION},
            "name": "MultiCharge checkpoint QA", "protected": False,
            "slug": archive.stem, "type": "partial", "version": 2,
        }
        path, size = await hass.async_add_executor_job(
            writer._mkdir_and_generate_backup_contents, metadata, True, None, archive)
        assert path == archive and size > 0
    asyncio.run(run())
else:
    assert action == "restore" and archive.is_file()
    (config / RESTORE_BACKUP_FILE).write_text(json.dumps({
        "path": str(archive), "password": None, "remove_after_restore": False,
        "restore_database": True, "restore_homeassistant": True,
    }))
    assert restore_backup(str(config))
    assert archive.is_file()
    assert not (config / RESTORE_BACKUP_FILE).exists()
print("Native HA Core", action, archive.name, "PASS")
"""


def verify_rollback_checkpoint(candidate, manifest, work):
    request = json.loads((ROOT / "release/TEST_REQUEST.json").read_text())
    rollback = request["rollback_evidence"]
    tag, filename = rollback["tag"], rollback["artifact"]
    if tag != "v"+filename.removeprefix("robotix_multicharge-").removesuffix(".zip"):
        raise ValueError("rollback artifact identity mismatch")
    # Verify the actual immutable tag/asset bytes; never substitute current
    # checkout files or a simulated predecessor implementation.
    url = "https://github.com/npinguin/robotix-multicharge/releases/download/"
    with urlopen(url + tag + "/" + filename, timeout=60) as response:
        content = response.read(25_000_001)
    if len(content) > 25_000_000 or hashlib.sha256(content).hexdigest() != rollback["sha256"]:
        raise ValueError("rollback artifact digest mismatch")
    prior = work / "prior"
    prior.mkdir()
    with ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
        if (not names or len(names) != len(set(names))
                or any(not name.startswith(PREFIX) or ".." in Path(name).parts
                       or name.endswith("/") for name in names)):
            raise ValueError("invalid rollback archive paths")
        if json.loads(archive.read(PREFIX + "manifest.json"))["version"] != tag[1:]:
            raise ValueError("rollback archive version mismatch")
        archive.extractall(prior)
    pre = work / "pre-upgrade"
    pre.mkdir()
    upgraded = work / "upgraded"
    restored = work / "restored"
    def run(code, action, state, version):
        subprocess.run([sys.executable, "-c", CHECKPOINT_TEST, action, str(state), version],
                       cwd=code, check=True)

    def backup(action, state, archive):
        subprocess.run([sys.executable, "-c", BACKUP_TEST, action, str(state), str(archive)],
                       cwd=work, check=True)

    def install(code, state):
        target = state / PREFIX
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(code / PREFIX, target, ignore=shutil.ignore_patterns("__pycache__"))

    def verify_installed(code, state):
        expected = {p.relative_to(code / PREFIX): p.read_bytes()
                    for p in (code / PREFIX).rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts}
        actual = {p.relative_to(state / PREFIX): p.read_bytes()
                  for p in (state / PREFIX).rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts}
        assert actual == expected, "Restored integration differs from exact artifact"

    run(prior, "seed", pre, tag[1:])
    install(prior, pre)
    before = work / "pre-upgrade.tar"
    after = work / "upgraded.tar"
    backup("backup", pre, before)
    shutil.copytree(pre, upgraded)
    install(candidate, upgraded)
    run(candidate, "upgrade", upgraded, manifest["version"])
    backup("backup", upgraded, after)
    run(prior, "reject_direct", upgraded, tag[1:])

    # Restore into a genuinely upgraded directory, not an empty or prior
    # directory. The actual native HA startup restore must replace code/state.
    shutil.copytree(upgraded, restored)
    backup("restore", restored, before)
    verify_installed(prior, restored)
    run(prior, "rollback", restored, tag[1:])
    backup("restore", restored, after)
    verify_installed(candidate, restored)
    run(candidate, "forward", restored, manifest["version"])
    assert before.is_file() and after.is_file()
    print("Exact predecessor/candidate native Core backup/restore and Store checkpoint PASS")
    print("Actual site backup UI, EVSE STOP and physical acceptance are separate gates")


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
from homeassistant.const import __version__ as ha_version
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
            with tempfile.TemporaryDirectory(prefix="multicharge-rollback-") as state:
                verify_rollback_checkpoint(Path(tmp), manifest, Path(state))
    print(f"Source artifact SHA256: {hashlib.sha256(content).hexdigest()}")
    print(f"Source artifact file count: {len(names)}")
    print("HACS source artifact + native HA module import PASS")
    print("Installed HA UI and physical/site readback remain separate qualification")


if __name__ == "__main__":
    main()
