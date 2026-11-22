"""Installed Home Assistant integration lifecycle, devices and diagnostics.

This uses the actual pinned HA engine and its official pytest fixtures.
Provider states are omitted here; physical EVSE evidence is a separate field
acceptance, not faked in this test.
"""
from __future__ import annotations

import shutil
import json
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant import config_entries
from homeassistant.components import frontend
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from homeassistant.util import yaml as yaml_util
from pytest_homeassistant.common import MockConfigEntry

from custom_components.robotix_multicharge.configuration import (
    validate_configuration, normalize_expert_json,
)
from custom_components.robotix_multicharge.const import DOMAIN
from custom_components.robotix_multicharge.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_native_setup_registry_diagnostics_and_unload(hass: HomeAssistant):
    # Real copied custom integration under a standard HA config path.
    source = (Path(__file__).resolve().parents[2] / "custom_components" /
              "robotix_multicharge")
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {
            "id": "site", "name": "Integration check",
            "mode": "Off", "max_parallel": 1, "max_power_kw": 3.6,
        },
        "assets": [{
            "id": "asset", "name": "Local name", "kind": "car",
            "requested_duration_minutes": 15,
        }],
        "chargers": [{
            "id": "charger", "name": "Test point", "kind": "on_off",
            "rated_power_kw": 3.6, "asset": "asset",
            "connected_entity": "binary_sensor.native_connected",
            "power_entity": "sensor.native_power",
            "control_owner": "external",
        }],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Robotix MultiCharge",
        data={"source": "ui", "configuration": cfg},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    # HA automatically sets up a config entry when its parent component is
    # initialized. Calling async_setup twice is forbidden on a loaded entry.
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert entry.state.value == "loaded"
    assert frontend.async_panel_exists(hass, "robotix-multicharge"), (
        "Native MultiCharge sidebar missing from real Home Assistant panel registry"
    )
    devices = dr.async_get(hass)
    for kind, uid in (("controller", "site"), ("charger", "charger"),
                      ("asset", "asset")):
        assert devices.async_get_device_by_identifier(
            (DOMAIN, f"{kind}/{uid}"), entry.entry_id
        ) is not None
    diagnostic = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostic["schema_major"] == 1
    assert len(diagnostic["chargers"]) == 1
    assert diagnostic["integration"]["active"] is True
    assert "Local name" not in str(diagnostic)
    assert "sensor.native_power" not in str(diagnostic)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
    assert not frontend.async_panel_exists(hass, "robotix-multicharge")


@pytest.mark.asyncio
async def test_native_empty_configuration_still_installs(hass: HomeAssistant):
    source = (Path(__file__).resolve().parents[2] / "custom_components" /
              "robotix_multicharge")
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {
            "id": "empty", "name": "Empty installation",
            "mode": "Off", "max_parallel": 1, "max_power_kw": 3.6,
        },
        "chargers": [],
        "assets": [],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Robotix MultiCharge",
        data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    # HA automatically sets up a config entry when its parent component is
    # initialized. Calling async_setup twice is forbidden on a loaded entry.
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert entry.state.value == "loaded"
    assert dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "controller/empty"), entry.entry_id
    ) is not None
    data = await async_get_config_entry_diagnostics(hass, entry)
    assert data["chargers"] == []
    assert data["assets"] == []
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_minimal_native_setup_then_yaml_takes_over_same_entry(hass: HomeAssistant):
    """Actual HA forms and one-way YAML adoption, without physical actuation."""
    source = (Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN)
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    assert await async_setup_component(hass, DOMAIN, {})

    wizard = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert wizard["type"] == FlowResultType.FORM
    assert wizard["step_id"] == "user"
    # All site electrical limits may be absent.
    wizard = await hass.config_entries.flow.async_configure(
        wizard["flow_id"], {"name": "Wessels Home", "max_parallel": 1}
    )
    assert wizard["step_id"] == "charger"
    # Exactly name + physical command entity are required to add a charger.
    wizard = await hass.config_entries.flow.async_configure(
        wizard["flow_id"], {
            "action": "add", "name": "Garage White",
            "control_entity": "switch.garage_white",
        }
    )
    assert wizard["step_id"] == "asset"
    wizard = await hass.config_entries.flow.async_configure(
        wizard["flow_id"], {"action": "finish"}
    )
    assert wizard["step_id"] == "sources"
    wizard = await hass.config_entries.flow.async_configure(
        wizard["flow_id"], {}
    )
    assert wizard["step_id"] == "verify"
    completed = await hass.config_entries.flow.async_configure(
        wizard["flow_id"], {"confirm": True}
    )
    assert completed["type"] == FlowResultType.CREATE_ENTRY
    entry = completed["result"]
    before_id = entry.entry_id
    assert entry.data["source"] == "ui"
    assert entry.data["configuration"]["chargers"][0]["name"] == "Garage White"
    assert entry.data["configuration"]["chargers"][0]["control_owner"] == "external"
    assert entry.data["configuration"]["chargers"][0]["physical_commissioned"] is False
    assert "max_power_kw" not in entry.data["configuration"]["controller"]

    # User adds YAML at a subsequent HA startup; there is no deletion,
    # re-pairing or second Config Entry.
    yaml_config = validate_configuration({
        **entry.data["configuration"],
        "controller": {
            **entry.data["configuration"]["controller"],
            "name": "Wessels Expert",
        },
    })
    # Reproduce the next boot after Home Assistant has loaded the YAML
    # package: the imported source must be present before an entry can run.
    hass.data[f"{DOMAIN}_source_present"] = True
    hass.config_entries.async_update_entry(
        entry, options={"configuration": entry.data["configuration"],
                        "enable_ux": True}
    )
    await hass.async_block_till_done()
    migrated = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_IMPORT},
        data=yaml_config,
    )
    await hass.async_block_till_done()
    assert migrated["type"] == FlowResultType.ABORT
    assert migrated["reason"] == "configuration_updated"
    assert entry.entry_id == before_id
    assert entry.data["source"] == "yaml"
    assert entry.data["configuration"] == yaml_config
    assert "configuration" not in entry.options
    assert entry.options["enable_ux"] is True
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state.value == "loaded"


