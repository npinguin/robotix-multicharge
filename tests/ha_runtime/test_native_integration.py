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


def test_expert_reimport_rejects_live_writer_before_entry_mutation():
    from types import SimpleNamespace
    from datetime import datetime, timezone
    from custom_components.robotix_multicharge.config_flow import (
        _assert_safe_expert_import,
    )
    old = validate_configuration({
        "controller": {
            "id": "site", "name": "Sample", "mode": "Off",
            "max_parallel": 1, "max_power_kw": 3,
        },
        "assets": [],
        "chargers": [{
            "id": "charger", "name": "Charged point",
            "kind": "on_off", "rated_power_kw": 0.5,
            "control_entity": "switch.charger",
            "connected_entity": "binary_sensor.cable",
            "power_entity": "sensor.charger_power",
            "control_owner": "multicharge",
            "physical_commissioned": True,
        }],
    })
    revised = validate_configuration({
        **old, "controller": {**old["controller"], "max_power_kw": 4},
    })
    now = datetime.now(timezone.utc)
    states = {
        "switch.charger": SimpleNamespace(state="on"),
        "sensor.charger_power": SimpleNamespace(
            state="300", attributes={"unit_of_measurement": "W"},
            last_updated=now,
        ),
    }
    executor = SimpleNamespace(
        _sessions={}, _start_pending=set(), _quarantine=set(),
        _inflight={}, _persistence_verified=True,
        _switch=lambda h, key: h.states.get(key),
    )
    runtime = SimpleNamespace(
        configuration=old, executor=executor,
        hass=SimpleNamespace(states=SimpleNamespace(get=states.get)),
    )
    with pytest.raises(ValueError, match="VERIFIED_IDLE"):
        _assert_safe_expert_import(runtime, revised)
    states["switch.charger"].state = "off"
    states["sensor.charger_power"].state = "0"
    _assert_safe_expert_import(runtime, revised)
    executor._sessions["charger"] = {"asset_id": None}
    with pytest.raises(ValueError, match="VERIFIED_IDLE"):
        _assert_safe_expert_import(runtime, revised)
    executor._sessions.clear()
    states["switch.charger"].state = "on"
    with pytest.raises(ValueError, match="VERIFIED_IDLE"):
        _assert_safe_expert_import(runtime, old, source_changed=True)
    # Presentation-only updates reuse the existing in-place path.
    _assert_safe_expert_import(runtime, validate_configuration({
        **old,
        "controller": {**old["controller"], "name": "Renamed"},
    }))
    # A switch owned by an existing EXTERNAL integration cannot silently
    # become MultiCharge's writer while still energized.
    external = validate_configuration({
        **old, "chargers": [{
            **old["chargers"][0],
            "control_owner": "external", "physical_commissioned": False,
        }],
    })
    runtime.configuration = external
    states["switch.charger"].state = "on"
    with pytest.raises(ValueError, match="VERIFIED_IDLE"):
        _assert_safe_expert_import(runtime, old)
    states["switch.charger"].state = "off"
    states["sensor.charger_power"].state = "300"
    with pytest.raises(ValueError, match="VERIFIED_IDLE"):
        _assert_safe_expert_import(runtime, old)
    states["sensor.charger_power"].state = "0"
    _assert_safe_expert_import(runtime, old)
    # An unclosed prior command is not an idle physical session even when
    # measured zero and switch OFF happen to be present.
    executor._inflight["asset"] = "unreconciled"
    with pytest.raises(ValueError, match="RECONCILED_CONTROL_STATE"):
        _assert_safe_expert_import(runtime, old)
    executor._inflight.clear()
    executor._persistence_verified = False
    with pytest.raises(ValueError, match="RECONCILED_CONTROL_STATE"):
        _assert_safe_expert_import(runtime, old)


