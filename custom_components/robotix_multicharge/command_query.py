"""Admin-only native Home Assistant command endpoint for real physical charging.

No commands are issued by plan reads or installation. Manual commands require
HA-admin authority; the separate qualified quarter callback may admit its own
planned execution through the same serialized and physically verified writer.
"""
from __future__ import annotations

import voluptuous as vol
from datetime import datetime, timezone

from .configuration import (
    apply_settings_change, configuration_revision,
    is_plan_presentation_only_change,
)
from .source_evidence import number
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "robotix_multicharge/command",
    vol.Required("charger_id"): str,
    vol.Required("action"): vol.In(("start", "stop", "set_current")),
    vol.Optional("current_a"): vol.Coerce(float),
    vol.Optional("request_id"): str,
})
@websocket_api.async_response
async def websocket_charge_command(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """HA-admin-authorized service command, with explicit observed result."""
    runtimes = tuple(hass.data.get(DOMAIN, {}).values())
    if len(runtimes) != 1:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND,
            "Exactly one active ChargeController is required"
        )
        return
    result = await runtimes[0].executor.execute(
        msg["charger_id"], msg["action"],
        request_id=msg.get("request_id"), context=connection.context(msg),
        current_a=msg.get("current_a")
    )
    connection.send_result(msg["id"], result)


def register_command_query(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, websocket_charge_command)


async def apply_native_preference(hass, entry, runtime, scope, target_id, changes,
                                  *, expected_revision=None, action="save"):
    """Single native settings writer for HA entities and admin WebSocket.

    Under the physical executor lock, validate the one Config Entry source and
    never reload a working EVSE for a visual-only preference.
    """
    if (entry is None or entry.source == "import"
            or entry.data.get("source") == "yaml"):
        raise ValueError("readonly_import_configuration")
    async with runtime.executor._lock:
        if expected_revision is not None and (
                expected_revision != configuration_revision(runtime.configuration)):
            raise ValueError("stale_settings")
        updated = apply_settings_change(
            runtime.configuration, scope, target_id, changes, action,
        )
        if not is_plan_presentation_only_change(runtime.configuration, updated):
            # A charger assignment changes both its own command boundary and
            # the former charger's assignment. Other active chargers are safe.
            if scope == "charger" and set(changes) <= {"asset"}:
                affected = {target_id}
                selected = changes.get("asset")
                affected.update(
                    c["id"] for c in runtime.configuration["chargers"]
                    if c.get("asset") == selected and selected
                )
                candidates = [
                    c for c in runtime.configuration["chargers"]
                    if c["id"] in affected
                ]
            else:
                candidates = runtime.configuration["chargers"]
            for charger in candidates:
                if (charger.get("control_owner") != "multicharge"
                        or charger.get("physical_commissioned") is not True):
                    continue
                observed = runtime.executor._switch(
                    hass, charger.get("control_entity")
                )
                power = number(
                    hass, charger.get("power_entity"), "power",
                    datetime.now(timezone.utc)
                )
                if (observed is None or observed.state != "off"
                        or power.quality != "ok" or power.value > 0.05):
                    raise ValueError("charger_busy")
        expected = configuration_revision(updated)
        runtime.record_settings_action(
            scope, target_id, action, changes, expected,
        )
        if not await runtime.persist_control_state():
            raise ValueError("settings_not_saved")
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, "configuration": updated},
        )
        return expected


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "robotix_multicharge/update_settings",
    vol.Required("scope"): vol.In(("controller", "asset", "charger")),
    vol.Required("target_id"): str,
    vol.Required("changes"): dict,
    vol.Required("expected_revision"): str,
    vol.Optional("action"): vol.In(("save", "create", "delete")),
})
@websocket_api.async_response
async def websocket_update_settings(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Validate a narrow preference update, never a physical commissioning change.

    Config Entry reload, not this reply, is the authoritative new settings readback.
    """
    rows = tuple(hass.data.get(DOMAIN, {}).items())
    if len(rows) != 1:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "Exactly one configured Controller required")
        return
    entry_id, runtime = rows[0]
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.data.get("source") == "yaml":
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              "YAML-owned configuration is edited through YAML")
        return
    try:
        next_revision = await apply_native_preference(
            hass, entry, runtime, msg["scope"], msg["target_id"],
            msg["changes"], expected_revision=msg["expected_revision"],
            action=msg.get("action", "save"),
        )
    except (ValueError, TypeError, KeyError):
        runtime.record_settings_action(
            msg["scope"], msg["target_id"], msg.get("action", "save"),
            msg["changes"], configuration_revision(runtime.configuration),
            status="rejected", reason="SETTINGS_VALIDATION_OR_SAFETY_HOLD",
        )
        if not await runtime.persist_control_state():
            runtime._settings_action["reason"] = "SETTINGS_AUDIT_PERSISTENCE_UNAVAILABLE"
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              "Settings rejected; verify fields, permissions and charging state")
        return
    connection.send_result(msg["id"], {
        "status": "accepted_unconfirmed",
        "expected_revision": next_revision,
        "reason": "Native Config Entry reload pending; refresh for verified settings",
    })


def register_settings_query(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, websocket_update_settings)
