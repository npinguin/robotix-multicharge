"""Optional standalone native Home Assistant frontend, independent of backend operation.

Only a fixed, public, bundled JavaScript file is served. No HA data or
physical commands are exposed by this static endpoint.
"""
from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import web
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
RESOURCE = "/robotix_multicharge/frontend/robotix-multicharge.js"
SCRIPT = Path(__file__).parent / "frontend" / "robotix-multicharge.js"
KEY = f"{DOMAIN}_frontend"
PANEL_PATH = "robotix-multicharge"
PANEL_ELEMENT = "robotix-multicharge-panel"
PANEL_TITLE = "Robotix MultiCharge"
PANEL_ICON = "mdi:ev-station"
PANEL_KEY = f"{DOMAIN}_sidebar_panel"

class MultiChargeScriptView(HomeAssistantView):
    def __init__(self, hass):
        self.hass = hass

    url = RESOURCE
    name = "robotix_multicharge:frontend"
    requires_auth = False  # Static JavaScript only, no user/HA observations.

    async def get(self, request):
        data = await self.hass.async_add_executor_job(SCRIPT.read_bytes)
        return web.Response(body=data, content_type="text/javascript",
                            headers={"Cache-Control": "no-store",
                                     "X-Content-Type-Options": "nosniff"})

def register_frontend(hass):
    """Register one static JavaScript source for card and standalone panel."""
    if getattr(hass, "http", None) is None or hass.data.get(KEY + "_route"):
        return
    hass.http.register_view(MultiChargeScriptView(hass))
    hass.data[KEY + "_route"] = True

def reconcile_frontend(hass, entry=None):
    """Expose optional bundled card without touching user-owned dashboards."""
    enabled = entry is not None and entry.options.get("enable_ux", True) is True
    active = hass.data.get(KEY, False)
    if enabled == active:
        return
    try:
        if enabled:
            frontend.add_extra_js_url(hass, RESOURCE)
        else:
            frontend.remove_extra_js_url(hass, RESOURCE)
    except (AttributeError, ValueError, KeyError) as exc:
        _LOGGER.warning("MultiCharge optional UI registration pending: %s", exc)
        return
    hass.data[KEY] = enabled



async def register_sidebar_panel(hass, entry):
    """Publish the existing five-view frontend as a native HA sidebar panel.

    The panel is a view onto one canonical runtime, not a second dashboard
    storage or a new charging writer. It is readable by all signed-in users.
    """
    if entry.options.get("enable_ux", True) is not True:
        return
    if hass.data.get(PANEL_KEY):
        return
    if frontend.async_panel_exists(hass, PANEL_PATH):
        # Never overwrite a preexisting, user-owned panel at our URL.
        _LOGGER.error("MultiCharge sidebar URL already occupied: /%s", PANEL_PATH)
        return
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_ELEMENT,
        frontend_url_path=PANEL_PATH,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=RESOURCE,
        embed_iframe=False,
        require_admin=False,
    )
    hass.data[PANEL_KEY] = True


def unregister_sidebar_panel(hass):
    """Remove only our panel on successful entry unload; keep other panels."""
    if not hass.data.pop(PANEL_KEY, False):
        return
    frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
