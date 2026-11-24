"""Admin-only native Home Assistant command endpoint for real physical charging.

No commands are issued by plan reads or installation. Manual commands require
HA-admin authority; the separate qualified quarter callback may admit its own
planned execution through the same serialized and physically verified writer.
"""
from __future__ import annotations

import voluptuous as vol
from copy import deepcopy
from datetime import datetime, timezone

from .configuration import (
    apply_settings_change, apply_dashboard_structure, configuration_revision,
    is_plan_presentation_only_change, is_in_place_runtime_preference_change,
    validate_configuration,
)
from .source_evidence import number
from .execution import stop_power_limit
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
        if expected_revision is not None and (
                expected_revision != configuration_revision(runtime.configuration)):
            raise ValueError("stale_settings")
        updated = (
            apply_dashboard_structure(
                runtime.configuration, scope, target_id, changes, action,
            ) if structural else apply_settings_change(
                runtime.configuration, scope, target_id, changes, action,
            )
        )
        if structural:
            # A selected-vehicle change requires real idle/power evidence even
            # though it is an in-place preference without HA platform reload.
            # Never silently reassign an occupied external Charger.
            rebind = scope == "charger" and "asset" in changes
            if rebind or not (
                is_plan_presentation_only_change(runtime.configuration, updated)
                or is_in_place_runtime_preference_change(
                    runtime.configuration, updated)
            ):
                from .config_flow import _assert_safe_yaml_ui_commit
                _assert_safe_yaml_ui_commit(runtime, updated)
        elif not is_plan_presentation_only_change(runtime.configuration, updated):
            # A charger assignment changes both its own command boundary and
            # the former charger's assignment. Other active chargers are safe.
            atomic_guest_assignment = (
                scope == "asset" and action == "create"
                and changes.get("assign_charger_id") is not None
            )
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
                rebind = (
                    (scope == "charger" and set(changes) <= {"asset"})
                    or (atomic_guest_assignment
                        and charger["id"] == changes["assign_charger_id"])
                )
                owned = (charger.get("control_owner") == "multicharge"
                         and charger.get("physical_commissioned") is True)
                if not rebind and not owned:
                    continue
                # A remembered assignment is not an active connection identity.
                # Never move an in-flight or unclosed physical session.
                if rebind and (charger["id"] in runtime.executor._sessions
                               or charger["id"] in runtime.executor._start_pending):
                    raise ValueError("charger_busy")
                observed = runtime.executor._switch(
                    hass, charger.get("control_entity")
                )
                power = number(
                    hass, charger.get("power_entity"), "power",
                    datetime.now(timezone.utc)
                )
                # For an idle-only rebind even an external-owned charger needs
                # physical power evidence: unobserved is not safely idle.
                if (power.quality != "ok"
                        or power.value > stop_power_limit(charger)
                        or (observed is not None and observed.state != "off")
                        or (owned and observed is None)):
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
    vol.Optional("structural", default=False): bool,
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
        }.get(str(exc), "SETTINGS_REJECTED")
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
    vol.Required("type"): "robotix_multicharge/dashboard_config",
    vol.Required("operation"): vol.In(("commission",)),
    vol.Required("expected_revision"): str,
    vol.Required("charger_id"): str,
    vol.Required("commission"): bool,
    vol.Optional("exclusive_writer_confirmed", default=False): bool,
    vol.Optional("electrical_limits_confirmed", default=False): bool,
})
@websocket_api.async_response
async def websocket_dashboard_config(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict,
) -> None:
    """Dashboard-only guarded physical commissioning, never free-text config.

    All ordinary/structural object settings use update_settings above.
    This narrowly allowed command changes ownership without issuing a physical
    switch command and cannot run without independently observed idle proof.
    """
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
    try:
        baseline = configuration_revision(runtime.configuration)
        if baseline != msg["expected_revision"]:
            raise ValueError("STALE_SETTINGS_REFRESH")
        desired = msg["commission"]
        if desired and (msg.get("exclusive_writer_confirmed") is not True
                        or msg.get("electrical_limits_confirmed") is not True):
            raise ValueError("COMMISSION_CHECKLIST_REQUIRED")
        async with runtime.executor._lock:
            if configuration_revision(runtime.configuration) != baseline:
                raise ValueError("STALE_SETTINGS_REFRESH")
            updated = deepcopy(runtime.configuration)
            charger = next(
                (c for c in updated["chargers"] if c["id"] == msg["charger_id"]),
                None,
            )
            if charger is None:
                raise ValueError("UNKNOWN_CHARGER")
            charger["control_owner"] = "multicharge" if desired else "external"
            charger["physical_commissioned"] = desired
            updated = validate_configuration(updated)
            from .config_flow import _assert_safe_expert_import
            _assert_safe_expert_import(runtime, updated, source_changed=True)
            if (charger["id"] in runtime.executor._sessions
                    or charger["id"] in runtime.executor._start_pending):
                raise ValueError("CHARGER_BUSY_STOP_FIRST")
            current = next(c for c in runtime.configuration["chargers"]
                           if c["id"] == charger["id"])
            observed = runtime.executor._switch(
                hass, current.get("control_entity"),
            )
            measured = number(
                hass, current.get("power_entity"), "power",
                datetime.now(timezone.utc),
            )
            if (observed is None or observed.state != "off"
                    or measured.quality != "ok"
                    or measured.value > stop_power_limit(current)):
                raise ValueError("COMMISSION_REQUIRES_VERIFIED_IDLE")
            revision = configuration_revision(updated)
            runtime.record_settings_action(
                "charger", charger["id"], "dashboard_commission",
                {"commission": desired,
                 "exclusive_writer_confirmed": bool(
                     msg.get("exclusive_writer_confirmed")),
                 "electrical_limits_confirmed": bool(
                     msg.get("electrical_limits_confirmed"))},
                revision,
            )
            if not await runtime.persist_control_state():
                raise ValueError("SETTINGS_AUDIT_PERSISTENCE_UNAVAILABLE")
            hass.config_entries.async_update_entry(
                entry, options={**entry.options, "configuration": updated},
            )
        connection.send_result(msg["id"], {
            "status": "accepted_unconfirmed",
            "expected_revision": revision,
            "reason": "Read back the authoritative Config Entry after reload",
        })
    except (ValueError, KeyError, TypeError) as exc:
        connection.send_error(
            msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc)[:180],
        )



