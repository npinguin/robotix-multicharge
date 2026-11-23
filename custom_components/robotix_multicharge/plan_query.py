"""Authenticated resident-readable HA WebSocket 48h charge plan query."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .configuration import WEEKDAYS
from .history import read_actual_history


@websocket_api.websocket_command({
    vol.Required("type"): "robotix_multicharge/get_plan",
    vol.Optional("controller_id"): str,
    vol.Optional("start"): str,
    vol.Optional("end"): str,
    vol.Optional("day"): vol.In(("today", "tomorrow")),
    vol.Optional("charger_id"): str,
    vol.Optional("asset_id"): str,
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
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "Unknown charging Controller")
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
            end = datetime.combine(chosen + timedelta(days=1), time.min, local_tz)
        elif "start" in msg and "end" in msg:
            start = datetime.fromisoformat(msg["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(msg["end"].replace("Z", "+00:00"))
        else:
            raise ValueError("day or start/end required")
        entry_id, runtime = selected
        result = runtime.read_plan(
            start, end,
            charger_id=msg.get("charger_id"), asset_id=msg.get("asset_id"),
        )
        actual, quality, estimates = await read_actual_history(
            hass, runtime.configuration, start, end,
            charger_id=msg.get("charger_id"), asset_id=msg.get("asset_id"),
            session_receipts=runtime.executor.completed_sessions(),
            price_slots=runtime.price_slots, include_valuations=True,
        )
        # A Recorder-based *indicative* variable component belongs in the
        # read-only view only. Never mutate persisted session receipts or
        # convert a power integration into an authoritative billed cost.
        for receipt in result["completed_sessions"]:
            if receipt.get("cost") is None:
                receipt.update(estimates.get((
                    receipt["charger_id"], receipt["started_at"],
                    receipt["ended_at"],
                ), {}))
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
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(hass)
        def native_entity(platform, kind, uid, field):
            return registry.async_get_entity_id(
                platform, DOMAIN, f"{DOMAIN}:{kind}:{uid}:{field}"
            )
        def native_select(kind, uid, field):
            return native_entity("select", kind, uid, field)
        cfg = runtime.configuration
        result["preference_entities"] = {
            "controller": {
                field: native_select("controller", cfg["controller"]["id"], field)
                for field in ("plan_label_mode", "plan_color_by",
                              "show_indicative_forecast", "mode")
            } | {
                "name": native_entity("text", "controller",
                                      cfg["controller"]["id"], "name"),
                **{
                    field: native_entity("text", "controller",
                                         cfg["controller"]["id"], field)
                    for field in ("price_entity", "solar_entity",
                                  "site_power_entity", "binding_entity")
                },
            } | {
                field: native_entity("number", "controller",
                                     cfg["controller"]["id"], field)
                for field in ("max_parallel", "max_power_kw")
            },
            "assets": {
                row["id"]: {
                    "name": native_entity("text", "asset", row["id"], "name"),
                    "soc_entity": native_entity("text", "asset", row["id"], "soc_entity"),
                    **{
                        f"charging_window_{day}": native_entity(
                            "text", "asset", row["id"], f"charging_window_{day}")
                        for day in WEEKDAYS
                    },
                    **{
                        field: native_select("asset", row["id"], field)
                        for field in ("plan_color", "ready_by_repeat", "kind",
                                      *(f"ready_day_{day}" for day in WEEKDAYS))
                    },
                    **{
                        field: native_entity("number", "asset", row["id"], field)
                        for field in ("target_soc", "requested_kwh",
                                      "requested_duration_minutes", "priority",
                                      "max_charge_kw", "capacity_kwh",
                                      "charge_efficiency")
                    },
                    **{
                        field: native_entity("datetime", "asset", row["id"], field)
                        for field in ("ready_by", "expected_connection_at",
                                      "expires_at")
                    },
                }
                for row in cfg["assets"]
            },
            "chargers": {
                row["id"]: {
                    "name": native_entity("text", "charger", row["id"], "name"),
                    **{
                        field: native_select("charger", row["id"], field)
                        for field in ("plan_color", "asset")
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
