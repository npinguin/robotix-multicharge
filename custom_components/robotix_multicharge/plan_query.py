"""Authenticated resident-readable HA WebSocket 48h charge plan query."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN, NOMINAL_PHASE_COUNT, NOMINAL_PHASE_VOLTAGE_V
from .configuration import WEEKDAYS, forecast_tariff_source
from .history import read_actual_history


def charger_setup_projection(hass, registry, runtime, charger):
    """Propose same-device native roles and expose effective current bounds.

    No guessed entity names, no writes, and no automatic electrical limit changes.
    """
    from homeassistant.helpers import entity_registry as er

    anchor = registry.async_get(charger.get("control_entity") or "")
    device_id = anchor.device_id if anchor is not None else None
    candidates = {}
    if device_id is not None:
        for entry in er.async_entries_for_device(registry, device_id, include_disabled_entities=False):
            state = hass.states.get(entry.entity_id)
            if state is None:
                continue
            domain = entry.entity_id.split(".", 1)[0]
            unit = state.attributes.get("unit_of_measurement")
            device_class = state.attributes.get("device_class")
            role = None
            if domain == "sensor":
                if device_class == "power" and unit in ("W", "kW"):
                    role = "power_entity"
                elif device_class == "energy" and unit in ("Wh", "kWh"):
                    role = "energy_entity"
                elif device_class == "current" and unit == "A":
                    role = "current_readback_entity"
            elif domain == "binary_sensor" and device_class == "plug":
                role = "connected_entity"
            elif domain == "number" and unit == "A" and charger["kind"] == "variable_current":
                role = "current_control_entity"
            if role:
                candidates.setdefault(role, []).append(entry.entity_id)
    already_bound = {
        value for row in runtime.configuration["chargers"]
        for key, value in row.items() if key.endswith("_entity")
    }
    proposals = {
        field: ids[0] for field, ids in candidates.items()
        if not charger.get(field) and len(ids) == 1
        and ids[0] not in already_bound
    }
    effective = runtime.executor.effective_charger(charger)
    bounds = ("min_current_a", "max_current_a", "current_step_a")
    native = runtime.executor.effective_charger({
        key: value for key, value in charger.items() if key not in bounds
    })
    # Native Amp metadata is a live observation, not an implicit user override.
    # Topology defaults are editable proposals only; explicit Save declares wiring.
    if charger["kind"] == "variable_current":
        if effective.get("phase_count") is None:
            proposals["phase_count"] = NOMINAL_PHASE_COUNT
        if effective.get("voltage_v") is None:
            proposals["voltage_v"] = NOMINAL_PHASE_VOLTAGE_V
    return {
        "device_matched": device_id is not None,
        "candidates": {field: sorted(ids) for field, ids in candidates.items()},
        "proposed_missing": proposals,
        "configured_current": {field: charger.get(field) for field in bounds},
        "effective_current": {field: effective.get(field) for field in bounds},
        "native_current": {field: native.get(field) for field in bounds},
        "current_capability_reason": effective.get("_current_capability_reason"),
        "effective_electrical": {field: effective.get(field)
                                 for field in ("phase_count", "voltage_v")},
        "missing_electrical": [
            field for field in ("phase_count", "voltage_v")
            if charger["kind"] == "variable_current" and effective.get(field) is None
        ],
    }


@websocket_api.websocket_command({
    vol.Required("type"): "robotix_multicharge/get_plan",
    vol.Optional("controller_id"): str,
    vol.Optional("start"): str,
    vol.Optional("end"): str,
    vol.Optional("day"): vol.In(("today", "tomorrow", "both")),
    vol.Optional("charger_id"): str,
    vol.Optional("asset_id"): str,
    vol.Optional("include_history", default=True): bool,
    vol.Optional("discover_charger"): {vol.Required("control_entity"): str,
                                      vol.Required("kind"): vol.In(("on_off", "variable_current"))},
})
@websocket_api.async_response
async def websocket_get_plan(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Only qualified read-only plan data. Never accept a charger command."""
    configured = list(hass.data.get(DOMAIN, {}).items())
    selected = next(
        (
            (entry_id, row) for entry_id, row in configured
            if msg.get("controller_id") in (None, row.configuration["controller"]["id"])
        ), None,
    )
    if selected is None:
        # A configured but unloaded/reloading controller is not an install
        # failure. The frontend may retain its last read-only snapshot.
        reason = ("NO_CONFIG_ENTRY" if not hass.config_entries.async_entries(DOMAIN)
                  else "CONTROLLER_UNAVAILABLE")
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, reason)
        return
    try:
        if "day" in msg:
            if "start" in msg or "end" in msg:
                raise ValueError("day and explicit interval are mutually exclusive")
            local_tz = ZoneInfo(hass.config.time_zone)
            chosen = datetime.now(local_tz).date() + timedelta(
                days=1 if msg["day"] == "tomorrow" else 0
            )
            start = datetime.combine(chosen, time.min, local_tz)
            end = datetime.combine(chosen + timedelta(days=2 if msg["day"] == "both" else 1), time.min, local_tz)
        elif "start" in msg and "end" in msg:
            start = datetime.fromisoformat(msg["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(msg["end"].replace("Z", "+00:00"))
        else:
            raise ValueError("day or start/end required")
        entry_id, runtime = selected
        result = deepcopy(runtime.read_plan(
            start, end,
            charger_id=msg.get("charger_id"), asset_id=msg.get("asset_id"),
        ))
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(hass)
        cfg = result["configuration"]
        setup_snapshot = {row["id"]: charger_setup_projection(hass, registry, runtime, row)
                          for row in cfg["chargers"]}
        recent = runtime.executor.completed_sessions(
            limit=200, charger_id=msg.get("charger_id"), asset_id=msg.get("asset_id"),
        )
        if msg.get("include_history", True):
            now = datetime.now(timezone.utc)
            history_end = min(end.astimezone(timezone.utc), now)
            history_start = min(start.astimezone(timezone.utc), history_end-timedelta(hours=48))
            receipts = runtime.executor.completed_sessions(
                start=history_start, end=history_end, charger_id=msg.get("charger_id"),
            )
            actual, quality, estimates, observed_sessions, session_metrics = await read_actual_history(
                hass, result["configuration"], start, end,
                charger_id=msg.get("charger_id"), asset_id=msg.get("asset_id"),
                session_receipts=receipts,
                price_slots=runtime.price_slots, include_valuations=True,
                power_bindings=deepcopy(runtime.power_bindings), energy_bindings=deepcopy(runtime.energy_bindings),
                tariff_bindings=deepcopy(runtime.tariff_bindings),
                include_observed_sessions=True, active_sessions=result["active_sessions"],
                tariff_entity=forecast_tariff_source(result["configuration"]["controller"]),
            )
        else:
            actual, quality, estimates, observed_sessions, session_metrics = [], "NOT_REQUESTED", {}, [], {}
        if runtime.configuration != cfg or not runtime.active:
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                                  "Configuration changed while reading plan; refresh")
            return
        # A Recorder-based *indicative* variable component belongs in the
        # read-only view only. Never mutate persisted session receipts or
        # convert a power integration into an authoritative billed cost.
        for receipt in result["completed_sessions"]:
            if receipt.get("cost") is None:
                receipt.update(estimates.get((
                    receipt["charger_id"], receipt["started_at"],
                    receipt["ended_at"],
                ), {}))
        for receipt in result["completed_sessions"]:
            receipt.update(session_metrics.get((receipt["charger_id"], receipt["started_at"], receipt["ended_at"]), {}))
        for uid, receipt in result["active_sessions"].items():
            receipt.update(session_metrics.get((uid, receipt["started_at"], None), {}))
        result["observed_sessions"] = observed_sessions
        result["recent_completed_sessions"] = [
            {**receipt, **session_metrics.get((receipt["charger_id"], receipt["started_at"], receipt["ended_at"]), {}),
             **estimates.get((receipt["charger_id"], receipt["started_at"], receipt["ended_at"]), {})}
            for receipt in recent
        ]
        entry = hass.config_entries.async_get_entry(entry_id)
        result["configuration_managed_by_yaml"] = bool(
            entry is not None and entry.data.get("source") in ("yaml", "json")
        )
        result["configuration_managed_by_json"] = bool(
            entry is not None and entry.data.get("source") == "json"
        )
        result["actual_slots"] = actual
        result["actual_history_quality"] = quality
        # Exact native Registry entity IDs: no guessed entity_id in the card.
        def native_entity(platform, kind, uid, field):
            return registry.async_get_entity_id(
                platform, DOMAIN, f"{DOMAIN}:{kind}:{uid}:{field}"
            )
        def native_select(kind, uid, field):
            return native_entity("select", kind, uid, field)
        # Use the same configuration snapshot as the response, even if an
        # asynchronous Recorder query overlapped a settings update.
        cfg = result["configuration"]
        admin = getattr(getattr(connection, "user", None), "is_admin", False)
        result["charger_setup"] = {}
        for row in cfg["chargers"]:
            projection = setup_snapshot[row["id"]]
            if not admin:
                projection.pop("candidates", None)
                projection.pop("proposed_missing", None)
            result["charger_setup"][row["id"]] = projection
        if "discover_charger" in msg:
            if not admin:
                connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Admin required")
                return
            # Only an explicitly selected native switch may anchor discovery.
            draft = msg["discover_charger"]
            if not draft["control_entity"].startswith("switch."):
                raise ValueError("native switch required")
            result["charger_setup_draft"] = charger_setup_projection(hass, registry, runtime, draft)
        result["preference_entities"] = {
            "controller": {
                field: native_select("controller", cfg["controller"]["id"], field)
                for field in ("plan_label_mode", "plan_color_by",
                              "show_indicative_forecast", "mode",
                              "solar_source_kind", "grid_power_direction")
            } | {
                "name": native_entity("text", "controller",
                                      cfg["controller"]["id"], "name"),
                **{
                    field: native_entity("text", "controller",
                                         cfg["controller"]["id"], field)
                    for field in ("price_entity", "solar_entity",
                                  "site_power_entity", "binding_entity",
                                  "solar_power_entity", "home_power_entity",
                                  "grid_power_entity", "solar_surplus_entity",
                                  "current_price_entity", "export_price_entity")
                },
            } | {
                field: native_entity("number", "controller",
                                     cfg["controller"]["id"], field)
                for field in ("max_parallel", "max_power_kw", "power_adjustment_interval_minutes")
            },
            "assets": {
                row["id"]: {
                    "name": native_entity("text", "asset", row["id"], "name"),
                    "soc_entity": native_entity("text", "asset", row["id"], "soc_entity"),
                    "price_currency": native_entity(
                        "text", "asset", row["id"], "price_currency"),
                    **{
                        f"charging_window_{day}": native_entity(
                            "text", "asset", row["id"], f"charging_window_{day}")
                        for day in WEEKDAYS
                    },
                    **{
                        field: native_select("asset", row["id"], field)
                        for field in ("plan_color", "ready_by_repeat", "continuous_charging",
                                      "opportunistic_kind", "kind",
                                      *(f"ready_day_{day}" for day in WEEKDAYS))
                    },
                    **{
                        field: native_entity("number", "asset", row["id"], field)
                        for field in ("target_soc", "requested_kwh",
                                      "requested_duration_minutes", "requested_budget_amount",
                                      "minimum_soc_pct", "maximum_price_per_kwh",
                                      "low_price_trigger_per_kwh", "low_soc_trigger_pct",
                                      "opportunistic_level_pct", "priority",
                                      "max_charge_kw", "capacity_kwh",
                                      "charge_efficiency")
                    },
                    **{
                        field: native_entity("datetime", "asset", row["id"], field)
                        for field in ("ready_by", "expected_connection_at",
                                      "expires_at", "earliest_start_at")
                    },
                }
                for row in cfg["assets"]
            },
            "chargers": {
                row["id"]: {
                    "name": native_entity("text", "charger", row["id"], "name"),
                    **{
                        field: native_select("charger", row["id"], field)
                        for field in ("plan_color", "asset", "control_owner")
                    },
                    **{
                        field: native_entity("number", "charger", row["id"], field)
                        for field in ("min_charging_power_kw",
                                      "max_charging_power_kw",
                                      "set_charging_power_kw")
                    },
                    "confirm_connection": native_entity(
                        "button", "charger", row["id"], "confirm_connection"
                    ),
                }
                for row in cfg["chargers"]
            },
        }

    except (ValueError, TypeError, OverflowError, KeyError):
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              "Invalid plan scope, filter or interval")
        return
    connection.send_result(msg["id"], result)


def register_plan_query(hass: HomeAssistant) -> None:
    """Register once at integration bootstrap, independent of config entries."""
    websocket_api.async_register_command(hass, websocket_get_plan)