@pytest.mark.asyncio
async def test_expert_json_include_skips_wizard_and_reuses_entry(hass: HomeAssistant):
    """Real HA 2026.11.2: JSON file via one !include, no five-step flow."""
    source = (Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN)
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)

    folder = Path(hass.config.config_dir)
    json_file = folder / "multicharge.json"
    yaml_file = folder / "configuration.yaml"
    expert = {
        "Controller": {"ID": "home", "Name": "Wessels Home"},
        "Charger": [{
            "Name": "Garage White",
            "Charging-Session-sensor": "sensor.white_session",
            "Charging-startstop-entity": "switch.white_control",
            "Charging-amp-entity": "number.white_amps",
            "ChargingAsset": "Audi Q8",
        }],
        "ChargingAsset": [{
            "Name": "Audi Q8",
            "Asset type": "Véhicule",
            "Vehicle-Charging-startstop-entity": "switch.audi_charge",
            "Vehicle-Charging-amp-entity": "number.audi_amps",
            "Vehicle-soc-sensor": "sensor.audi_soc",
        }],
    }
    json_file.write_text(json.dumps(expert), encoding="utf8")
    yaml_file.write_text(
        "robotix_multicharge: !include multicharge.json\n",
        encoding="utf8",
    )
    # The user config file is plain JSON; HA's native !include is only
    # bootstrap wiring. No config-flow-user step is requested.
    loaded = await hass.async_add_executor_job(yaml_util.load_yaml, str(yaml_file))
    assert loaded[DOMAIN]["ChargingAsset"][0]["Asset type"] == "Véhicule"
    assert await async_setup_component(hass, DOMAIN, loaded)
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.state.value == "loaded"
    assert entry.data["source"] == "json"
    assert entry.data["configuration"] == normalize_expert_json(expert)
    assert frontend.async_panel_exists(hass, "robotix-multicharge"), (
        "Direct JSON expert import must also create resident sidebar dashboard"
    )
    assert entry.data["configuration"]["controller"]["mode"] == "Off"
    assert entry.data["configuration"]["chargers"][0]["control_owner"] == "external"
    assert entry.data["configuration"]["assets"][0]["vehicle_current_entity"] == (
        "number.audi_amps"
    )
    devices = dr.async_get(hass)
    before = devices.async_get_device_by_identifier(
        (DOMAIN, "charger/garage_white"), entry.entry_id
    )
    assert before is not None
    before_id = before.id
    entry_id = entry.entry_id

    # Edit the JSON and reload through the *same* import authority:
    # Config Entry and device identities survive.
    expert["Charger"][0]["Charging-Session-sensor"] = "sensor.changed_session"
    json_file.write_text(json.dumps(expert), encoding="utf8")
    revised = await hass.async_add_executor_job(yaml_util.load_yaml, str(yaml_file))
    import_result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT, "expert_format": "json"},
        data=normalize_expert_json(revised[DOMAIN]),
    )
    await hass.async_block_till_done()
    assert import_result["type"] == FlowResultType.ABORT
    assert import_result["reason"] == "configuration_updated"
    assert entry.entry_id == entry_id
    assert entry.data["source"] == "json"
    assert entry.data["configuration"]["chargers"][0]["session_entity"] == (
        "sensor.changed_session"
    )
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert devices.async_get_device_by_identifier(
        (DOMAIN, "charger/garage_white"), entry_id
    ).id == before_id
    assert entry.state.value == "loaded"
