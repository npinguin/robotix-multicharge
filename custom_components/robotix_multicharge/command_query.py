"""Admin-only native Home Assistant command endpoint for real physical charging.

No commands are issued by plan reads or installation. Manual commands require
HA-admin authority; the separate qualified quarter callback may admit its own
planned execution through the same serialized and physically verified writer.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import voluptuous as vol

from .configuration import (
    apply_settings_change, apply_dashboard_structure, configuration_revision,
    assert_expert_authority_change, validate_configuration, effective_configuration,
)
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "robotix_multicharge/command",
    vol.Required("charger_id"): str,
    vol.Required("action"): vol.In(("start", "stop", "set_current", "pause", "resume")),
    vol.Optional("current_a"): vol.Coerce(float),
    vol.Optional("energy_kwh"): vol.Coerce(float),
    vol.Optional("duration_minutes"): vol.Coerce(int),
    vol.Optional("cost_amount"): vol.Coerce(float),
    vol.Optional("currency"): str,
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
    manual_request = {
        key: msg[key] for key in ("energy_kwh", "duration_minutes",
                                 "cost_amount", "currency")
        if key in msg
    }
    if manual_request and msg["action"] != "start":
        connection.send_error(
            msg["id"], websocket_api.ERR_INVALID_FORMAT,
            "One-off energy/duration/budget is valid only for manual START",
        )
        return
    result = await runtimes[0].executor.execute(
        msg["charger_id"], msg["action"],
        request_id=msg.get("request_id"), context=connection.context(msg),
        current_a=msg.get("current_a"), manual_request=manual_request or None,
    )
    connection.send_result(msg["id"], result)


def register_command_query(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, websocket_charge_command)


async def require_native_admin(hass, context):
    """Only actual HA administrators may edit domain-owned native settings.

    Entity-service contexts originate in Home Assistant, never from the
    browser's client-side role claims. Automated/system calls without an
    authenticated user must use an explicitly authorized Config Flow instead.
    """
    actor = getattr(context, "user_id", None)
    user = await hass.auth.async_get_user(actor) if actor else None
    if user is None or not user.is_admin:
        raise RuntimeError("MultiCharge settings require a Home Assistant administrator")


async def apply_native_preference(hass, entry, runtime, scope, target_id, changes,
                                  *, expected_revision=None, action="save",
                                  structural=False):
    """Single native settings writer for HA entities and dashboard.

    Under the physical executor lock, validate the one Config Entry source and
    never reload a working EVSE for a visual-only preference.
    """
    if (entry is None or entry.source == "import"
            or entry.data.get("source") in ("yaml", "json")):
        raise ValueError("readonly_import_configuration")
    async with runtime.executor._lock:
        committed = effective_configuration(entry)
        if (not runtime.active or committed != runtime.configuration
                or (expected_revision is not None and
                    expected_revision != configuration_revision(committed))):
            raise ValueError("stale_settings")
        if "ready_by_local" in changes:
            # Transport-only wall clock; persist the existing aware anchor.
            if scope != "asset" or action != "save" or "ready_by" in changes:
                raise ValueError("invalid_schedule")
            changes = dict(changes)
            local = changes.pop("ready_by_local")
            wall = datetime.fromisoformat(local)
            if wall.tzinfo is not None:
                raise ValueError("invalid_schedule")
            zone = ZoneInfo(hass.config.time_zone)
            first, second = wall.replace(tzinfo=zone, fold=0), wall.replace(tzinfo=zone, fold=1)
            if first.utcoffset() != second.utcoffset():
                raise ValueError("deadline_dst_unresolved")
            changes["ready_by"] = first.isoformat()
        updated = (
            apply_dashboard_structure(
                runtime.configuration, scope, target_id, changes, action,
                site_time_zone=hass.config.time_zone,
            ) if structural else apply_settings_change(
                runtime.configuration, scope, target_id, changes, action,
                site_time_zone=hass.config.time_zone,
            )
        )
        from .config_flow import _assert_safe_yaml_ui_commit
        _assert_safe_yaml_ui_commit(runtime, updated)
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
    vol.Optional("structural", default=False): bool,
})
@websocket_api.async_response
async def websocket_update_settings(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Validate an ordinary settings update, including explicit Charger activation.

    Config Entry reload, not this reply, is the authoritative new settings readback.
    """
    rows = tuple(hass.data.get(DOMAIN, {}).items())
    if len(rows) != 1:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "Exactly one configured Controller required")
        return
    entry_id, runtime = rows[0]
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.data.get("source") in ("yaml", "json"):
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              "Expert-managed configuration is edited in its JSON/YAML source")
        return
    try:
        next_revision = await apply_native_preference(
            hass, entry, runtime, msg["scope"], msg["target_id"],
            msg["changes"], expected_revision=msg["expected_revision"],
            action=msg.get("action", "save"),
            structural=msg.get("structural", False),
        )
    except (ValueError, TypeError, KeyError) as exc:
        # Give the admin an actionable *bounded* reason, never raw source
        # entity IDs or internal exceptions. Physical authority is unchanged.
        code = {
            "charger_busy": "CHARGER_BUSY_STOP_FIRST",
            "charger_occupied": "CHARGER_HAS_OTHER_ASSET",
            "stale_settings": "STALE_SETTINGS_REFRESH",
        }.get(str(exc).split(":", 1)[0], "SETTINGS_REJECTED")
        runtime.record_settings_action(
            msg["scope"], msg["target_id"], msg.get("action", "save"),
            msg["changes"], configuration_revision(runtime.configuration),
            status="rejected", reason=code,
        )
        if not await runtime.persist_control_state():
            runtime._settings_action["reason"] = "SETTINGS_AUDIT_PERSISTENCE_UNAVAILABLE"
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              code)
        return
    connection.send_result(msg["id"], {
        "status": "accepted_unconfirmed",
        "expected_revision": next_revision,
        "reason": "Native Config Entry reload pending; refresh for verified settings",
    })



