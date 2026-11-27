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
    # A permitted return to monitoring still requires safe structural reload.
    from custom_components.robotix_multicharge.configuration import assert_expert_authority_change
    assert_expert_authority_change(old, external)
    runtime.configuration = old
    _assert_safe_expert_import(runtime, external)
    states["switch.charger"].state = "on"
    with pytest.raises(ValueError, match="VERIFIED_IDLE"):
        _assert_safe_expert_import(runtime, external)
    states["switch.charger"].state = "off"
    runtime.configuration = external
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
    hass: HomeAssistant, hass_ws_client,
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
    assert not issued, "A native switch state alone is not permission to control"

    # Authorize through the ordinary charger settings path, without a second
    # commissioning workflow. The isolated HA service confirms the switch
    # state only; it does not supply battery, cable or measured power evidence.
    from custom_components.robotix_multicharge.command_query import apply_native_preference
    from datetime import timedelta
    async def observed_switch_on(call):
        issued.append(call.service)
        hass.states.async_set("switch.suitable_plug", "on")
    async def observed_switch_off(call):
        issued.append(call.service)
        hass.states.async_set("switch.suitable_plug", "off")
    hass.services.async_register("switch", "turn_on", observed_switch_on)
    hass.services.async_register("switch", "turn_off", observed_switch_off)
    await apply_native_preference(hass, entry, runtime, "charger", "plug",
                                  {"control_owner": "multicharge"}, structural=True)
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    assert runtime.configuration["chargers"][0]["control_owner"] == "multicharge"
    assert issued == [], "Configuration Save is not a charging command"
    assert runtime.executor.capabilities()["plug"]["manual_goal_reasons"]["duration"] == "READY"
    assert runtime.executor.capabilities()["plug"]["manual_goal_reasons"]["energy"] != "READY"
    started = await runtime.executor.execute(
        "plug", "start", manual_request={"duration_minutes": 10}
    )
    assert started["status"] == "confirmed"
    assert started["reason"] == "NATIVE_SWITCH_STATE"
    assert started["measured_power_kw"] is None
    assert runtime.charger_states()["plug"]["charging_session"] == "unknown"
    await hass.async_block_till_done()
    assert hass.states.get("switch.suitable_plug").state == "on"
    assert not runtime.executor._supervising
    runtime.executor._sessions["plug"]["started_at"] -= timedelta(minutes=11)
    await runtime.executor.supervise()
    await hass.async_block_till_done()
    assert issued == ["turn_on", "turn_off"]
    assert hass.states.get("switch.suitable_plug").state == "off"
    receipt = runtime.executor.completed_sessions()[-1]
    assert receipt["switch_stop_confirmed"] is True
    assert receipt["physical_stop_confirmed"] is False
    assert receipt["actual_energy_kwh"] is None
    # Actual installed HA websocket dispatch uses the same native writer.
    client = await hass_ws_client(hass)
    await client.send_json({"id": 101, "type": "robotix_multicharge/command", "charger_id": "plug", "action": "manual_start", "duration_minutes": 10})
    reply = await client.receive_json()
    assert reply["success"] and reply["result"]["status"] == "confirmed"
    assert runtime.executor.capabilities()["plug"]["control_mode"] == "Manual"
    await client.send_json({"id": 102, "type": "robotix_multicharge/command", "charger_id": "plug", "action": "manual_stop"})
    reply = await client.receive_json()
    assert reply["success"] and reply["result"]["status"] == "confirmed"
    assert runtime.executor.capabilities()["plug"]["control_mode"] == "Stopped"
    await client.send_json({"id": 103, "type": "robotix_multicharge/command", "charger_id": "plug", "action": "auto"})
    reply = await client.receive_json()
    assert reply["success"] and reply["result"]["status"] == "confirmed"
    assert runtime.executor.capabilities()["plug"]["control_mode"] == "Automatic"
    assert issued == ["turn_on", "turn_off", "turn_on", "turn_off"]
    await apply_native_preference(hass, entry, runtime, "charger", "plug",
                                  {"control_owner": "external"}, structural=True)
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    assert runtime.charger_states()["plug"]["activation"] == "inactive"
    assert runtime.configuration["chargers"][0]["control_entity"] == "switch.suitable_plug"
    assert issued == ["turn_on", "turn_off", "turn_on", "turn_off"]
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
async def test_native_concurrent_exact_recorder_reads_share_only_running_query(
    hass: HomeAssistant, monkeypatch,
):
    """Native Recorder evidence stays exact; no stale or wider-range cache."""
    import asyncio
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from homeassistant.components import recorder
    from custom_components.robotix_multicharge.runtime import MultiChargeRuntime

    end = datetime.now(timezone.utc) - timedelta(minutes=1)
    start = end - timedelta(minutes=30)
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    class NativeRecorder:
        async def async_add_executor_job(self, fn, *args):
            calls.append(args)
            entered.set()
            await release.wait()
            return {"sensor.native_power": [
                SimpleNamespace(state="2000", last_updated=start,
                                attributes={"unit_of_measurement": "W"}),
            ]}

    monkeypatch.setattr(recorder, "get_instance", lambda _hass: NativeRecorder())
    hass.config.components.add("recorder")
    cfg = validate_configuration({
        "controller": {"id": "site", "name": "Site", "mode": "Off"},
        "assets": [], "chargers": [{"id": "drive", "name": "Drive",
            "kind": "on_off", "rated_power_kw": 2,
            "power_entity": "sensor.native_power", "control_owner": "external"}],
    })
    runtime = MultiChargeRuntime(hass, cfg)
    a = asyncio.create_task(runtime.read_history(cfg, start, end, as_of=end))
    await asyncio.wait_for(entered.wait(), timeout=2)
    b = asyncio.create_task(runtime.read_history(cfg, start, end, as_of=end))
    cancelled = asyncio.create_task(runtime.read_history(cfg, start, end, as_of=end))
    await asyncio.sleep(0)
    cancelled.cancel()
    with pytest.raises(asyncio.CancelledError):
        await cancelled
    release.set()
    first, second = await asyncio.wait_for(asyncio.gather(a, b), timeout=2)
    assert first == second
    assert len(calls) == 1
    assert runtime.performance_snapshot()["recorder_query"]["count"] == 1
    assert runtime._recorder_inflight == {}
    # A later identical request must see new Recorder evidence; different
    # exact boundaries must also cause a separate query.
    assert await runtime.read_history(cfg, start, end, as_of=end) == first
    await runtime.read_history(cfg, start, end + timedelta(seconds=1),
                               as_of=end + timedelta(seconds=1))
    assert len(calls) == 3
    runtime.stop()


@pytest.mark.asyncio
async def test_native_financial_day_reuses_single_recorder_query(hass: HomeAssistant, monkeypatch):
    """Exercise the real HA background projection seam with deterministic input."""
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from homeassistant.components import recorder
    from custom_components.robotix_multicharge.contracts import PriceSlot
    from custom_components.robotix_multicharge.history import read_actual_history, civil_period_costs

    end = datetime.now(timezone.utc)-timedelta(seconds=5)
    start = end-timedelta(minutes=30)
    middle = start+timedelta(minutes=15)
    calls = []
    class NativeRecorder:
        async def async_add_executor_job(self, fn, *args):
            calls.append((fn, args))
            return {"sensor.native_power": [
                SimpleNamespace(state="2000", last_updated=start,
                                attributes={"unit_of_measurement": "W"}),
                SimpleNamespace(state="4000", last_updated=middle,
                                attributes={"unit_of_measurement": "W"}),
            ]}
    monkeypatch.setattr(recorder, "get_instance", lambda _hass: NativeRecorder())
    hass.config.components.add("recorder")
    cfg = {"controller": {"id": "site"}, "chargers": [
        {"id": "charger", "power_entity": "sensor.native_power"}],
        "assets": [{"id": "car"}]}
    receipt = {"charger_id": "charger", "asset_id": "car",
               "started_at": start.isoformat(), "ended_at": end.isoformat(),
               "physical_stop_confirmed": True, "actual_energy_kwh": 1.5,
               "energy_quality": "measured"}
    days = {start.date().isoformat(): (start, end)}
    _, _, estimates, _, _, raw = await read_actual_history(
        hass, cfg, start, end, financial_days=days,
        include_observed_sessions=True, include_valuations=True,
        session_receipts=[receipt], price_slots=[
            PriceSlot(start, middle, 0.2, "EUR"),
            PriceSlot(middle, end, 0.32, "EUR")],
    )
    result = civil_period_costs(days, raw)
    assert len(calls) == 1
    assert result["controller"]["site"]["today"]["cost"] == pytest.approx(0.42)
    assert result["asset"]["car"]["today"]["cost"] == pytest.approx(0.42)
    assert result["charger"]["charger"]["today"]["average_price_per_kwh"] == pytest.approx(0.28)
    assert estimates[("charger", receipt["started_at"], receipt["ended_at"])]["estimated_variable_cost"] == pytest.approx(0.42)
    # The background finance caller needs no quarter graph. It must retain
    # exactly the same cost and observed-session evidence from one query.
    from custom_components.robotix_multicharge import history as mc_history
    original = mc_history.reconciled_quarter_history

    def unused_chart(*args, **kwargs):
        raise AssertionError("Background finance must not project unused graph rows")

    monkeypatch.setattr(mc_history, "reconciled_quarter_history", unused_chart)
    chart, quality, fast_estimates, _, _, fast_raw = await read_actual_history(
        hass, cfg, start, end, financial_days=days, as_of=end,
        include_observed_sessions=True, include_valuations=True, include_quarters=False,
        session_receipts=[receipt], price_slots=[
            PriceSlot(start, middle, 0.2, "EUR"),
            PriceSlot(middle, end, 0.32, "EUR")],
    )
    assert chart == [] and quality == "QUARTERS_NOT_REQUESTED"
    assert fast_raw == raw and fast_estimates == estimates
    assert len(calls) == 2
    monkeypatch.setattr(mc_history, "reconciled_quarter_history", original)


