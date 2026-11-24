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


def test_native_expert_editor_json_defaults_and_rejects_duplicate_fields():
    """Native GUI JSON is data-only and duplicate keys cannot overwrite silently."""
    from custom_components.robotix_multicharge.config_flow import (
        _parse_editor_yaml,
    )
    from custom_components.robotix_multicharge.configuration import (
        configuration_json,
    )
    payload = configuration_json(validate_configuration({
        "controller": {
            "id": "home", "name": "House", "mode": "Off",
            "max_parallel": 1, "max_power_kw": 3.6,
        },
        "assets": [], "chargers": [],
    }))
    assert _parse_editor_yaml(payload) == json.loads(payload)
    with pytest.raises(ValueError, match="duplicate YAML key"):
        _parse_editor_yaml('{"controller": {}, "controller": {}}')
    with pytest.raises(ValueError):
        _parse_editor_yaml('{broken json')
    assert _parse_editor_yaml('{"controller": {"id":"home"}, "assets": [], '
                              '"chargers": []}')["assets"] == []


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
        _context=SimpleNamespace(user_id="resident"),
        hass=SimpleNamespace(auth=SimpleNamespace(
            async_get_user=AsyncMock(
                return_value=SimpleNamespace(is_admin=False)
            )
        )),
    )
    with pytest.raises(RuntimeError, match="administrator"):
        await _AdminChargeActionButton._require_admin_context(fake)
    fake._context.user_id = None
    with pytest.raises(RuntimeError, match="administrator"):
        await _AdminChargeActionButton._require_admin_context(fake)
    fake._context.user_id = "admin"
    fake.hass.auth.async_get_user.return_value = SimpleNamespace(is_admin=True)
    await _AdminChargeActionButton._require_admin_context(fake)


@pytest.mark.asyncio
async def test_all_native_owner_settings_deny_resident_service_bypass():
    """Backend enforces HA admin regardless of a browser's hidden controls."""
    from types import SimpleNamespace
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock
    from custom_components.robotix_multicharge.command_query import (
        require_native_admin,
    )
    from custom_components.robotix_multicharge.select import _OwnedSelect
    from custom_components.robotix_multicharge.number import _AssetNumber
    from custom_components.robotix_multicharge.datetime import _AssetDateTime
    from custom_components.robotix_multicharge.text import (
        _OwnerName, _AssetWindowText,
    )

    fake = SimpleNamespace(
        _context=SimpleNamespace(user_id="resident"),
        hass=SimpleNamespace(auth=SimpleNamespace(
            async_get_user=AsyncMock(
                return_value=SimpleNamespace(is_admin=False)
            )
        )),
    )
    for action in (
        lambda: _OwnedSelect.async_select_option(fake, "off"),
        lambda: _AssetNumber.async_set_native_value(fake, 40),
        lambda: _AssetDateTime.async_set_value(
            fake, datetime.now(timezone.utc)),
        lambda: _OwnerName.async_set_value(fake, "Other"),
        lambda: _AssetWindowText.async_set_value(fake, "22:00-06:00"),
    ):
        with pytest.raises(RuntimeError, match="administrator"):
            await action()
    fake._context.user_id = None
    with pytest.raises(RuntimeError, match="administrator"):
        await require_native_admin(fake.hass, fake._context)
    fake._context.user_id = "admin"
    fake.hass.auth.async_get_user.return_value = SimpleNamespace(
        is_admin=True
    )
    await require_native_admin(fake.hass, fake._context)