@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "robotix_multicharge/yaml_configuration",
    # Recognize the retired Review protocol only to return explicit upgrade
    # guidance; no legacy review or save is executed.
    vol.Optional("operation"): str,
    vol.Optional("reviewed_revision"): str,
    vol.Required("expected_revision"): str,
    vol.Required("yaml_text"): str,
})
@websocket_api.async_response
async def websocket_yaml_configuration(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict,
) -> None:
    """Save a complete mapping into the existing, guarded Home Assistant Config Entry.

    JSON (YAML-compatible) is only a transient text presentation. No file,
    separate state store, physical command or HA Options Flow is created.
    """
    if "operation" in msg or "reviewed_revision" in msg:
        connection.send_error(
            msg["id"], websocket_api.ERR_INVALID_FORMAT,
            "FRONTEND_VERSION_MISMATCH: reload Home Assistant in a new tab; "
            "this editor uses the retired Review protocol. Your configuration is unchanged.",
        )
        return
    rows = tuple(hass.data.get(DOMAIN, {}).items())
    if len(rows) != 1:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "NO_ACTIVE_CHARGE_CONTROLLER")
        return
    entry_id, runtime = rows[0]
    entry = hass.config_entries.async_get_entry(entry_id)
    if (entry is None or entry.source == "import"
            or entry.data.get("source") in ("yaml", "json")):
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              "FILE_OWNED_CONFIG_READONLY")
        return

    from .config_flow import (
        _parse_editor_yaml, _assert_safe_yaml_ui_commit,
    )

    try:
        # Parsing and schema validation are side-effect free, and bounded.
        proposed = validate_configuration(_parse_editor_yaml(msg["yaml_text"]))
        if proposed["controller"]["id"] != runtime.configuration["controller"]["id"]:
            raise ValueError("CONTROLLER_ID_IMMUTABLE")
        assert_expert_authority_change(runtime.configuration, proposed)

        # No review token or second UI step: validate once, then commit
        # under the original executor lock and authoritative revision.
        async with runtime.executor._lock:
            committed = effective_configuration(entry)
            if (not runtime.active or committed != runtime.configuration
                    or configuration_revision(committed) != msg["expected_revision"]):
                raise ValueError("STALE_SETTINGS_REFRESH")
            _assert_safe_yaml_ui_commit(runtime, proposed)
            desired_revision = configuration_revision(proposed)
            runtime.record_settings_action(
                "controller", proposed["controller"]["id"],
                "yaml_save",
                {"format": "yaml"},
                desired_revision,
            )
            if not await runtime.persist_control_state():
                raise ValueError("SETTINGS_AUDIT_PERSISTENCE_UNAVAILABLE")
            hass.config_entries.async_update_entry(
                entry, options={**entry.options, "configuration": proposed},
            )
        connection.send_result(msg["id"], {
            "status": "accepted_unconfirmed",
            "expected_revision": desired_revision,
            "reason": "Authoritative Config Entry readback required",
        })
    except (ValueError, TypeError, KeyError) as exc:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              str(exc)[:4096])



def register_settings_query(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, websocket_update_settings)
    websocket_api.async_register_command(hass, websocket_yaml_configuration)
