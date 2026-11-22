"""Home Assistant lifecycle for one logical MultiCharge configuration.

Native source/planning lifecycle and a physically guarded single charging writer.
"""

from __future__ import annotations

import logging
from datetime import datetime as utc_datetime, timedelta, timezone

from homeassistant.core import callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import (
    async_track_time_interval, async_track_state_change_event,
    async_track_time_change,
)

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .configuration import (
    effective_configuration, validate_configuration,
    is_plan_presentation_only_change,
    is_in_place_runtime_preference_change,
)
from .const import DOMAIN
from .runtime import MultiChargeRuntime
from .plan_query import register_plan_query
from .command_query import register_command_query, register_settings_query
from .frontend import register_frontend, reconcile_frontend

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button", "select", "number", "datetime", "text", "binary_sensor"]


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply validated GUI changes through HA's single Config Entry reload.

    Failures are reported; no second config store or silent change ignoring.
    """
    existing = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if existing is not None:
        try:
            changed = effective_configuration(entry)
        except (KeyError, ValueError):
            _LOGGER.error("MultiCharge updated configuration failed validation")
            return
        if (is_plan_presentation_only_change(existing.configuration, changed)
                or is_in_place_runtime_preference_change(existing.configuration, changed)):
            # Existing device preferences (including qualified idle-only rebind)
            # must not reload and STOP unrelated active charging hardware.
            # Structural wiring/registration changes retain guarded reload.
            original = existing.configuration
            existing.configuration = changed
            existing.refresh()
            from homeassistant.helpers import device_registry as dr
            registry = dr.async_get(hass)
            for kind, before_rows, after_rows in (
                ("controller", [original["controller"]], [changed["controller"]]),
                ("asset", original["assets"], changed["assets"]),
                ("charger", original["chargers"], changed["chargers"]),
            ):
                former = {row["id"]: row["name"] for row in before_rows}
                for row in after_rows:
                    if former.get(row["id"]) == row["name"]:
                        continue
                    device = registry.async_get_device_by_identifier(
                        (DOMAIN, f"{kind}/{row['id']}"), entry.entry_id
                    )
                    if device is not None:
                        registry.async_update_device(device.id, name=row["name"])
            return
    if not await hass.config_entries.async_reload(entry.entry_id):
        _LOGGER.error("MultiCharge options changed but safe integration reload failed")

CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): dict}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Optional expert YAML, imported through the same native Config Entry."""
    register_plan_query(hass)
    register_command_query(hass)
    register_settings_query(hass)
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
    store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}_control")
    try:
        saved = await store.async_load()
    except (OSError, ValueError, RuntimeError):
        _LOGGER.exception("Cannot read stored MultiCharge control state; START disabled")
        saved = {"schema_major": -1}
    runtime.attach_control_store(store, saved)
    runtime.refresh()

    pending = None
    dirty = False

    async def reconcile():
        nonlocal dirty
        while dirty and runtime.active:
            dirty = False
            runtime.refresh()
            await runtime.executor.supervise()

    @callback
    def on_source_change(event=None):
        nonlocal pending, dirty
        if not runtime.active:
            return
        dirty = True
        if pending is None or pending.done():
            pending = hass.async_create_task(reconcile())

    runtime.set_unsubscribe(
        async_track_time_interval(hass, on_source_change, timedelta(minutes=1))
    )

    @callback
    def on_quarter(_event=None):
        async def apply_quarter():
            if not runtime.active:
                return
            at = utc_datetime.now(timezone.utc)
            quarter = at.replace(minute=(at.minute // 15) * 15,
                                 second=0, microsecond=0)
            runtime.refresh(quarter)
            await runtime.executor.advance_plan(quarter)
            await runtime.executor.supervise()
        hass.async_create_task(apply_quarter())

    runtime.set_unsubscribe(async_track_time_change(
        hass, on_quarter, minute=[0, 15, 30, 45], second=0
    ))
    monitored = {
        value for row in (
            cfg["controller"], *cfg["chargers"], *cfg["assets"]
        )
        for key, value in row.items()
        if key.endswith("_entity") and isinstance(value, str)
    }
    if monitored:
        runtime.set_unsubscribe(
            async_track_state_change_event(hass, list(monitored), on_source_change)
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
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime is not None and not await runtime.executor.shutdown():
        _LOGGER.error("MultiCharge unload blocked by unconfirmed physical STOP")
        return False
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        reconcile_frontend(hass)
        runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if runtime is not None:
            runtime.stop()
    return ok
