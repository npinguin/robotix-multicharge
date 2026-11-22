"""Real executor source tests against recording HA state/service contract.

These execute the actual production NativeSwitchExecutor, including its
async_call and fresh power-readback path; no simulated production actuator.
Target HA installation and hardware acceptance are separate requirements.
"""
from __future__ import annotations

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
        if self.reconcile_observations:
            entity = data["entity_id"]
            self.sources[entity].state = "on" if service == "turn_on" else "off"
            self.sources[entity].last_updated = datetime.now(timezone.utc)
            self.sources["sensor.actual_power"].state = (
                "1600" if service == "turn_on" else "0"
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
                      "rated_power_kw": 2.0, "asset": "car",
                      "control_entity": "switch.evse_control",
                      "power_entity": "sensor.actual_power",
                      "connected_entity": "binary_sensor.cable",
                      "control_owner": owner,
                      "physical_commissioned": commissioned}],
    }
    cfg = validate_configuration(cfg)
    sources = {
        "switch.evse_control": state("off"),
        "sensor.actual_power": state(0, "W"),
        "binary_sensor.cable": state("on"),
    }
    services = NativeServices(sources)
    hass = SimpleNamespace(
        states=SimpleNamespace(get=sources.get),
        services=services,
        config=SimpleNamespace(time_zone="Europe/Brussels"),
    )
    runtime = MultiChargeRuntime(hass, cfg)
    runtime.refresh()
    return runtime, sources, services


class PhysicalNativeExecutorTests(unittest.IsolatedAsyncioTestCase):
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
            "PHYSICAL_COMMISSIONING_REQUIRED",
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
        self.assertEqual(len(services.calls), 1)

    async def test_timeout_does_not_forge_success_and_quarantines_start(self):
        rt, _, services = rig()
        services.reconcile_observations = False
        result = await rt.executor.execute("evse", "start", readback_seconds=0.015)
        self.assertEqual(result["status"], "execution_unknown")
        self.assertEqual(result["reason"], "PHYSICAL_READBACK_TIMEOUT")
        self.assertIsNone(result["readback_at"])
        self.assertFalse(rt.executor.capabilities()["evse"]["start_allowed"])
        self.assertEqual(len(services.calls), 1)

    async def test_stop_does_not_claim_positive_command_with_old_power(self):
        rt, sources, services = rig()
        sources["switch.evse_control"].state = "on"
        sources["sensor.actual_power"].state = "1200"
        services.reconcile_observations = False
        result = await rt.executor.execute("evse", "stop", readback_seconds=0.015)
        self.assertEqual(result["status"], "execution_unknown")
        self.assertIsNone(result["readback_at"])
        self.assertEqual(services.calls[0][1], "turn_off")

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