@pytest.mark.asyncio
async def test_clean_ha_minimal_unassigned_charger_has_finite_manual_hold(
    hass: HomeAssistant,
):
    """UC05/11/17: a clean site can configure a suitable on/off role safely."""
    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    hass.states.async_set("switch.suitable_plug", "off")
    config = validate_configuration({
        "controller": {
            "id": "home", "name": "Minimal house",
            "mode": "Force Charge", "max_parallel": 1,
            "max_power_kw": 2.0,
        },
        "assets": [],
        "chargers": [{
            "id": "plug", "name": "Unqualified suitable plug",
            "kind": "on_off", "rated_power_kw": 1.0,
            "phase_count": 1,
            "control_entity": "switch.suitable_plug",
            "control_owner": "external",
            "physical_commissioned": False,
        }],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Minimal independent site",
        data={"source": "ui", "configuration": config},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    assert len(runtime.configuration["assets"]) == 0
    assert runtime.configuration["controller"]["mode"] == "Force Charge"
    assert runtime.executor.capabilities()["plug"]["manual_one_off_reason"] == (
        "EXTERNAL_WRITER_OWNS_CHARGER"
    )
    assert runtime.executor.capabilities()["plug"]["manual_one_off_allowed"] is False
    devices = dr.async_get(hass)
    assert devices.async_get_device_by_identifier(
        (DOMAIN, "controller/home"), entry.entry_id
    )
    assert devices.async_get_device_by_identifier(
        (DOMAIN, "charger/plug"), entry.entry_id
    )
    issued = []
    async def unsafe_vendor_start(call):
        issued.append(call)
    hass.services.async_register("switch", "turn_on", unsafe_vendor_start)
    outcome = await runtime.executor.execute(
        "plug", "start", manual_request={"duration_minutes": 10},
    )
    assert outcome["status"] == "rejected"
    assert not issued, "A native switch state is not cable or permission proof"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_native_recorder_history_pricing_reuses_one_ha_query_without_billing(
    hass: HomeAssistant, monkeypatch,
):
    """UC15: actual HA Recorder API seam, complete effective interval coverage.

    Source samples are isolated; this does not claim site/utility billing proof.
    """
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from homeassistant.components import recorder
    from custom_components.robotix_multicharge.contracts import PriceSlot
    from custom_components.robotix_multicharge.history import read_actual_history

    at = datetime.now(timezone.utc)
    start = at - timedelta(minutes=30)
    mid = start + timedelta(minutes=15)
    end = at - timedelta(seconds=5)
    samples = [
        SimpleNamespace(state="2000", attributes={"unit_of_measurement": "W"},
                        last_updated=start),
        SimpleNamespace(state="4000", attributes={"unit_of_measurement": "W"},
                        last_updated=mid),
    ]
    recorder_calls = []
    class NativeRecorder:
        async def async_add_executor_job(self, fn, *args):
            recorder_calls.append((fn, args))
            return {"sensor.native_power": samples}
    monkeypatch.setattr(recorder, "get_instance", lambda _hass: NativeRecorder())
    hass.config.components.add("recorder")
    receipt = {
        "charger_id": "charger", "asset_id": "car",
        "started_at": start.isoformat(), "ended_at": end.isoformat(),
        "actual_energy_kwh": 1.5, "energy_quality": "measured",
        "physical_stop_confirmed": True,
        "cost": None, "currency": None, "cost_quality": "unknown",
    }
    configuration = {
        "chargers": [{"id": "charger", "power_entity": "sensor.native_power"}]
    }
    slots = [
        PriceSlot(start, mid, 0.2, "EUR"),
        PriceSlot(mid, end, 0.32, "EUR"),
    ]
    rows, quality, values = await read_actual_history(
        hass, configuration, start, end,
        session_receipts=[receipt], price_slots=slots,
        include_valuations=True,
    )
    key = ("charger", receipt["started_at"], receipt["ended_at"])
    assert key in values
    assert values[key]["estimated_variable_cost_currency"] == "EUR"
    assert values[key]["estimated_variable_cost_quality"] == (
        "observed_power_integral_effective_tariff"
    )
    assert len(recorder_calls) == 1, (
        "One native HA Recorder query, not a parallel meter/history database"
    )
    assert receipt["cost"] is None, "Billed financial receipt stays immutable"
    spot = [PriceSlot(start, end, -0.2, "EUR", basis="spot")]
    _, _, rejected = await read_actual_history(
        hass, configuration, start, end,
        session_receipts=[receipt], price_slots=spot,
        include_valuations=True,
    )
    assert rejected == {}, "A negative spot price must never be billed"
    assert rows is not None
    assert quality in ("MEASURED_POWER_HISTORY", "INCOMPLETE_POWER_HISTORY",
                       "NO_RECORDED_QUARTERS")


@pytest.mark.asyncio
async def test_direct_native_ha_electricity_price_reference_without_robotix_bridge(
    hass: HomeAssistant,
):
    """UC07/17/28: real HA State/Registry source shape, no Basic dependency."""
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo
    from custom_components.robotix_multicharge.source_evidence import intervals
    from custom_components.robotix_multicharge.runtime import MultiChargeRuntime

    at = datetime.now(timezone.utc)
    zone = ZoneInfo("Europe/Brussels")
    day = at.astimezone(zone).date()
    midnight = datetime(day.year,day.month,day.day,tzinfo=zone)
    first = midnight.astimezone(timezone.utc)
    next_day = day + timedelta(days=1)
    after_day = datetime(next_day.year,next_day.month,next_day.day,
                         tzinfo=zone).astimezone(timezone.utc)
    length = int((after_day-first).total_seconds()//3600)
    observed = [
        {"start":(first+timedelta(hours=i)).astimezone(zone).isoformat(),
         "all_in": -0.02 if i == 0 else 0.24}
        for i in range(length)
    ]
    hass.states.async_set("sensor.native_all_in","0.24",{
        "unit_of_measurement":"€/kWh", "time_zone":"Europe/Brussels",
        "today":observed, "tomorrow":[], "snapshot_stale":False,
    })
    slots, quality = intervals(hass, "sensor.native_all_in", "price", at)
    assert quality == "OK"
    assert len(slots) == length
    assert slots[0].basis == "variable_reference"
    assert slots[0].effective_price_per_kwh == -0.02
    assert slots[-1].end == after_day
    runtime = MultiChargeRuntime(hass, validate_configuration({
        "controller":{
            "id":"site","name":"Independent","mode":"Economy",
            "max_parallel":1,"price_entity":"sensor.native_all_in"
        },
        "assets":[], "chargers":[],
    }))
    runtime.refresh()
    assert len(runtime.price_slots) == length
    assert runtime.observations["sources"]["tariff_quality"] == "OK"
    assert runtime.price_slots[0].basis == "variable_reference"
    hass.states.async_set("sensor.native_all_in","0.24",{
        "unit_of_measurement":"€/kWh", "time_zone":"Europe/Brussels",
        "today":observed[:-1], "snapshot_stale":False,
    })
    missing, reason = intervals(hass,"sensor.native_all_in","price",
                                datetime.now(timezone.utc))
    assert not missing
    assert reason == "INTERVAL_COVERAGE_INCOMPLETE"


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
    for kind, uid, record in (
        ("controller", "site", cfg["controller"]),
        ("charger", "charger", cfg["chargers"][0]),
        ("asset", "asset", cfg["assets"][0]),
    ):
        # Every logical device exposes ALL persisted keys without additional
        # configuration authority or per-field copy entities.
        entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}:{kind}:{uid}:configuration",
        )
        assert entity_id is not None, (kind, uid)
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.attributes["logical_owner"] == kind
        assert state.attributes["read_only_projection"] is True
        for key, value in record.items():
            assert state.attributes[key] == value, (kind, key)
        owning = devices.async_get_device_by_identifier(
            (DOMAIN, f"{kind}/{uid}"), entry.entry_id,
        )
        assert registry.async_get(entity_id).device_id == owning.id
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
                       "show_indicative_forecast", "solar_source_kind",
                       "grid_power_direction"),
            "number": ("max_parallel", "max_power_kw"),
            "text": ("name", "price_entity", "solar_entity",
                     "site_power_entity", "binding_entity",
                     "solar_power_entity", "home_power_entity",
                     "grid_power_entity", "solar_surplus_entity",
                     "current_price_entity", "export_price_entity"),
        },
        ("asset", "car"): {
            "number": ("target_soc", "requested_kwh",
                       "requested_duration_minutes", "priority",
                       "max_charge_kw", "capacity_kwh",
                       "charge_efficiency"),
            "select": ("plan_color", "ready_by_repeat", "kind",
                       "continuous_charging", "opportunistic_kind",
                       "ready_day_mon", "ready_day_tue", "ready_day_wed",
                       "ready_day_thu", "ready_day_fri", "ready_day_sat",
                       "ready_day_sun"),
            "datetime": ("ready_by", "expected_connection_at",
                         "expires_at", "earliest_start_at"),
            "text": ("name", "soc_entity", "price_currency",
                     "charging_window_mon", "charging_window_tue",
                     "charging_window_wed", "charging_window_thu",
                     "charging_window_fri", "charging_window_sat",
                     "charging_window_sun"),
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
async def test_dashboard_created_charger_auto_registers_device_owned_controls(
    hass: HomeAssistant,
):
    """Real HA: dashboard typed create registers owning Charger and its Entities."""
    from homeassistant.helpers import entity_registry as er
    from custom_components.robotix_multicharge.command_query import (
        apply_native_preference,
    )
    from custom_components.robotix_multicharge.configuration import (
        configuration_revision,
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
        data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    revision = await apply_native_preference(
        hass, entry, runtime, "charger", "wallbox",
        {"name": "Standalone EVSE", "kind": "variable_current",
         "rated_power_kw": 3.6, "min_current_a": 6,
         "max_current_a": 16},
        action="create", structural=True,
        expected_revision=configuration_revision(runtime.configuration),
    )
    await hass.async_block_till_done()
    assert configuration_revision(entry.options["configuration"]) == revision
    registry = er.async_get(hass)
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "charger/wallbox"), entry.entry_id,
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
async def test_options_flow_is_not_a_yaml_or_configuration_surface(hass: HomeAssistant):
    """Owner requirement: HA Options is retired; dashboard owns runtime editing."""
    source = (Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN)
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "site", "name": "Independent home",
                       "mode": "Automatic", "max_parallel": 1},
        "assets": [{"id": "car", "name": "Car", "kind": "car"}],
        "chargers": [],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Standalone MultiCharge",
        data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "dashboard_only"
    assert not entry.options.get("configuration")
    assert entry.data["configuration"] == cfg
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_unconfigured_energy_dashboard_does_not_initialize_component(
    hass: HomeAssistant,
):
    """Optional discovery must not start Energy on clean standalone HA."""
    from unittest.mock import patch
    from custom_components.robotix_multicharge.config_flow import (
        _energy_dashboard_defaults,
    )

    assert "energy" not in hass.config.components
    with patch(
        "homeassistant.components.energy.data.async_get_manager",
    ) as manager:
        suggestions = await _energy_dashboard_defaults(hass)
        assert suggestions == {}
        manager.assert_not_called()



