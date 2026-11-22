"""Home Assistant lifecycle for one logical MultiCharge configuration.

Read-only live source evidence and plan evaluation; no physical execution.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .configuration import effective_configuration, validate_configuration
from .const import DOMAIN
from .runtime import MultiChargeRuntime
from .plan_query import register_plan_query
from .command_query import register_command_query
from .frontend import register_frontend, reconcile_frontend

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): dict}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Optional expert YAML, imported through the same native Config Entry."""
    register_plan_query(hass)
    register_command_query(hass)
    register_frontend(hass)
    if DOMAIN not in config:
        return True
    try:
        checked = validate_configuration(config[DOMAIN])
    except ValueError as exc:
        _LOGGER.error("MultiCharge YAML configuration rejected: %s", exc)
        return False
    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=checked
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Expose only truthful configuration-status entities in this bootstrap."""
    try:
        cfg = effective_configuration(entry)
    except (ValueError, KeyError) as exc:
        _LOGGER.error("MultiCharge configuration rejected: %s", exc)
        return False
    runtime = MultiChargeRuntime(hass, cfg)
    runtime.refresh()

    @callback
    def on_tick(now):
        runtime.refresh(now)
        hass.async_create_task(runtime.executor.supervise())

    runtime.set_unsubscribe(
        async_track_time_interval(hass, on_tick, timedelta(minutes=1))
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        runtime.stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise
    reconcile_frontend(hass, entry)
    await runtime.executor.supervise()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        reconcile_frontend(hass)
        runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if runtime is not None:
            runtime.stop()
    return ok
