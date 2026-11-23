"""Admin-only native Home Assistant command endpoint for real physical charging.

No commands are issued by plan reads or installation. Manual commands require
HA-admin authority; the separate qualified quarter callback may admit its own
planned execution through the same serialized and physically verified writer.
"""
from __future__ import annotations

import voluptuous as vol
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json

from .configuration import (
    apply_settings_change, apply_dashboard_structure, configuration_revision,
    is_plan_presentation_only_change, is_in_place_runtime_preference_change,
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
            # Reuse the very same guarded structural safety contract as native
            # Options, no new physical writer or readback rules.
            if not (
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



def _strict_dashboard_json(document: str) -> dict:
    """Parse bounded JSON-only input with duplicate and NaN refusal."""
    if (not isinstance(document, str) or not document.strip()
            or len(document.encode("utf-8")) > 131072):
        raise ValueError("JSON_REQUIRED_128K_LIMIT")

    def unique(pairs):
        mapping = {}
        for key, value in pairs:
            if key in mapping:
                raise ValueError("DUPLICATE_JSON_KEY")
            mapping[key] = value
        return mapping

    def invalid_constant(_value):
        raise ValueError("NON_FINITE_JSON_VALUE")

    try:
        parsed = json.loads(
            document, object_pairs_hook=unique, parse_constant=invalid_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("INVALID_JSON_SYNTAX") from exc
    if not isinstance(parsed, dict):
        raise ValueError("JSON_OBJECT_REQUIRED")
    return parsed


def _dashboard_candidate(current: dict, document: str, mode: str) -> dict:
    if mode not in ("replace", "merge"):
        raise ValueError("INVALID_JSON_MODE")
    return prepare_expert_yaml_revision(
        current, _strict_dashboard_json(document), mode,
    )


def _dashboard_review(current: dict, candidate: dict, mode: str) -> dict:
    """One deterministic preview fingerprint; no duplicate draft store."""
    from .config_flow import _yaml_review_summary
    fields = sorted(
        k for k in set(current["controller"]) | set(candidate["controller"])
        if current["controller"].get(k) != candidate["controller"].get(k)
    )
    groups = {}
    for group in ("assets", "chargers"):
        old = {item["id"]: item for item in current[group]}
        new = {item["id"]: item for item in candidate[group]}
        groups[group] = {
            "add": sorted(new.keys() - old.keys()),
            "remove": sorted(old.keys() - new.keys()),
            "modify": sorted(
                uid for uid in new.keys() & old.keys() if new[uid] != old[uid]
            ),
            "total": len(new),
        }
    baseline = configuration_revision(current)
    updated = configuration_revision(candidate)
    fingerprint = sha256(f"{baseline}|{mode}|{updated}".encode()).hexdigest()
    return {
        "baseline_revision": baseline,
        "expected_revision": updated,
        "review_fingerprint": fingerprint,
        "summary": _yaml_review_summary(current, candidate),
        "controller_changed": fields,
        "groups": groups,
        "changes_present": current != candidate,
        "mode": mode,
    }


def register_settings_query(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, websocket_update_settings)