@pytest.mark.asyncio
async def test_dashboard_native_energy_source_mapping_no_shadow_settings(
    hass: HomeAssistant,
):
    """One dashboard source selection, no templating or Options flow."""
    from custom_components.robotix_multicharge.command_query import (
        apply_native_preference,
    )
    from custom_components.robotix_multicharge.configuration import (
        configuration_revision,
    )

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "home", "name": "Energy choice",
                       "mode": "Off", "max_parallel": 1},
        "assets": [], "chargers": [],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Standalone MultiCharge",
        data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert entry.options.get("configuration") is None
    runtime = hass.data[DOMAIN][entry.entry_id]
    revision = await apply_native_preference(
        hass, entry, runtime, "controller", "home", {
            "solar_power_entity": "sensor.ha_pv_live",
            "grid_power_entity": "sensor.ha_grid_live",
            "current_price_entity": "sensor.ha_import_price",
            "home_power_entity": "sensor.explicit_home_w",
            "solar_source_kind": "grid_export",
            "grid_power_direction": "import_positive",
        }, structural=True,
        expected_revision=configuration_revision(runtime.configuration),
    )
    await hass.async_block_till_done()
    stored = entry.options["configuration"]["controller"]
    assert configuration_revision(entry.options["configuration"]) == revision
    assert stored["solar_power_entity"] == "sensor.ha_pv_live"
    assert stored["grid_power_entity"] == "sensor.ha_grid_live"
    assert stored["current_price_entity"] == "sensor.ha_import_price"
    assert stored["home_power_entity"] == "sensor.explicit_home_w"
    assert stored["solar_source_kind"] == "grid_export"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    menu = await hass.config_entries.options.async_init(entry.entry_id)
    assert menu["type"] == FlowResultType.ABORT
    assert menu["reason"] == "dashboard_only"
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

    completed = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER},
    )
    assert completed["type"] == FlowResultType.CREATE_ENTRY
    entry = completed["result"]
    before_id = entry.entry_id
    assert entry.data["source"] == "ui"
    assert entry.data["configuration"]["chargers"] == []
    assert entry.data["configuration"]["controller"]["id"] == "home"
    assert "max_power_kw" not in entry.data["configuration"]["controller"]

    # User adds YAML at a subsequent HA startup; there is no deletion,
    # re-pairing or second Config Entry.
    yaml_config = validate_configuration({
        **entry.data["configuration"],
        "controller": {
            **entry.data["configuration"]["controller"],
            "name": "Legacy Wessels source",
        },
        "chargers": [{
            "id": "garage_white", "name": "Garage White",
            "kind": "on_off", "rated_power_kw": 3.6,
            "control_entity": "switch.garage_white",
            "control_owner": "external", "physical_commissioned": False,
        }],
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
async def test_dashboard_typed_owner_edit_and_recorder_identity(hass: HomeAssistant):
    """Real HA Config Entry, single Controller name edit, preserved Device ID."""
    from custom_components.robotix_multicharge.command_query import (
        apply_native_preference,
    )
    from custom_components.robotix_multicharge.configuration import (
        configuration_revision,
    )

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    initial = validate_configuration({
        "controller": {"id": "home", "name": "Original home", "mode": "Off",
                       "max_parallel": 1},
        "assets": [], "chargers": [],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Robotix MultiCharge",
        data={"source": "ui", "configuration": initial}, unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    devices = dr.async_get(hass)
    prior = devices.async_get_device_by_identifier(
        (DOMAIN, "controller/home"), entry.entry_id,
    )
    assert prior is not None
    runtime = hass.data[DOMAIN][entry.entry_id]
    revision = await apply_native_preference(
        hass, entry, runtime, "controller", "home",
        {"name": "Reviewed home"}, structural=True,
        expected_revision=configuration_revision(runtime.configuration),
    )
    await hass.async_block_till_done()
    assert entry.options["configuration"]["controller"]["name"] == "Reviewed home"
    assert configuration_revision(entry.options["configuration"]) == revision
    after = devices.async_get_device_by_identifier(
        (DOMAIN, "controller/home"), entry.entry_id,
    )
    assert after.id == prior.id
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_new_install_dashboard_typed_four_chargers_four_assets(
    hass: HomeAssistant,
):
    """One-click bootstrap; 4/4 objects created via typed dashboard write path."""
    from custom_components.robotix_multicharge.command_query import (
        apply_native_preference,
    )
    from custom_components.robotix_multicharge.configuration import (
        configuration_revision,
    )
    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    assert await async_setup_component(hass, DOMAIN, {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    entry = result["result"]
    await hass.async_block_till_done()
    assert not entry.data["configuration"]["assets"]
    assert not entry.data["configuration"]["chargers"]
    for key in ("audi", "vw", "guest1", "guest2"):
        runtime = hass.data[DOMAIN][entry.entry_id]
        await apply_native_preference(
            hass, entry, runtime, "asset", key,
            {"name": key.title(), "kind": "car",
             "soc_entity": "sensor." + key + "_soc"},
            action="create", structural=True,
            expected_revision=configuration_revision(runtime.configuration),
        )
        await hass.async_block_till_done()
    for key in ("white", "black", "peblar", "utility"):
        runtime = hass.data[DOMAIN][entry.entry_id]
        await apply_native_preference(
            hass, entry, runtime, "charger", key,
            {"name": key.title(), "kind": "on_off",
             "rated_power_kw": 3.6,
             "control_entity": "switch." + key,
             "connected_entity": "binary_sensor." + key + "_connected",
             "power_entity": "sensor." + key + "_power"},
            action="create", structural=True,
            expected_revision=configuration_revision(runtime.configuration),
        )
        await hass.async_block_till_done()
    saved = entry.options["configuration"]
    assert len(saved["assets"]) == len(saved["chargers"]) == 4
    assert all(c["control_owner"] == "external"
               and c["physical_commissioned"] is False
               for c in saved["chargers"])
    devices = dr.async_get(hass)
    assert devices.async_get_device_by_identifier(
        (DOMAIN, "charger/white"), entry.entry_id,
    )
    assert devices.async_get_device_by_identifier(
        (DOMAIN, "asset/audi"), entry.entry_id,
    )
    opts = await hass.config_entries.options.async_init(entry.entry_id)
    assert opts["type"] == FlowResultType.ABORT
    assert opts["reason"] == "dashboard_only"
    assert await hass.config_entries.async_unload(entry.entry_id)


def test_dashboard_structural_config_rejects_unsafe_field_updates():
    """Typed dashboard cannot forge owner/identity or delete assigned Asset."""
    from custom_components.robotix_multicharge.configuration import (
        apply_dashboard_structure,
    )
    cfg = validate_configuration({
        "controller": {"id": "home", "name": "Home", "mode": "Off",
                       "max_parallel": 1},
        "assets": [{"id": "a", "name": "Vehicle A", "kind": "car"}],
        "chargers": [{"id": "c", "name": "Charger C",
                      "kind": "on_off", "rated_power_kw": 3.6,
                      "asset": "a"}],
    })
    for changes in (
        {"id": "different"},
        {"control_owner": "multicharge"},
        {"physical_commissioned": True},
        {"template": []},
        {"phase_count": 5},
    ):
        with pytest.raises(ValueError):
            apply_dashboard_structure(cfg, "charger", "c", changes)
    with pytest.raises(ValueError, match="unassign"):
        apply_dashboard_structure(cfg, "asset", "a", {}, "delete")
    after = apply_dashboard_structure(
        cfg, "controller", "home", {"name": "New Home"},
    )
    assert after["controller"]["name"] == "New Home"
    assert after["chargers"] == cfg["chargers"]
    assert after["assets"] == cfg["assets"]


@pytest.mark.asyncio
async def test_native_state_events_invalidate_identity_on_fast_replug(hass: HomeAssistant):
    """UC21/23/29: every HA event is processed before planner refresh coalescing."""
    from datetime import datetime, timezone

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)

    hass.states.async_set("sensor.real_status", "Preparing")
    hass.states.async_set("sensor.real_power", "0",
                          {"unit_of_measurement": "W"})
    config = validate_configuration({
        "controller": {
            "id": "site", "name": "Independent site", "mode": "Automatic",
            "max_parallel": 1, "max_power_kw": 3.6,
        },
        "assets": [{
            "id": "car", "name": "Registered car", "kind": "car",
            "requested_kwh": 1.0,
        }],
        "chargers": [{
            "id": "evse", "name": "Native EVSE", "kind": "on_off",
            "rated_power_kw": 3.6, "control_owner": "external",
            "physical_commissioned": False,
            "asset": "car", "control_entity": "switch.real_control",
            "connected_entity": "sensor.real_status",
            "connected_states": ["preparing", "charging"],
            "disconnected_states": ["available"],
            "power_entity": "sensor.real_power",
        }],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Native event protection",
        data={"source": "ui", "configuration": config},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    charger = runtime.configuration["chargers"][0]

    confirmed = runtime.executor.confirm_current_connection("evse")
    assert confirmed["status"] == "confirmed"
    assert runtime.executor.connection_confirmation(charger, datetime.now(timezone.utc))
    original_epoch = confirmed["connected_at"]

    # Mapped connected substate transition preserves the same physical plug,
    # but does not bypass actual writer ownership or issue a command.
    hass.states.async_set("sensor.real_status", "Charging")
    await hass.async_block_till_done()
    current = runtime.executor.connection_confirmation(charger, datetime.now(timezone.utc))
    assert current is not None
    assert current["connected_at"] == original_epoch

    # Quick unplug -> new plug, with no intermediate planner refresh. HA
    # state_changed events retain both transitions even when refresh coalesces.
    hass.states.async_set("sensor.real_status", "Available")
    hass.states.async_set("sensor.real_status", "Preparing")
    await hass.async_block_till_done()
    assert runtime.executor.connection_confirmation(
        charger, datetime.now(timezone.utc)
    ) is None, "Observed physical disconnect invalidates previous Asset"
    runtime.refresh()
    assert not runtime.assessment.plan.slots
    assert runtime.executor.snapshot() == {} or all(
        action.get("status") != "confirmed"
        for action in runtime.executor.snapshot().values()
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_ha_idle_rebind_is_atomic_and_keeps_logical_device_ids(hass: HomeAssistant):
    """FLEX-06/08/17, UC16/29: real HA entry revision, idle gate and registry."""
    from custom_components.robotix_multicharge.command_query import (
        apply_native_preference,
    )
    from custom_components.robotix_multicharge.configuration import (
        configuration_revision,
    )

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    for charger in ("c1", "c2"):
        hass.states.async_set(f"sensor.{charger}_power", "0",
                              {"unit_of_measurement": "W"})
        hass.states.async_set(f"switch.{charger}", "off")
    config = validate_configuration({
        "controller": {
            "id": "home", "name": "Home", "mode": "Off",
            "max_parallel": 2, "max_power_kw": 7.2,
        },
        "assets": [{"id": "a", "name": "A", "kind": "car",
                    "requested_kwh": 2.0}],
        "chargers": [
            {"id": "c1", "name": "C1", "kind": "on_off",
             "rated_power_kw": 3.6, "asset": "a",
             "control_entity": "switch.c1",
             "power_entity": "sensor.c1_power",
             "control_owner": "external"},
            {"id": "c2", "name": "C2", "kind": "on_off",
             "rated_power_kw": 3.6,
             "control_entity": "switch.c2",
             "power_entity": "sensor.c2_power",
             "control_owner": "external"},
        ],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Two independent chargers",
        data={"source": "ui", "configuration": config},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    devices = dr.async_get(hass)
    old_ids = {
        key: devices.async_get_device_by_identifier(
            (DOMAIN, key), entry.entry_id
        ).id for key in ("controller/home", "charger/c1",
                        "charger/c2", "asset/a")
    }
    previous_revision = configuration_revision(runtime.configuration)

    # An observed 2 kW source reading on C1 forbids an implicit handoff.
    hass.states.async_set("sensor.c1_power", "2000",
                          {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    with pytest.raises(ValueError, match="charger_busy"):
        await apply_native_preference(
            hass, entry, runtime, "charger", "c2", {"asset": "a"},
            expected_revision=previous_revision,
        )
    assert entry.options.get("configuration") is None
    assert runtime.configuration["chargers"][0]["asset"] == "a"

    # Explicit fresh observed idle evidence enables a single atomic rebind.
    hass.states.async_set("sensor.c1_power", "0",
                          {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    revision = await apply_native_preference(
        hass, entry, runtime, "charger", "c2", {"asset": "a"},
        expected_revision=previous_revision,
    )
    await hass.async_block_till_done()
    assert configuration_revision(runtime.configuration) == revision
    assert runtime is hass.data[DOMAIN][entry.entry_id], (
        "Idle-only assignment must not reload/STOP an unrelated HA device"
    )
    assert [(c["id"], c.get("asset")) for c in runtime.configuration["chargers"]] == [
        ("c1", None), ("c2", "a"),
    ]
    assert all(
        devices.async_get_device_by_identifier((DOMAIN, key), entry.entry_id).id
        == original for key, original in old_ids.items()
    )
    with pytest.raises(ValueError, match="stale_settings"):
        await apply_native_preference(
            hass, entry, runtime, "charger", "c1", {"asset": "a"},
            expected_revision=previous_revision,
        )
    assert hass.states.get("switch.c1").state == "off"
    assert hass.states.get("switch.c2").state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_native_ha_service_injects_context_for_real_vehicle_quick_action(
    hass: HomeAssistant,
):
    """Regression: iPad/HA Select must not access nonexistent Entity.context.

    Test the real HA select.select_option service dispatch (not direct mocks),
    Config Entry persistence, admin/resident and physical busy refusal.
    """
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch
    from homeassistant.core import Context
    from homeassistant.helpers import entity_registry as er

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    hass.states.async_set("switch.real_quick", "off")
    hass.states.async_set(
        "sensor.real_quick_power", "0",
        {"unit_of_measurement": "W"},
    )
    cfg = validate_configuration({
        "controller": {
            "id": "site", "name": "Service context regression",
            "mode": "Off", "max_parallel": 1, "max_power_kw": 3.6,
        },
        "assets": [
            {"id": "a", "name": "Car A", "kind": "car", "target_soc": 80},
            {"id": "b", "name": "Car B", "kind": "car", "target_soc": 90},
        ],
        "chargers": [{
            "id": "c", "name": "Charger", "kind": "on_off",
            "rated_power_kw": 3.6, "asset": "a",
            "control_entity": "switch.real_quick",
            "power_entity": "sensor.real_quick_power",
            "control_owner": "external",
            "physical_commissioned": False,
        }],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Quick Select HA service",
        data={"source": "ui", "configuration": cfg},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    ids = er.async_get(hass)
    vehicle = ids.async_get_entity_id(
        "select", DOMAIN, f"{DOMAIN}:charger:c:asset",
    )
    mode = ids.async_get_entity_id(
        "select", DOMAIN, f"{DOMAIN}:controller:site:mode",
    )
    target = ids.async_get_entity_id(
        "number", DOMAIN, f"{DOMAIN}:asset:b:target_soc",
    )
    assert all((vehicle, mode, target))
    assert hass.states.get(vehicle).state == "Car A"
    assert hass.states.get(mode).state == "off"
    assert hass.states.get(target).state == "90.0"

    def user_for_context(user_id):
        return SimpleNamespace(
            is_admin=user_id == "admin",
            # HA's native service registry checks entity permissions before
            # dispatch. Grant service visibility here to test MultiCharge's
            # stricter independent admin-only write authorization.
            permissions=SimpleNamespace(check_entity=lambda *args: True),
        )

    with patch.object(
        hass.auth, "async_get_user",
        new=AsyncMock(side_effect=user_for_context),
    ):
        # Service propagation into Entity._context is the regression,
        # not simply access to mocked fake.context in a unit test.
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": vehicle, "option": "Car B"},
            blocking=True, context=Context(user_id="admin"),
        )
        await hass.async_block_till_done()
        assert entry.options["configuration"]["chargers"][0]["asset"] == "b"
        assert hass.states.get(vehicle).state == "Car B"
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": mode, "option": "economy"},
            blocking=True, context=Context(user_id="admin"),
        )
        await hass.async_block_till_done()
        assert entry.options["configuration"]["controller"]["mode"] == "Economy"
        await hass.services.async_call(
            "number", "set_value",
            {"entity_id": target, "value": 85},
            blocking=True, context=Context(user_id="admin"),
        )
        await hass.async_block_till_done()
        assert entry.options["configuration"]["assets"][1]["target_soc"] == 85

        for user_id in ("resident", None):
            with pytest.raises(RuntimeError, match="administrator"):
                await hass.services.async_call(
                    "select", "select_option",
                    {"entity_id": vehicle, "option": "Car A"},
                    blocking=True, context=Context(user_id=user_id),
                )
            assert entry.options["configuration"]["chargers"][0]["asset"] == "b"

        hass.states.async_set(
            "sensor.real_quick_power", "1500",
            {"unit_of_measurement": "W"},
        )
        await hass.async_block_till_done()
        with pytest.raises(ValueError, match="charger_busy"):
            await hass.services.async_call(
                "select", "select_option",
                {"entity_id": vehicle, "option": "Car A"},
                blocking=True, context=Context(user_id="admin"),
            )
        assert entry.options["configuration"]["chargers"][0]["asset"] == "b"
        assert hass.states.get("switch.real_quick").state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_gui_managed_setup_does_not_register_rejected_yaml_editor(hass: HomeAssistant):
    """A real HA setup retains native typed settings, without a raw YAML writer."""
    from custom_components.robotix_multicharge import command_query
    assert not hasattr(command_query, "websocket_dashboard_yaml_configuration")

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "home", "name": "Home charging",
                       "mode": "Off", "max_parallel": 1},
        "assets": [], "chargers": [],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Robotix MultiCharge",
        data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "controller/home"), entry.entry_id,
    ) is not None
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_direct_yaml_save_native_websocket_single_entry_roundtrip(
    hass: HomeAssistant, hass_ws_client,
):
    """Real HA WS: one YAML Save with server-side validation and real readback.

    This does not simulate physical device or site commissioning.
    """
    from custom_components.robotix_multicharge.configuration import (
        configuration_revision,
    )

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "home", "name": "Existing site",
                       "mode": "Off", "max_parallel": 1},
        "assets": [], "chargers": [{
            "id": "plug", "name": "External EVSE",
            "kind": "on_off", "rated_power_kw": 3.6,
            "control_entity": "switch.test_plug",
            "power_entity": "sensor.unverified_plug_power",
            "control_owner": "external", "physical_commissioned": False,
        }],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="MultiCharge Community",
        data={"source": "ui", "configuration": cfg},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    request_id = 200

    async def yaml_ws(text, baseline):
        nonlocal request_id
        request_id += 1
        msg = {
            "id": request_id,
            "type": "robotix_multicharge/yaml_configuration",
            "yaml_text": text,
            "expected_revision": baseline,
        }
        await client.send_json(msg)
        result = await client.receive_json()
        assert result["id"] == request_id
        return result

    initial = configuration_revision(cfg)
    changed = json.loads(json.dumps(cfg))
    changed["controller"]["name"] = "Saved site name"
    # This read-only external Charger can be mapped without fake idle evidence.
    changed["chargers"][0]["connected_entity"] = "sensor.native_connection"
    text = json.dumps(changed, indent=2)

    bad = await yaml_ws('controller: {}\\ncontroller: {}', initial)
    assert bad["success"] is False
    assert entry.options.get("configuration") is None

    updated = await yaml_ws(text, initial)
    assert updated["success"] is True
    assert updated["result"]["status"] == "accepted_unconfirmed"
    proposed = updated["result"]["expected_revision"]
    assert isinstance(proposed, str)
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert entry.options["configuration"]["controller"]["name"] == "Saved site name"
    assert entry.options["configuration"]["chargers"][0]["connected_entity"] == "sensor.native_connection"
    assert entry.options["configuration"]["chargers"][0]["control_owner"] == "external"
    assert entry.options["configuration"]["chargers"][0]["physical_commissioned"] is False
    assert configuration_revision(entry.options["configuration"]) == proposed

    stale = await yaml_ws(text, initial)
    assert stale["success"] is False
    assert "STALE_SETTINGS_REFRESH" in stale["error"]["message"]

    # Even with admin rights and a correct revision, free text cannot
    # commission a previously external charger or switch the physical owner.
    unsafe = json.loads(text)
    unsafe["chargers"][0]["control_owner"] = "multicharge"
    unsafe["chargers"][0]["physical_commissioned"] = True
    denied = await yaml_ws(json.dumps(unsafe), proposed)
    assert denied["success"] is False
    assert entry.options["configuration"]["chargers"][0]["control_owner"] == "external"

    await client.close()
    assert await hass.config_entries.async_unload(entry.entry_id)
