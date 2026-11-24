"""Real executor source tests against recording HA state/service contract.

These execute the actual production NativeSwitchExecutor, including its
async_call and fresh power-readback path; no simulated production actuator.
Target HA installation and hardware acceptance are separate requirements.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

PKG = Path(__file__).resolve().parents[1] / "custom_components" / "robotix_multicharge"
ROOT = "multicharge_physical_execution_test"
package = type(sys)(ROOT)
package.__path__ = [str(PKG)]
sys.modules[ROOT] = package
for name in ("domain", "contracts", "configuration", "planner",
             "source_evidence", "execution", "runtime"):
    spec = importlib.util.spec_from_file_location(f"{ROOT}.{name}", PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from multicharge_physical_execution_test.configuration import validate_configuration  # noqa: E402
from multicharge_physical_execution_test.runtime import MultiChargeRuntime  # noqa: E402


def state(value, unit=None):
    return SimpleNamespace(
        state=str(value),
        attributes={"unit_of_measurement": unit} if unit is not None else {},
        last_updated=datetime.now(timezone.utc) - timedelta(seconds=1),
        last_changed=datetime.now(timezone.utc) - timedelta(seconds=1),
    )


class NativeServices:
    """Recording HA service boundary with independent observed physical states."""

    def __init__(self, sources):
        self.sources = sources
        self.calls = []
        self.fail = False
        self.reconcile_observations = True

    async def async_call(self, domain, service, data, *, blocking, context):
        self.calls.append((domain, service, dict(data), blocking, context))
        if self.fail:
            raise RuntimeError("Native HA service failed")
        if self.reconcile_observations and domain == "number":
            entity = data["entity_id"]
            self.sources[entity].state = str(data["value"])
            self.sources[entity].last_updated = datetime.now(timezone.utc)
            if "sensor.actual_current" in self.sources:
                self.sources["sensor.actual_current"].state = str(data["value"])
                self.sources["sensor.actual_current"].last_updated = datetime.now(timezone.utc)
                self.sources["sensor.actual_power"].state = str(
                    round(float(data["value"]) * 230)
                )
                self.sources["sensor.actual_power"].last_updated = datetime.now(timezone.utc)
            elif ("sensor.actual_power" in self.sources and
                  self.sources["switch.evse_control"].state == "on"):
                # Fixture models separately reported measured power from a
                # device with native limit control but no independent amp sensor.
                self.sources["sensor.actual_power"].state = str(round(float(data["value"]) * 230))
                self.sources["sensor.actual_power"].last_updated = datetime.now(timezone.utc)
            return
        if self.reconcile_observations:
            entity = data["entity_id"]
            self.sources[entity].state = "on" if service == "turn_on" else "off"
            self.sources[entity].last_updated = datetime.now(timezone.utc)
            self.sources["sensor.actual_power"].state = (
                str(round(float(self.sources["sensor.actual_current"].state) * 230))
                if service == "turn_on" and "sensor.actual_current" in self.sources
                else "1600" if service == "turn_on" else "0"
            )
            self.sources["sensor.actual_power"].last_updated = datetime.now(timezone.utc)


def rig(*, owner="multicharge", commissioned=True, group_kw=4.0,
        mode="Force Charge"):
    cfg = {
        "controller": {"id": "site", "name": "Site", "max_parallel": 1,
                       "max_power_kw": group_kw, "mode": mode},
        "assets": [{"id": "car", "name": "Car", "kind": "car",
                    "requested_kwh": 1.0}],
        "chargers": [{"id": "evse", "name": "EVSE", "kind": "on_off",
                      "rated_power_kw": 2.0, "phase_count": 1, "asset": "car",
                      "control_entity": "switch.evse_control",
                      "power_entity": "sensor.actual_power",
                      "energy_entity": "sensor.meter",
                      "connected_entity": "binary_sensor.cable",
                      "control_owner": owner,
                      "physical_commissioned": commissioned}],
    }
    cfg = validate_configuration(cfg)
    sources = {
        "switch.evse_control": state("off"),
        "sensor.actual_power": state(0, "W"),
        "sensor.meter": state(5, "kWh"),
        "binary_sensor.cable": state("on"),
    }
    services = NativeServices(sources)
    hass = SimpleNamespace(
        states=SimpleNamespace(get=sources.get),
        services=services,
        config=SimpleNamespace(time_zone="Europe/Brussels"),
    )
    runtime = MultiChargeRuntime(hass, cfg)
    assert runtime.executor.confirm_current_connection("evse")["status"] == "confirmed"
    runtime.refresh()
    return runtime, sources, services


class PhysicalNativeExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_energy_dashboard_power_sources_monitor_and_bound_solar(self):
        """HA W/kW native PV, home, grid and prices need no Robotix templates."""
        rt, sources, calls = rig(mode="Solar")
        ctl = rt.configuration["controller"]
        ctl.update(
            solar_source_kind="grid_export",
            grid_power_direction="import_positive",
            solar_power_entity="sensor.pv_live",
            home_power_entity="sensor.house_live",
            grid_power_entity="sensor.meter_live",
            current_price_entity="sensor.price_now",
        )
        sources.update({
            "sensor.pv_live": state("3000", "W"),
            "sensor.house_live": state("1200", "W"),
            "sensor.meter_live": state("-1600", "W"),
            "sensor.price_now": state("-0.08", "EUR/kWh"),
        })
        now = datetime.now(timezone.utc)
        available, quality = rt.native_surplus_power(now)
        self.assertEqual(quality, "OK")
        self.assertAlmostEqual(available, 1.6)
        rt.refresh(now)
        metrics = rt.observations["sources"]
        self.assertEqual(metrics["solar_power"]["value"], 3)
        self.assertEqual(metrics["home_power"]["value"], 1.2)
        self.assertEqual(metrics["grid_power"]["value"], -1.6)
        self.assertEqual(metrics["current_price"]["basis"], "current_only")
        self.assertEqual(metrics["current_price"]["currency"], "EUR")
        self.assertNotEqual(metrics["tariff_quality"], "OK")
        self.assertEqual(rt.executor._physical_budget(
            rt.configuration["chargers"][0], now, 2.0, None,
        ), "NATIVE_SOLAR_SURPLUS_INSUFFICIENT")
        sources["sensor.meter_live"].state = "-2500"
        sources["sensor.meter_live"].last_updated = datetime.now(timezone.utc)
        self.assertEqual(rt.executor._physical_budget(
            rt.configuration["chargers"][0],
            datetime.now(timezone.utc), 2.0, None,
        ), None)
        ctl["grid_power_direction"] = "export_positive"
        sources["sensor.meter_live"].state = "2500"
        self.assertEqual(rt.native_surplus_power(
            datetime.now(timezone.utc))[0], 2.5)
        sources["sensor.meter_live"].state = "unavailable"
        self.assertIsNone(rt.native_surplus_power(
            datetime.now(timezone.utc))[0])
        self.assertEqual(rt.executor._physical_budget(
            rt.configuration["chargers"][0],
            datetime.now(timezone.utc), 2.0, None,
        ), "NATIVE_SOLAR_SOURCE_UNQUALIFIED")
        self.assertEqual(calls.calls, [])

    async def test_owned_sessions_added_back_only_once_to_live_grid_surplus(self):
        rt, sources, services = rig()
        ctl = rt.configuration["controller"]
        ctl["solar_source_kind"] = "grid_export"
        ctl["grid_power_direction"] = "import_positive"
        ctl["grid_power_entity"] = "sensor.grid_meter"
        sources["sensor.grid_meter"] = state("-500", "W")
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        # The charger is delivering 1.6kW and grid currently exports 0.5kW.
        # Solar budget for this ONE already-owned session is 2.1kW, not 0.5.
        source = rt.configuration["chargers"][0]
        self.assertEqual(source["control_owner"], "multicharge")
        value, quality = rt.native_surplus_power(datetime.now(timezone.utc))
        self.assertEqual(quality, "OK")
        self.assertAlmostEqual(value, 2.1)
        sources["sensor.grid_meter"].state = "0"
        sources["sensor.grid_meter"].last_updated = datetime.now(timezone.utc)
        self.assertAlmostEqual(rt.native_surplus_power(
            datetime.now(timezone.utc))[0], 1.6)
        # A stale owned meter cannot be added back or treated as free kW.
        sources["sensor.actual_power"].last_updated = (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        result, reason = rt.native_surplus_power(datetime.now(timezone.utc))
        self.assertIsNone(result)
        self.assertEqual(reason, "OWNED_CHARGER_POWER_UNKNOWN")

    async def test_native_spot_price_cannot_be_billed_as_effective_session_cost(self):
        """Source-neutral Economy quotes are NOT all-in monetary evidence."""
        from multicharge_physical_execution_test.contracts import PriceSlot

        runtime, sources, services = rig()
        started = await runtime.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        sources["sensor.meter"].state = "5.5"
        sources["sensor.meter"].last_updated = datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)
        runtime.price_slots = (PriceSlot(
            now - timedelta(hours=1), now + timedelta(hours=1),
            -0.04, "EUR", basis="spot",
        ),)
        runtime.observations["sources"]["tariff_quality"] = "OK"
        finished = await runtime.executor.execute("evse", "stop")
        self.assertEqual(finished["status"], "confirmed")
        result = runtime.executor.completed_sessions()[-1]
        self.assertAlmostEqual(result["actual_energy_kwh"], 0.5)
        self.assertIsNone(result["cost"])
        self.assertIsNone(result["currency"])
        self.assertEqual(result["cost_quality"], "unknown")
        self.assertTrue(result["physical_stop_confirmed"])

    async def test_direct_native_evse_enum_connected_status_controls_real_executor(self):
        """No site template: the guarded sole executor reads native raw status."""
        runtime, sources, services = rig()
        charger = runtime.configuration["chargers"][0]
        charger["connected_entity"] = "sensor.native_charger_state"
        charger["connected_states"] = ["charging", "preparing"]
        charger["disconnected_states"] = ["available"]
        sources["sensor.native_charger_state"] = state("Charging")
        runtime.executor._plug_confirmations.clear()
        self.assertEqual(
            runtime.executor.confirm_current_connection("evse")["status"],
            "confirmed",
        )
        runtime.refresh()
        self.assertEqual(
            (await runtime.executor.execute("evse", "start"))["status"],
            "confirmed",
        )
        self.assertEqual(
            (await runtime.executor.execute("evse", "stop"))["status"],
            "confirmed",
        )
        before = len(services.calls)
        sources["sensor.native_charger_state"].state = "Available"
        sources["sensor.native_charger_state"].last_updated = datetime.now(timezone.utc)
        sources["sensor.native_charger_state"].last_changed = datetime.now(timezone.utc)
        runtime.refresh()
        rejected = await runtime.executor.execute("evse", "start")
        self.assertEqual(rejected["reason"], "PHYSICAL_CONNECTION_UNVERIFIED")
        self.assertEqual(len(services.calls), before)

    async def test_current_plug_confirmation_survives_witnessed_substate_not_replug(self):
        """Only an ordered HA positive->positive event can retain the same plug."""
        runtime, sources, services = rig()
        charger = runtime.configuration["chargers"][0]
        charger["connected_entity"] = "sensor.native_charger_state"
        charger["connected_states"] = ["preparing", "charging"]
        charger["disconnected_states"] = ["available"]
        original = state("Preparing")
        sources["sensor.native_charger_state"] = original
        runtime.refresh()
        record = runtime.executor.confirm_current_connection("evse")
        self.assertEqual(record["status"], "confirmed")
        first_epoch = record["connected_at"]

        charging = state("Charging")
        sources["sensor.native_charger_state"] = charging
        # Same plug: genuine HA event carries both the previous and new
        # qualified physical states, even when scheduled refresh is delayed.
        runtime.executor.observe_connection_event(charger, original, charging)
        runtime.refresh()
        kept = runtime.executor.connection_confirmation(
            charger, datetime.now(timezone.utc)
        )
        self.assertIsNotNone(kept)
        self.assertEqual(kept["connected_at"], first_epoch)

        # Two physical transitions can happen before the next refresh.
        available = state("Available")
        preparing_again = state("Preparing")
        sources["sensor.native_charger_state"] = preparing_again
        runtime.executor.observe_connection_event(charger, charging, available)
        runtime.executor.observe_connection_event(charger, available, preparing_again)
        runtime.refresh()
        self.assertIsNone(runtime.executor.connection_confirmation(
            charger, datetime.now(timezone.utc)
        ), "Brief disconnected state invalidates previous vehicle identity")
        self.assertEqual(services.calls, [])

    async def test_unwitnessed_native_substate_jump_never_retains_vehicle_identity(self):
        """A raw snapshot change alone cannot prove no unplug occurred."""
        runtime, sources, services = rig()
        charger = runtime.configuration["chargers"][0]
        charger["connected_entity"] = "sensor.native_charger_state"
        charger["connected_states"] = ["preparing", "charging"]
        charger["disconnected_states"] = ["available"]
        sources["sensor.native_charger_state"] = state("Preparing")
        runtime.refresh()
        self.assertEqual(
            runtime.executor.confirm_current_connection("evse")["status"],
            "confirmed",
        )
        sources["sensor.native_charger_state"] = state("Charging")
        # No on_source_change event was witnessed: fail closed.
        runtime.refresh()
        self.assertIsNone(runtime.executor.connection_confirmation(
            charger, datetime.now(timezone.utc)
        ))
        self.assertFalse(runtime.assessment.plan.slots)
        self.assertEqual(services.calls, [])

    async def test_native_same_status_refresh_vs_provider_recreation(self):
        """Same raw label is continuous only when HA preserves last_changed."""
        runtime, sources, services = rig()
        charger = runtime.configuration["chargers"][0]
        charger["connected_entity"] = "sensor.native_status"
        charger["connected_states"] = ["charging", "preparing"]
        charger["disconnected_states"] = ["available"]
        original = state("Charging")
        original.last_changed = datetime.now(timezone.utc) - timedelta(seconds=4)
        sources["sensor.native_status"] = original
        runtime.refresh()
        first = runtime.executor.confirm_current_connection("evse")
        self.assertEqual(first["status"], "confirmed")

        # Ordinary attribute-only refresh keeps last_changed and may retain
        # the explicitly identified current plug; it creates no new session.
        reported = state("Charging")
        reported.last_changed = original.last_changed
        reported.last_updated = datetime.now(timezone.utc)
        sources["sensor.native_status"] = reported
        runtime.executor.observe_connection_event(charger, original, reported)
        runtime.refresh()
        self.assertIsNotNone(runtime.executor.connection_confirmation(
            charger, datetime.now(timezone.utc)
        ))

        # Recreated provider state with the same raw label but a NEW native
        # last_changed cannot prove uninterrupted physical connector identity.
        restarted = state("Charging")
        restarted.last_changed = original.last_changed + timedelta(seconds=2)
        restarted.last_updated = datetime.now(timezone.utc)
        sources["sensor.native_status"] = restarted
        runtime.executor.observe_connection_event(charger, reported, restarted)
        runtime.refresh()
        self.assertIsNone(runtime.executor.connection_confirmation(
            charger, datetime.now(timezone.utc)
        ))
        self.assertEqual(services.calls, [])

    async def test_manual_force_start_is_durably_held_across_restart(self):
        rt, states, services = rig()
        class MemoryStore:
            def __init__(self):
                self.data = None
            async def async_save(self, payload):
                self.data = payload

        store = MemoryStore()
        rt.attach_control_store(store, None)
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        self.assertIn("car", store.data["inflight"])
        restarted = MultiChargeRuntime(rt.hass, rt.configuration)
        restarted.attach_control_store(store, store.data)
        self.assertIn("car", restarted.executor._inflight)
        # A restart cannot reuse previous connection identity as evidence.
        self.assertEqual(
            restarted.executor.confirm_current_connection("evse")["status"],
            "confirmed",
        )
        before = len(services.calls)
        states["switch.evse_control"].state = "off"
        states["sensor.actual_power"].state = "0"
        states["sensor.actual_power"].last_updated = datetime.now(timezone.utc)
        blocked = await restarted.executor.execute("evse", "start")
        self.assertEqual(blocked["reason"], "UNRESOLVED_PREVIOUS_CHARGE_INTENT")
        self.assertEqual(len(services.calls), before)

    async def test_manual_force_start_fails_closed_when_intent_persistence_fails(self):
        rt, sources, services = rig()
        class RejectingStore:
            async def async_save(self, payload):
                raise OSError("storage unavailable")
        rt.attach_control_store(RejectingStore(), None)
        result = await rt.executor.execute("evse", "start")
        self.assertEqual(result["reason"], "MANUAL_INTENT_NOT_PERSISTED")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(services.calls, [])
        self.assertFalse(rt.executor._persistence_verified)

    async def test_charger_only_manual_intent_is_durable_until_measured_stop(self):
        rt, sources, services = rig()
        rt.configuration["chargers"][0].pop("asset")
        rt.refresh()
        before = rt.executor.export_state()["inflight"]
        self.assertEqual(before, {})
        started = await rt.executor.execute(
            "evse", "start", manual_request={"energy_kwh": 2.0}
        )
        self.assertEqual(started["status"], "confirmed")
        key = "charger:evse"
        self.assertIn(key, rt.executor.export_state()["inflight"])
        restored = MultiChargeRuntime(rt.hass, rt.configuration)
        restored.executor.restore_state(rt.executor.export_state())
        self.assertIn(key, restored.executor._inflight)
        sources["sensor.meter"].state = "6"
        sources["sensor.meter"].last_updated = datetime.now(timezone.utc)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"],
                         "confirmed")
        self.assertNotIn(key, rt.executor.export_state()["inflight"])
        self.assertEqual(rt.executor.completed_sessions()[-1]["actual_energy_kwh"],
                         1.0)

    async def test_pause_persists_hold_and_resume_never_starts_hardware(self):
        rt, sources, services = rig()
        outcome = await rt.executor.execute("evse", "pause")
        self.assertEqual(outcome["status"], "confirmed")
        self.assertTrue(rt.executor.capabilities()["evse"]["paused"])
        self.assertEqual(
            (await rt.executor.execute("evse", "start"))["reason"],
            "USER_PAUSED",
        )
        stored = rt.executor.export_state()
        self.assertEqual(stored["paused"], ["evse"])
        other, other_sources, other_services = rig()
        other.executor.restore_state(stored)
        self.assertTrue(other.executor.capabilities()["evse"]["paused"])
        self.assertEqual(other.executor.capabilities()["evse"]["start_allowed"], False)
        self.assertEqual(other_services.calls, [])
        resumed = await other.executor.execute("evse", "resume")
        self.assertEqual(resumed["status"], "confirmed")
        self.assertEqual(resumed["reason"], "PAUSE_RELEASED_NO_PHYSICAL_START")
        self.assertEqual(other_services.calls, [], "Resume must never energize")
        self.assertEqual(other.executor.export_state()["paused"], [])
        self.assertEqual(
            (await other.executor.execute("evse", "start"))["status"],
            "confirmed",
        )

    async def test_pause_physically_stops_and_preserves_measured_remaining_need(self):
        rt, sources, services = rig()
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        sources["sensor.meter"].state = "5.4"
        sources["sensor.meter"].last_updated = datetime.now(timezone.utc)
        paused = await rt.executor.execute("evse", "pause")
        self.assertEqual(paused["status"], "confirmed")
        self.assertEqual(sources["switch.evse_control"].state, "off")
        self.assertEqual(rt.executor.completed_sessions()[-1]["actual_energy_kwh"], 0.4)
        self.assertEqual(rt.executor.measured_intent_usage(
            rt.configuration["assets"][0], rt.configuration["chargers"][0],
            None)["energy_kwh"], 0.4)
        self.assertEqual((await rt.executor.execute("evse", "resume"))["status"],
                         "confirmed")
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        self.assertAlmostEqual(
            rt.executor.session_snapshot()["evse"]["requested_kwh"], 0.6
        )

    async def test_failed_pause_stop_keeps_durable_hold_and_blocks_resume(self):
        rt, sources, services = rig()
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        services.fail = True
        unknown = await rt.executor.execute("evse", "pause")
        self.assertEqual(unknown["status"], "execution_unknown")
        self.assertEqual(rt.executor.export_state()["paused"], ["evse"])
        self.assertEqual(
            (await rt.executor.execute("evse", "resume"))["reason"],
            "UNCONFIRMED_SESSION_CANNOT_RESUME",
        )
        before = len(services.calls)
        self.assertEqual(
            (await rt.executor.execute("evse", "start"))["status"], "rejected"
        )
        self.assertEqual(len(services.calls), before)

    async def test_pause_does_not_confirm_while_power_remains_high(self):
        """Switch OFF alone is never physical Pause / STOP readback."""
        rt, sources, services = rig()
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        self.assertEqual(sources["switch.evse_control"].state, "on")

        async def switch_off_but_power_stays(domain, service, data, *,
                                            blocking, context):
            services.calls.append((domain, service, dict(data), blocking, context))
            self.assertEqual((domain, service), ("switch", "turn_off"))
            source = sources["switch.evse_control"]
            source.state = "off"
            source.last_updated = datetime.now(timezone.utc)
            # Independent physical meter still indicates an energized EVSE.
            power = sources["sensor.actual_power"]
            power.state = "1600"
            power.last_updated = datetime.now(timezone.utc)

        services.async_call = switch_off_but_power_stays
        paused = await rt.executor.execute(
            "evse", "pause", readback_seconds=0.05
        )
        self.assertEqual(paused["status"], "execution_unknown")
        self.assertIn("PHYSICAL_READBACK_TIMEOUT", paused["reason"])
        self.assertEqual(rt.executor.export_state()["paused"], ["evse"])
        self.assertIn("evse", rt.executor._quarantine)
        self.assertEqual(
            (await rt.executor.execute("evse", "resume"))["status"], "rejected"
        )
        self.assertTrue(
            any(action == "turn_off" for _, action, *_ in services.calls)
        )

    async def test_confirmed_stop_reconciles_inflight_only_when_energy_measured(self):
        rt, sources, services = rig()
        charger = rt.configuration["chargers"][0]
        asset = rt.configuration["assets"][0]
        key = rt.executor._intent_key(asset, charger, None)
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        rt.executor._inflight[asset["id"]] = key
        sources["sensor.meter"].state = "5.2"
        sources["sensor.meter"].last_updated = datetime.now(timezone.utc)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"],
                         "confirmed")
        self.assertNotIn(asset["id"], rt.executor._inflight)
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        rt.executor._inflight[asset["id"]] = key
        sources["sensor.meter"].state = "unknown"
        sources["sensor.meter"].last_updated = datetime.now(timezone.utc)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"],
                         "confirmed")
        self.assertIn(asset["id"], rt.executor._inflight,
                      "Unmeasured energy must not permit automatic replay")

    async def test_verified_vehicle_energy_follows_asset_not_charger(self):
        rt, states, services = rig()
        asset = rt.configuration["assets"][0]
        asset["requested_kwh"] = 2.0
        charger = rt.configuration["chargers"][0]
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        states["sensor.meter"].state = "5.8"
        states["sensor.meter"].last_updated = datetime.now(timezone.utc)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"],
                         "confirmed")
        receipt = rt.executor.completed_sessions()[0]
        self.assertEqual(receipt["actual_energy_kwh"], 0.8)
        another = {**charger, "id": "replacement"}
        self.assertEqual(rt.executor._intent_key(asset, charger, None),
                         rt.executor._intent_key(asset, another, None))
        self.assertEqual(rt.executor.measured_intent_usage(
            asset, another, None)["energy_kwh"], 0.8)
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        self.assertAlmostEqual(
            rt.executor.session_snapshot()["evse"]["requested_kwh"], 1.2
        )

    async def test_unknown_prior_measured_energy_blocks_incorrect_replay(self):
        rt, states, services = rig()
        rt.configuration["assets"][0]["requested_kwh"] = 2.0
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        states["sensor.meter"].state = "unavailable"
        states["sensor.meter"].last_updated = datetime.now(timezone.utc)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"],
                         "confirmed")
        states["sensor.meter"].state = "6.2"
        states["sensor.meter"].last_updated = datetime.now(timezone.utc)
        reject = await rt.executor.execute("evse", "start")
        self.assertEqual(reject["reason"], "ASSET_MEASURED_PROGRESS_UNAVAILABLE")
        self.assertEqual([x[1] for x in services.calls], ["turn_on", "turn_off"])

    async def test_charger_only_measured_kwh_stops_and_keeps_asset_unattributed(self):
        rt, sources, services = rig()
        rt.configuration["chargers"][0].pop("asset")
        rt.refresh()
        self.assertTrue(rt.executor.capabilities()["evse"]["manual_one_off_allowed"])
        result = await rt.executor.execute(
            "evse", "start", manual_request={"energy_kwh": 2.0}
        )
        self.assertEqual(result["status"], "confirmed")
        self.assertIsNone(rt.executor.session_snapshot()["evse"]["asset_id"])
        sources["sensor.meter"].state = "7"
        sources["sensor.meter"].last_updated = datetime.now(timezone.utc)
        await rt.executor.supervise()
        self.assertEqual([x[1] for x in services.calls], ["turn_on", "turn_off"])
        completed = rt.executor.completed_sessions()
        self.assertEqual(len(completed), 1)
        self.assertIsNone(completed[0]["asset_id"])
        self.assertEqual(completed[0]["actual_energy_kwh"], 2.0)
        self.assertTrue(completed[0]["physical_stop_confirmed"])
        saved = rt.executor.export_state()
        rt2, _, _ = rig()
        rt2.executor.restore_state(saved)
        self.assertIsNone(rt2.executor.completed_sessions()[0]["asset_id"])

    async def test_charger_only_duration_without_meter_is_real_and_finite(self):
        rt, sources, services = rig()
        rt.configuration["chargers"][0].pop("asset")
        rt.configuration["chargers"][0].pop("energy_entity")
        rt.refresh()
        result = await rt.executor.execute(
            "evse", "start", manual_request={"duration_minutes": 30}
        )
        self.assertEqual(result["status"], "confirmed")
        rt.executor._sessions["evse"]["started_at"] -= timedelta(minutes=31)
        await rt.executor.supervise()
        self.assertEqual([x[1] for x in services.calls], ["turn_on", "turn_off"])
        receipt = rt.executor.completed_sessions()[0]
        self.assertIsNone(receipt["asset_id"])
        self.assertIsNone(receipt["actual_energy_kwh"])
        self.assertEqual(receipt["energy_quality"], "unknown")

    async def test_assigned_guest_duration_without_optional_connection_or_meter(self):
        rt, sources, services = rig()
        charger = rt.configuration["chargers"][0]
        asset = rt.configuration["assets"][0]
        asset.pop("requested_kwh")
        asset["requested_duration_minutes"] = 20
        for field in ("connected_entity", "power_entity", "energy_entity"):
            charger.pop(field, None)
        rt.refresh()
        outcome = await rt.executor.execute("evse", "start")
        self.assertEqual(outcome["status"], "confirmed")
        self.assertEqual(rt.charger_states()["evse"]["connection_state"], "unknown")
        self.assertEqual(rt.charger_states()["evse"]["charging_session"], "unknown")
        await rt.executor.supervise()
        self.assertEqual(sources["switch.evse_control"].state, "on")
        rt.executor._sessions["evse"]["started_at"] -= timedelta(minutes=21)
        await rt.executor.supervise()
        self.assertEqual(sources["switch.evse_control"].state, "off")
        self.assertEqual([c[1] for c in services.calls], ["turn_on", "turn_off"])
        self.assertIsNone(rt.executor.completed_sessions()[-1]["actual_energy_kwh"])
        self.assertGreaterEqual(rt.executor.measured_intent_usage(asset, charger, None)["duration_minutes"], 20)
        self.assertEqual((await rt.executor.execute("evse", "start"))["reason"], "TARGET_ALREADY_MET")

    async def test_guest_switch_only_automatic_bounded_duration_and_truthful_receipt(self):
        rt, sources, services = rig(mode="Automatic")
        charger = rt.configuration["chargers"][0]
        for field in ("asset", "phase_count", "power_entity", "energy_entity", "connected_entity"):
            charger.pop(field, None)
        rt.configuration["controller"].pop("max_power_kw")
        rt.refresh()
        first = await rt.executor.execute("evse", "start", manual_request={"duration_minutes": 30})
        self.assertEqual(first["status"], "confirmed")
        self.assertEqual(first["reason"], "NATIVE_SWITCH_STATE")
        self.assertIsNone(first["measured_power_kw"])
        self.assertIsNone(rt.live_state()["actual_power_kw"])
        states = rt.charger_states()["evse"]
        self.assertEqual(states["activation"], "active")
        self.assertEqual(states["connection_state"], "unknown")
        self.assertEqual(states["charging_session"], "unknown")
        self.assertEqual(states["switch_state"], "on")
        self.assertTrue(rt.executor.session_snapshot()["evse"]["switch_only"])
        await rt.executor.supervise()
        self.assertEqual([c[1] for c in services.calls], ["turn_on"])
        rt.executor._sessions["evse"]["started_at"] -= timedelta(minutes=31)
        await rt.executor.supervise()
        self.assertEqual([c[1] for c in services.calls], ["turn_on", "turn_off"])
        receipt = rt.executor.completed_sessions()[0]
        self.assertFalse(receipt["physical_stop_confirmed"])
        self.assertTrue(receipt["switch_stop_confirmed"])
        self.assertIsNone(receipt["actual_energy_kwh"])
        self.assertFalse(rt.executor._inflight)
        self.assertFalse(rt.executor._sessions)
        self.assertEqual(sources["switch.evse_control"].state, "off")

    async def test_switch_only_restart_reconciles_without_replaying_start(self):
        rt, sources, services = rig(mode="Automatic")
        charger = rt.configuration["chargers"][0]
        for field in ("asset", "power_entity", "energy_entity", "connected_entity"):
            charger.pop(field, None)
        rt.refresh()
        started = await rt.executor.execute("evse", "start", manual_request={"duration_minutes": 30})
        self.assertEqual(started["status"], "confirmed")
        persisted = rt.executor.export_state()
        restored = MultiChargeRuntime(rt.hass, rt.configuration)
        restored.executor.restore_state(persisted)
        restored.refresh()
        await restored.executor.supervise()
        self.assertEqual(sources["switch.evse_control"].state, "off")
        self.assertEqual([c[1] for c in services.calls], ["turn_on", "turn_off"])
        self.assertFalse(restored.executor._inflight)
        self.assertFalse(restored.executor._sessions)

    async def test_optional_energy_meter_loss_does_not_stop_duration(self):
        rt, sources, services = rig()
        rt.configuration["chargers"][0].pop("asset")
        started = await rt.executor.execute(
            "evse", "start", manual_request={"duration_minutes": 30}
        )
        self.assertEqual(started["status"], "confirmed")
        sources["sensor.meter"].state = "unavailable"
        await rt.executor.supervise()
        self.assertEqual([call[1] for call in services.calls], ["turn_on"])
        self.assertIsNone(rt.executor.session_snapshot()["evse"]["actual_energy_kwh"])
        rt.executor._sessions["evse"]["started_at"] -= timedelta(minutes=31)
        await rt.executor.supervise()
        self.assertEqual([call[1] for call in services.calls], ["turn_on", "turn_off"])
        self.assertIsNone(rt.executor.completed_sessions()[0]["actual_energy_kwh"])

    async def test_external_adjustable_kw_only_does_not_require_amp_readback(self):
        rt, sources, services = rig(group_kw=5)
        rt.configuration["controller"]["max_parallel"] = 2
        rt.configuration["chargers"].append({
            "id": "other", "name": "External EVSE",
            "kind": "variable_current", "rated_power_kw": 2,
            "power_entity": "sensor.other_power",
            "control_owner": "external", "physical_commissioned": False,
        })
        sources["sensor.other_power"] = state(1500, "W")
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        self.assertEqual([call[1] for call in services.calls], ["turn_on"])
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"],
                         "confirmed")
        # A configured aggregate phase limit genuinely needs amp evidence.
        rt.configuration["controller"]["phase_limits_a"] = {"L1": 32}
        self.assertEqual(rt.executor._physical_budget(
            rt.configuration["chargers"][0], datetime.now(timezone.utc), 2, 10
        ), "OTHER_CHARGER_CURRENT_UNAVAILABLE")

    async def test_charger_only_rejects_unbounded_invalid_or_assigned_requests(self):
        rt, _, services = rig()
        refused = await rt.executor.execute(
            "evse", "start", manual_request={"duration_minutes": 30}
        )
        self.assertEqual(refused["reason"], "MANUAL_ONE_OFF_REQUIRES_UNASSIGNED_CHARGER")
        rt.configuration["chargers"][0].pop("asset")
        for intent in ({}, {"duration_minutes": 0},
                       {"energy_kwh": 0}, {"duration_minutes": 1441},
                       {"energy_kwh": 2, "duration_minutes": 30}):
            refused = await rt.executor.execute(
                "evse", "start", manual_request=intent,
            )
            self.assertEqual(refused["status"], "rejected")
        self.assertFalse(services.calls)

    async def test_low_power_bicycle_uses_relative_physical_start_stop_thresholds(self):
        rt, source, services = rig(group_kw=0.5)
        charger = rt.configuration["chargers"][0]
        charger["rated_power_kw"] = 0.08
        charger["kind"] = "on_off"
        original = services.async_call

        async def measured_small_charge(domain, action, args, *, blocking, context):
            await original(domain, action, args, blocking=blocking, context=context)
            if domain == "switch" and action == "turn_on":
                source["sensor.actual_power"].state = "65"
                source["sensor.actual_power"].last_updated = datetime.now(timezone.utc)

        services.async_call = measured_small_charge
        rt.refresh()
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        self.assertAlmostEqual(started["measured_power_kw"], 0.065)
        # A residual 30W is meaningful for an 80W bike charger, not STOP.
        source["switch.evse_control"].state = "off"
        source["sensor.actual_power"].state = "30"
        source["sensor.actual_power"].last_updated = datetime.now(timezone.utc)
        self.assertIsNone(rt.executor._readback(
            charger, "stop", datetime.now(timezone.utc) - timedelta(seconds=1)
        ))
        stopped = await rt.executor.execute("evse", "stop")
        self.assertEqual(stopped["status"], "confirmed")
        self.assertAlmostEqual(stopped["measured_power_kw"], 0)

    async def test_unconfirmed_or_replugged_vehicle_cannot_start(self):
        rt, states, services = rig()
        rt.executor._plug_confirmations.clear()
        rt.refresh()
        self.assertFalse(rt.assessment.plan.slots)
        denied = await rt.executor.execute("evse", "start")
        self.assertEqual(denied["reason"], "CURRENT_PLUG_ASSET_UNCONFIRMED")
        self.assertEqual(services.calls, [])
        confirmed = rt.executor.confirm_current_connection("evse")
        self.assertEqual(confirmed["status"], "confirmed")
        self.assertTrue(rt.executor.connection_confirmation(
            rt.configuration["chargers"][0], datetime.now(timezone.utc)
        ))
        states["binary_sensor.cable"].last_changed = datetime.now(timezone.utc)
        rt.refresh()
        self.assertFalse(rt.assessment.plan.slots)
        self.assertIsNone(rt.executor.connection_confirmation(
            rt.configuration["chargers"][0], datetime.now(timezone.utc)
        ))


    async def test_indicative_unplugged_vehicle_never_reaches_physical_writer(self):
        rt, states, services = rig(mode="Automatic")
        states["binary_sensor.cable"].state = "off"
        at = datetime.now(timezone.utc)
        quarter = at.replace(minute=(at.minute // 15) * 15,
                             second=0, microsecond=0)
        for sample in states.values():
            sample.last_updated = quarter + timedelta(seconds=1)
        rt.refresh(quarter)
        self.assertFalse(rt.assessment.plan.slots)
        self.assertTrue(rt.forecast_assessment.plan.slots)
        await rt.executor.advance_plan(quarter)
        self.assertEqual(services.calls, [])
        self.assertFalse(rt.executor.accepted_slots())
        self.assertEqual(rt.executor.session_snapshot(), {})

    async def test_automatic_quarter_applies_only_physically_confirmed_plan(self):
        rt, states, services = rig(mode="Automatic")
        at = datetime.now(timezone.utc)
        quarter = at.replace(minute=(at.minute // 15) * 15, second=0, microsecond=0)
        for source in states.values():
            source.last_updated = quarter + timedelta(seconds=1)
        rt.refresh(quarter)
        self.assertTrue(rt.assessment.plan.slots)
        await rt.executor.advance_plan(quarter)
        self.assertEqual([x[1] for x in services.calls], ["turn_on"])
        accepted = rt.executor.accepted_slots()
        self.assertEqual(len(accepted), 1)
        self.assertIsNotNone(list(accepted.values())[0]["revision"])
        view = rt.read_plan(quarter, quarter + timedelta(minutes=15))
        self.assertEqual(view["slots"][0]["accepted_power_kw"], 2)
        await rt.executor.advance_plan(quarter)
        self.assertEqual(len(services.calls), 1)
        rt.configuration["controller"]["mode"] = "Off"
        await rt.executor.supervise()
        self.assertEqual(services.calls[-1][1], "turn_off")

    async def test_economy_solar_without_sources_never_auto_start(self):
        for mode in ("Economy", "Solar"):
            rt, states, services = rig(mode=mode)
            at = datetime.now(timezone.utc)
            quarter = at.replace(minute=(at.minute // 15) * 15, second=0, microsecond=0)
            for source in states.values():
                source.last_updated = quarter + timedelta(seconds=1)
            rt.refresh(quarter)
            await rt.executor.advance_plan(quarter)
            self.assertEqual(services.calls, [])
            self.assertFalse(rt.executor.accepted_slots())

    async def test_adjustable_charger_without_unselected_site_phase_or_circuit_limits(self):
        rt, states, services = rig(group_kw=3.6)
        cfg = rt.configuration["chargers"][0]
        cfg.update(kind="variable_current", rated_power_kw=3.68,
                   voltage_v=230, min_current_a=6, max_current_a=16,
                   current_step_a=1, current_control_entity="number.charge_limit",
                   current_readback_entity="sensor.actual_current")
        rt.configuration = validate_configuration(rt.configuration)
        number_state = state(6, "A")
        number_state.attributes.update(min=6, max=16, step=1)
        states["number.charge_limit"] = number_state
        states["sensor.actual_current"] = state(0, "A")
        rt.refresh()
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        self.assertEqual(services.calls[0][2]["value"], 15)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"], "confirmed")

    async def test_adjustable_native_ceiling_accepts_lower_actual_vehicle_draw(self):
        rt, states, services = rig(group_kw=3.6)
        charger = rt.configuration["chargers"][0]
        charger.update(kind="variable_current", rated_power_kw=3.68,
                       voltage_v=230, min_current_a=6, max_current_a=16, current_step_a=1,
                       current_control_entity="number.charge_limit",
                       current_readback_entity="sensor.actual_current")
        entity = state(6, "A")
        entity.attributes.update(min=6, max=16, step=1)
        states["number.charge_limit"] = entity
        states["sensor.actual_current"] = state(0, "A")
        original = services.async_call
        async def vehicle_draw(domain, service, data, **kwargs):
            await original(domain, service, data, **kwargs)
            if service in ("turn_on", "set_value"):
                states["sensor.actual_current"].state = "7"
                states["sensor.actual_current"].last_updated = datetime.now(timezone.utc)
                states["sensor.actual_power"].state = "1610"
                states["sensor.actual_power"].last_updated = datetime.now(timezone.utc)
        services.async_call = vehicle_draw
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        self.assertEqual(started["measured_power_kw"], 1.61)
        self.assertEqual(rt.executor.session_snapshot()["evse"]["target_current_a"], 15)
        await rt.executor.supervise()
        self.assertEqual(states["switch.evse_control"].state, "on")
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"], "confirmed")

    async def test_native_adjustable_bounds_and_setpoint_with_power_without_amp_sensor(self):
        rt, states, services = rig(group_kw=3.6)
        cfg = rt.configuration["chargers"][0]
        cfg.update(kind="variable_current", rated_power_kw=3.68,
                   voltage_v=230, current_control_entity="number.charge_limit")
        rt.configuration = validate_configuration(rt.configuration)
        entity = state(6, "A")
        entity.attributes.update(min=6, max=16, step=1)
        states["number.charge_limit"] = entity
        rt.refresh()
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        self.assertEqual(services.calls[0][2]["value"], 15)
        self.assertNotIn("min_current_a", rt.configuration["chargers"][0])
        self.assertEqual((await rt.executor.execute("evse", "set_current", current_a=10))["reason"],
                         "NATIVE_SETPOINT_AND_POWER_READBACK")
        await rt.executor.supervise()
        self.assertEqual(states["switch.evse_control"].state, "on")
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"], "confirmed")

    async def test_verified_adjustable_native_setpoint_and_physical_start(self):
        rt, states, services = rig(group_kw=7.5)
        cfg = rt.configuration["chargers"][0]
        cfg.update(kind="variable_current", rated_power_kw=3.7,
                   phase_ids=["L1"], voltage_v=230,
                   min_current_a=6, max_current_a=16, current_step_a=1,
                   circuit_id="drive", circuit_limit_a=16,
                   current_control_entity="number.charge_limit",
                   current_readback_entity="sensor.actual_current")
        number_state = state(6, "A")
        number_state.attributes.update(min=6, max=16, step=1)
        states["number.charge_limit"] = number_state
        states["sensor.actual_current"] = state(0, "A")
        rt.configuration["controller"]["phase_limits_a"] = {"L1": 16}
        self.assertTrue(rt.executor.capabilities()["evse"]["start_allowed"])
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        self.assertEqual([x[1] for x in services.calls[:2]], ["set_value", "turn_on"])
        adjusted = await rt.executor.execute("evse", "set_current", current_a=8)
        self.assertEqual(adjusted["status"], "confirmed")
        self.assertEqual(services.calls[-1][:2], ("number", "set_value"))
        self.assertEqual(rt.executor.session_snapshot()["evse"]["target_current_a"], 8)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"], "confirmed")

    async def test_user_charger_power_limit_bounds_real_amp_commands(self):
        rt, states, services = rig(group_kw=7.5)
        rt.configuration["controller"]["phase_limits_a"] = {"L1": 16}
        rt.configuration["chargers"][0].update(
            kind="variable_current", rated_power_kw=3.68,
            phase_ids=["L1"], voltage_v=230,
            min_current_a=6, max_current_a=16, current_step_a=1,
            min_charging_power_kw=1.84, max_charging_power_kw=2.76,
            circuit_id="drive", circuit_limit_a=16,
            current_control_entity="number.charge_limit",
            current_readback_entity="sensor.actual_current",
        )
        limit = state(6, "A")
        limit.attributes.update(min=6, max=16, step=1)
        states["number.charge_limit"] = limit
        states["sensor.actual_current"] = state(0, "A")
        result = await rt.executor.execute("evse", "start")
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(services.calls[0][2]["value"], 12)
        too_high = await rt.executor.execute("evse", "set_current", current_a=13)
        too_low = await rt.executor.execute("evse", "set_current", current_a=7)
        self.assertEqual(too_high["reason"], "ABOVE_USER_CHARGING_POWER_MAXIMUM")
        self.assertEqual(too_low["reason"], "BELOW_USER_CHARGING_POWER_MINIMUM")
        self.assertEqual(len(services.calls), 2)
        valid = await rt.executor.execute("evse", "set_current", current_a=10)
        self.assertEqual(valid["status"], "confirmed")
        self.assertEqual(services.calls[-1][2]["value"], 10)

    async def test_force_charge_selects_highest_safe_verified_current(self):
        rt, states, services = rig(group_kw=3)
        rt.configuration["controller"]["phase_limits_a"] = {"L1": 12}
        rt.configuration["chargers"][0].update(
            kind="variable_current", rated_power_kw=3.7,
            phase_ids=["L1"], voltage_v=230,
            min_current_a=6, max_current_a=16, current_step_a=1,
            circuit_id="drive", circuit_limit_a=14,
            current_control_entity="number.charge_limit",
            current_readback_entity="sensor.actual_current",
        )
        entity = state(6, "A")
        entity.attributes.update(min=6, max=16, step=1)
        states["number.charge_limit"] = entity
        states["sensor.actual_current"] = state(0, "A")
        outcome = await rt.executor.execute("evse", "start")
        self.assertEqual(outcome["status"], "confirmed")
        self.assertEqual(services.calls[0][2]["value"], 12)
        self.assertEqual(rt.executor.session_snapshot()["evse"]["target_current_a"], 12)


    async def test_automatic_modes_require_qualified_interval_sources(self):
        for mode in ("Automatic", "Economy", "Solar", "Ready By"):
            rt, states, services = rig(mode=mode)
            at = datetime.now(timezone.utc)
            quarter = at.replace(minute=(at.minute // 15) * 15,
                                 second=0, microsecond=0)
            rt.configuration["assets"][0]["ready_by"] = (
                quarter + timedelta(hours=1)
            ).isoformat()
            if mode == "Economy":
                rt.configuration["controller"]["price_entity"] = "sensor.price"
                meter = state("ready")
                meter.attributes = {
                    "kind": "effective_price_kwh", "currency": "EUR",
                    "valid_until": (quarter + timedelta(hours=1)).isoformat(),
                    "intervals": [{"start": quarter.isoformat(),
                                   "end": (quarter + timedelta(hours=1)).isoformat(),
                                   "value": -0.04}],
                }
                states["sensor.price"] = meter
            if mode == "Solar":
                rt.configuration["controller"]["solar_entity"] = "sensor.solar"
                available = state("ready")
                available.attributes = {
                    "kind": "solar_limit_kw",
                    "valid_until": (quarter + timedelta(hours=1)).isoformat(),
                    "intervals": [{"start": quarter.isoformat(),
                                   "end": (quarter + timedelta(hours=1)).isoformat(),
                                   "value": 2.5}],
                }
                states["sensor.solar"] = available
            for row in states.values():
                row.last_updated = quarter + timedelta(seconds=1)
            rt.refresh(quarter)
            await rt.executor.advance_plan(quarter)
            self.assertEqual([c[1] for c in services.calls], ["turn_on"], mode)
            self.assertEqual(len(rt.executor.accepted_slots()), 1, mode)
            self.assertTrue(rt.executor._inflight, mode)

    async def test_persisted_intent_blocks_restart_replay_until_reconciled(self):
        class MemoryStore:
            def __init__(self):
                self.data = None
            async def async_save(self, data):
                self.data = data

        rt, states, services = rig(mode="Automatic")
        store = MemoryStore()
        rt.attach_control_store(store, None)
        at = datetime.now(timezone.utc)
        quarter = at.replace(minute=(at.minute // 15) * 15,
                             second=0, microsecond=0)
        for row in states.values():
            row.last_updated = quarter + timedelta(seconds=1)
        rt.refresh(quarter)
        await rt.executor.advance_plan(quarter)
        self.assertEqual(store.data["schema_major"], 1)
        self.assertTrue(store.data["inflight"])
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"],
                         "confirmed")
        new = MultiChargeRuntime(rt.hass, rt.configuration)
        new.attach_control_store(store, store.data)
        new.refresh(quarter)
        before = len(services.calls)
        await new.executor.advance_plan(quarter)
        self.assertEqual(len(services.calls), before)
        self.assertFalse(new.executor.accepted_slots() == {})

    async def test_corrupt_persisted_control_state_fails_closed(self):
        rt, _, services = rig()
        rt.executor.restore_state({"schema_major": 100, "inflight": {}})
        denied = await rt.executor.execute("evse", "start")
        self.assertEqual(denied["reason"], "CONTROL_STATE_UNVERIFIED")
        self.assertEqual(services.calls, [])
        self.assertTrue(rt.executor.capabilities()["evse"]["stop_allowed"])

    async def test_minimal_unassigned_charger_exposes_specific_manual_start_holds(self):
        """UC05/11/17: no SoC, price or PV prerequisite; no fake cable proof."""
        rt, sources, services = rig(owner="external", commissioned=False)
        charger = rt.configuration["chargers"][0]
        charger.pop("asset")
        cap = rt.executor.capabilities()["evse"]
        self.assertFalse(cap["manual_one_off_allowed"])
        self.assertEqual(cap["manual_one_off_reason"],
                         "EXTERNAL_WRITER_OWNS_CHARGER")

        charger["control_owner"] = "multicharge"
        charger["physical_commissioned"] = False
        cap = rt.executor.capabilities()["evse"]
        self.assertEqual(cap["manual_one_off_reason"],
                         "PHYSICAL_COMMISSIONING_REQUIRED")

        charger["physical_commissioned"] = True
        sources.pop("binary_sensor.cable")
        cap = rt.executor.capabilities()["evse"]
        self.assertEqual(cap["manual_one_off_reason"],
                         "PHYSICAL_CONNECTION_UNVERIFIED")
        denied = await rt.executor.execute(
            "evse", "start", manual_request={"duration_minutes": 15},
        )
        self.assertEqual(denied["status"], "rejected")
        self.assertEqual(denied["reason"], "PHYSICAL_CONNECTION_UNVERIFIED")
        self.assertEqual(services.calls, [], "Switch-only can never prove a cable")

        # With independently observed native connection and physical meter,
        # the same already-existing bounded executor becomes available.
        sources["binary_sensor.cable"] = state("on")
        cap = rt.executor.capabilities()["evse"]
        self.assertTrue(cap["manual_one_off_allowed"])
        self.assertEqual(cap["manual_one_off_reason"], "READY")
        outcome = await rt.executor.execute(
            "evse", "start", manual_request={"duration_minutes": 15},
        )
        self.assertEqual(outcome["status"], "confirmed")
        self.assertEqual(rt.executor.session_snapshot()["evse"]["asset_id"], None)
        self.assertEqual(
            rt.executor.session_snapshot()["evse"]["requested_duration_minutes"],
            15,
        )
        self.assertEqual(services.calls[0][1], "turn_on")

    async def test_corrupt_trailing_receipt_never_partially_restores_control_state(self):
        """UC23/26: validate every persisted field before mutating live truth."""
        rt, _, services = rig()
        rt.executor._completed["car"] = "prior-valid-intent"
        rt.executor._inflight["car"] = "prior-unresolved-intent"
        rt.executor._paused.add("evse")
        rt.executor._session_history = [{
            "charger_id": "evse", "asset_id": "car",
            "started_at": "2026-11-22T12:00:00+00:00",
            "ended_at": "2026-11-22T12:30:00+00:00",
            "duration_minutes": 30.0, "actual_energy_kwh": 0.3,
            "physical_stop_confirmed": True,
        }]
        original = rt.executor.export_state()
        candidate = {
            **original,
            "completed": {"car": "replacement-intent"},
            "inflight": {"car": "replacement-unsafe-intent"},
            "paused": [],
            "sessions": [
                dict(original["sessions"][0]),
                {**original["sessions"][0],
                 "ended_at": "not-an-ISO-date"},
            ],
        }
        rt.executor.restore_state(candidate)
        self.assertFalse(rt.executor._persistence_verified)
        self.assertEqual(rt.executor.export_state(), original,
                         "Late corrupt receipt cannot partially adopt intent/holds/history")
        denied = await rt.executor.execute("evse", "start")
        self.assertEqual(denied["reason"], "CONTROL_STATE_UNVERIFIED")
        self.assertEqual(services.calls, [])

    async def test_completed_measured_demand_is_retained_after_restart(self):
        class MemoryStore:
            def __init__(self):
                self.data = None
            async def async_save(self, data):
                self.data = data

        rt, states, services = rig(mode="Automatic")
        store = MemoryStore()
        rt.attach_control_store(store, None)
        at = datetime.now(timezone.utc)
        quarter = at.replace(minute=(at.minute // 15) * 15,
                             second=0, microsecond=0)
        for row in states.values():
            row.last_updated = quarter + timedelta(seconds=1)
        rt.refresh(quarter)
        await rt.executor.advance_plan(quarter)
        self.assertEqual(services.calls[0][1], "turn_on")
        states["sensor.meter"].state = "6.1"
        states["sensor.meter"].last_updated = datetime.now(timezone.utc)
        await rt.executor.supervise()
        self.assertEqual(services.calls[-1][1], "turn_off")
        self.assertTrue(store.data["completed"])
        self.assertEqual(store.data["inflight"], {})
        rt.refresh(quarter)
        self.assertFalse(rt.assessment.plan.slots)
        restarted = MultiChargeRuntime(rt.hass, rt.configuration)
        restarted.attach_control_store(store, store.data)
        restarted.refresh(quarter)
        self.assertFalse(restarted.assessment.plan.slots)

    async def test_shared_phase_and_circuit_excess_block_without_any_write(self):
        rt, states, services = rig(group_kw=4)
        rt.configuration["controller"]["phase_limits_a"] = {"L1": 16}
        rt.configuration["controller"]["max_parallel"] = 2
        rt.configuration["chargers"][0].update(
            phase_ids=["L1"], voltage_v=230, fixed_current_a=10,
            circuit_id="common", circuit_limit_a=16)
        rt.configuration["chargers"].append({
            "id": "other", "name": "Other", "kind": "on_off",
            "rated_power_kw": 2, "phase_count": 1, "phase_ids": ["L1"],
            "voltage_v": 230, "fixed_current_a": 10,
            "circuit_id": "common", "circuit_limit_a": 16,
            "control_entity": "switch.other",
            "power_entity": "sensor.other_power",
            "control_owner": "external", "physical_commissioned": False,
        })
        states["switch.other"] = state("on")
        states["sensor.other_power"] = state(2000, "W")
        denied = await rt.executor.execute("evse", "start")
        self.assertEqual(denied["reason"], "SITE_PHASE_CURRENT_EXCEEDED")
        self.assertFalse(services.calls)


    async def test_binding_reduction_modulates_qualified_current_without_unsafe_stop(self):
        rt, states, services = rig(group_kw=4)
        rt.configuration["controller"]["phase_limits_a"] = {"L1": 16}
        rt.configuration["chargers"][0].update(
            kind="variable_current", rated_power_kw=3.7,
            phase_ids=["L1"], voltage_v=230,
            min_current_a=6, max_current_a=16, current_step_a=1,
            circuit_id="drive", circuit_limit_a=16,
            current_control_entity="number.charge_limit",
            current_readback_entity="sensor.actual_current",
        )
        entity = state(6, "A")
        entity.attributes.update(min=6, max=16, step=1)
        states["number.charge_limit"] = entity
        states["sensor.actual_current"] = state(0, "A")
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        self.assertEqual(rt.executor.session_snapshot()["evse"]["target_current_a"], 16)
        rt.configuration["controller"]["max_power_kw"] = 2.3
        await rt.executor.supervise()
        self.assertEqual(rt.executor.session_snapshot()["evse"]["target_current_a"], 10)
        self.assertEqual(services.calls[-1][:2], ("number", "set_value"))
        self.assertEqual(services.calls[-1][2]["value"], 10)

    async def test_auto_mode_cannot_bypass_accepted_plan_with_manual_current_increase(self):
        rt, states, services = rig(group_kw=4)
        rt.configuration["controller"]["phase_limits_a"] = {"L1": 16}
        rt.configuration["chargers"][0].update(
            kind="variable_current", rated_power_kw=3.7,
            phase_ids=["L1"], voltage_v=230,
            min_current_a=6, max_current_a=16, current_step_a=1,
            circuit_id="drive", circuit_limit_a=16,
            current_control_entity="number.charge_limit",
            current_readback_entity="sensor.actual_current",
        )
        entity = state(6, "A")
        entity.attributes.update(min=6, max=16, step=1)
        states["number.charge_limit"] = entity
        states["sensor.actual_current"] = state(0, "A")
        self.assertEqual((await rt.executor.execute(
            "evse", "start", current_a=6
        ))["status"], "confirmed")
        rt.configuration["controller"]["mode"] = "Automatic"
        before = len(services.calls)
        denied = await rt.executor.execute("evse", "set_current", current_a=16)
        self.assertEqual(denied["reason"], "CURRENT_INCREASE_REQUIRES_ACCEPTED_SLOT")
        self.assertEqual(len(services.calls), before)

    async def test_invalid_adjustable_current_is_rejected_without_physical_write(self):
        rt, states, services = rig(group_kw=7.5)
        rt.configuration["chargers"][0].update(
            kind="variable_current", rated_power_kw=3.7,
            phase_ids=["L1"], voltage_v=230,
            min_current_a=6, max_current_a=16, current_step_a=1,
            circuit_id="drive", circuit_limit_a=16,
            current_control_entity="number.charge_limit",
            current_readback_entity="sensor.actual_current",
        )
        entity = state(6, "A")
        entity.attributes.update(min=6, max=16, step=1)
        states["number.charge_limit"] = entity
        states["sensor.actual_current"] = state(0, "A")
        result = await rt.executor.execute("evse", "set_current", current_a=20)
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(services.calls)

    async def test_completed_session_is_measured_persisted_and_stable_after_reload(self):
        rt, states, services = rig()
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"], "confirmed")
        states["sensor.meter"].state = "5.8"
        states["sensor.meter"].last_updated = datetime.now(timezone.utc)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"], "confirmed")
        receipts = rt.executor.completed_sessions()
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["charger_id"], "evse")
        self.assertEqual(receipts[0]["asset_id"], "car")
        self.assertAlmostEqual(receipts[0]["actual_energy_kwh"], 0.8, places=6)
        self.assertEqual(receipts[0]["energy_quality"], "measured")
        self.assertIsNone(receipts[0]["cost"])
        self.assertEqual(receipts[0]["cost_quality"], "unknown")
        self.assertTrue(receipts[0]["physical_stop_confirmed"])
        reloaded = MultiChargeRuntime(rt.hass, rt.configuration)
        reloaded.executor.restore_state(rt.executor.export_state())
        self.assertEqual(reloaded.executor.completed_sessions(), receipts)

    async def test_unqualified_meter_keeps_closed_session_energy_unknown(self):
        rt, states, _ = rig()
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"], "confirmed")
        states["sensor.meter"].state = "unavailable"
        states["sensor.meter"].last_updated = datetime.now(timezone.utc)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"], "confirmed")
        receipt = rt.executor.completed_sessions()[0]
        self.assertIsNone(receipt["actual_energy_kwh"])
        self.assertIsNone(receipt["cost"])
        self.assertEqual(receipt["energy_quality"], "unknown")

    async def test_urgent_stop_other_evse_dispatched_before_unconfirmed_start_timeout(self):
        rt, sources, services = rig(group_kw=8.0)
        rt.configuration["controller"]["max_parallel"] = 2
        rt.configuration["chargers"].append({
            "id": "other", "name": "Other", "kind": "on_off",
            "rated_power_kw": 2.0, "phase_count": 1,
            "control_owner": "multicharge",
            "physical_commissioned": True,
            "control_entity": "switch.other_control",
            "power_entity": "sensor.other_power",
            "connected_entity": "binary_sensor.other_cable",
        })
        sources["switch.other_control"] = state("on")
        sources["sensor.other_power"] = state("1600", "W")
        sources["binary_sensor.other_cable"] = state("on")
        # Keep A's physical START unconfirmed, holding the global lock.
        # B already charges; its urgent physical STOP must not await A.
        services.reconcile_observations = False
        pending_a = asyncio.create_task(
            rt.executor.execute("evse", "start", readback_seconds=0.65))
        for _ in range(80):
            if "evse" in rt.executor._start_pending:
                break
            await asyncio.sleep(0.005)
        self.assertIn("evse", rt.executor._start_pending)
        pending_b = asyncio.create_task(
            rt.executor.execute("other", "stop", readback_seconds=0.05))
        await asyncio.sleep(0.05)
        self.assertTrue(any(
            action == "turn_off" and args.get("entity_id") ==
            "switch.other_control"
            for domain, action, args, *_ in services.calls
            if domain == "switch"
        ), "B physical STOP must be issued before A readback timeout")
        self.assertFalse(pending_a.done(),
                         "A still awaits independent source confirmation")
        result_a, result_b = await asyncio.gather(pending_a, pending_b)
        self.assertNotEqual(result_a["status"], "confirmed")
        self.assertNotEqual(result_b["status"], "confirmed")
        # A second request cannot bypass physical confirmation of B's STOP.

    async def test_qualified_eur_budget_physically_stops_with_measured_kwh(self):
        rt, states, service = rig()
        asset = rt.configuration["assets"][0]
        asset.pop("requested_kwh")
        asset["requested_budget_amount"] = 10.0
        asset["requested_budget_currency"] = "EUR"
        now = datetime.now(timezone.utc)
        provider = state("ready")
        provider.attributes = {
            "kind": "effective_price_kwh", "currency": "EUR",
            "valid_until": (now + timedelta(hours=3)).isoformat(),
            "intervals": [{
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=3)).isoformat(),
                "value": 10.0,
            }],
        }
        states["sensor.effective_price"] = provider
        rt.configuration["controller"]["price_entity"] = "sensor.effective_price"
        rt.refresh()
        self.assertEqual(rt.observations["sources"]["tariff_quality"], "OK")
        result = await rt.executor.execute("evse", "start")
        self.assertEqual(result["status"], "confirmed")
        snapshot = rt.executor.session_snapshot()["evse"]
        self.assertEqual(snapshot["requested_budget_amount"], 10)
        states["sensor.meter"].state = "6"
        states["sensor.meter"].last_updated = datetime.now(timezone.utc)
        await rt.executor.supervise()
        self.assertEqual(service.calls[-1][1], "turn_off")
        self.assertFalse(rt.executor.session_snapshot())
        receipt = rt.executor.completed_sessions()[0]
        self.assertEqual(receipt["budget_cost_quality"],
                         "qualified_effective_meter_increments")
        self.assertAlmostEqual(receipt["budget_accrued_cost"], 10.0)
        self.assertEqual(receipt["actual_energy_kwh"], 1.0)
        self.assertTrue(receipt["physical_stop_confirmed"])
        blocked_repeat = await rt.executor.execute("evse", "start")
        self.assertEqual(blocked_repeat["reason"], "TARGET_ALREADY_MET",
                         "Verified €10 must not be silently charged twice")
        # Historical receipt does not change when later a different asset
        # is selected on the same physical Charger.
        rt.configuration["chargers"][0]["asset"] = None
        self.assertEqual(rt.executor.completed_sessions()[0]["asset_id"], "car")

    async def test_money_meter_delta_across_dynamic_price_boundary_is_upper_bound(self):
        from multicharge_physical_execution_test.contracts import PriceSlot
        rt, sources, _ = rig()
        asset = rt.configuration["assets"][0]
        asset.pop("requested_kwh")
        asset.update(requested_budget_amount=10.0,
                     requested_budget_currency="EUR")
        now = datetime.now(timezone.utc)
        provider = state("ready")
        provider.attributes = {
            "kind": "effective_price_kwh", "currency": "EUR",
            "valid_until": (now + timedelta(hours=3)).isoformat(),
            "intervals": [{
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=3)).isoformat(),
                "value": 0.2,
            }],
        }
        sources["sensor.price"] = provider
        rt.configuration["controller"]["price_entity"] = "sensor.price"
        rt.refresh()
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        session = rt.executor._sessions["evse"]
        now = datetime.now(timezone.utc)
        session["budget_last_meter_value"] = 5.0
        session["budget_last_meter_at"] = now - timedelta(minutes=1)
        rt.price_slots = (
            PriceSlot(now - timedelta(hours=1), now - timedelta(seconds=30),
                      0.2, "EUR", "effective"),
            PriceSlot(now - timedelta(seconds=30), now + timedelta(hours=1),
                      0.4, "EUR", "effective"),
        )
        sources["sensor.meter"].state = "6.0"
        sources["sensor.meter"].last_updated = now
        reason = rt.executor._session_stop_reason(
            rt.configuration["chargers"][0], now)
        self.assertIsNone(reason)
        self.assertEqual(session["budget_quality"],
                         "conservative_effective_upper_bound")
        self.assertAlmostEqual(session["budget_cost"], 0.4, places=4)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"],
                         "confirmed")
        receipt = rt.executor.completed_sessions()[0]
        self.assertEqual(receipt["budget_cost_quality"],
                         "conservative_effective_upper_bound")
        self.assertAlmostEqual(receipt["budget_accrued_cost"], 0.4)
        self.assertAlmostEqual(
            rt.executor.measured_intent_usage(
                asset, rt.configuration["chargers"][0], None)["budget_amount"],
            0.4)

    async def test_price_ceiling_physically_blocks_start_and_stops_active_after_rate_change(self):
        rt, states, services = rig()
        asset = rt.configuration["assets"][0]
        asset.update(maximum_price_per_kwh=0.20, price_currency="EUR")
        now = datetime.now(timezone.utc)
        price = state("ready")
        price.attributes = {
            "kind": "effective_price_kwh", "currency": "EUR",
            "valid_until": (now + timedelta(hours=3)).isoformat(),
            "intervals": [{
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=3)).isoformat(),
                "value": 0.30,
            }],
        }
        states["sensor.price"] = price
        rt.configuration["controller"]["price_entity"] = "sensor.price"
        rt.refresh()
        blocked = await rt.executor.execute("evse", "start")
        self.assertEqual(blocked["reason"], "PRICE_LIMIT_BLOCKED")
        self.assertEqual(services.calls, [])
        price.attributes["intervals"][0]["value"] = 0.10
        price.last_updated = datetime.now(timezone.utc)
        rt.refresh()
        running = await rt.executor.execute("evse", "start")
        self.assertEqual(running["status"], "confirmed")
        price.attributes["intervals"][0]["value"] = 0.30
        price.last_updated = datetime.now(timezone.utc)
        rt.refresh()
        self.assertEqual(rt.executor._session_stop_reason(
            rt.configuration["chargers"][0], datetime.now(timezone.utc)),
            "PRICE_LIMIT_BLOCKED")
        await rt.executor.supervise()
        self.assertEqual(services.calls[-1][1], "turn_off")
        self.assertFalse(rt.executor.session_snapshot())

    async def test_earliest_start_and_low_soc_price_override_are_source_bound(self):
        rt, states, services = rig()
        asset = rt.configuration["assets"][0]
        asset["earliest_start_at"] = (
            datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        result = await rt.executor.execute("evse", "start")
        self.assertEqual(result["reason"], "EARLIEST_START_NOT_REACHED")
        self.assertEqual(services.calls, [])
        asset.pop("earliest_start_at")
        asset.pop("requested_kwh")
        asset.update(target_soc=80, capacity_kwh=50,
                     charge_efficiency=0.9, soc_entity="sensor.car_soc",
                     minimum_soc_pct=30,
                     maximum_price_per_kwh=0.20, price_currency="EUR")
        states["sensor.car_soc"] = state("25", "%")
        now = datetime.now(timezone.utc)
        price = state("ready")
        price.attributes = {
            "kind": "effective_price_kwh", "currency": "EUR",
            "valid_until": (now + timedelta(hours=3)).isoformat(),
            "intervals": [{
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=3)).isoformat(),
                "value": 0.30,
            }],
        }
        states["sensor.price"] = price
        rt.configuration["controller"]["price_entity"] = "sensor.price"
        rt.refresh()
        active = await rt.executor.execute("evse", "start")
        self.assertEqual(active["status"], "confirmed")
        states["sensor.car_soc"].state = "40"
        states["sensor.car_soc"].last_updated = datetime.now(timezone.utc)
        rt.refresh()
        self.assertEqual(rt.executor._session_stop_reason(
            rt.configuration["chargers"][0], datetime.now(timezone.utc)),
            "PRICE_LIMIT_BLOCKED",
            "Minimum SoC may bypass economic cap only while actually below minimum")
        await rt.executor.supervise()
        self.assertEqual(services.calls[-1][1], "turn_off")

    async def test_money_negative_tariff_does_not_make_unlimited_24h_intent(self):
        rt, states, service = rig()
        asset = rt.configuration["assets"][0]
        asset.pop("requested_kwh")
        asset["requested_budget_amount"] = 10.0
        asset["requested_budget_currency"] = "EUR"
        now = datetime.now(timezone.utc)
        provider = state("ready")
        provider.attributes = {
            "kind": "effective_price_kwh", "currency": "EUR",
            "valid_until": (now + timedelta(hours=3)).isoformat(),
            "intervals": [{
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=3)).isoformat(),
                "value": -0.08,
            }],
        }
        states["sensor.price"] = provider
        rt.configuration["controller"]["price_entity"] = "sensor.price"
        rt.refresh()
        self.assertEqual(
            rt.observations["sources"]["tariff_quality"], "OK")
        # Earlier independently-confirmed session receipts exhaust a
        # combined 24h money-intent safety ceiling even at zero price.
        target_key = rt.executor._intent_key(
            asset, rt.configuration["chargers"][0], None)
        rt.executor._session_history.append({
            "charger_id": "evse", "asset_id": "car",
            "intent_key": target_key,
            "started_at": (now - timedelta(hours=24)).isoformat(),
            "ended_at": now.isoformat(),
            "duration_minutes": 1440,
            "actual_energy_kwh": 0.0,
            "budget_accrued_cost": 0.0,
            "budget_cost_quality": "qualified_effective_meter_increments",
            "budget_currency": "EUR",
            "physical_stop_confirmed": True,
        })
        rt.refresh()
        blocked = await rt.executor.execute("evse", "start")
        self.assertEqual(blocked["reason"], "TARGET_ALREADY_MET")
        self.assertEqual(service.calls, [])

    async def test_money_stop_remains_safe_if_meter_entity_removed(self):
        rt, states, _ = rig()
        asset = rt.configuration["assets"][0]
        asset.pop("requested_kwh")
        asset.update(requested_budget_amount=10.0,
                     requested_budget_currency="EUR")
        now = datetime.now(timezone.utc)
        provider = state("ready")
        provider.attributes = {
            "kind": "effective_price_kwh", "currency": "EUR",
            "valid_until": (now + timedelta(hours=3)).isoformat(),
            "intervals": [{
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=3)).isoformat(),
                "value": 0.15,
            }],
        }
        states["sensor.price"] = provider
        rt.configuration["controller"]["price_entity"] = "sensor.price"
        rt.refresh()
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        rt.configuration["chargers"][0].pop("energy_entity")
        result = await rt.executor.execute("evse", "stop")
        self.assertEqual(result["status"], "confirmed")
        receipt = rt.executor.completed_sessions()[0]
        self.assertIsNone(receipt["budget_accrued_cost"])
        self.assertEqual(receipt["budget_cost_quality"], "unknown")
        self.assertIsNone(receipt["actual_energy_kwh"])
        self.assertTrue(receipt["physical_stop_confirmed"])

    async def test_eur_budget_spot_reference_and_missing_meter_fail_closed(self):
        rt, states, service = rig()
        asset = rt.configuration["assets"][0]
        asset.pop("requested_kwh")
        asset["requested_budget_amount"] = 10
        asset["requested_budget_currency"] = "EUR"
        rt.refresh()
        self.assertEqual((await rt.executor.execute("evse", "start"))["reason"],
                         "BUDGET_EFFECTIVE_TARIFF_UNAVAILABLE")
        now = datetime.now(timezone.utc)
        from multicharge_physical_execution_test.contracts import PriceSlot
        for basis in ("spot", "variable_reference"):
            rt.price_slots = (PriceSlot(
                now - timedelta(hours=1), now + timedelta(hours=3),
                0.25, "EUR", basis=basis,
            ),)
            rt.observations["sources"]["tariff_quality"] = "OK"
            self.assertIsNone(rt.executor._qualified_budget_price(now, "EUR"))
            self.assertEqual((await rt.executor.execute("evse", "start"))["reason"],
                             "BUDGET_EFFECTIVE_TARIFF_UNAVAILABLE")
        self.assertFalse(service.calls)
        rt.configuration["chargers"][0]["energy_entity"] = None
        blocked = await rt.executor.execute("evse", "start")
        self.assertEqual(blocked["reason"], "BUDGET_ENERGY_METER_REQUIRED")
        self.assertFalse(service.calls)

    async def test_charger_only_money_one_off_remains_anonymous(self):
        rt, states, service = rig()
        rt.configuration["chargers"][0]["asset"] = None
        now = datetime.now(timezone.utc)
        provider = state("ready")
        provider.attributes = {
            "kind": "effective_price_kwh", "currency": "EUR",
            "valid_until": (now + timedelta(hours=3)).isoformat(),
            "intervals": [{
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=3)).isoformat(),
                "value": 1.0,
            }],
        }
        states["sensor.effective_price"] = provider
        rt.configuration["controller"]["price_entity"] = "sensor.effective_price"
        rt.refresh()
        result = await rt.executor.execute(
            "evse", "start",
            manual_request={"cost_amount": 10.0, "currency": "EUR"},
        )
        self.assertEqual(result["status"], "confirmed")
        self.assertIsNone(rt.executor.session_snapshot()["evse"]["asset_id"])
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"],
                         "confirmed")
        self.assertIsNone(rt.executor.completed_sessions()[0]["asset_id"])
        self.assertTrue(service.calls)

    async def test_charging_weekday_window_blocks_start_and_stops_running_session(self):
        from zoneinfo import ZoneInfo
        from multicharge_physical_execution_test.configuration import WEEKDAYS
        rt, states, services = rig()
        today = datetime.now(ZoneInfo(rt.hass.config.time_zone))
        other = WEEKDAYS[(today.weekday() + 2) % 7]
        asset = rt.configuration["assets"][0]
        asset["charging_windows"] = {
            other: {"start": "09:00", "end": "10:00"}
        }
        rejected = await rt.executor.execute("evse", "start")
        self.assertEqual(rejected["reason"], "CHARGING_WINDOW_CLOSED")
        self.assertEqual(services.calls, [])
        asset.pop("charging_windows")
        rt.refresh()
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        asset["charging_windows"] = {
            other: {"start": "09:00", "end": "10:00"}
        }
        self.assertEqual(
            rt.executor._session_stop_reason(
                rt.configuration["chargers"][0], datetime.now(timezone.utc)),
            "CHARGING_WINDOW_CLOSED",
        )
        await rt.executor.supervise()
        self.assertEqual(services.calls[-1][1], "turn_off")
        self.assertFalse(rt.executor.session_snapshot())

    async def test_temporary_guest_expiry_rejects_start_and_stops_active_guest(self):
        rt, states, services = rig()
        guest = rt.configuration["assets"][0]
        guest["temporary"] = True
        guest["expires_at"] = (datetime.now(timezone.utc)
                                + timedelta(hours=1)).isoformat()
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"], "confirmed")
        guest["expires_at"] = (datetime.now(timezone.utc)
                                - timedelta(seconds=1)).isoformat()
        await rt.executor.supervise()
        self.assertEqual(services.calls[-1][1], "turn_off")
        self.assertFalse(rt.executor.session_snapshot())
        before = len(services.calls)
        rejected = await rt.executor.execute("evse", "start")
        self.assertEqual(rejected["reason"], "TEMPORARY_ASSET_EXPIRED")
        self.assertEqual(before, len(services.calls))

    async def test_measured_session_uses_only_full_qualified_effective_tariff(self):
        rt, states, _ = rig()
        now = datetime.now(timezone.utc)
        price = state("ready")
        price.attributes = {
            "kind": "effective_price_kwh", "currency": "EUR",
            "valid_until": (now + timedelta(hours=2)).isoformat(),
            "intervals": [{
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=2)).isoformat(),
                "value": -0.08,
            }],
        }
        states["sensor.effective_price"] = price
        rt.configuration["controller"]["price_entity"] = "sensor.effective_price"
        rt.refresh()
        self.assertEqual(rt.observations["sources"]["tariff_quality"], "OK")
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"], "confirmed")
        states["sensor.meter"].state = "5.5"
        states["sensor.meter"].last_updated = datetime.now(timezone.utc)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"], "confirmed")
        receipt = rt.executor.completed_sessions()[0]
        self.assertEqual(receipt["cost_quality"], "qualified_effective_tariff")
        self.assertEqual(receipt["currency"], "EUR")
        self.assertAlmostEqual(receipt["actual_energy_kwh"], 0.5)
        self.assertAlmostEqual(receipt["cost"], -0.04)

    async def test_rebinding_does_not_rewrite_completed_session_asset_identity(self):
        rt, states, _ = rig()
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"], "confirmed")
        states["sensor.meter"].state = "5.25"
        states["sensor.meter"].last_updated = datetime.now(timezone.utc)
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"], "confirmed")
        rt.configuration["assets"].append({
            "id": "guest", "name": "Guest", "kind": "car", "requested_kwh": 2
        })
        rt.configuration["chargers"][0]["asset"] = "guest"
        rt.refresh()
        self.assertEqual(rt.executor.completed_sessions()[0]["asset_id"], "car")
        at = datetime.now(timezone.utc)
        result = rt.read_plan(at - timedelta(hours=1), at + timedelta(minutes=1),
                              asset_id="car")
        self.assertEqual(result["completed_sessions"][0]["asset_id"], "car")

    async def test_external_charger_without_switch_uses_verified_real_power_budget(self):
        """A provider-neutral external Charger can coexist without a writable switch."""
        rt, states, services = rig(group_kw=4.0)
        rt.configuration["controller"]["max_parallel"] = 2
        rt.configuration["chargers"].append({
            "id": "external", "name": "Other provider",
            "kind": "on_off", "rated_power_kw": 1.5,
            "power_entity": "sensor.external_power",
            "connected_entity": "binary_sensor.external_connected",
            "control_owner": "external", "physical_commissioned": False,
        })
        states["sensor.external_power"] = state(0, "W")
        states["binary_sensor.external_connected"] = state("off")
        rt.refresh()
        self.assertTrue(rt.executor.capabilities()["evse"]["start_allowed"])
        first = await rt.executor.execute("evse", "start")
        self.assertEqual(first["status"], "confirmed")
        # Recorder-quality energy evidence must be independently fresh after
        # the start, or a second request correctly refuses unknown progress.
        states["sensor.meter"].state = "5.1"
        states["sensor.meter"].last_updated = datetime.now(timezone.utc)
        await rt.executor.execute("evse", "stop")
        # Actual external power must now consume the shared budget even if
        # its native provider has no switch entity exposed to MultiCharge.
        states["sensor.external_power"].state = "2500"
        states["sensor.external_power"].last_updated = datetime.now(timezone.utc)
        rt.refresh()
        blocked = await rt.executor.execute("evse", "start")
        self.assertEqual(blocked["reason"], "SITE_CAPACITY_EXCEEDED")
        self.assertEqual([call[1] for call in services.calls],
                         ["turn_on", "turn_off"])

    async def test_independent_charger_actions_remain_scoped_in_controller_projection(self):
        rt, sources, services = rig()
        cfg = rt.configuration
        cfg["controller"]["max_parallel"] = 2
        cfg["controller"]["max_power_kw"] = 4.0
        cfg["chargers"].append({
            "id": "second", "name": "Second", "kind": "on_off",
            "rated_power_kw": 2.0, "phase_count": 1,
            "control_entity": "switch.second",
            "power_entity": "sensor.second_power",
            "connected_entity": "binary_sensor.second_cable",
            "control_owner": "external", "physical_commissioned": False,
        })
        sources["switch.second"] = state("off")
        sources["sensor.second_power"] = state(0, "W")
        sources["binary_sensor.second_cable"] = state("off")
        rt.refresh()
        self.assertEqual(rt.live_state()["connected_chargers"], 1)
        result = await rt.executor.execute("evse", "start")
        self.assertEqual(result["status"], "confirmed")
        summary = rt.live_state()
        self.assertEqual(summary["charging_chargers"], 1)
        self.assertEqual(summary["last_action"]["charger_id"], "evse")
        self.assertEqual(summary["command_outcomes"]["evse"]["status"], "confirmed")
        self.assertNotIn("second", summary["command_outcomes"])

    async def test_controller_action_projection_updates_on_requested_and_confirmed(self):
        rt, _, services = rig()
        observed = []
        rt.subscribe(lambda: observed.append(rt.live_state()))
        confirmed = await rt.executor.execute("evse", "start")
        self.assertEqual(confirmed["status"], "confirmed")
        self.assertGreaterEqual(len(observed), 2)
        self.assertEqual(observed[0]["action_health"], "pending")
        self.assertEqual(observed[0]["last_action"]["action"], "start")
        self.assertEqual(observed[-1]["action_health"], "confirmed")
        self.assertEqual(observed[-1]["charging_chargers"], 1)
        self.assertEqual(observed[-1]["last_action"]["readback_at"],
                         confirmed["readback_at"])
        self.assertEqual(observed[-1]["last_action"]["charger_id"], "evse")
        await rt.executor.execute("evse", "stop")
        self.assertEqual(rt.live_state()["charging_chargers"], 0)
        self.assertEqual(rt.live_state()["last_action"]["action"], "stop")

    async def test_real_on_and_off_calls_require_independent_power_confirmation(self):
        runtime, states, services = rig()
        self.assertTrue(runtime.executor.capabilities()["evse"]["start_allowed"])
        first = await runtime.executor.execute("evse", "start", request_id="start-001")
        self.assertEqual(first["status"], "confirmed")
        self.assertEqual(first["reason"], "INDEPENDENT_POWER_READBACK")
        self.assertTrue(first["service_sent"])
        self.assertIsNotNone(first["readback_at"])
        self.assertEqual(services.calls[0][:2], ("switch", "turn_on"))
        self.assertEqual(services.calls[0][2], {"entity_id": "switch.evse_control"})
        second = await runtime.executor.execute("evse", "stop", request_id="stop-001")
        self.assertEqual(second["status"], "confirmed")
        self.assertEqual(second["measured_power_kw"], 0)
        self.assertEqual([x[1] for x in services.calls], ["turn_on", "turn_off"])

    async def test_idempotent_request_does_not_reissue_physical_service(self):
        rt, _, services = rig()
        first = await rt.executor.execute("evse", "start", request_id="fixed-key")
        repeated = await rt.executor.execute("evse", "start", request_id="fixed-key")
        self.assertEqual(first, repeated)
        self.assertEqual(len(services.calls), 1)
        with self.assertRaisesRegex(ValueError, "different command"):
            await rt.executor.execute("evse", "stop", request_id="fixed-key")

    async def test_external_writer_default_blocks_start_and_stop(self):
        rt, _, services = rig(owner="external", commissioned=False)
        for action in ("start", "stop"):
            outcome = await rt.executor.execute("evse", action)
            self.assertEqual(outcome["status"], "rejected")
            self.assertEqual(outcome["reason"], "EXTERNAL_WRITER_OWNS_CHARGER")
        self.assertEqual(services.calls, [])

    async def test_commissioning_is_not_implicit_and_start_is_force_only(self):
        rt, _, services = rig(commissioned=False)
        self.assertEqual(
            (await rt.executor.execute("evse", "start"))["reason"],
            "EXTERNAL_WRITER_OWNS_CHARGER",
        )
        self.assertEqual(services.calls, [])
        rt, _, services = rig(mode="Automatic")
        self.assertEqual(
            (await rt.executor.execute("evse", "start"))["reason"],
            "MANUAL_START_REQUIRES_FORCE_CHARGE",
        )
        self.assertEqual(services.calls, [])

    async def test_missing_physical_connection_rejects_start_but_stop_can_run(self):
        rt, sources, services = rig()
        sources["binary_sensor.cable"].state = "off"
        denied = await rt.executor.execute("evse", "start")
        self.assertEqual(denied["reason"], "PHYSICAL_CONNECTION_UNVERIFIED")
        self.assertFalse(services.calls)
        sources["switch.evse_control"].state = "on"
        sources["sensor.actual_power"].state = "500"
        stop = await rt.executor.execute("evse", "stop")
        self.assertEqual(stop["status"], "confirmed")
        self.assertEqual(services.calls[0][1], "turn_off")

    async def test_source_stale_capacity_and_offline_never_start(self):
        rt, sources, services = rig(group_kw=1.0)
        self.assertEqual((await rt.executor.execute("evse", "start"))["reason"],
                         "SITE_CAPACITY_EXCEEDED")
        self.assertEqual(services.calls, [])
        rt, sources, services = rig()
        sources["binary_sensor.cable"].last_updated -= timedelta(hours=1)
        self.assertEqual((await rt.executor.execute("evse", "start"))["reason"],
                         "PHYSICAL_CONNECTION_UNVERIFIED")
        self.assertEqual(services.calls, [])
        rt, sources, services = rig()
        sources["switch.evse_control"].state = "unavailable"
        self.assertEqual((await rt.executor.execute("evse", "stop"))["reason"],
                         "NATIVE_SWITCH_UNAVAILABLE")
        self.assertEqual(services.calls, [])

    async def test_native_exception_is_unknown_and_blocks_repeated_start(self):
        rt, _, services = rig()
        services.fail = True
        outcome = await rt.executor.execute("evse", "start")
        self.assertEqual(outcome["status"], "execution_unknown")
        self.assertIn("NATIVE_SERVICE_EXCEPTION", outcome["reason"])
        self.assertEqual((await rt.executor.execute("evse", "start"))["reason"],
                         "PREVIOUS_COMMAND_UNCONFIRMED")
        self.assertEqual(len(services.calls), 2)
        self.assertEqual(services.calls[-1][1], "turn_off")

    async def test_timeout_does_not_forge_success_and_quarantines_start(self):
        rt, _, services = rig()
        services.reconcile_observations = False
        result = await rt.executor.execute("evse", "start", readback_seconds=0.015)
        self.assertEqual(result["status"], "execution_unknown")
        self.assertTrue(result["reason"].startswith("PHYSICAL_READBACK_TIMEOUT"))
        self.assertIn("PROTECTIVE_STOP_SENT", result["reason"])
        self.assertIsNone(result["readback_at"])
        self.assertFalse(rt.executor.capabilities()["evse"]["start_allowed"])
        self.assertEqual([x[1] for x in services.calls], ["turn_on", "turn_off"])

    async def test_stop_does_not_claim_positive_command_with_old_power(self):
        rt, sources, services = rig()
        sources["switch.evse_control"].state = "on"
        sources["sensor.actual_power"].state = "1200"
        services.reconcile_observations = False
        result = await rt.executor.execute("evse", "stop", readback_seconds=0.015)
        self.assertEqual(result["status"], "execution_unknown")
        self.assertIsNone(result["readback_at"])
        self.assertEqual(services.calls[0][1], "turn_off")

    async def test_stop_after_timeout_can_reconcile_quarantine(self):
        rt, sources, services = rig()
        services.reconcile_observations = False
        first = await rt.executor.execute("evse", "start", readback_seconds=0.015)
        self.assertEqual(first["status"], "execution_unknown")
        self.assertFalse(rt.executor.capabilities()["evse"]["start_allowed"])
        # The native physical source eventually confirms a stopped charger.
        sources["switch.evse_control"].state = "off"
        sources["sensor.actual_power"].state = "0"
        sources["sensor.actual_power"].last_updated = datetime.now(timezone.utc)
        stopped = await rt.executor.execute("evse", "stop")
        self.assertEqual(stopped["status"], "confirmed")
        # There was no confirmed START/session meter baseline before the
        # timeout. Even an independently confirmed STOP cannot establish how
        # much energy the earlier uncertain request actually delivered.
        self.assertFalse(rt.executor.capabilities()["evse"]["start_allowed"])
        self.assertEqual(
            rt.executor.capabilities()["evse"]["reason"],
            "UNRESOLVED_PREVIOUS_CHARGE_INTENT",
        )

    async def test_unknown_external_switch_reserves_possible_parallel_slot(self):
        rt, sources, services = rig()
        rt.configuration["chargers"].append({
            "id": "other", "name": "Another charger", "kind": "on_off",
            "rated_power_kw": 1.0, "asset": "car",
            "power_entity": "sensor.other_power",
            "control_entity": "switch.other",
            "control_owner": "external",
        })
        sources["sensor.other_power"] = state(0, "W")
        outcome = await rt.executor.execute("evse", "start")
        self.assertEqual(outcome["reason"], "MAX_PARALLEL_REACHED")
        self.assertEqual(services.calls, [])

    async def test_zero_demand_and_only_relevant_phase_constraints_block_start(self):
        rt, _, services = rig()
        rt.configuration["assets"][0]["requested_kwh"] = 0
        self.assertEqual(
            (await rt.executor.execute("evse", "start"))["reason"],
            "TARGET_ALREADY_MET",
        )
        rt, _, services = rig()
        rt.configuration["chargers"][0].pop("phase_count")
        rt.configuration["controller"]["phase_limits_a"] = {"L1": 16}
        self.assertEqual(
            (await rt.executor.execute("evse", "start"))["reason"],
            "PHYSICAL_PHASES_UNVERIFIED",
        )
        self.assertFalse(services.calls)
        rt.configuration["controller"].pop("phase_limits_a")
        self.assertEqual((await rt.executor.execute("evse", "start"))["status"],
                         "confirmed")
        self.assertEqual((await rt.executor.execute("evse", "stop"))["status"],
                         "confirmed")

    async def test_mode_off_physically_stops_a_qualified_active_switch(self):
        rt, states, services = rig(mode="Off")
        states["switch.evse_control"].state = "on"
        states["sensor.actual_power"].state = "1600"
        await rt.executor.supervise()
        self.assertEqual([c[1] for c in services.calls], ["turn_off"])
        self.assertEqual(rt.executor.snapshot()["evse"]["status"], "confirmed")
        self.assertEqual(states["sensor.actual_power"].state, "0")

    async def test_unowned_charger_is_stopped_after_restart_even_if_limits_good(self):
        rt, states, services = rig(mode="Force Charge")
        states["switch.evse_control"].state = "on"
        states["sensor.actual_power"].state = "1600"
        await rt.executor.supervise()
        self.assertEqual([c[1] for c in services.calls], ["turn_off"])

    async def test_missing_binding_forces_real_stop_not_unlimited_fallback(self):
        rt, states, services = rig(mode="Force Charge")
        rt.configuration["controller"]["binding_entity"] = "sensor.expired"
        states["switch.evse_control"].state = "on"
        states["sensor.actual_power"].state = "1600"
        await rt.executor.supervise()
        self.assertEqual([x[1] for x in services.calls], ["turn_off"])
        self.assertEqual(rt.executor.snapshot()["evse"]["status"], "confirmed")

    async def test_protective_site_limit_includes_external_charger(self):
        rt, states, services = rig(mode="Force Charge", group_kw=3.0)
        rt.configuration["chargers"].append({
            "id": "other", "name": "External", "kind": "on_off",
            "rated_power_kw": 2.0, "power_entity": "sensor.other",
            "control_entity": "switch.other", "control_owner": "external",
        })
        states["switch.other"] = state("on")
        states["sensor.other"] = state(1500, "W")
        states["switch.evse_control"].state = "on"
        states["sensor.actual_power"].state = "1600"
        await rt.executor.supervise()
        self.assertEqual([x[1] for x in services.calls], ["turn_off"])
        self.assertEqual(rt.executor.snapshot()["evse"]["status"], "confirmed")

    async def test_no_protective_action_for_externally_owned_charger(self):
        rt, states, services = rig(owner="external", commissioned=False, mode="Off")
        states["switch.evse_control"].state = "on"
        states["sensor.actual_power"].state = "1600"
        await rt.executor.supervise()
        self.assertEqual(services.calls, [])

    async def test_measured_energy_target_stops_only_from_real_meter_delta(self):
        rt, sources, services = rig()
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        self.assertEqual(rt.executor.session_snapshot()["evse"]["starting_energy_kwh"], 5)
        sources["sensor.meter"].state = "5.4"
        sources["sensor.meter"].last_updated = datetime.now(timezone.utc)
        await rt.executor.supervise()
        self.assertEqual(len(services.calls), 1)
        self.assertEqual(rt.executor.session_snapshot()["evse"]["actual_energy_kwh"], 0.4)
        sources["sensor.meter"].state = "6.02"
        sources["sensor.meter"].last_updated = datetime.now(timezone.utc)
        await rt.executor.supervise()
        self.assertEqual([c[1] for c in services.calls], ["turn_on", "turn_off"])
        self.assertEqual(rt.executor.session_snapshot(), {})

    async def test_session_energy_meter_lost_causes_real_stop(self):
        rt, sources, services = rig()
        await rt.executor.execute("evse", "start")
        sources["sensor.meter"].state = "unavailable"
        await rt.executor.supervise()
        self.assertEqual([c[1] for c in services.calls], ["turn_on", "turn_off"])

    async def test_missing_energy_meter_rejects_real_start(self):
        rt, _, services = rig()
        rt.configuration["chargers"][0].pop("energy_entity")
        outcome = await rt.executor.execute("evse", "start")
        self.assertEqual(outcome["status"], "rejected")
        self.assertEqual(outcome["reason"], "MEASURED_ENERGY_METER_REQUIRED")
        self.assertEqual(services.calls, [])

    async def test_manual_duration_hard_stop_closes_real_session(self):
        rt, sources, services = rig()
        rt.configuration["assets"][0].pop("requested_kwh")
        rt.configuration["assets"][0]["requested_duration_minutes"] = 1
        first = await rt.executor.execute("evse", "start")
        self.assertEqual(first["status"], "confirmed")
        rt.executor._sessions["evse"]["started_at"] -= timedelta(minutes=2)
        await rt.executor.supervise()
        self.assertEqual([c[1] for c in services.calls], ["turn_on", "turn_off"])

    async def test_manual_soc_target_stops_from_qualified_soc_source(self):
        rt, sources, services = rig()
        asset = rt.configuration["assets"][0]
        asset.pop("requested_kwh")
        asset.update({"soc_entity": "sensor.battery", "target_soc": 75,
                      "capacity_kwh": 20, "charge_efficiency": 0.9})
        sources["sensor.battery"] = state(50, "%")
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        sources["sensor.battery"].state = "76"
        sources["sensor.battery"].last_updated = datetime.now(timezone.utc)
        await rt.executor.supervise()
        self.assertEqual([c[1] for c in services.calls], ["turn_on", "turn_off"])

    async def test_switching_from_manual_to_other_mode_physically_stops(self):
        rt, _, services = rig()
        first = await rt.executor.execute("evse", "start")
        self.assertEqual(first["status"], "confirmed")
        rt.configuration["controller"]["mode"] = "Economy"
        await rt.executor.supervise()
        self.assertEqual([c[1] for c in services.calls], ["turn_on", "turn_off"])

    async def test_unload_calls_real_stop_and_requires_observed_zero(self):
        rt, _, services = rig()
        started = await rt.executor.execute("evse", "start")
        self.assertEqual(started["status"], "confirmed")
        result = await rt.executor.shutdown()
        self.assertTrue(result)
        self.assertEqual([x[1] for x in services.calls], ["turn_on", "turn_off"])
        self.assertEqual(rt.executor.snapshot()["evse"]["status"], "confirmed")

    async def test_unload_refuses_unknown_physical_switch_state(self):
        rt, states, services = rig()
        states["switch.evse_control"].state = "unavailable"
        result = await rt.executor.shutdown()
        self.assertFalse(result)
        self.assertEqual(services.calls, [])

    async def test_unload_does_not_touch_native_external_owner(self):
        rt, states, services = rig(owner="external", commissioned=False)
        states["switch.evse_control"].state = "on"
        result = await rt.executor.shutdown()
        self.assertTrue(result)
        self.assertEqual(services.calls, [])

    async def test_unload_never_allows_new_commands(self):
        rt, _, services = rig()
        rt.stop()
        result = await rt.executor.execute("evse", "start")
        self.assertEqual(result["reason"], "INTEGRATION_UNLOADED")
        self.assertEqual(services.calls, [])

    async def test_unknown_charger_is_rejected_not_accepted(self):
        rt, _, services = rig()
        result = await rt.executor.execute("missing", "start")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "UNKNOWN_CHARGER")
        self.assertEqual(services.calls, [])


if __name__ == "__main__":
    unittest.main()
