"""Optional standalone native Home Assistant frontend, independent of backend operation.

Only a fixed, public, bundled JavaScript file is served. No HA data or
physical commands are exposed by this static endpoint.
"""
from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import web
from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
RESOURCE = "/robotix_multicharge/frontend/robotix-multicharge.js"
SCRIPT = Path(__file__).parent / "frontend" / "robotix-multicharge.js"
KEY = f"{DOMAIN}_frontend"

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
    """One fixed route per integration setup; no dashboard modifications."""
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
