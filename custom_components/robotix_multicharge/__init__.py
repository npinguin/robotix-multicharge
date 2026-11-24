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
    effective_configuration, normalize_expert_json, apply_new_asset_defaults,
    is_plan_presentation_only_change,
    is_in_place_runtime_preference_change,
)
from .const import DOMAIN
from .runtime import MultiChargeRuntime
from .source_evidence import async_native_nordpool_prices
from .plan_query import register_plan_query
from .command_query import register_command_query, register_settings_query
from .frontend import (
    register_frontend, reconcile_frontend, register_sidebar_panel,
    unregister_sidebar_panel,
)

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
        if existing.configuration == changed:
            return  # identical Save is not a physical reload
        if (is_plan_presentation_only_change(existing.configuration, changed)
                or is_in_place_runtime_preference_change(existing.configuration, changed)):
            # Existing device preferences (including qualified idle-only rebind)
            # must not reload and STOP unrelated active charging hardware.
            # Structural wiring/registration changes retain guarded reload.
            original = existing.configuration
            existing.configuration = changed
            existing.refresh()
            await existing.executor.supervise()
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
    # An imported YAML-owned entry must never silently replay a historic
    # persisted configuration if its authoritative YAML was removed.
    hass.data[f"{DOMAIN}_source_present"] = DOMAIN in config
    if DOMAIN not in config:
        return True
    try:
        source = config[DOMAIN]
        direct_json = any(key in source for key in ("Controller", "Charger", "ChargingAsset"))
        checked = normalize_expert_json(source)
    except ValueError as exc:
        _LOGGER.error("MultiCharge YAML configuration rejected: %s", exc)
        return False
    # Defer the import until HA has finished the component setup lock.
    # Awaiting an import which itself sets up this integration can deadlock
    # startup. The one native Config Entry remains the only authority.
    hass.async_create_task(hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT,
                 "expert_format": "json" if direct_json else "yaml"},
        data=checked,
    ))
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Repair missing targets once; never implicitly authorize Active charging."""
    if entry.version != 1:
        return False
    if entry.minor_version >= 2:
        return True
    if entry.data.get("source") in ("yaml", "json"):
        hass.config_entries.async_update_entry(entry, minor_version=2)
        return True
    try:
        cfg = effective_configuration(entry)
    except (KeyError, ValueError, TypeError):
        return False
    active_assets = {c.get("asset") for c in cfg["chargers"]
                     if c.get("control_owner") == "multicharge"}
    for asset in cfg["assets"]:
        if asset.get("soc_entity") and asset["id"] not in active_assets:
            apply_new_asset_defaults(asset)
    if "configuration" in entry.options:
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, "configuration": cfg}, minor_version=2)
    else:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "configuration": cfg}, minor_version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Expose only truthful configuration-status entities in this bootstrap."""
    if (entry.data.get("source") in ("yaml", "json")
            and not hass.data.get(f"{DOMAIN}_source_present", False)):
        _LOGGER.error("MultiCharge expert source missing; previous settings are NOT resumed")
        return False
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
    # Only persist new/changed mapping metadata, never raw Recorder values.
    # Do not replace an invalid physical intent snapshot with an empty one.
    previous_bindings = saved.get("power_bindings") if isinstance(saved, dict) else None
    if runtime.executor._persistence_verified and previous_bindings != runtime.power_bindings:
        if not await runtime.persist_control_state():
            runtime.executor._persistence_verified = False
    runtime.refresh()

    pending = None
    dirty = False
    pending_quarter = None
    price_pending = None
    price_last_attempt = None
    price_source = cfg["controller"].get("price_entity") or cfg["controller"].get("current_price_entity")

    async def reconcile():
        nonlocal dirty, pending_quarter
        while dirty and runtime.active:
            dirty = False
            quarter, pending_quarter = pending_quarter, None
            at = utc_datetime.now(timezone.utc)
            current_quarter = at.replace(minute=(at.minute // 15) * 15,
                                         second=0, microsecond=0)
            if quarter is not None and quarter == current_quarter:
                # Only the native quarter event grants execution. Minute and
                # source refreshes are serialized in the same existing task.
                runtime.refresh(quarter)
                await runtime.executor.advance_plan(quarter)
            else:
                runtime.refresh(at)
            await runtime.executor.supervise()

    async def fetch_price():
        result = await async_native_nordpool_prices(hass, price_source, utc_datetime.now(timezone.utc))
        if result is not None and runtime.active:
            slots, quality = result
            runtime.nordpool_prices = (price_source, slots, quality, utc_datetime.now(timezone.utc))
            on_source_change()

    @callback
    def on_source_change(event=None):
        nonlocal pending, dirty, price_pending, price_last_attempt
        if not runtime.active:
            return
        if event is not None:
            # HA calls this synchronously for each state_changed event.
            # Identity continuity must see *every* native transition before
            # multiple source updates are coalesced into a single refresh.
            # The callback only updates volatile evidence: no physical writes.
            entity = event.data.get("entity_id")
            for charger in runtime.configuration["chargers"]:
                if charger.get("connected_entity") == entity:
                    runtime.executor.observe_connection_event(
                        charger, event.data.get("old_state"),
                        event.data.get("new_state"),
                    )
        now = utc_datetime.now(timezone.utc)
        if (price_source and (price_pending is None or price_pending.done())
                and (price_last_attempt is None or now-price_last_attempt >= timedelta(minutes=15))):
            price_last_attempt = now
            price_pending = hass.async_create_task(fetch_price())
        dirty = True
        if pending is None or pending.done():
            pending = hass.async_create_task(reconcile())

    @callback
    def on_minute(_now):
        # HA interval callbacks receive datetime, not a state-change Event.
        on_source_change()

    runtime.set_unsubscribe(
        async_track_time_interval(hass, on_minute, timedelta(minutes=1))
    )
    runtime.set_unsubscribe(lambda: price_pending.cancel() if price_pending is not None and not price_pending.done() else None)

    @callback
    def on_quarter(now):
        nonlocal pending_quarter
        if not runtime.active:
            return
        at = now.astimezone(timezone.utc)
        pending_quarter = at.replace(minute=(at.minute // 15) * 15,
                                     second=0, microsecond=0)
        on_source_change()

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
    await register_sidebar_panel(hass, entry)
    await runtime.executor.supervise()
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    if price_source:
        on_source_change()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime is not None and not await runtime.executor.shutdown():
        _LOGGER.error("MultiCharge unload blocked by unconfirmed physical STOP")
        return False
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        unregister_sidebar_panel(hass)
        reconcile_frontend(hass)
        runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if runtime is not None:
            runtime.stop()
    return ok
