"""Admin-authorized native HA WebSocket read-only 48h charge plan query."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN


@websocket_api.require_admin
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
    configured = list(hass.data.get(DOMAIN, {}).values())
    runtime = next(
        (
            row for row in configured
            if msg.get("controller_id") in (None, row.configuration["controller"]["id"])
        ), None,
    )
    if runtime is None:
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
        result = runtime.read_plan(
            start, end,
            charger_id=msg.get("charger_id"), asset_id=msg.get("asset_id"),
        )
    except (ValueError, TypeError, OverflowError, KeyError):
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              "Invalid plan scope, filter or interval")
        return
    connection.send_result(msg["id"], result)


def register_plan_query(hass: HomeAssistant) -> None:
    """Register once at integration bootstrap, independent of config entries."""
    websocket_api.async_register_command(hass, websocket_get_plan)