@pytest.mark.asyncio
async def test_native_recorder_remap_keeps_original_measured_quarters(hass: HomeAssistant, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from homeassistant.components import recorder
    from custom_components.robotix_multicharge.history import (
        read_actual_history, reconcile_power_bindings,
    )

    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end = end.replace(minute=(end.minute // 15)*15)
    start = end - timedelta(hours=1)
    change = start + timedelta(minutes=37)
    old = {"chargers": [{"id": "drive", "power_entity": "sensor.old"}]}
    new = {"chargers": [{"id": "drive", "power_entity": "sensor.new"}]}
    bindings = reconcile_power_bindings(reconcile_power_bindings(None, old, start), new, change)
    calls = []

    def samples(watts):
        return [SimpleNamespace(state=str(watts), last_updated=start+timedelta(minutes=i),
                                attributes={"unit_of_measurement": "W"})
                for i in range(0, 60, 15)]

    class NativeRecorder:
        async def async_add_executor_job(self, fn, *args):
            calls.append(args)
            return {"sensor.old": samples(1000), "sensor.new": samples(3000)}

    monkeypatch.setattr(recorder, "get_instance", lambda _hass: NativeRecorder())
    hass.config.components.add("recorder")
    rows, quality = await read_actual_history(hass, new, start, end, power_bindings=bindings)
    assert [row["actual_power_kw"] for row in rows] == [1.0, 1.0, None, 3.0]
    assert quality == "INCOMPLETE_POWER_HISTORY"
    assert len(calls) == 1


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
    # Separate current import and forecast are independent native HA sources.
    hass.states.async_set("sensor.native_import", "0.32", {
        "unit_of_measurement": "EUR/kWh",
    })
    runtime.configuration["controller"]["current_price_entity"] = "sensor.native_import"
    hass.states.async_set("sensor.native_all_in", "0.24", {
        "unit_of_measurement": "€/kWh", "time_zone": "Europe/Brussels",
        "today": observed, "tomorrow": [{"start": after_day.isoformat(), "all_in": 0.1}],
        "snapshot_stale": False,
    })
    runtime.refresh(at)
    sources = runtime.observations["sources"]
    assert sources["current_price"]["value"] == 0.32
    assert sources["current_price"]["basis"] == "current_only"
    assert sources["tariff_tomorrow_quality"] == "INTERVAL_COVERAGE_INCOMPLETE"
    assert len(runtime.price_slots) == length
    assert runtime.price_slots[-1].end == after_day
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
            "home_power_entity": "sensor.native_house",
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
    for kind, uid in (("controller", "site"), ("charger", "charger"), ("asset", "asset")):
        entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}:{kind}:{uid}:current_import_price",
        )
        assert entity_id is not None
        owning = devices.async_get_device_by_identifier(
            (DOMAIN, f"{kind}/{uid}"), entry.entry_id,
        )
        assert registry.async_get(entity_id).device_id == owning.id
        state = hass.states.get(entity_id)
        assert state.state == "unknown"
        assert state.attributes["shared_site_import_rate"] is True
        planned_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}:{kind}:{uid}:planned_charging_cost",
        )
        assert planned_id is not None
        assert registry.async_get(planned_id).device_id == owning.id
        assert hass.states.get(planned_id).state == "unknown"
        for phase in ("active",) if kind == "controller" else ("active", "last"):
            cost_id = registry.async_get_entity_id(
                "sensor", DOMAIN, f"{DOMAIN}:{kind}:{uid}:{phase}_session_cost",
            )
            assert cost_id is not None
            assert registry.async_get(cost_id).device_id == owning.id
            assert hass.states.get(cost_id).state == "unknown"
        for period in ("today", "month", "year"):
            for metric in ("charging_cost", "average_charging_price"):
                entity_id = registry.async_get_entity_id(
                    "sensor", DOMAIN, f"{DOMAIN}:{kind}:{uid}:{metric}_{period}",
                )
                assert entity_id is not None
                assert registry.async_get(entity_id).device_id == owning.id
                assert hass.states.get(entity_id).state == "unknown"
    named = [registry.async_get_entity_id("sensor", DOMAIN, f"{DOMAIN}:charger:charger:{field}") for field in ("power", "readiness", "command_status", "selected_vehicle")]
    names = [registry.async_get(entity_id).original_name for entity_id in named]
    assert all(names) and len(set(names)) == len(names), names
    diagnostic = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostic["schema_major"] == 1
    assert len(diagnostic["chargers"]) == 1
    assert diagnostic["integration"]["active"] is True
    runtime = hass.data[DOMAIN][entry.entry_id]
    original_plan = runtime.assessment
    hass.states.async_set("sensor.native_house", "1200", {"unit_of_measurement": "W"})
    await hass.async_block_till_done()
    assert runtime.assessment is original_plan
    assert runtime.observations["sources"]["home_power"]["value"] == 1.2
    hass.states.async_set("sensor.native_session", "charging")
    await hass.async_block_till_done()
    assert runtime.assessment is not original_plan
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
    hass.states.async_set("number.hardware_limit", "12", {
        "min": 0, "max": 16, "step": 1, "unit_of_measurement": "A",
    })
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
    max_entity = registry.async_get_entity_id(
        "number", DOMAIN, f"{DOMAIN}:charger:drive:max_charging_power_kw"
    )
    maximum = hass.states.get(max_entity)
    assert float(maximum.state) == 3.0
    assert maximum.attributes["effective_min_power_kw"] == 1.84
    assert maximum.attributes["effective_max_power_kw"] == 2.99
    hass.states.async_set("number.hardware_limit", "11", {
        "min": 0, "max": 11, "step": 1, "unit_of_measurement": "A",
    })
    await hass.async_block_till_done()
    maximum = hass.states.get(max_entity)
    assert float(maximum.state) == 3.0
    assert maximum.attributes["effective_max_power_kw"] == 2.53
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_native_nordpool_action_resolves_selected_registry_area(hass: HomeAssistant):
    """Real HA registry and response-service contract; fixture market values."""
    from datetime import datetime, timedelta, timezone
    from homeassistant.core import SupportsResponse
    from homeassistant.helpers import entity_registry as er
    from custom_components.robotix_multicharge.source_evidence import async_native_nordpool_prices

    provider = MockConfigEntry(domain="nordpool", title="Selected market",
                               data={"areas": ["BE", "NL"], "currency": "EUR"})
    provider.add_to_hass(hass)
    selected = er.async_get(hass).async_get_or_create(
        "sensor", "nordpool", "BE-current_price", config_entry=provider,
        suggested_object_id="renamed_price_sensor")
    at = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
    calls = []

    async def price_service(call):
        calls.append(dict(call.data))
        if len(calls) == 2:
            return {"BE": []}  # tomorrow not published
        return {"BE": [{"start": at.isoformat(),
                        "end": (at + timedelta(minutes=15)).isoformat(),
                        "price": -25.0}]}

    hass.services.async_register("nordpool", "get_prices_for_date",
                                 price_service, supports_response=SupportsResponse.ONLY)
    slots, status = await async_native_nordpool_prices(hass, selected.entity_id, at)
    assert status == "OK" and len(slots) == 1
    assert slots[0].effective_price_per_kwh == -0.025
    assert slots[0].basis == "spot"
    assert [c["date"] for c in calls] == ["2026-11-24", "2026-11-25"]
    assert all(c["areas"] == ["BE"] and c["config_entry"] == provider.entry_id
               and c["currency"] == "EUR" for c in calls)
    assert await async_native_nordpool_prices(hass, "sensor.unrelated", at) is None


