"""One source-neutral configuration schema for both guided UI and expert YAML import.

This module never reads Home Assistant state or sends physical commands.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from math import isfinite
from re import fullmatch

from .domain import ChargeableAsset, Charger, ChargeController


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: required nonempty string")
    return value.strip()


def _number(value, name, *, zero=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name}: expected a number")
    result = float(value)
    if not isfinite(result) or result < 0 or (not zero and result == 0):
        raise ValueError(f"{name}: invalid amount")
    return result


def _entity(value, name):
    entity = _text(value, name)
    if not fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", entity):
        raise ValueError(f"{name}: invalid Home Assistant entity ID")
    return entity


def _allowed(row, fields, name):
    if not isinstance(row, dict):
        raise ValueError(f"{name}: expected mapping")
    extra = set(row) - set(fields)
    if extra:
        raise ValueError(f"{name}: unknown keys {', '.join(sorted(extra))}")


def default_configuration(name="Home charging"):
    return {"controller": {"id": "home", "name": name, "max_parallel": 1},
            "assets": [], "chargers": []}


def validate_configuration(value):
    """Return normalized, safe-to-persist settings or fail with a useful reason."""
    _allowed(value, ("controller", "assets", "chargers"), "configuration")
    ctl = value.get("controller")
    _allowed(ctl, ("id", "name", "max_parallel", "max_power_kw",
                   "price_entity", "site_power_entity", "solar_entity",
                   "binding_entity", "mode"), "controller")
    cid = _text(ctl.get("id", "home"), "controller.id")
    parallel = ctl.get("max_parallel", 1)
    if isinstance(parallel, bool) or not isinstance(parallel, int) or parallel < 1:
        raise ValueError("controller.max_parallel: expected positive integer")
    mode = ctl.get("mode", "Off")
    if mode not in ("Automatic", "Solar", "Economy", "Ready By", "Force Charge", "Off"):
        raise ValueError("controller.mode: unsupported charging mode")
    controller = {"id": cid, "name": _text(ctl.get("name"), "controller.name"),
                  "max_parallel": parallel, "mode": mode}
    if ctl.get("max_power_kw") is not None:
        controller["max_power_kw"] = _number(ctl["max_power_kw"], "controller.max_power_kw")
    if ctl.get("binding_entity") and ctl.get("site_power_entity"):
        raise ValueError("controller: select one authoritative capacity binding source")
    for key in ("price_entity", "site_power_entity", "solar_entity", "binding_entity"):
        if ctl.get(key):
            controller[key] = _entity(ctl[key], "controller." + key)
    ChargeController(uid=cid, name=controller["name"],
                     max_parallel=parallel, max_group_power_kw=controller.get("max_power_kw"))

    assets = []
    ids = set()
    if not isinstance(value.get("assets", []), list):
        raise ValueError("assets: expected list")
    for source in value.get("assets", []):
        _allowed(source, ("id", "name", "kind", "soc_entity",
                          "capacity_kwh", "target_soc", "max_charge_kw",
                          "requested_kwh", "requested_duration_minutes", "ready_by",
                          "ready_by_repeat", "charge_efficiency", "priority"), "asset")
        uid = _text(source.get("id"), "asset.id")
        if uid in ids:
            raise ValueError("asset.id: duplicate")
        ids.add(uid)
        asset = {"id": uid, "name": _text(source.get("name"), "asset.name"),
                 "kind": _text(source.get("kind", "car"), "asset.kind")}
        if source.get("soc_entity"):
            asset["soc_entity"] = _entity(source["soc_entity"], "asset.soc_entity")
        for key in ("capacity_kwh", "max_charge_kw"):
            if source.get(key) is not None:
                asset[key] = _number(source[key], "asset." + key)
        if source.get("target_soc") is not None:
            asset["target_soc"] = _number(source["target_soc"], "asset.target_soc", zero=True)
        if source.get("requested_kwh") is not None:
            asset["requested_kwh"] = _number(
                source["requested_kwh"], "asset.requested_kwh", zero=True
            )
        if source.get("requested_duration_minutes") is not None:
            minutes = source["requested_duration_minutes"]
            if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
                raise ValueError("asset.requested_duration_minutes: positive integer required")
            asset["requested_duration_minutes"] = minutes
        if "requested_kwh" in asset and "requested_duration_minutes" in asset:
            raise ValueError("asset: choose kWh or minutes, not both")
        if source.get("priority") is not None:
            priority = source["priority"]
            if isinstance(priority, bool) or not isinstance(priority, int) or not 0 <= priority <= 100:
                raise ValueError("asset.priority: expected integer 0..100")
            asset["priority"] = priority
        if source.get("charge_efficiency") is not None:
            efficiency = _number(source["charge_efficiency"], "asset.charge_efficiency")
            if efficiency > 1:
                raise ValueError("asset.charge_efficiency: expected >0 and <=1")
            asset["charge_efficiency"] = efficiency
        if source.get("ready_by") is not None:
            ready = _text(source["ready_by"], "asset.ready_by")
            try:
                parsed = datetime.fromisoformat(ready.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("asset.ready_by: expected ISO-8601 timestamp") from exc
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError("asset.ready_by: explicit timezone required")
            asset["ready_by"] = parsed.isoformat()
        repeat = source.get("ready_by_repeat", "none")
        if repeat not in ("none", "daily", "weekly"):
            raise ValueError("asset.ready_by_repeat: expected none/daily/weekly")
        if repeat != "none" and "ready_by" not in asset:
            raise ValueError("asset.ready_by_repeat: Ready By anchor required")
        if source.get("ready_by_repeat") is not None:
            asset["ready_by_repeat"] = repeat
        ChargeableAsset(uid=uid, name=asset["name"], kind=asset["kind"],
                        usable_capacity_kwh=asset.get("capacity_kwh"),
                        target_soc_pct=asset.get("target_soc"),
                        max_charge_kw=asset.get("max_charge_kw"))
        assets.append(asset)

    chargers = []
    charger_ids = set()
    if not isinstance(value.get("chargers", []), list):
        raise ValueError("chargers: expected list")
    for source in value.get("chargers", []):
        _allowed(source, ("id", "name", "kind", "rated_power_kw", "asset",
                          "control_entity", "connected_entity", "power_entity",
                          "energy_entity", "min_current_a", "max_current_a",
                          "phase_count", "control_owner", "physical_commissioned"), "charger")
        uid = _text(source.get("id"), "charger.id")
        if uid in charger_ids:
            raise ValueError("charger.id: duplicate")
        charger_ids.add(uid)
        charger = {
            "id": uid,
            "name": _text(source.get("name"), "charger.name"),
            "kind": _text(source.get("kind"), "charger.kind"),
            "rated_power_kw": _number(source.get("rated_power_kw"), "charger.rated_power_kw"),
        }
        owner = source.get("control_owner", "external")
        if owner not in ("external", "multicharge"):
            raise ValueError("charger.control_owner: expected external/multicharge")
        if "physical_commissioned" in source and type(source["physical_commissioned"]) is not bool:
            raise ValueError("charger.physical_commissioned: expected boolean")
        commissioned = source.get("physical_commissioned", False)
        if commissioned and owner != "multicharge":
            raise ValueError("charger: physical commissioning requires MultiCharge owner")
        if owner == "multicharge" and source.get("kind") != "on_off":
            raise ValueError("charger: variable current commands not implemented")
        if owner == "multicharge" and (
            not str(source.get("control_entity", "")).startswith("switch.")
            or not source.get("connected_entity")
            or not source.get("power_entity")
        ):
            raise ValueError("charger: native switch, connection and power source required")
        charger["control_owner"] = owner
        charger["physical_commissioned"] = commissioned
        if source.get("phase_count") is not None:
            p = source["phase_count"]
            if isinstance(p, bool) or not isinstance(p, int) or p not in (1, 2, 3):
                raise ValueError("charger.phase_count: expected 1, 2 or 3")
            charger["phase_count"] = p
        for key in ("min_current_a", "max_current_a"):
            if source.get(key) is not None:
                charger[key] = _number(source[key], "charger." + key)
        for key in ("control_entity", "connected_entity", "power_entity", "energy_entity"):
            if source.get(key):
                charger[key] = _entity(source[key], "charger." + key)
        if source.get("asset"):
            aid = _text(source["asset"], "charger.asset")
            if aid not in ids:
                raise ValueError("charger.asset: unknown asset")
            charger["asset"] = aid
        Charger(uid=uid, name=charger["name"], controller_uid=cid,
                control_kind=charger["kind"], rated_power_kw=charger["rated_power_kw"],
                min_current_a=charger.get("min_current_a"),
                max_current_a=charger.get("max_current_a"),
                phase_count=charger.get("phase_count"))
        chargers.append(charger)

    assignments = [c["asset"] for c in chargers if "asset" in c]
    if len(assignments) != len(set(assignments)):
        raise ValueError("asset assigned to more than one charger")

    # Each exact physical charger input/command must be attributable to one
    # logical Charger. Shared raw entities cannot silently create duplicate
    # command owners, occupancy or kWh attribution inside MultiCharge.
    physical_sources = {}
    for charger in chargers:
        for role in (
            "control_entity", "connected_entity", "power_entity", "energy_entity"
        ):
            entity = charger.get(role)
            if not entity:
                continue
            previous = physical_sources.setdefault(entity, (charger["id"], role))
            if previous != (charger["id"], role):
                raise ValueError(
                    f"charger.{role}: entity also bound as {previous[0]}.{previous[1]}"
                )
    return {"controller": controller, "assets": assets, "chargers": chargers}


def effective_configuration(entry):
    """Only config-entry data/options own runtime structure, never a YAML shadow."""
    return validate_configuration(deepcopy(
        entry.options.get("configuration", entry.data["configuration"])
    ))