@pytest.mark.asyncio
async def test_native_pause_resume_never_bypass_admin_authorization():
    """Admin-only native buttons may not turn a resident into a charger owner."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from custom_components.robotix_multicharge.button import (
        _AdminChargeActionButton,
    )

    fake = SimpleNamespace(
        context=SimpleNamespace(user_id="resident"),
        hass=SimpleNamespace(auth=SimpleNamespace(
            async_get_user=AsyncMock(
                return_value=SimpleNamespace(is_admin=False)
            )
        )),
    )
    with pytest.raises(RuntimeError, match="administrator"):
        await _AdminChargeActionButton._require_admin_context(fake)
    fake.context.user_id = None
    with pytest.raises(RuntimeError, match="administrator"):
        await _AdminChargeActionButton._require_admin_context(fake)
    fake.context.user_id = "admin"
    fake.hass.auth.async_get_user.return_value = SimpleNamespace(is_admin=True)
    await _AdminChargeActionButton._require_admin_context(fake)


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
            "session_entity": "sensor.native_session",
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
    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(hass)
    for kind, uid, field in (
        ("controller", "site", "price_entity"),
        ("controller", "site", "solar_entity"),
        ("controller", "site", "site_power_entity"),
        ("controller", "site", "binding_entity"),
        ("asset", "asset", "soc_entity"),
    ):
        entity_id = registry.async_get_entity_id(
            "text", DOMAIN, f"{DOMAIN}:{kind}:{uid}:{field}"
        )
        assert entity_id is not None, (kind, uid, field)
        owning = devices.async_get_device_by_identifier(
            (DOMAIN, f"{kind}/{uid}"), entry.entry_id
        )
        assert registry.async_get(entity_id).device_id == owning.id
    diagnostic = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostic["schema_major"] == 1
    assert len(diagnostic["chargers"]) == 1
    assert diagnostic["integration"]["active"] is True
    hass.states.async_set("sensor.native_session", "charging")
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    # A real native state event must trigger the existing HA subscription;
    # the test must not manually refresh to manufacture its readback.
    session = runtime.observations["chargers"]["charger"]["session"]
    assert session.value == "charging"
    assert session.quality == "ok"
    assert runtime.executor.capabilities()["charger"]["start_allowed"] is False
    # A provider session observation is never permission to command equipment.
    assert "Local name" not in str(diagnostic)
    assert "sensor.native_power" not in str(diagnostic)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
    assert not frontend.async_panel_exists(hass, "robotix-multicharge")


@pytest.mark.asyncio
async def test_variable_charger_native_power_controls_share_owning_device(hass: HomeAssistant):
    """Real HA registration, without an unqualified physical service call."""
    from homeassistant.helpers import entity_registry as er

    source = (Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN)
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {
            "id": "site", "name": "Site", "mode": "Off",
            "max_parallel": 1, "max_power_kw": 3.68,
        },
        "assets": [],
        "chargers": [{
            "id": "drive", "name": "Adjustable charger", "kind": "variable_current",
            "rated_power_kw": 3.68, "phase_count": 1,
            "phase_ids": ["L1"], "voltage_v": 230,
            "min_current_a": 6, "max_current_a": 16,
            "current_step_a": 1,
            "min_charging_power_kw": 1.84,
            "max_charging_power_kw": 3.0,
            "current_control_entity": "number.hardware_limit",
            "current_readback_entity": "sensor.hardware_current",
            "control_owner": "external",
        }],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="MultiCharge native Charger power",
        data={"source": "ui", "configuration": cfg},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "charger/drive"), entry.entry_id
    )
    assert device is not None
    registry = er.async_get(hass)
    for field in ("min_charging_power_kw", "max_charging_power_kw",
                  "set_charging_power_kw"):
        entity_id = registry.async_get_entity_id(
            "number", DOMAIN, f"{DOMAIN}:charger:drive:{field}"
        )
        assert entity_id is not None, field
        assert registry.async_get(entity_id).device_id == device.id
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_every_logical_device_auto_creates_own_native_inputs(hass: HomeAssistant):
    """No user-created input_number/input_select/helpers; one owned Config Entry.

    An adjustable Charger gets native inputs from creation even before its
    physical Amp and phase facts are known. Those entities are unavailable,
    not represented as a working physical setpoint.
    """
    from homeassistant.helpers import entity_registry as er

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {
            "id": "site", "name": "Community",
            "mode": "Automatic", "max_parallel": 1, "max_power_kw": 3.6,
        },
        "assets": [{"id": "car", "name": "Car", "kind": "car",
                    "target_soc": 80}],
        "chargers": [
            {"id": "socket", "name": "Fixed outlet",
             "kind": "on_off", "rated_power_kw": 2.0},
            {"id": "smart", "name": "Adjustable EVSE",
             "kind": "variable_current", "rated_power_kw": 3.6,
             "min_current_a": 6, "max_current_a": 16},
        ],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Independent Community",
        data={"source": "ui", "configuration": cfg},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    devreg = dr.async_get(hass)

    expected = {
        ("controller", "site"): {
            "select": ("mode", "plan_color_by", "plan_label_mode",
                       "show_indicative_forecast"),
            "number": ("max_parallel", "max_power_kw"),
            "text": ("name", "price_entity", "solar_entity",
                     "site_power_entity", "binding_entity"),
        },
        ("asset", "car"): {
            "number": ("target_soc", "requested_kwh",
                       "requested_duration_minutes", "priority",
                       "max_charge_kw", "capacity_kwh",
                       "charge_efficiency"),
            "select": ("plan_color", "ready_by_repeat", "kind"),
            "datetime": ("ready_by", "expected_connection_at", "expires_at"),
            "text": ("name", "soc_entity"),
        },
        ("charger", "socket"): {
            "select": ("plan_color", "asset"),
            "text": ("name",),
            "button": ("confirm_connection", "stop", "pause", "resume"),
        },
        ("charger", "smart"): {
            "number": ("min_charging_power_kw", "max_charging_power_kw",
                       "set_charging_power_kw"),
            "select": ("plan_color", "asset"),
            "text": ("name",),
            "button": ("confirm_connection", "stop", "pause", "resume"),
        },
    }
    for (kind, uid), platforms in expected.items():
        device = devreg.async_get_device_by_identifier(
            (DOMAIN, f"{kind}/{uid}"), entry.entry_id
        )
        assert device is not None, (kind, uid)
        for platform, fields in platforms.items():
            for field in fields:
                entity_id = registry.async_get_entity_id(
                    platform, DOMAIN, f"{DOMAIN}:{kind}:{uid}:{field}"
                )
                assert entity_id is not None, (kind, uid, field)
                assert registry.async_get(entity_id).device_id == device.id
                assert not entity_id.startswith("input_")
    for field in ("min_charging_power_kw", "max_charging_power_kw",
                  "set_charging_power_kw"):
        uid = f"{DOMAIN}:charger:smart:{field}"
        entity_id = registry.async_get_entity_id("number", DOMAIN, uid)
        assert hass.states.get(entity_id).state == "unavailable", field
        # Fixed on/off equipment cannot advertise fake current modulation.
        assert registry.async_get_entity_id(
            "number", DOMAIN, f"{DOMAIN}:charger:socket:{field}"
        ) is None
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_new_asset_from_dashboard_gets_its_own_native_inputs(
    hass: HomeAssistant,
):
    """Creating a car in the Community dashboard provisions its HA entities.

    Only the MultiCharge Config Entry is updated. The user never creates
    input_number, input_datetime or input_select helpers.
    """
    from homeassistant.helpers import entity_registry as er
    from custom_components.robotix_multicharge.command_query import (
        apply_native_preference,
    )

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "home", "name": "Home",
                       "mode": "Automatic", "max_parallel": 1},
        "assets": [], "chargers": [],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="MultiCharge Community",
        data={"source": "ui", "configuration": cfg},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    await apply_native_preference(
        hass, entry, runtime, "asset", "fresh_car",
        {"name": "Fresh car", "kind": "car"}, action="create",
    )
    await hass.async_block_till_done()
    current = entry.options["configuration"]
    assert current["assets"][0]["target_soc"] == 80
    registry = er.async_get(hass)
    for platform, field in (
        ("number", "target_soc"),
        ("number", "requested_duration_minutes"),
        ("select", "ready_by_repeat"),
        ("datetime", "ready_by"),
        ("text", "name"),
    ):
        entity_id = registry.async_get_entity_id(
            platform, DOMAIN, f"{DOMAIN}:asset:fresh_car:{field}"
        )
        assert entity_id is not None, (platform, field)
        device = dr.async_get(hass).async_get_device_by_identifier(
            (DOMAIN, "asset/fresh_car"), entry.entry_id,
        )
        assert device is not None
        assert registry.async_get(entity_id).device_id == device.id
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_options_created_charger_auto_registers_device_owned_controls(
    hass: HomeAssistant,
):
    """One Options setup adds a Charger; native controls appear automatically."""
    from homeassistant.helpers import entity_registry as er

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "home", "name": "Home",
                       "mode": "Automatic", "max_parallel": 1},
        "assets": [], "chargers": [],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="MultiCharge Community",
        data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    menu = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "charger"}
    )
    saved = await hass.config_entries.options.async_configure(
        form["flow_id"], {
            "action": "save", "id": "wallbox",
            "name": "Standalone EVSE",
            "kind": "variable_current", "rated_power_kw": 3.6,
            "min_current_a": 6, "max_current_a": 16,
        }
    )
    assert saved["type"] == FlowResultType.CREATE_ENTRY, saved
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "charger/wallbox"), entry.entry_id
    )
    assert device is not None
    for platform, field in (
        ("number", "min_charging_power_kw"),
        ("number", "max_charging_power_kw"),
        ("number", "set_charging_power_kw"),
        ("select", "asset"),
        ("button", "stop"),
    ):
        entity_id = registry.async_get_entity_id(
            platform, DOMAIN, f"{DOMAIN}:charger:wallbox:{field}"
        )
        assert entity_id is not None, (platform, field)
        assert registry.async_get(entity_id).device_id == device.id
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_options_flow_is_device_setup_not_daily_charge_operations(
    hass: HomeAssistant,
):
    """HA Options may bind and commission devices; everyday controls are native."""
    source = (Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN)
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {
            "id": "site", "name": "Independent home",
            "mode": "Automatic", "max_parallel": 1, "max_power_kw": 3.6,
        },
        "assets": [{"id": "car", "name": "Car", "kind": "car",
                    "target_soc": 80}],
        "chargers": [{
            "id": "drive", "name": "Drive", "kind": "on_off",
            "rated_power_kw": 3.6, "control_entity": "switch.drive",
        }],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Standalone MultiCharge",
        data={"source": "ui", "configuration": cfg},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    scope = {
        "controller": (
            {"name", "phase_limits_a", "price_entity"},
            {"mode", "max_parallel", "max_power_kw"},
        ),
        "asset": (
            {"name", "kind", "soc_entity", "capacity_kwh"},
            {"target_soc", "ready_by", "ready_by_repeat", "priority",
             "requested_kwh", "requested_duration_minutes"},
        ),
        "charger": (
            {"kind", "control_entity", "connected_entity", "power_entity"},
            {"asset", "control_owner", "physical_commissioned",
             "min_charging_power_kw", "max_charging_power_kw"},
        ),
        "commission": (
            {"charger_id", "commission", "exclusive_writer_confirmed",
             "electrical_limits_confirmed"},
            {"mode", "max_parallel", "ready_by"},
        ),
    }
    for step, (required, prohibited) in scope.items():
        menu = await hass.config_entries.options.async_init(entry.entry_id)
        assert menu["type"] == FlowResultType.MENU
        assert step in menu["menu_options"]
        form = await hass.config_entries.options.async_configure(
            menu["flow_id"], {"next_step_id": step}
        )
        assert form["type"] == FlowResultType.FORM
        available = {
            key.schema if hasattr(key, "schema") else key
            for key in form["data_schema"].schema
        }
        assert required <= available, (step, required - available)
        assert not (prohibited & available), (step, prohibited & available)

    # User confirmation alone does not prove physical command readiness.
    # An unqualified generic charger remains external, with no HA write.
    menu = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "commission"}
    )
    rejected = await hass.config_entries.options.async_configure(
        form["flow_id"], {
            "charger_id": "drive", "commission": True,
            "exclusive_writer_confirmed": False,
            "electrical_limits_confirmed": False,
        }
    )
    assert rejected["type"] == FlowResultType.FORM
    assert rejected["errors"]["base"] == "invalid_config"
    assert entry.data["configuration"] == cfg
    assert entry.options.get("configuration") is None
    assert await hass.config_entries.async_unload(entry.entry_id)


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
    assert wizard["type"] == FlowResultType.MENU
    assert wizard["step_id"] == "user"
    assert set(wizard["menu_options"]) == {"guided", "expert"}
    wizard = await hass.config_entries.flow.async_configure(
        wizard["flow_id"], {"next_step_id": "guided"}
    )
    assert wizard["type"] == FlowResultType.FORM
    assert wizard["step_id"] == "guided"
    # All site electrical limits may be absent.
    wizard = await hass.config_entries.flow.async_configure(
        wizard["flow_id"], {"name": "Home charging", "max_parallel": 1}
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
        "Controller": {"ID": "home", "Name": "Home charging"},
        "Charger": [{
            "Name": "Garage White",
            "Charging-Session-sensor": "sensor.white_session",
            "Charging-startstop-entity": "switch.white_control",
            "Charging-amp-entity": "number.white_amps",
            "ChargingAsset": "Family car",
        }],
        "ChargingAsset": [{
            "Name": "Family car",
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
    expert["Controller"]["Mode"] = "Economy"
    expert["Controller"]["Max-power-kW"] = 7.2
    expert["ChargingAsset"][0]["Requested-kWh"] = 3.5
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
    assert entry.data["configuration"]["controller"]["mode"] == "Economy"
    assert entry.data["configuration"]["controller"]["max_power_kw"] == 7.2
    assert entry.data["configuration"]["assets"][0]["requested_kwh"] == 3.5
    # Reimport preserves one Config Entry without silently commissioning
    # an EVSE or changing the existing external writer.
    assert entry.data["configuration"]["chargers"][0]["control_owner"] == "external"
    assert entry.data["configuration"]["chargers"][0]["physical_commissioned"] is False
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert devices.async_get_device_by_identifier(
        (DOMAIN, "charger/garage_white"), entry_id
    ).id == before_id
    assert entry.state.value == "loaded"


@pytest.mark.asyncio
async def test_native_yaml_options_review_save_and_recorder_identity(hass: HomeAssistant):
    """Real pinned Home Assistant Options Flow: edit, validate, review and save."""
    import yaml

    source = (Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN)
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    initial = validate_configuration({
        "controller": {
            "id": "home", "name": "Original home", "mode": "Off",
            "max_parallel": 1,
        },
        "assets": [],
        "chargers": [],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Robotix MultiCharge",
        data={"source": "ui", "configuration": initial},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    devices = dr.async_get(hass)
    controller_before = devices.async_get_device_by_identifier(
        (DOMAIN, "controller/home"), entry.entry_id
    )
    assert controller_before is not None

    opts = await hass.config_entries.options.async_init(entry.entry_id)
    assert opts["type"] == FlowResultType.MENU
    assert "yaml" in opts["menu_options"]
    opts = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"next_step_id": "yaml"}
    )
    assert opts["type"] == FlowResultType.FORM
    assert opts["step_id"] == "yaml"

    # Invalid/ambiguous YAML must not silently overwrite an existing key.
    opts = await hass.config_entries.options.async_configure(
        opts["flow_id"], {
            "mode": "replace",
            "yaml_text": "controller:\n  id: home\n  id: other\n",
        },
    )
    assert opts["step_id"] == "yaml"
    assert opts["errors"]["base"] == "invalid_config"
    assert "duplicate YAML key" in opts["description_placeholders"]["note"]
    assert entry.data["configuration"] == initial
    assert not entry.options.get("configuration")

    updated = validate_configuration({
        "controller": {**initial["controller"], "name": "Reviewed home"},
        "assets": [{"id": "guest", "name": "Guest", "kind": "car"}],
        "chargers": [{
            "id": "outside", "name": "Outside", "kind": "on_off",
            "rated_power_kw": 3.6, "control_entity": "switch.outside",
            "control_owner": "external", "physical_commissioned": False,
        }],
    })
    opts = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"mode": "replace",
                          "yaml_text": yaml.safe_dump(updated, sort_keys=False)}
    )
    assert opts["type"] == FlowResultType.FORM
    assert opts["step_id"] == "yaml_review"
    assert "Outside" not in str(opts.get("description_placeholders", {})) or (
        "outside" in str(opts["description_placeholders"]))
    assert entry.options.get("configuration") is None, (
        "Preview and review must not persist any configuration"
    )

    # Continue editing is a real native server-backed step, not a UI rewind.
    opts = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"edit_again": True}
    )
    assert opts["step_id"] == "yaml"
    opts = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"mode": "replace",
                          "yaml_text": yaml.safe_dump(updated, sort_keys=False)}
    )
    assert opts["step_id"] == "yaml_review"
    saved = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"confirm": True}
    )
    assert saved["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.entry_id in [x.entry_id for x in hass.config_entries.async_entries(DOMAIN)]
    assert entry.data["source"] == "ui"
    assert entry.options["configuration"]["controller"]["name"] == "Reviewed home"
    assert entry.options["configuration"]["chargers"][0]["control_owner"] == "external"
    assert entry.options["configuration"]["chargers"][0]["physical_commissioned"] is False
    assert devices.async_get_device_by_identifier(
        (DOMAIN, "controller/home"), entry.entry_id
    ).id == controller_before.id
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state.value == "loaded"


@pytest.mark.asyncio
async def test_new_install_expert_single_ui_config_entry_four_chargers_four_assets(
    hass: HomeAssistant,
):
    """UC01/02/17: full native one-shot setup; no YAML file, package or helper."""
    import yaml

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    assert await async_setup_component(hass, DOMAIN, {})
    start = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert start["type"] == FlowResultType.MENU
    assert "expert" in start["menu_options"]
    editor = await hass.config_entries.flow.async_configure(
        start["flow_id"], {"next_step_id": "expert"}
    )
    assert editor["step_id"] == "expert"

    chargers = [
        {"id": key, "name": key.replace("_", " ").title(), "kind": "on_off",
         "rated_power_kw": 3.6, "control_entity": f"switch.{key}",
         "connected_entity": f"binary_sensor.{key}_connected",
         "power_entity": f"sensor.{key}_power",
         "control_owner": "external", "physical_commissioned": False}
        for key in ("white", "black", "peblar", "utility")
    ]
    assets = [
        {"id": key, "name": key.title(), "kind": "car",
         "target_soc": 80, "soc_entity": f"sensor.{key}_soc"}
        for key in ("audi", "vw", "guest1", "guest2")
    ]
    proposed = {
        "controller": {
            "id": "home", "name": "Independent charge site",
            "mode": "Automatic", "max_parallel": 4,
            "max_power_kw": 3.6, "price_entity": "sensor.prices",
            "plan_color_by": "vehicle",
        },
        "chargers": chargers, "assets": assets,
    }
    review = await hass.config_entries.flow.async_configure(
        editor["flow_id"], {
            "yaml_text": yaml.safe_dump(proposed, sort_keys=False)
        }
    )
    assert review["step_id"] == "expert_review"
    assert not hass.config_entries.async_entries(DOMAIN), (
        "Expert draft/review must not create a Config Entry"
    )
    # Back to the actual draft, correct one field and review again.
    again = await hass.config_entries.flow.async_configure(
        review["flow_id"], {"edit_again": True}
    )
    assert again["step_id"] == "expert"
    review = await hass.config_entries.flow.async_configure(
        again["flow_id"], {
            "yaml_text": yaml.safe_dump(proposed, sort_keys=False)
        }
    )
    assert review["step_id"] == "expert_review"
    approved = await hass.config_entries.flow.async_configure(
        review["flow_id"], {"confirm": True}
    )
    assert approved["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    entry = approved["result"]
    assert entry.data["source"] == "ui", "GUI owns the source, not file YAML"
    assert entry.data["configuration"] == validate_configuration(proposed)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    reg = dr.async_get(hass)
    for key in ("white", "black", "peblar", "utility"):
        assert reg.async_get_device_by_identifier(
            (DOMAIN, f"charger/{key}"), entry.entry_id,
        ) is not None
    for key in ("audi", "vw", "guest1", "guest2"):
        assert reg.async_get_device_by_identifier(
            (DOMAIN, f"asset/{key}"), entry.entry_id,
        ) is not None
    assert reg.async_get_device_by_identifier(
        (DOMAIN, "controller/home"), entry.entry_id,
    ) is not None
    # Daily/expert Settings remain enabled via the *same* Config Entry.
    options = await hass.config_entries.options.async_init(entry.entry_id)
    assert options["type"] == FlowResultType.MENU
    assert "yaml" in options["menu_options"]
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_initial_bulk_yaml_rejects_templates_duplicate_keys_and_commissioning(
    hass: HomeAssistant,
):
    """UC01/02 negative paths: no hidden provider creation or physical writer."""
    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    assert await async_setup_component(hass, DOMAIN, {})
    start = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    editor = await hass.config_entries.flow.async_configure(
        start["flow_id"], {"next_step_id": "expert"}
    )
    documents = (
        "controller:\n  id: home\n  id: another\n",
        "template:\n- sensor: []\ncontroller:\n  id: home\n",
        "controller:\n  id: home\n  name: Site\n"
        "chargers:\n- id: x\n  name: X\n  kind: on_off\n"
        "  rated_power_kw: 3.6\n  control_entity: switch.x\n"
        "  control_owner: multicharge\n  physical_commissioned: true\n",
    )
    for doc in documents:
        editor = await hass.config_entries.flow.async_configure(
            editor["flow_id"], {"yaml_text": doc}
        )
        assert editor["step_id"] == "expert"
        assert editor["errors"]["base"] == "invalid_config"
        assert not hass.config_entries.async_entries(DOMAIN)
    # Full empty-site source is valid and cannot accidentally start charging.
    good = ("controller:\n  id: home\n  name: Empty site\n"
            "  mode: 'Off'\n  max_parallel: 1\n")
    preview = await hass.config_entries.flow.async_configure(
        editor["flow_id"], {"yaml_text": good}
    )
    assert preview["step_id"] == "expert_review"
    not_confirmed = await hass.config_entries.flow.async_configure(
        preview["flow_id"], {"confirm": False}
    )
    assert not_confirmed["step_id"] == "expert_review"
    assert not hass.config_entries.async_entries(DOMAIN)