@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "robotix_multicharge/yaml_configuration",
    vol.Required("operation"): vol.In(("review", "save")),
    vol.Required("expected_revision"): str,
    vol.Required("yaml_text"): str,
    vol.Optional("reviewed_revision"): str,
})
@websocket_api.async_response
async def websocket_yaml_configuration(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict,
) -> None:
    """Review and commit a *single* Config Entry via the existing guarded owner.

    JSON (YAML-compatible) is only a transient text presentation. No file,
    separate state store, physical command or HA Options Flow is created.
    """
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
        _parse_editor_yaml, _yaml_review_summary, _assert_safe_yaml_ui_commit,
    )

    try:
        # Parsing and schema validation are side-effect free, and bounded.
        proposed = validate_configuration(_parse_editor_yaml(msg["yaml_text"]))
        if proposed["controller"]["id"] != runtime.configuration["controller"]["id"]:
            raise ValueError("CONTROLLER_ID_IMMUTABLE")
        # Commissioning / exclusive physical writer is only available through
        # the separate native owner-aware commissioning transaction. A text
        # import cannot silently activate a physical charger.
        existing = {c["id"]: c for c in runtime.configuration["chargers"]}
        for uid, former in existing.items():
            if (uid not in {c["id"] for c in proposed["chargers"]}
                    and (former.get("control_owner") == "multicharge"
                         or former.get("physical_commissioned") is True)):
                raise ValueError("COMMISSIONING_ONLY_IN_NATIVE_FLOW")
        for charger in proposed["chargers"]:
            former = existing.get(charger["id"], {})
            if (charger.get("control_owner", "external")
                    != former.get("control_owner", "external")
                    or charger.get("physical_commissioned", False)
                    != former.get("physical_commissioned", False)):
                raise ValueError("COMMISSIONING_ONLY_IN_NATIVE_FLOW")

        if msg["operation"] == "review":
            if configuration_revision(runtime.configuration) != msg["expected_revision"]:
                raise ValueError("STALE_SETTINGS_REFRESH")
            connection.send_result(msg["id"], {
                "status": "reviewed",
                "expected_revision": msg["expected_revision"],
                "proposed_revision": configuration_revision(proposed),
                "summary": _yaml_review_summary(runtime.configuration, proposed),
            })
            return

        if msg.get("reviewed_revision") != configuration_revision(proposed):
            raise ValueError("REVIEW_REQUIRED_OR_TEXT_CHANGED")

        # Save performs all validation again under the *same* executor lock
        # as native preferences. Stale reviews or changed physical states fail.
        async with runtime.executor._lock:
            if configuration_revision(runtime.configuration) != msg["expected_revision"]:
                raise ValueError("STALE_SETTINGS_REFRESH")
            _assert_safe_yaml_ui_commit(runtime, proposed)
            desired_revision = configuration_revision(proposed)
            runtime.record_settings_action(
                "controller", proposed["controller"]["id"],
                "yaml_reviewed_save",
                {"format": "yaml", "reviewed": True},
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
                              str(exc)[:180])



def register_settings_query(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, websocket_update_settings)
    websocket_api.async_register_command(hass, websocket_dashboard_config)
    websocket_api.async_register_command(hass, websocket_yaml_configuration)
