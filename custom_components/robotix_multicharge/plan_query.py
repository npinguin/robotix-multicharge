"""Admin-authorized native HA WebSocket read-only 48h charge plan query."""

from __future__ import annotations

from datetime import datetime

import probatio
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import DOMAIN


@websocket_api.require_admin
@websocket_api.websocket_command({
    probatio.Required("type"): "robotix_multicharge/get_plan",
    probatio.Required("controller_id"): str,
    probatio.Required("start"): str,
    probatio.Required("end"): str,
    probatio.Optional("charger_id"): str,
    probatio.Optional("asset_id"): str,
})
@websocket_api.async_response
async def websocket_get_plan(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Only qualified read-only plan data. Never accept a charger command."""
    runtime = next(
        (
            runtime for runtime in hass.data.get(DOMAIN, {}).values()
            if runtime.configuration["controller"]["id"] == msg["controller_id"]
        ),
        None,
    )
    if runtime is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND,
                              "Unknown charging Controller")
        return
    try:
        result = runtime.read_plan(
            datetime.fromisoformat(msg["start"].replace("Z", "+00:00")),
            datetime.fromisoformat(msg["end"].replace("Z", "+00:00")),
            charger_id=msg.get("charger_id"), asset_id=msg.get("asset_id"),
        )
    except (ValueError, TypeError, OverflowError):
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT,
                              "Invalid plan scope, filter or interval")
        return
    connection.send_result(msg["id"], result)


def register_plan_query(hass: HomeAssistant) -> None:
    """Register once at integration bootstrap, independent of config entries."""
    websocket_api.async_register_command(hass, websocket_get_plan)