@pytest.mark.asyncio
async def test_v1_migration_keeps_identity_and_repairs_missing_inactive_soc_target(hass: HomeAssistant):
    """Upgrade existing UI profiles without granting an active new charging intent."""
    from homeassistant.helpers import entity_registry as er

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "home", "name": "Home", "mode": "Off"},
        "assets": [
            {"id": "car", "name": "Car", "kind": "car", "soc_entity": "sensor.car_soc"},
            {"id": "explicit", "name": "Explicit", "kind": "car",
             "soc_entity": "sensor.explicit_soc", "target_soc": 65},
            {"id": "guest", "name": "Guest", "kind": "car"},
        ],
        "chargers": [{"id": "socket", "name": "Socket", "kind": "on_off",
                      "rated_power_kw": 2.0, "asset": "car",
                      "control_owner": "external", "control_entity": "switch.socket"}],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="MultiCharge", version=1, minor_version=1,
        data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    original_id = entry.entry_id
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert entry.state.value == "loaded"
    assert entry.entry_id == original_id and entry.minor_version == 2
    actual = entry.data["configuration"]
    assets = {row["id"]: row for row in actual["assets"]}
    assert assets["car"]["target_soc"] == 80
    assert assets["explicit"]["target_soc"] == 65
    assert "target_soc" not in assets["guest"]
    assert actual["chargers"] == cfg["chargers"]
    registry = er.async_get(hass)
    assert any(row.unique_id.endswith(":car:target_soc")
               for row in er.async_entries_for_config_entry(registry, entry.entry_id))
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
            "number": ("max_parallel", "max_power_kw", "power_adjustment_interval_minutes"),
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
            "select": ("plan_color", "asset", "control_owner"),
            "text": ("name",),
            "button": ("confirm_connection", "stop", "pause", "resume"),
        },
        ("charger", "smart"): {
            "number": ("min_charging_power_kw", "max_charging_power_kw",
                       "set_charging_power_kw"),
            "select": ("plan_color", "asset", "control_owner"),
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
        expected_state = "unavailable" if field == "set_charging_power_kw" else "unknown"
        assert hass.states.get(entity_id).state == expected_state, field
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
    assert current["assets"][0]["ready_by_repeat"] == "daily"
    assert "T06:00:00" in current["assets"][0]["ready_by"]
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
    # First Daily schedule needs no prior datetime; one revision owns it.
    runtime = hass.data[DOMAIN][entry.entry_id]
    await apply_native_preference(hass, entry, runtime, "asset", "fresh_car", {
        "ready_by_repeat": "daily", "ready_by_local": "2026-11-25T07:00:00",
        "ready_by_weekdays": None,
    })
    await hass.async_block_till_done()
    saved = entry.options["configuration"]["assets"][0]
    assert saved["ready_by_repeat"] == "daily"
    assert saved["target_soc"] == 80
    for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
        entity_id = registry.async_get_entity_id(
            "select", DOMAIN, f"{DOMAIN}:asset:fresh_car:ready_day_{day}"
        )
        assert hass.states.get(entity_id).state == "07:00"
    runtime = hass.data[DOMAIN][entry.entry_id]
    await apply_native_preference(hass, entry, runtime, "asset", "fresh_car", {
        "ready_by_repeat": "none", "ready_by": None, "ready_by_weekdays": None,
    })
    await hass.async_block_till_done()
    saved = entry.options["configuration"]["assets"][0]
    assert "ready_by" not in saved
    assert saved["target_soc"] == 80
    runtime = hass.data[DOMAIN][entry.entry_id]
    await apply_native_preference(hass, entry, runtime, "asset", "fresh_car", {"target_soc": 95})
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    saved = hass.data[DOMAIN][entry.entry_id].configuration["assets"][0]
    assert saved["target_soc"] == 95
    assert saved["ready_by_repeat"] == "none"
    assert "ready_by" not in saved
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
async def test_native_options_menu_expert_prefill_save_and_reject_unsafe(
    hass: HomeAssistant,
):
    """Real HA Options, one Config Entry, no mandatory install wizard."""
    from custom_components.robotix_multicharge.configuration import (
        configuration_revision,
    )

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "site", "name": "Independent home",
                       "mode": "Automatic", "max_parallel": 1},
        "assets": [{"id": "car", "name": "Car", "kind": "car"}],
        "chargers": [{
            "id": "wall", "name": "Wall",
            "kind": "on_off", "rated_power_kw": 3.6,
            "control_entity": "switch.wall", "control_owner": "external",
            "physical_commissioned": False,
        }],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="Standalone MultiCharge",
        data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    menu = await hass.config_entries.options.async_init(entry.entry_id)
    assert menu["type"] == FlowResultType.MENU
    assert set(("controller", "charger_pick", "asset_pick",
                "energy", "yaml")).issubset(menu["menu_options"])

    editor = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "yaml"},
    )
    assert editor["type"] == FlowResultType.FORM
    assert editor["step_id"] == "yaml"
    marker = next(k for k in editor["data_schema"].schema
                  if str(k) == "yaml_text")
    prefilled = json.loads(marker.default())
    assert validate_configuration(prefilled) == cfg, "Expert editor must preserve the actual Config Entry"
    assert "physical_commissioned" not in prefilled["chargers"][0]

    invalid = await hass.config_entries.options.async_configure(
        editor["flow_id"], {"yaml_text": 'controller: {}\\ncontroller: {}'},
    )
    assert invalid["type"] == FlowResultType.FORM
    assert "YAML" in invalid["errors"]["base"] or "duplicate" in invalid["errors"]["base"]
    assert entry.options.get("configuration") is None

    changed = json.loads(json.dumps(cfg))
    changed["controller"]["name"] = "Native Configured home"
    changed["chargers"][0]["connected_entity"] = "binary_sensor.wall_plugged"
    saved = await hass.config_entries.options.async_configure(
        editor["flow_id"], {"yaml_text": json.dumps(changed)},
    )
    assert saved["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    actual = entry.options["configuration"]
    assert actual["controller"]["name"] == "Native Configured home"
    assert actual["chargers"][0]["connected_entity"] == "binary_sensor.wall_plugged"
    assert actual["chargers"][0]["control_owner"] == "external"
    assert actual["chargers"][0]["physical_commissioned"] is False

    # A separate Options visit must show current readback, not a stale template.
    again = await hass.config_entries.options.async_init(entry.entry_id)
    screen = await hass.config_entries.options.async_configure(
        again["flow_id"], {"next_step_id": "yaml"},
    )
    marker = next(k for k in screen["data_schema"].schema
                  if str(k) == "yaml_text")
    assert validate_configuration(json.loads(marker.default())) == actual

    # Explicit control intent is permitted, but not while the same endpoint
    # is visibly energized under another owner.
    hass.states.async_set("switch.wall", "on")
    await hass.async_block_till_done()
    unsafe = json.loads(json.dumps(actual))
    unsafe["chargers"][0]["control_owner"] = "multicharge"
    unsafe["chargers"][0]["physical_commissioned"] = True
    blocked = await hass.config_entries.options.async_configure(
        screen["flow_id"], {"yaml_text": json.dumps(unsafe)},
    )
    assert blocked["type"] == FlowResultType.FORM
    assert blocked["errors"]["base"] != "invalid_config"
    assert entry.options["configuration"] == actual
    hass.states.async_set("switch.wall", "off")
    await hass.async_block_till_done()

    # Concurrent changes cannot be overwritten by an older open form.
    hass.config_entries.async_update_entry(entry, options={
        **entry.options,
        "configuration": validate_configuration({
            **actual, "controller": {**actual["controller"],
                                     "name": "Concurrent native user"},
        }),
    })
    await hass.async_block_till_done()
    stale = await hass.config_entries.options.async_configure(
        screen["flow_id"], {"yaml_text": json.dumps(actual)},
    )
    assert stale["type"] == FlowResultType.FORM
    assert stale["errors"]["base"] == "selection_changed"
    assert entry.options["configuration"]["controller"]["name"] == "Concurrent native user"
    assert configuration_revision(entry.options["configuration"]) != configuration_revision(actual)
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_native_expert_save_four_external_adjustable_chargers_without_guessed_amps(
    hass: HomeAssistant,
):
    """Pinned real Home Assistant Options Flow, not a substitute data writer.

    Representative four-Charger/four-Asset source shape from a real reported
    Save failure, with generic IDs so private site bindings remain site-owned.
    """
    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    starting = validate_configuration({
        "controller": {"id": "home", "name": "Existing site",
                       "mode": "Automatic", "max_parallel": 1},
        "assets": [], "chargers": [],
    })
    entry = MockConfigEntry(
        domain=DOMAIN, title="MultiCharge Community",
        data={"source": "ui", "configuration": starting}, unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    menu = await hass.config_entries.options.async_init(entry.entry_id)
    assert menu["type"] == FlowResultType.MENU
    editor = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "yaml"},
    )
    assert editor["step_id"] == "yaml"
    config = {
        "controller": {
            "id": "home", "name": "Example Home", "mode": "Automatic",
            "max_parallel": 1, "max_power_kw": 3.6,
            "plan_label_mode": "both", "plan_color_by": "vehicle",
            "show_indicative_forecast": True,
            "solar_power_entity": "sensor.energy_solar_power",
            "home_power_entity": "sensor.energy_home_power",
            "grid_power_entity": "sensor.energy_grid_power",
            "solar_surplus_entity": "sensor.energy_surplus_power",
            "current_price_entity": "sensor.energy_current_price",
            "solar_source_kind": "direct_surplus",
            "grid_power_direction": "import_positive",
        },
        "assets": [
            {"id": "car_a", "name": "Car A", "kind": "car",
             "soc_entity": "sensor.car_a_soc"},
            {"id": "car_b", "name": "Car B", "kind": "car",
             "soc_entity": "sensor.car_b_soc"},
            {"id": "guest_1", "name": "Guest 1", "kind": "car"},
            {"id": "guest_2", "name": "Guest 2", "kind": "car"},
        ],
        "chargers": [{
            "id": uid, "name": label, "kind": "variable_current",
            "rated_power_kw": 3.6,
            "control_entity": f"switch.{uid}_charge",
            "current_control_entity": f"number.{uid}_current",
            "connected_entity": f"sensor.{uid}_connected",
            "power_entity": f"sensor.{uid}_power",
            "energy_entity": f"sensor.{uid}_session_energy",
            "control_owner": "external", "physical_commissioned": False,
            **({"current_readback_entity": f"sensor.{uid}_current_actual"}
               if n < 2 else {}),
        } for n, (uid, label) in enumerate((
            ("wall_a", "Wall A"), ("wall_b", "Wall B"),
            ("outside", "Outside"),
        ))] + [{
            "id": "utility_plug", "name": "Utility Plug",
            "kind": "on_off", "rated_power_kw": 2,
            "control_entity": "switch.utility_plug",
            "connected_entity": "sensor.utility_connected",
            "power_entity": "sensor.utility_power",
            "energy_entity": "sensor.utility_session_energy",
            "control_owner": "external", "physical_commissioned": False,
        }],
    }

    # Contradictory explicit overrides are rejected, with the *reason*
    # visibly available through Home Assistant's form placeholders.
    unsafe = json.loads(json.dumps(config))
    unsafe["chargers"][0].update(min_current_a=16, max_current_a=6)
    invalid = await hass.config_entries.options.async_configure(
        editor["flow_id"], {"yaml_text": json.dumps(unsafe)},
    )
    assert invalid["type"] == FlowResultType.FORM
    assert "min_current_a" in invalid["errors"]["base"]
    assert "min_current_a" in invalid["description_placeholders"]["validation_error"]
    assert "max_current_a" in invalid["description_placeholders"]["validation_error"]
    assert entry.options.get("configuration") is None
    marker = next(k for k in invalid["data_schema"].schema
                  if str(k) == "yaml_text")
    assert json.loads(marker.default()) == unsafe, "Rejected text must remain editable"

    # Now save the complete externally-owned configuration in one HA Options
    # transaction. No physical control, commission or invented Amp limits.
    saved = await hass.config_entries.options.async_configure(
        editor["flow_id"], {"yaml_text": json.dumps(config)},
    )
    assert saved["type"] == FlowResultType.CREATE_ENTRY, saved.get("errors")
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    actual = entry.options["configuration"]
    assert len(actual["assets"]) == len(actual["chargers"]) == 4
    assert actual["controller"]["solar_source_kind"] == "direct_surplus"
    assert actual["controller"]["current_price_entity"] == "sensor.energy_current_price"
    assert [c["kind"] for c in actual["chargers"]] == (
        ["variable_current"] * 3 + ["on_off"]
    )
    assert all(c["control_owner"] == "external"
               and c["physical_commissioned"] is False
               for c in actual["chargers"])
    assert all("min_current_a" not in c and "max_current_a" not in c
               for c in actual["chargers"])

    # Reopen the actual Home Assistant Config Entry: no second store.
    reopened = await hass.config_entries.options.async_init(entry.entry_id)
    again = await hass.config_entries.options.async_configure(
        reopened["flow_id"], {"next_step_id": "yaml"},
    )
    marker = next(k for k in again["data_schema"].schema
                  if str(k) == "yaml_text")
    assert validate_configuration(json.loads(marker.default())) == actual
    assert "physical_commissioned" not in json.loads(marker.default())["chargers"][0]
    # Real existing options (not only first save from an empty entry).
    repeated = await hass.config_entries.options.async_configure(
        again["flow_id"], {"yaml_text": json.dumps(config)},
    )
    assert repeated["type"] == FlowResultType.CREATE_ENTRY, repeated.get("errors")
    await hass.async_block_till_done()
    assert entry.options["configuration"] == actual

    # Independent explicit minimum is a valid preference, not a native maximum.
    partial = json.loads(json.dumps(config))
    partial["chargers"][0]["min_current_a"] = 6
    menu = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(menu["flow_id"], {"next_step_id": "yaml"})
    saved = await hass.config_entries.options.async_configure(form["flow_id"], {"yaml_text": json.dumps(partial)})
    assert saved["type"] == FlowResultType.CREATE_ENTRY, saved.get("errors")
    await hass.async_block_till_done()
    assert entry.options["configuration"]["chargers"][0]["min_current_a"] == 6
    assert "max_current_a" not in entry.options["configuration"]["chargers"][0]
    assert "current_step_a" not in entry.options["configuration"]["chargers"][0]
    assert hass.data[DOMAIN][entry.entry_id].configuration == entry.options["configuration"]

    # Reproduce the previous installed-site ownership mismatch on all four
    # objects, retaining the legacy writer and all existing source bindings.
    legacy = json.loads(json.dumps(actual))
    legacy["chargers"][0].update(kind="on_off", control_owner="multicharge",
                                  physical_commissioned=True)
    hass.states.async_set(legacy["chargers"][0]["control_entity"], "off")
    hass.states.async_set(legacy["chargers"][0]["power_entity"], "0",
                          {"unit_of_measurement": "W"})
    hass.config_entries.async_update_entry(entry, options={"configuration": validate_configuration(legacy)})
    await hass.async_block_till_done()
    menu = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(menu["flow_id"], {"next_step_id": "yaml"})
    saved = await hass.config_entries.options.async_configure(form["flow_id"], {"yaml_text": json.dumps(config)})
    assert saved["type"] == FlowResultType.CREATE_ENTRY, saved.get("errors")
    await hass.async_block_till_done()
    assert entry.options["configuration"] == actual
    assert hass.data[DOMAIN][entry.entry_id].configuration == actual
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_mixed_four_charger_site_native_integrated_soc_and_adjustable_readback(hass: HomeAssistant):
    """Installed HA, actual service APIs, representative sources, not hardware proof."""
    from datetime import datetime, timedelta, timezone

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "home", "name": "Mixed site", "mode": "Force Charge",
                       "max_parallel": 1, "max_power_kw": 3.6},
        "assets": [
            {"id": "car_a", "name": "Car A", "kind": "car", "soc_entity": "sensor.car_a_soc"},
            {"id": "car_b", "name": "Car B", "kind": "car", "soc_entity": "sensor.car_b_soc",
             "target_soc": 80, "capacity_kwh": 60, "charge_efficiency": 0.9},
            {"id": "guest_1", "name": "Guest 1", "kind": "car", "requested_duration_minutes": 30},
            {"id": "guest_2", "name": "Guest 2", "kind": "car", "requested_kwh": 2},
        ],
        "chargers": [{
            "id": uid, "name": uid, "kind": "variable_current",
            "rated_power_kw": 3.6, "control_entity": f"switch.{uid}",
            "current_control_entity": f"number.{uid}_limit",
            "connected_entity": f"sensor.{uid}_connected", "power_entity": f"sensor.{uid}_power",
            "energy_entity": f"sensor.{uid}_energy", "control_owner": "external",
            **({"asset": "car_b", "phase_count": 1, "voltage_v": 230}
               if uid == "outside" else {"current_readback_entity": f"sensor.{uid}_amps"}),
        } for uid in ("wall_a", "wall_b", "outside")] + [{
            "id": "utility", "name": "Utility", "kind": "on_off", "rated_power_kw": 2,
            "control_entity": "switch.utility", "connected_entity": "sensor.utility_connection",
            "power_entity": "sensor.utility_power", "energy_entity": "sensor.utility_energy",
            "control_owner": "external",
        }],
    })
    for uid in ("wall_a", "wall_b", "outside", "utility"):
        hass.states.async_set(f"switch.{uid}", "off")
        hass.states.async_set(f"sensor.{uid}_power", "0", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.outside_connected", "connected")
    hass.states.async_set("sensor.outside_energy", "10", {"unit_of_measurement": "kWh"})
    hass.states.async_set("sensor.car_b_soc", "50", {"unit_of_measurement": "%"})
    hass.states.async_set("number.outside_limit", "6",
                          {"unit_of_measurement": "A", "min": 6, "max": 16, "step": 1})
    entry = MockConfigEntry(domain=DOMAIN, title="Mixed MultiCharge",
                            data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    from custom_components.robotix_multicharge.command_query import apply_native_preference
    await apply_native_preference(hass, entry, runtime, "charger", "outside",
                                  {"control_owner": "multicharge"}, structural=True)
    await hass.async_block_till_done()
    assert hass.data[DOMAIN][entry.entry_id] is runtime
    assert runtime.executor.confirm_current_connection("outside")["status"] == "confirmed"

    commands = []
    async def set_current(call):
        commands.append(("set_value", call.data["value"]))
        hass.states.async_set("number.outside_limit", str(call.data["value"]),
                              {"unit_of_measurement": "A", "min": 6, "max": 16, "step": 1})
    async def start(call):
        commands.append(("turn_on", call.data["entity_id"]))
        hass.states.async_set("switch.outside", "on")
        hass.states.async_set("sensor.outside_power", "1600", {"unit_of_measurement": "W"})
    async def stop(call):
        commands.append(("turn_off", call.data["entity_id"]))
        hass.states.async_set("switch.outside", "off")
        hass.states.async_set("sensor.outside_power", "0", {"unit_of_measurement": "W"})
    hass.services.async_register("number", "set_value", set_current)
    hass.services.async_register("switch", "turn_on", start)
    hass.services.async_register("switch", "turn_off", stop)
    result = await runtime.executor.execute("outside", "start")
    assert result["status"] == "confirmed", result
    assert commands[:2] == [("set_value", 15.0), ("turn_on", "switch.outside")]
    await hass.async_block_till_done()
    assert hass.states.get("switch.outside").state == "on"
    assert runtime.charger_states()["outside"]["charging_session"] == "charging"
    assert runtime.executor.session_snapshot()["outside"]["target_current_a"] == 15
    hass.states.async_set("sensor.car_b_soc", "80", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.outside_energy", "11", {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    await runtime.executor.supervise()
    await hass.async_block_till_done()
    assert commands[-1] == ("turn_off", "switch.outside")
    assert runtime.executor.completed_sessions()[-1]["asset_id"] == "car_b"
    assert all(c["control_owner"] == "external" for c in runtime.configuration["chargers"] if c["id"] != "outside")
    # Reuse the same native sources in a real Ready By proposal; no fictitious tariff.
    hass.states.async_set("sensor.car_b_soc", "50", {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    deadline = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
    await apply_native_preference(hass, entry, runtime, "asset", "car_b", {"ready_by": deadline})
    await hass.async_block_till_done()
    await apply_native_preference(hass, entry, runtime, "controller", "home", {"mode": "Ready By"})
    await hass.async_block_till_done()
    runtime.refresh()
    assert runtime.assessment is not None
    assert any(slot.charger_uid == "outside" for slot in runtime.assessment.plan.slots)
    assert len(runtime.configuration["chargers"]) == len(runtime.configuration["assets"]) == 4
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_native_expert_can_relinquish_existing_idle_owner_in_one_save(hass: HomeAssistant):
    """Existing Config Entry, explicit monitoring intent, not physical certification."""
    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "home", "name": "Existing site", "mode": "Off",
                       "max_parallel": 1, "max_power_kw": 3.6},
        "assets": [],
        "chargers": [{
            "id": "wall", "name": "Existing wall", "kind": "on_off",
            "rated_power_kw": 3.6, "control_entity": "switch.wall",
            "connected_entity": "binary_sensor.wall_connected",
            "power_entity": "sensor.wall_power", "control_owner": "multicharge",
            "physical_commissioned": True,
        }],
    })
    hass.states.async_set("switch.wall", "off")
    hass.states.async_set("sensor.wall_power", "0", {"unit_of_measurement": "W"})
    entry = MockConfigEntry(domain=DOMAIN, title="MultiCharge Community",
                            data={"source": "ui", "configuration": cfg},
                            unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    menu = await hass.config_entries.options.async_init(entry.entry_id)
    editor = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "yaml"},
    )
    proposed = json.loads(json.dumps(cfg))
    proposed["chargers"][0].update(control_owner="external",
                                   physical_commissioned=False,
                                   kind="variable_current")
    proposed["controller"]["current_price_entity"] = "sensor.optional_price"
    result = await hass.config_entries.options.async_configure(
        editor["flow_id"], {"yaml_text": json.dumps(proposed)},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY, result.get("errors")
    await hass.async_block_till_done()
    assert entry.options["configuration"] == validate_configuration(proposed)
    assert hass.data[DOMAIN][entry.entry_id].configuration == validate_configuration(proposed)
    assert hass.states.get("switch.wall").state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_optional_one_click_install_and_native_guided_configure(
    hass: HomeAssistant,
):
    """Real HA: install without a wizard, configure real objects afterwards."""
    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    assert await async_setup_component(hass, DOMAIN, {})
    installed_entry = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER},
    )
    assert installed_entry["type"] == FlowResultType.CREATE_ENTRY
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    entry = entries[0]
    initial = entry.data["configuration"]
    assert initial["assets"] == []
    assert initial["chargers"] == []
    await hass.async_block_till_done()

    async def menu_step(step_id):
        menu = await hass.config_entries.options.async_init(entry.entry_id)
        assert menu["type"] == FlowResultType.MENU
        assert step_id in menu["menu_options"]
        return await hass.config_entries.options.async_configure(
            menu["flow_id"], {"next_step_id": step_id},
        )

    site = await menu_step("controller")
    assert site["type"] == FlowResultType.FORM
    assert site["step_id"] == "controller"
    result = await hass.config_entries.options.async_configure(
        site["flow_id"], {
            "name": "Configured Home", "mode": "Automatic",
            "max_parallel": 2, "max_power_kw": 7.2,
            "power_adjustment_interval_minutes": 7,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY, result.get("errors")
    await hass.async_block_till_done()
    assert entry.options["configuration"]["controller"]["name"] == "Configured Home"
    assert entry.options["configuration"]["controller"]["max_parallel"] == 2
    assert entry.options["configuration"]["controller"]["power_adjustment_interval_minutes"] == 7

    choose_charger = await menu_step("charger_pick")
    assert choose_charger["step_id"] == "charger_pick"
    new_charger = await hass.config_entries.options.async_configure(
        choose_charger["flow_id"], {"selected": "__new__"},
    )
    assert new_charger["step_id"] == "charger"
    hass.states.async_set("switch.wallbox_test", "off")
    hass.states.async_set("sensor.wallbox_test_power", "0", {"unit_of_measurement": "kW"})
    charger = await hass.config_entries.options.async_configure(
        new_charger["flow_id"], {
            "action": "save", "id": "garage_white", "name": "Garage White",
            "kind": "on_off", "rated_power_kw": 3.6,
            "control_entity": "switch.wallbox_test",
            "power_entity": "sensor.wallbox_test_power",
        },
    )
    assert charger["type"] == FlowResultType.CREATE_ENTRY, charger.get("errors")
    await hass.async_block_till_done()
    assert entry.options["configuration"]["chargers"][0]["id"] == "garage_white"
    assert entry.options["configuration"]["chargers"][0]["control_owner"] == "multicharge"

    choose_existing = await menu_step("charger_pick")
    assert choose_existing["data_schema"].schema
    edit_charger = await hass.config_entries.options.async_configure(
        choose_existing["flow_id"], {"selected": "garage_white"},
    )
    assert edit_charger["step_id"] == "charger"
    name_marker = next(k for k in edit_charger["data_schema"].schema
                       if str(k) == "name")
    assert name_marker.default() == "Garage White"
    edited_charger = await hass.config_entries.options.async_configure(
        edit_charger["flow_id"], {"action": "save", "name": "White Wallbox",
                                 "kind": "on_off", "rated_power_kw": 3.6,
                                 "control_owner": "external"},
    )
    assert edited_charger["type"] == FlowResultType.CREATE_ENTRY, edited_charger.get("errors")
    await hass.async_block_till_done()
    saved_charger = entry.options["configuration"]["chargers"][0]
    assert saved_charger["id"] == "garage_white"
    assert saved_charger["name"] == "White Wallbox"
    assert saved_charger["control_entity"] == "switch.wallbox_test"

    choose_asset = await menu_step("asset_pick")
    new_asset = await hass.config_entries.options.async_configure(
        choose_asset["flow_id"], {"selected": "__new__"},
    )
    saved_asset = await hass.config_entries.options.async_configure(
        new_asset["flow_id"], {
            "action": "save", "id": "audi_q8", "name": "Audi Q8",
            "kind": "car", "soc_entity": "sensor.audi_oem_soc",
            "target_soc": 80,
        },
    )
    assert saved_asset["type"] == FlowResultType.CREATE_ENTRY, saved_asset.get("errors")
    await hass.async_block_till_done()
    assert entry.options["configuration"]["assets"][0]["id"] == "audi_q8"
    assert entry.options["configuration"]["assets"][0]["soc_entity"] == "sensor.audi_oem_soc"

    source_form = await menu_step("energy")
    assert source_form["step_id"] == "energy"
    energy = await hass.config_entries.options.async_configure(
        source_form["flow_id"], {
            "use_energy_dashboard": False, "solar_source_kind": "none",
            "grid_power_direction": "import_positive",
            "current_price_entity": "sensor.energy_current_price",
            "solar_power_entity": "sensor.energy_solar_power",
        },
    )
    assert energy["type"] == FlowResultType.CREATE_ENTRY, energy.get("errors")
    await hass.async_block_till_done()
    final = entry.options["configuration"]
    assert final["controller"]["current_price_entity"] == "sensor.energy_current_price"
    assert final["controller"]["solar_power_entity"] == "sensor.energy_solar_power"
    assert final["assets"][0]["id"] == "audi_q8"
    assert final["chargers"][0]["id"] == "garage_white"

    choose_current_asset = await menu_step("asset_pick")
    edit_asset = await hass.config_entries.options.async_configure(
        choose_current_asset["flow_id"], {"selected": "audi_q8"},
    )
    soc_marker = next(k for k in edit_asset["data_schema"].schema
                      if str(k) == "soc_entity")
    assert soc_marker.default() == "sensor.audi_oem_soc"
    update_asset = await hass.config_entries.options.async_configure(
        edit_asset["flow_id"], {
            "action": "save", "name": "Audi Q8", "kind": "car",
            "target_soc": 85,
        },
    )
    assert update_asset["type"] == FlowResultType.CREATE_ENTRY, update_asset.get("errors")
    await hass.async_block_till_done()
    assert entry.options["configuration"]["assets"][0]["target_soc"] == 85
    assert entry.options["configuration"]["assets"][0]["soc_entity"] == (
        "sensor.audi_oem_soc"
    )

    choose_current_charger = await menu_step("charger_pick")
    delete_form = await hass.config_entries.options.async_configure(
        choose_current_charger["flow_id"], {"selected": "garage_white"},
    )
    deleted = await hass.config_entries.options.async_configure(
        delete_form["flow_id"], {"action": "delete", "name": "White Wallbox",
                                 "kind": "on_off", "rated_power_kw": 3.6},
    )
    assert deleted["type"] == FlowResultType.CREATE_ENTRY, deleted.get("errors")
    await hass.async_block_till_done()
    assert entry.options["configuration"]["chargers"] == []

    choose_current_asset = await menu_step("asset_pick")
    delete_asset = await hass.config_entries.options.async_configure(
        choose_current_asset["flow_id"], {"selected": "audi_q8"},
    )
    deleted_asset = await hass.config_entries.options.async_configure(
        delete_asset["flow_id"], {"action": "delete", "name": "Audi Q8",
                                  "kind": "car"},
    )
    assert deleted_asset["type"] == FlowResultType.CREATE_ENTRY, deleted_asset.get("errors")
    await hass.async_block_till_done()
    assert entry.options["configuration"]["assets"] == []
    assert entry.options["configuration"]["controller"]["name"] == "Configured Home"
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
    """One native source owner, no templates or shadow Options settings."""
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
    assert menu["type"] == FlowResultType.MENU
    assert "energy" in menu["menu_options"]
    assert await hass.config_entries.async_unload(entry.entry_id)

@pytest.mark.asyncio
async def test_installed_automatic_soc_recovers_external_stop_and_source_return(
    hass: HomeAssistant, freezer,
):
    """End-to-end native HA time/events, one writer, no repeated resident actions."""
    from datetime import datetime, timezone
    from pytest_homeassistant.common import async_fire_time_changed

    initial = datetime(2026, 11, 26, 8, 1, tzinfo=timezone.utc)
    freezer.move_to(initial)
    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "site", "name": "Autonomous recovery", "mode": "Automatic",
                       "max_parallel": 1, "max_power_kw": 3.6},
        "assets": [{"id": "car", "name": "Car", "kind": "car",
                    "soc_entity": "sensor.auto_soc", "target_soc": 80,
                    "capacity_kwh": 30, "charge_efficiency": 0.9}],
        "chargers": [{"id": "drive", "name": "Drive", "kind": "on_off",
                      "asset": "car", "rated_power_kw": 2, "phase_count": 1,
                      "control_owner": "multicharge", "physical_commissioned": True,
                      "control_entity": "switch.auto_drive",
                      "connected_entity": "binary_sensor.auto_cable",
                      "power_entity": "sensor.auto_power", "energy_entity": "sensor.auto_meter"}],
    })
    def power(watts):
        hass.states.async_set("sensor.auto_power", str(watts), {"unit_of_measurement": "W"})

    hass.states.async_set("switch.auto_drive", "off")
    hass.states.async_set("binary_sensor.auto_cable", "on")
    hass.states.async_set("sensor.auto_soc", "50", {"unit_of_measurement": "%"})
    hass.states.async_set("sensor.auto_meter", "5", {"unit_of_measurement": "kWh"})
    power(0)
    commands = []

    async def start(call):
        commands.append(call.service)
        hass.states.async_set("switch.auto_drive", "on")
        power(0)  # vehicle initially refuses energy; switch is positively enabled

    async def stop(call):
        commands.append(call.service)
        hass.states.async_set("switch.auto_drive", "off")
        power(0)

    hass.services.async_register("switch", "turn_on", start)
    hass.services.async_register("switch", "turn_off", stop)
    entry = MockConfigEntry(domain=DOMAIN, title="Automatic recovery",
                            data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    assert commands == []

    async def quarter(minute):
        when = initial.replace(minute=minute)
        freezer.move_to(when)
        # Refresh independent provider evidence before the actual HA timer.
        hass.states.async_set("binary_sensor.auto_cable", "on")
        hass.states.async_set("sensor.auto_soc", "50", {"unit_of_measurement": "%"})
        power(0)
        await hass.async_block_till_done()
        async_fire_time_changed(hass, when)
        await hass.async_block_till_done()
        assert hass.states.get("switch.auto_drive").state == "on"
        assert runtime.executor.snapshot()["drive"]["reason"] == "ENABLED_WAITING_FOR_VEHICLE"
        assert runtime.executor.session_snapshot()["drive"]["asset_id"] == "car"
        assert runtime.charger_states()["drive"]["operational_status"]["status"] == "idle"

    await quarter(15)
    freezer.move_to(initial.replace(minute=16))
    power(1200)
    await hass.async_block_till_done()
    assert runtime.charger_states()["drive"]["operational_status"]["status"] == "charging"
    assert commands == ["turn_on"]
    freezer.move_to(initial.replace(minute=17))
    hass.states.async_set("sensor.auto_meter", "5.1", {"unit_of_measurement": "kWh"})
    hass.states.async_set("switch.auto_drive", "off")
    power(0)
    await hass.async_block_till_done()
    assert not runtime.executor._inflight and not runtime.executor.session_snapshot()
    assert commands == ["turn_on"]  # external verified STOP needs no repeat command

    await quarter(30)
    freezer.move_to(initial.replace(minute=31))
    hass.states.async_set("binary_sensor.auto_cable", "unavailable")
    await hass.async_block_till_done()
    assert hass.states.get("switch.auto_drive").state == "off"
    assert commands == ["turn_on", "turn_on", "turn_off"]
    assert not runtime.executor._inflight
    freezer.move_to(initial.replace(minute=32))
    hass.states.async_set("binary_sensor.auto_cable", "on")
    await hass.async_block_till_done()
    assert commands[-1] == "turn_off"  # next eligible quarter owns admission

    await quarter(45)
    freezer.move_to(initial.replace(minute=46))
    power(1200)
    hass.states.async_set("sensor.auto_meter", "5.3", {"unit_of_measurement": "kWh"})
    hass.states.async_set("sensor.auto_soc", "80", {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    assert hass.states.get("switch.auto_drive").state == "off"
    assert commands == ["turn_on", "turn_on", "turn_off", "turn_on", "turn_off"]
    assert not runtime.executor._inflight and not runtime.executor.session_snapshot()
    assert runtime.goal_assessments["drive"]["status"] == "target_met"
    # A normal OEM-app action is not a second autonomous controller. Stop an
    # externally energized output when the goal is already met.
    freezer.move_to(initial.replace(minute=47))
    hass.states.async_set("switch.auto_drive", "on")
    power(1000)
    await hass.async_block_till_done()
    assert hass.states.get("switch.auto_drive").state == "off"
    assert commands[-1] == "turn_off"
    receipts = runtime.executor.completed_sessions()
    assert len(receipts) == 3
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    replacement = hass.data[DOMAIN][entry.entry_id]
    assert replacement is not runtime and replacement.configuration == cfg
    assert replacement.executor.completed_sessions() == receipts
    assert not replacement.executor._inflight
    assert commands.count("turn_on") == 3
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize("count", [0, 1, 4, 10])
@pytest.mark.asyncio
async def test_installed_scale_source_publication_and_reload(hass: HomeAssistant, count):
    """Measured HA owner/aggregate publication and lifecycle; not EVSE or soak proof."""
    from time import perf_counter, process_time
    from homeassistant.helpers import entity_registry as er

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    cfg = validate_configuration({
        "controller": {"id": "site", "name": "Scale", "mode": "Automatic",
                       "max_parallel": max(1, count), "max_power_kw": 3.6*max(1, count),
                       "home_power_entity": "sensor.scale_home"},
        "assets": [{"id": f"car_{i}", "name": f"Car {i}", "kind": "car",
                    "soc_entity": f"sensor.scale_soc_{i}", "target_soc": 80,
                    "capacity_kwh": 30, "charge_efficiency": 0.9}
                   for i in range(count)],
        "chargers": [{"id": f"drive_{i}", "name": f"Drive {i}", "kind": "on_off",
                      "asset": f"car_{i}", "rated_power_kw": 3.6,
                      "control_owner": "external", "control_entity": f"switch.scale_{i}",
                      "connected_entity": f"binary_sensor.scale_{i}",
                      "power_entity": f"sensor.scale_power_{i}"}
                     for i in range(count)],
    })
    hass.states.async_set("sensor.scale_home", "1000", {"unit_of_measurement": "W"})
    for i in range(count):
        hass.states.async_set(f"switch.scale_{i}", "off")
        hass.states.async_set(f"binary_sensor.scale_{i}", "on")
        hass.states.async_set(f"sensor.scale_power_{i}", "0", {"unit_of_measurement": "W"})
        hass.states.async_set(f"sensor.scale_soc_{i}", "50", {"unit_of_measurement": "%"})
    entry = MockConfigEntry(domain=DOMAIN, title="Scale qualification",
                            data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    started, cpu_start = perf_counter(), process_time()
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    runtime = hass.data[DOMAIN][entry.entry_id]
    setup_ms = (perf_counter()-started)*1000
    registry = er.async_get(hass)
    aggregate = registry.async_get_entity_id("sensor", DOMAIN, f"{DOMAIN}:controller:site:power")
    assert aggregate
    owner_ids = [registry.async_get_entity_id("sensor", DOMAIN,
                 f"{DOMAIN}:charger:drive_{i}:power") for i in range(count)]
    assert all(owner_ids)
    samples = []
    for cycle in range(6):
        watts = 1000 if cycle % 2 == 0 else 0
        started = perf_counter()
        for i in range(count):
            hass.states.async_set(f"sensor.scale_power_{i}", str(watts),
                                  {"unit_of_measurement": "W"})
        hass.states.async_set("sensor.scale_home", str(1001+cycle),
                              {"unit_of_measurement": "W"})
        await hass.async_block_till_done()
        samples.append((perf_counter()-started)*1000)
        if count:
            assert float(hass.states.get(aggregate).state) == pytest.approx(count*watts/1000)
        else:
            assert hass.states.get(aggregate).state == "unknown"
        assert all(float(hass.states.get(entity).state) == pytest.approx(watts/1000)
                   for entity in owner_ids)
        assert runtime.executor.snapshot() == {}
    assert max(samples) <= 2000, (count, samples)
    metrics = runtime.performance_snapshot()
    # The test does not depend on a page or a minute timer to publish.
    print("MC_NATIVE_SCALE", count, "setup_ms", round(setup_ms, 2),
          "publication_batch_max_ms", round(max(samples), 2),
          "cpu_ms", round((process_time()-cpu_start)*1000, 2),
          "runtime", json.dumps(metrics, sort_keys=True))
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    replacement = hass.data[DOMAIN][entry.entry_id]
    assert replacement is not runtime and not runtime.active
    assert replacement.configuration == cfg
    assert not runtime._listeners and not runtime._unsubscribers
    assert not runtime._recorder_inflight and not runtime.executor._source_stop_tasks
    assert [registry.async_get_entity_id("sensor", DOMAIN,
            f"{DOMAIN}:charger:drive_{i}:power") for i in range(count)] == owner_ids
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert not replacement.active and not replacement._listeners
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


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
    from datetime import datetime
    from zoneinfo import ZoneInfo
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
    expected = normalize_expert_json(expert)
    expected["assets"][0]["target_soc"] = 80.0
    saved_asset = entry.data["configuration"]["assets"][0]
    assert saved_asset["ready_by_repeat"] == "daily"
    anchor = datetime.fromisoformat(saved_asset["ready_by"])
    assert anchor.astimezone(ZoneInfo(hass.config.time_zone)).strftime("%H:%M") == "06:00"
    expected["assets"][0].update(
        ready_by=saved_asset["ready_by"], ready_by_repeat="daily",
        maintain_soc_until_ready_by=False,
    )
    assert entry.data["configuration"] == expected
    unchanged = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT, "expert_format": "json"},
        data=normalize_expert_json(expert),
    )
    await hass.async_block_till_done()
    assert unchanged["reason"] == "already_configured"
    assert entry.data["configuration"] == expected
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
        # Active defaults still require observed idle hardware for registration.
        hass.states.async_set("switch." + key, "off")
        hass.states.async_set("sensor." + key + "_power", "0",
                              {"unit_of_measurement": "W"})
        hass.states.async_set("binary_sensor." + key + "_connected", "off")
        await hass.async_block_till_done()
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
    assert all(c["control_owner"] == "multicharge"
               and c["physical_commissioned"] is True
               for c in saved["chargers"])
    assert all(a["target_soc"] == 80 and a["ready_by_repeat"] == "daily"
               for a in saved["assets"])
    devices = dr.async_get(hass)
    assert devices.async_get_device_by_identifier(
        (DOMAIN, "charger/white"), entry.entry_id,
    )
    assert devices.async_get_device_by_identifier(
        (DOMAIN, "asset/audi"), entry.entry_id,
    )
    opts = await hass.config_entries.options.async_init(entry.entry_id)
    assert opts["type"] == FlowResultType.MENU
    assert {"charger_pick", "asset_pick", "yaml"}.issubset(opts["menu_options"])
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

    # Actual HA timer callback: the helper advances HA scheduled time, not
    # a fabricated state_changed Event. No automatic command for Inactive.
    from datetime import timedelta
    from pytest_homeassistant.common import async_fire_time_changed
    from unittest.mock import patch
    with patch.object(runtime, "refresh", wraps=runtime.refresh) as refresh:
        async_fire_time_changed(hass, datetime.now(timezone.utc)+timedelta(minutes=1, seconds=2))
        await hass.async_block_till_done()
        assert refresh.call_count >= 1

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
    replugged = runtime.executor.connection_confirmation(charger, datetime.now(timezone.utc))
    assert replugged is not None
    assert replugged["connected_at"] != original_epoch
    assert replugged["basis"] == "user_assignment"
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
    # A committed revision can precede the asynchronous runtime update.
    # A second native writer without a supplied revision must not overwrite it.
    from copy import deepcopy
    applied = deepcopy(runtime.configuration)
    pending = deepcopy(entry.options["configuration"])
    pending["controller"]["name"] = "First committed edit"
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "configuration": pending},
    )
    await hass.async_block_till_done()
    # HA may dispatch the listener eagerly; explicitly reproduce the
    # unapplied runtime snapshot rather than assuming a scheduling order.
    runtime.configuration = applied
    try:
        with pytest.raises(ValueError, match="stale_settings"):
            await apply_native_preference(
                hass, entry, runtime, "controller", "home", {"name": "Stale edit"},
            )
    finally:
        runtime.configuration = pending
        runtime.refresh()
    await hass.async_block_till_done()
    assert entry.options["configuration"]["controller"]["name"] == "First committed edit"
    assert runtime.configuration["controller"]["name"] == "First committed edit"
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
    interval = ids.async_get_entity_id(
        "number", DOMAIN, f"{DOMAIN}:controller:site:power_adjustment_interval_minutes",
    )
    maintain = ids.async_get_entity_id(
        "select", DOMAIN, f"{DOMAIN}:asset:b:maintain_soc_until_ready_by",
    )
    assert all((vehicle, mode, target, interval, maintain))
    assert hass.states.get(maintain).state == "on"  # legacy behavior retained
    assert float(hass.states.get(interval).state) == 5
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
        await hass.services.async_call(
            "select", "select_option",
            {"entity_id": maintain, "option": "off"},
            blocking=True, context=Context(user_id="admin"),
        )
        await hass.async_block_till_done()
        assert entry.options["configuration"]["assets"][1]["maintain_soc_until_ready_by"] is False
        assert hass.states.get(maintain).state == "off"
        await hass.services.async_call(
            "number", "set_value", {"entity_id": interval, "value": 7},
            blocking=True, context=Context(user_id="admin"),
        )
        await hass.async_block_till_done()
        assert entry.options["configuration"]["controller"]["power_adjustment_interval_minutes"] == 7
        assert float(hass.states.get(interval).state) == 7

        for user_id in ("resident", None):
            with pytest.raises(RuntimeError, match="administrator"):
                await hass.services.async_call(
                    "number", "set_value", {"entity_id": interval, "value": 3},
                    blocking=True, context=Context(user_id=user_id),
                )
            assert entry.options["configuration"]["controller"]["power_adjustment_interval_minutes"] == 7
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
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert float(hass.states.get(interval).state) == 7
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

    request_id += 1
    await client.send_json({
        "id": request_id, "type": "robotix_multicharge/yaml_configuration",
        "operation": "review", "yaml_text": text, "expected_revision": initial,
    })
    legacy = await client.receive_json()
    assert legacy["success"] is False
    assert "FRONTEND_VERSION_MISMATCH" in legacy["error"]["message"]
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

    # A direct native Config Entry change during the Store await must not be
    # overwritten by the older dashboard transaction.
    from unittest.mock import patch
    runtime = hass.data[DOMAIN][entry.entry_id]
    actual_save = runtime._control_store.async_save
    competing = json.loads(json.dumps(changed))
    competing["controller"]["name"] = "Native concurrent edit"
    older = json.loads(json.dumps(changed))
    older["controller"]["name"] = "Stale dashboard edit"
    injected = False

    async def concurrent_save(payload):
        nonlocal injected
        await actual_save(payload)
        if not injected:
            injected = True
            hass.config_entries.async_update_entry(
                entry, options={**entry.options, "configuration": competing},
            )

    with patch.object(runtime._control_store, "async_save", side_effect=concurrent_save):
        conflicted = await yaml_ws(json.dumps(older), proposed)
        assert conflicted["success"] is False
    await hass.async_block_till_done()
    assert entry.options["configuration"] == competing
    runtime = hass.data[DOMAIN][entry.entry_id]
    proposed = configuration_revision(competing)
    with patch.object(runtime._control_store, "async_save", side_effect=OSError("Store unavailable")):
        failed = await yaml_ws(json.dumps(older), proposed)
        assert failed["success"] is False
    assert entry.options["configuration"] == competing
    changed = competing
    text = json.dumps(changed, indent=2)

    # Even an admin cannot acquire a visibly energized endpoint while
    # its former owner is still using it. Explicit idle activation is valid.
    control = changed["chargers"][0]["control_entity"]
    hass.states.async_set(control, "on")
    await hass.async_block_till_done()
    unsafe = json.loads(text)
    unsafe["chargers"][0]["control_owner"] = "multicharge"
    unsafe["chargers"][0]["physical_commissioned"] = True
    denied = await yaml_ws(json.dumps(unsafe), proposed)
    assert denied["success"] is False
    assert entry.options["configuration"]["chargers"][0]["control_owner"] == "external"
    hass.states.async_set(control, "off")
    await hass.async_block_till_done()
    enabled = await yaml_ws(json.dumps(unsafe), proposed)
    assert enabled["success"] is True
    await hass.async_block_till_done()
    assert entry.options["configuration"]["chargers"][0]["control_owner"] == "multicharge"

    await client.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_native_discovery_activation_and_reload_through_websocket(
    hass: HomeAssistant, hass_ws_client,
):
    """Installed HA registry, typed Save, busy refusal and persistent readback.

    Native HA states here are controlled test inputs, not EVSE field evidence.
    """
    from homeassistant.helpers import entity_registry as er

    source = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN
    installed = Path(hass.config.config_dir) / "custom_components" / DOMAIN
    if not installed.exists():
        shutil.copytree(source, installed)
    provider = MockConfigEntry(domain="demo", title="Native source")
    provider.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=provider.entry_id, identifiers={("demo", "native_evse")},
    )
    registry = er.async_get(hass)

    def native(domain, uid, value, attrs=None):
        row = registry.async_get_or_create(
            domain, "demo", uid, config_entry=provider,
            device_id=device.id, suggested_object_id=uid,
        )
        hass.states.async_set(row.entity_id, value, attrs or {})
        return row.entity_id

    switch = native("switch", "native_enable", "off")
    power_attrs = {"device_class": "power", "unit_of_measurement": "W"}
    power = native("sensor", "native_power", "0", power_attrs)
    plug = native("binary_sensor", "native_plug", "off", {"device_class": "plug"})
    current = native("number", "native_current", "16", {
        "unit_of_measurement": "A", "min": 6, "max": 32, "step": 1,
    })
    meter = native("sensor", "native_meter", "10", {
        "device_class": "energy", "unit_of_measurement": "kWh",
        "state_class": "total_increasing",
    })
    cfg = validate_configuration({
        "controller": {"id": "home", "name": "Home", "mode": "Off", "max_parallel": 1},
        "assets": [],
        "chargers": [{"id": "native", "name": "Native EVSE", "kind": "variable_current",
                      "rated_power_kw": 7.4, "control_entity": switch,
                      "control_owner": "external", "physical_commissioned": False}],
    })
    entry = MockConfigEntry(domain=DOMAIN, title="MultiCharge",
                            data={"source": "ui", "configuration": cfg}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    request_id = 700

    async def ws(kind, **fields):
        nonlocal request_id
        request_id += 1
        await client.send_json({"id": request_id, "type": f"robotix_multicharge/{kind}", **fields})
        reply = await client.receive_json()
        assert reply["id"] == request_id
        return reply

    async def read(**fields):
        reply = await ws("get_plan", day="today", include_history=False, **fields)
        assert reply["success"], reply
        return reply["result"]

    initial = await read(discover_charger={"control_entity": switch, "kind": "variable_current"})
    proposal = initial["charger_setup"]["native"]["proposed_missing"]
    assert proposal["power_entity"] == power
    assert proposal["connected_entity"] == plug
    assert proposal["current_control_entity"] == current
    assert proposal["energy_entity"] == meter
    assert (proposal["phase_count"], proposal["voltage_v"]) == (1, 230)
    assert not {"min_current_a", "max_current_a", "current_step_a"} & proposal.keys()
    assert initial["charger_setup_draft"]["proposed_missing"] == proposal
    assert entry.options.get("configuration") is None  # discovery never writes
    saved = await ws("update_settings", scope="charger", target_id="native",
                     structural=True, changes={**proposal, "min_current_a": 6, "max_current_a": 16,
                                                "current_step_a": 1},
                     expected_revision=initial["configuration_revision"])
    assert saved["success"], saved
    await hass.async_block_till_done()
    readback = await read()
    assert readback["configuration_revision"] == saved["result"]["expected_revision"]
    setup = readback["charger_setup"]["native"]
    assert setup["configured_current"]["max_current_a"] == 16
    assert setup["native_current"]["max_current_a"] == 32
    assert setup["effective_current"]["max_current_a"] == 16
    assert "current_control_entity" not in setup["proposed_missing"]
    hass.states.async_set(switch, "on")
    hass.states.async_set(power, "2000", power_attrs)
    await hass.async_block_till_done()
    denied = await ws("update_settings", scope="charger", target_id="native",
                      structural=True, changes={"control_owner": "multicharge"},
                      expected_revision=readback["configuration_revision"])
    assert not denied["success"] and "CHARGER_BUSY_STOP_FIRST" in denied["error"]["message"]
    assert entry.options["configuration"]["chargers"][0]["control_owner"] == "external"
    hass.states.async_set(switch, "off")
    hass.states.async_set(power, "0", power_attrs)
    await hass.async_block_till_done()
    enabled = await ws("update_settings", scope="charger", target_id="native",
                       structural=True, changes={"control_owner": "multicharge"},
                       expected_revision=readback["configuration_revision"])
    assert enabled["success"], enabled
    await hass.async_block_till_done()
    confirmed = await read()
    assert confirmed["configuration_revision"] == enabled["result"]["expected_revision"]
    assert confirmed["charger_states"]["native"]["activation"] == "active"
    assert hass.states.get(switch).state == "off"  # Save is not a START
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    after = await read()
    assert after["configuration_revision"] == confirmed["configuration_revision"]
    assert after["charger_setup"]["native"]["configured_current"]["max_current_a"] == 16
    await client.close()
    assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_native_control_store_failed_restore_keeps_original_receipts(hass: HomeAssistant):
    """Use HA's actual Store and reopen it, never replace invalid evidence."""
    from datetime import datetime, timedelta, timezone
    from homeassistant.helpers.storage import Store
    from custom_components.robotix_multicharge.runtime import MultiChargeRuntime
    cfg = validate_configuration({
        "controller": {"id": "site", "name": "Site", "mode": "Off"},
        "chargers": [], "assets": [],
    })
    initial = MultiChargeRuntime(hass, cfg)
    valid = initial.executor.export_state()
    stamp = datetime.now(timezone.utc)-timedelta(days=1)
    valid["sessions"] = [
        {"charger_id": "retired", "asset_id": "car",
         "started_at": (stamp+timedelta(minutes=i*2)).isoformat(),
         "ended_at": (stamp+timedelta(minutes=i*2+1)).isoformat(),
         "duration_minutes": 1.0, "actual_energy_kwh": 0.1,
         "physical_stop_confirmed": True}
        for i in range(201)
    ]
    for field, corrupted in (
        ("sessions", [*valid["sessions"], {"started_at": "corrupt"}]),
        ("power_bindings", {"retired": [{"start": "corrupt", "entity": "sensor.old"}]}),
        ("energy_bindings", {"retired": [{"start": "corrupt", "entity": "sensor.old"}]}),
        ("sessions", [*valid["sessions"][:-1], {**valid["sessions"][-1], "duration_minutes": -1}]),
    ):
        key = "multicharge_recovery_"+field
        store = Store(hass, 1, key)
        original = {**valid, field: corrupted}
        await store.async_save(original)
        runtime = MultiChargeRuntime(hass, cfg)
        runtime.attach_control_store(store, await store.async_load())
        assert not runtime.executor._persistence_verified
        assert runtime._control_restore_failed
        assert not await runtime.persist_control_state()
        from custom_components.robotix_multicharge.config_flow import (
            _assert_safe_expert_import, _assert_safe_yaml_ui_commit,
        )
        from custom_components.robotix_multicharge.diagnostics import build_diagnostics
        from types import SimpleNamespace
        revised = {**cfg, "controller": {**cfg["controller"], "name": "New"}}
        for save in (_assert_safe_expert_import, _assert_safe_yaml_ui_commit):
            save(runtime, cfg)  # identical configuration remains a no-op
            with pytest.raises(ValueError, match="CONTROL_STATE_UNVERIFIED"):
                save(runtime, revised)
        runtime.refresh()
        assert build_diagnostics(runtime, SimpleNamespace())["execution"]["original_store_retained"]
        reopened = Store(hass, 1, key)
        assert await reopened.async_load() == original
        # Explicit recovery of valid state, followed by a fresh runtime.
        await reopened.async_save(valid)
        recovered = MultiChargeRuntime(hass, cfg)
        recovered.attach_control_store(reopened, await reopened.async_load())
        assert recovered.executor._persistence_verified
        assert not recovered._control_restore_failed
        _assert_safe_yaml_ui_commit(recovered, revised)
        assert len(recovered.executor.completed_sessions()) == 201
        assert await recovered.persist_control_state()
        assert (await Store(hass, 1, key).async_load())["sessions"] == valid["sessions"]


@pytest.mark.asyncio
@pytest.mark.parametrize("goal", [
    {"requested_kwh": 4},
    {"requested_duration_minutes": 60},
    {"requested_budget_amount": 10, "requested_budget_currency": "EUR"},
])
async def test_native_store_pending_and_confirmed_start_reconcile_without_replay(
    hass: HomeAssistant, goal,
):
    """Actual HA Store, services and state recreation; not live EVSE hardware."""
    from copy import deepcopy
    from datetime import datetime, timedelta, timezone
    from homeassistant.helpers.storage import Store
    from custom_components.robotix_multicharge.runtime import MultiChargeRuntime

    now = datetime.now(timezone.utc)
    cfg = validate_configuration({
        "controller": {"id": "site", "name": "Native recovery", "mode": "Force Charge",
                       "max_parallel": 1, "max_power_kw": 3.6,
                       "price_entity": "sensor.recovery_tariff"},
        "assets": [{"id": "car", "name": "Car", "kind": "car", **goal}],
        "chargers": [{"id": "drive", "name": "Drive", "kind": "on_off",
                      "rated_power_kw": 2, "phase_count": 1, "asset": "car",
                      "control_owner": "multicharge", "physical_commissioned": True,
                      "control_entity": "switch.recovery",
                      "connected_entity": "binary_sensor.recovery",
                      "power_entity": "sensor.recovery_power",
                      "energy_entity": "sensor.recovery_energy"}],
    })
    hass.states.async_set("sensor.recovery_tariff", "ready", {
        "kind": "effective_price_kwh", "currency": "EUR",
        "valid_until": (now+timedelta(hours=3)).isoformat(),
        "intervals": [{"start": (now-timedelta(hours=1)).isoformat(),
                       "end": (now+timedelta(hours=3)).isoformat(), "value": 0.25}],
    })
    hass.states.async_set("binary_sensor.recovery", "on")
    hass.states.async_set("switch.recovery", "off")
    hass.states.async_set("sensor.recovery_power", "0", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.recovery_energy", "5", {"unit_of_measurement": "kWh"})
    store = Store(hass, 1, "mc_actual_start_recovery")
    runtime = MultiChargeRuntime(hass, cfg)
    runtime.attach_control_store(store, None)
    runtime.refresh()
    commands = []
    pending = None
    async def start(call):
        nonlocal pending
        pending = deepcopy(await Store(hass, 1, "mc_actual_start_recovery").async_load())
        commands.append(call.service)
        hass.states.async_set("switch.recovery", "on")
        hass.states.async_set("sensor.recovery_power", "1600", {"unit_of_measurement": "W"})
    async def stop(call):
        commands.append(call.service)
        hass.states.async_set("switch.recovery", "off")
        hass.states.async_set("sensor.recovery_power", "0", {"unit_of_measurement": "W"})
    hass.services.async_register("switch", "turn_on", start)
    hass.services.async_register("switch", "turn_off", stop)
    outcome = await runtime.executor.execute("drive", "start")
    assert outcome["status"] == "confirmed", outcome
    assert pending["interrupted_sessions"]["drive"]["pending"] is True
    confirmed = deepcopy(await Store(hass, 1, "mc_actual_start_recovery").async_load())
    assert not confirmed["interrupted_sessions"]["drive"].get("pending")
    for label, snapshot in (("pending", pending), ("confirmed", confirmed)):
        # A real native provider recreation gives new timestamps. Old
        # physical continuity cannot be assumed from these state values.
        for entity, value, attrs in (
                ("switch.recovery", "on", {}),
                ("binary_sensor.recovery", "on", {}),
                ("sensor.recovery_power", "1600", {"unit_of_measurement": "W"}),
                ("sensor.recovery_energy", "5.4", {"unit_of_measurement": "kWh"})):
            hass.states.async_remove(entity)
            hass.states.async_set(entity, value, attrs)
        reopened = Store(hass, 1, "mc_recreated_"+label)
        await reopened.async_save(snapshot)
        restored = MultiChargeRuntime(hass, cfg)
        restored.attach_control_store(reopened, await reopened.async_load())
        assert restored.executor._persistence_verified
        assert not restored.executor.session_snapshot()
        restored.refresh()
        rejected = await restored.executor.execute("drive", "start")
        assert rejected["status"] == "rejected"
        assert rejected["reason"] in ("UNRESOLVED_PREVIOUS_CHARGE_INTENT", "SWITCH_ALREADY_ON")
        await restored.executor.supervise()
        assert hass.states.get("switch.recovery").state == "off"
        assert not restored.executor._inflight
        assert not restored.executor._interrupted_sessions
        receipt = restored.executor.completed_sessions()[-1]
        assert receipt["continuity_quality"] == "unknown"
        assert receipt["actual_energy_kwh"] is None and receipt["duration_minutes"] is None
        again = MultiChargeRuntime(hass, cfg)
        again.attach_control_store(reopened, await Store(hass, 1, "mc_recreated_"+label).async_load())
        again.refresh()
        assert again.executor._persistence_verified
        assert not again.executor.capabilities()["drive"]["start_allowed"]
        assert not again.executor._inflight
    assert commands == ["turn_on", "turn_off", "turn_off"]


@pytest.mark.asyncio
async def test_native_finance_archive_survives_raw_history_absence(hass: HomeAssistant):
    """Real HA long-term statistics, independent of raw history and control Store."""
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from homeassistant.components.recorder import get_instance
    from homeassistant.helpers.recorder import DATA_RECORDER, async_initialize_recorder
    from custom_components.robotix_multicharge.contracts import PriceSlot
    from custom_components.robotix_multicharge.history import daily_costs
    from custom_components.robotix_multicharge.cost_archive import (
        hour_slices, write_archive, read_archive, merge_slices, archive_records,
        decode_archive, owner_map,
    )
    if DATA_RECORDER not in hass.data:
        async_initialize_recorder(hass)
    assert await async_setup_component(hass, "recorder", {
        "recorder": {"db_url": f"sqlite:///{Path(hass.config.config_dir) / 'mc-costs.db'}", "commit_interval": 0},
    })
    recorder = get_instance(hass)
    await recorder.async_recorder_ready.wait()
    await hass.async_block_till_done()
    first = (datetime.now(timezone.utc)-timedelta(days=40)).replace(minute=30, second=0, microsecond=0)
    end = first+timedelta(hours=2)
    cfg = {"chargers": [{"id": "drive"}], "assets": [{"id": "retired_vehicle"}]}
    binding = {"drive": [{"start": None, "entity": "sensor.not_in_recorder"}]}
    receipts = [{"charger_id": "drive", "asset_id": "retired_vehicle",
                 "started_at": first.isoformat(), "ended_at": end.isoformat(),
                 "physical_stop_confirmed": True}]
    states = {"sensor.not_in_recorder": [
        SimpleNamespace(state="3000", last_updated=first+timedelta(minutes=i),
                        attributes={"unit_of_measurement": "W"})
        for i in range(0, 120, 15)]}
    slices = hour_slices(first, end)
    rates = [PriceSlot(first, end, -0.2, "EUR", basis="spot")]
    projections = {key: daily_costs(states, binding, cfg, a, b, rates, receipts)
                   for key, (a, b) in slices.items()}
    write_archive(hass, "original-entry", slices, projections)
    await recorder.async_block_till_done()
    result = await read_archive(hass, "original-entry", {"day": (first, end)}, cfg, binding, [])
    assert result is not None and len(result) == 3
    site = merge_slices(result)["controller"]["site"]
    assert site["observed_energy_kwh"] == pytest.approx(6.0)
    assert site["valuations"][("EUR", "spot")][0] == pytest.approx(-1.2)
    # The original vehicle has disappeared from current config and recent
    # receipts. Native statistic identity/metadata still proves ownership.
    retired = {"chargers": [], "assets": []}
    after_deletion = await read_archive(hass, "original-entry",
                                       {"day": (first, end)}, retired, {}, [])
    old = merge_slices(after_deletion)["asset"]["retired_vehicle"]
    assert old["observed_energy_kwh"] == pytest.approx(6.0)
    assert old["valuations"][("EUR", "spot")][0] == pytest.approx(-1.2)
    assert await read_archive(hass, "other-entry", {"day": (first, end)}, cfg, binding, []) == {}

    # A timezone change can remove a civil-midnight split inside the UTC hour.
    # Native statistics retain both exact halves; reconstruct the full hour
    # without raw telemetry or double counting. The reverse is not inferable.
    whole_start = first.replace(minute=0)+timedelta(hours=1)
    middle = whole_start+timedelta(minutes=30)
    whole_end = whole_start+timedelta(hours=1)
    split = {**hour_slices(whole_start, middle), **hour_slices(middle, whole_end)}
    split_values = {key: daily_costs(states, binding, cfg, a, b, rates, receipts)
                    for key, (a, b) in split.items()}
    write_archive(hass, "split-entry", split, split_values)
    await recorder.async_block_till_done()
    recomposed = await read_archive(hass, "split-entry", {"day": (whole_start, whole_end)},
                                    cfg, binding, [])
    combined = merge_slices(recomposed)["controller"]["site"]
    assert combined["observed_energy_kwh"] == pytest.approx(3.0)
    assert combined["valuations"][("EUR", "spot")][0] == pytest.approx(-0.6)
    assert await read_archive(hass, "split-entry", {"day": (whole_start, whole_end)},
                              cfg, binding, [], allow_recompose=False) == {}
    assert await read_archive(hass, "original-entry", {"day": (whole_start, middle)},
                              cfg, binding, []) == {}
    records = archive_records("original-entry", slices, projections)
    raw = {uid: [{"start": r["start"].timestamp(), "mean": r["mean"]} for r in s["rows"]]
           for uid, s in records.items()}
    del raw[next(uid for uid in raw if uid.endswith("_cost_eur_spot"))]
    assert len(decode_archive("original-entry", slices, raw, owner_map(cfg, binding, []))) < 3

    # Persist original, unacknowledged evidence through a new runtime and
    # the real HA Store. No raw state exists to revalue after restart.
    from homeassistant.helpers.storage import Store
    from custom_components.robotix_multicharge.runtime import MultiChargeRuntime
    full_cfg = validate_configuration({
        "controller": {"id": "site", "name": "Site"},
        "chargers": [{"id": "drive", "name": "Drive", "kind": "on_off",
                      "rated_power_kw": 3, "power_entity": "sensor.not_in_recorder"}],
        "assets": [],
    })
    store = Store(hass, 1, "multicharge_pending_archive_regression")
    pending = MultiChargeRuntime(hass, full_cfg)
    pending.attach_control_store(store, None)
    day = first.date().isoformat()
    pending._archive_pending[day] = {"start": first, "end": end,
                                     "projections": projections}
    assert await pending.persist_control_state()
    restarted = MultiChargeRuntime(hass, full_cfg)
    restarted.statistics_namespace = "pending-entry"
    restarted.attach_control_store(store, await store.async_load())
    assert restarted._archive_pending == pending._archive_pending
    identity = restarted._current_session_cost_identity()
    await restarted._retry_cost_archive({}, full_cfg, [], identity)
    assert day in restarted._archive_pending
    await recorder.async_block_till_done()
    await restarted._retry_cost_archive({}, full_cfg, [], identity)
    assert restarted._archive_pending == {}
    assert (await store.async_load())["pending_cost_archive"] == {}
    recovered = await read_archive(hass, "pending-entry", {day: (first, end)},
                                   full_cfg, binding, [])
    assert merge_slices(recovered)["controller"]["site"]["observed_energy_kwh"] == pytest.approx(6.0)


@pytest.mark.asyncio
async def test_observed_external_session_from_actual_ha_recorder(hass: HomeAssistant):
    """Real HA Recorder database/state events, not a replacement history API."""
    import asyncio
    from datetime import datetime, timedelta, timezone
    from homeassistant.components.recorder import get_instance
    from custom_components.robotix_multicharge.history import read_actual_history

    # HA bootstrap normally initializes this shared recorder helper before loading integrations.
    from homeassistant.helpers.recorder import DATA_RECORDER, async_initialize_recorder
    if DATA_RECORDER not in hass.data:
        async_initialize_recorder(hass)
    assert await async_setup_component(hass, "recorder", {
        "recorder": {"db_url": f"sqlite:///{Path(hass.config.config_dir) / 'mc-history.db'}", "commit_interval": 0},
    })
    recorder = get_instance(hass)
    await recorder.async_recorder_ready.wait()
    await hass.async_block_till_done()
    first = datetime.now(timezone.utc) - timedelta(seconds=1)
    price_start = first - timedelta(minutes=1)
    price_end = first + timedelta(hours=1)
    boundary = datetime.now(timezone.utc) + timedelta(seconds=0.15)
    hass.states.async_set("sensor.reference", "0.2", {
        "kind": "effective_price_kwh", "valid_until": price_end.isoformat(),
        "currency": "EUR", "intervals": [
            {"start": price_start.isoformat(), "end": boundary.isoformat(), "value": 0.2},
            {"start": boundary.isoformat(), "end": price_end.isoformat(), "value": 0.32},
        ],
    })
    attrs = {"device_class": "power", "unit_of_measurement": "W",
             "state_class": "measurement"}
    hass.states.async_set("sensor.external_power", "0", attrs)
    await asyncio.sleep(0.03)
    hass.states.async_set("sensor.external_power", "2000", attrs)
    await asyncio.sleep(0.20)
    hass.states.async_set("sensor.external_power", "4000", attrs)
    await asyncio.sleep(0.06)
    hass.states.async_set("sensor.external_power", "0", attrs)
    await hass.async_block_till_done()
    # The native async_block_till_done fast path can see an empty queue
    # while its final state is being inserted (CI SQL trace showed SELECT
    # before COMMIT). Explicitly queue the native commit barrier in this
    # installed-HA fixture, not a retry or sleep in production history.
    from homeassistant.components.recorder.tasks import SynchronizeTask
    committed = hass.loop.create_future()
    recorder.queue_task(SynchronizeTask(committed))
    await asyncio.wait_for(committed, timeout=10)
    end = datetime.now(timezone.utc)
    configuration = {"chargers": [{"id": "outside", "power_entity": "sensor.external_power",
                                    "control_owner": "external"}]}
    _, _, _, runs, _ = await read_actual_history(
        hass, configuration, first, end, include_valuations=True,
        include_observed_sessions=True, tariff_entity="sensor.reference",
    )
    assert len(runs) == 1, runs
    run = runs[0]
    assert run["asset_id"] is None
    assert run["complete_observed_window"] and run["end_known"] and not run["ongoing"], run
    assert run["observed_energy_kwh"] > 0
    assert 2 <= run["average_power_kw"] <= 4
    assert run["peak_power_kw"] == 4
    assert run["estimated_cost_basis"] == "effective"
    assert run["estimated_cost_currency"] == "EUR"
    assert run["estimated_cost"] > 0
    assert 0.19 <= run["estimated_cost"]/run["observed_energy_kwh"] <= 0.33
