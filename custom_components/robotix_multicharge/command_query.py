"""Admin-only native Home Assistant command endpoint for real physical charging.

No commands are issued by plan reads or installation. Manual commands require
HA-admin authority; the separate qualified quarter callback may admit its own
planned execution through the same serialized and physically verified writer.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import uuid4

import voluptuous as vol

from .configuration import (
    apply_settings_change, apply_dashboard_structure, configuration_revision,
    assert_expert_authority_change, validate_configuration, effective_configuration,
    apply_new_import_defaults,
)
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "robotix_multicharge/command",
    vol.Required("charger_id"): str,
    vol.Required("action"): vol.In(("start", "stop", "set_current", "pause", "resume", "manual_start", "manual_stop", "auto")),
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
    if manual_request and msg["action"] not in ("start", "manual_start"):
        connection.send_error(
            msg["id"], websocket_api.ERR_INVALID_FORMAT,
            "One-off energy/duration/budget is valid only for manual START",
        )
        return
    try:
        result = await runtimes[0].executor.execute(
            msg["charger_id"], msg["action"],
            request_id=msg.get("request_id", uuid4().hex), context=connection.context(msg),
            current_a=msg.get("current_a"), manual_request=manual_request or None,
        )
    except ValueError as exc:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc))
        return
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


async def commit_ui_configuration_locked(hass, entry, runtime, updated, *,
                                         expected_revision, scope, target_id,
                                         action, changes):
    """One guarded revision, durable receipt and Config Entry write.

    Caller holds the existing executor lock. Native Options Flow, native
    entities, typed UI and expert text use this same commit boundary.
    """
    if (entry is None or entry.source == "import"
            or entry.data.get("source") in ("yaml", "json")):
        raise ValueError("readonly_import_configuration")
    committed = effective_configuration(entry)
    if configuration_revision(committed) != expected_revision:
        raise ValueError("stale_settings")
    updated = validate_configuration(updated)
    expected = configuration_revision(updated)
    from .config_flow import _assert_safe_yaml_ui_commit
    from .configuration import charger_is_active
    if runtime is None:
        # The Options Flow may edit an entirely external configuration before
        # its runtime loads. No runtime receipt or physical command is claimed.
        if any(charger_is_active(row) for row in (*committed["chargers"], *updated["chargers"])):
            raise ValueError("EXPERT_IMPORT_REQUIRES_RECONCILED_CONTROL_STATE")
        if hass.data.get(DOMAIN, {}).get(entry.entry_id) is not None:
            raise ValueError("stale_settings")
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, "configuration": updated},
        )
        return expected
    if not runtime.active or committed != runtime.configuration:
        raise ValueError("stale_settings")
    _assert_safe_yaml_ui_commit(runtime, updated)
    receipt = runtime.record_settings_action(
        scope, target_id, action, changes, expected, publish=False,
    )
    if not await runtime.persist_control_state(settings_action=receipt):
        raise ValueError("settings_not_saved")
    try:
        # A native provider, an external Config Entry owner or a safety
        # event can change while the Store write awaits. Recheck the SAME
        # revision and live guard immediately before the synchronous commit.
        if (not runtime.active or effective_configuration(entry) != committed
                or runtime.configuration != committed):
            raise ValueError("stale_settings")
        _assert_safe_yaml_ui_commit(runtime, updated)
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, "configuration": updated},
        )
        if effective_configuration(entry) != updated:
            raise ValueError("settings_not_saved")
    except (ValueError, RuntimeError, TypeError, KeyError) as exc:
        runtime._settings_action = {**receipt, "status": "rejected",
                                    "reason": "SETTINGS_COMMIT_REJECTED"}
        runtime.notify()
        await runtime.persist_control_state()
        raise ValueError(str(exc)) from exc
    runtime._settings_action = receipt
    runtime.notify()
    return expected


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
            if changes.get("ready_by_repeat", "none") == "none" and first <= datetime.now(zone):
                raise ValueError("deadline_must_be_future")
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
        return await commit_ui_configuration_locked(
            hass, entry, runtime, updated,
            expected_revision=configuration_revision(committed),
            scope=scope, target_id=target_id, action=action, changes=changes,
        )


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
            "EXPERT_IMPORT_REQUIRES_VERIFIED_IDLE_CHARGERS": "STRUCTURAL_SAVE_REQUIRES_IDLE",
            "EXPERT_IMPORT_REQUIRES_RECONCILED_CONTROL_STATE": "SETTINGS_CONTROL_RECONCILIATION_REQUIRED",
            "settings_not_saved": "SETTINGS_PERSISTENCE_UNAVAILABLE",
            "charger charging power limits exceed hardware envelope": "CHARGER_POWER_ENVELOPE_INVALID",
            "charger power envelope has no supported current step": "CHARGER_POWER_STEP_INVALID",
            "charger.voltage_v": "CHARGER_VOLTAGE_INVALID",
            "charger.phase_count": "CHARGER_PHASE_COUNT_INVALID",
            "charger.phase_ids": "CHARGER_PHASE_MAPPING_INVALID",
            "dedicated assignment requires the selected permanent asset and connection source": "DEDICATED_ASSIGNMENT_INVALID",
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

    from .config_flow import _parse_editor_yaml

    try:
        # Parsing and schema validation are side-effect free, and bounded.
        document = _parse_editor_yaml(msg["yaml_text"])
        proposed = apply_new_import_defaults(
            runtime.configuration, validate_configuration(document),
            site_time_zone=hass.config.time_zone, raw_assets=document.get("assets", []),
        )
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
            desired_revision = await commit_ui_configuration_locked(
                hass, entry, runtime, proposed,
                expected_revision=msg["expected_revision"],
                scope="controller", target_id=proposed["controller"]["id"],
                action="yaml_save", changes={"format": "yaml"},
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
