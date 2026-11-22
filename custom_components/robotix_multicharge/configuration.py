"""One source-neutral configuration schema for native UI and expert JSON/YAML.

This module never reads Home Assistant state or sends physical commands.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from json import dumps
from datetime import datetime
from math import isfinite
from re import fullmatch

from .domain import ChargeableAsset, Charger, ChargeController

# One shared, accessible identity palette. Keys are stable HA select options.
PLAN_COLORS = {
    "blue": "#3779B9", "orange": "#BA6B3F", "green": "#32816E",
    "purple": "#9568B4", "gold": "#A78529", "teal": "#397E91",
    "pink": "#B05D81", "indigo": "#6370B9", "olive": "#738638",
    "brown": "#916052", "coral": "#BE6D5E", "slate": "#658398",
    "violet": "#8055A7", "lime": "#649041", "salmon": "#B77E70",
    "cyan": "#337F99", "wine": "#95506D", "forest": "#376F4D",
    "peach": "#AA774C", "lavender": "#8480B8", "turquoise": "#21877F",
    "rust": "#AD5C39", "navy": "#52668B", "moss": "#687845",
}


def assign_default_plan_colors(rows):
    """Stable unique defaults for each logical device kind; explicit picks win."""
    taken = {row["plan_color"] for row in rows if row.get("plan_color")}
    choices = list(PLAN_COLORS)
    for row in sorted(rows, key=lambda item: item["id"]):
        if row.get("plan_color"):
            continue
        color = next((c for c in choices if c not in taken), None)
        if color is None:
            raise ValueError("too many devices for distinct default colors")
        row["plan_color"] = color
        taken.add(color)



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
                   "binding_entity", "mode", "phase_limits_a",
                   "plan_label_mode", "plan_color_by", "show_indicative_forecast"), "controller")
    cid = _text(ctl.get("id", "home"), "controller.id")
    parallel = ctl.get("max_parallel", 1)
    if isinstance(parallel, bool) or not isinstance(parallel, int) or parallel < 1:
        raise ValueError("controller.max_parallel: expected positive integer")
    mode = ctl.get("mode", "Off")
    if mode not in ("Automatic", "Solar", "Economy", "Ready By", "Force Charge", "Off"):
        raise ValueError("controller.mode: unsupported charging mode")
    label_mode = ctl.get("plan_label_mode", "both")
    color_by = ctl.get("plan_color_by", "vehicle")
    show_forecast = ctl.get("show_indicative_forecast", True)
    if label_mode not in ("vehicle", "charger", "both"):
        raise ValueError("controller.plan_label_mode: choose vehicle/charger/both")
    if color_by not in ("vehicle", "charger"):
        raise ValueError("controller.plan_color_by: choose vehicle/charger")
    if type(show_forecast) is not bool:
        raise ValueError("controller.show_indicative_forecast: expected boolean")
    controller = {"id": cid, "name": _text(ctl.get("name"), "controller.name"),
                  "max_parallel": parallel, "mode": mode,
                  "plan_label_mode": label_mode, "plan_color_by": color_by,
                  "show_indicative_forecast": show_forecast}
    if ctl.get("max_power_kw") is not None:
        controller["max_power_kw"] = _number(ctl["max_power_kw"], "controller.max_power_kw")
    if ctl.get("phase_limits_a") is not None:
        limits = ctl["phase_limits_a"]
        if not isinstance(limits, dict) or not limits or any(
            phase not in ("L1", "L2", "L3") for phase in limits
        ):
            raise ValueError("controller.phase_limits_a: use L1/L2/L3 map")
        controller["phase_limits_a"] = {
            phase: _number(current, "controller.phase_limits_a." + phase)
            for phase, current in limits.items()
        }
    if ctl.get("binding_entity") and ctl.get("site_power_entity"):
        raise ValueError("controller: select one authoritative capacity binding source")
    for key in ("price_entity", "site_power_entity", "solar_entity", "binding_entity"):
        if ctl.get(key):
            controller[key] = _entity(ctl[key], "controller." + key)
    ChargeController(uid=cid, name=controller["name"],
                     max_parallel=parallel, max_group_power_kw=controller.get("max_power_kw"),
                     phase_limits_a=controller.get("phase_limits_a"))

    assets = []
    ids = set()
    if not isinstance(value.get("assets", []), list):
        raise ValueError("assets: expected list")
    for source in value.get("assets", []):
        _allowed(source, ("id", "name", "kind", "soc_entity",
                          "vehicle_control_entity", "vehicle_current_entity",
                          "capacity_kwh", "target_soc", "max_charge_kw",
                          "requested_kwh", "requested_duration_minutes", "ready_by",
                          "ready_by_repeat", "charge_efficiency", "priority",
                          "temporary", "expires_at", "expected_connection_at",
                          "plan_color"), "asset")
        uid = _text(source.get("id"), "asset.id")
        if uid in ids:
            raise ValueError("asset.id: duplicate")
        ids.add(uid)
        asset = {"id": uid, "name": _text(source.get("name"), "asset.name"),
                 "kind": _text(source.get("kind", "car"), "asset.kind")}
        if source.get("plan_color") is not None:
            if source["plan_color"] not in PLAN_COLORS:
                raise ValueError("asset.plan_color: invalid palette color")
            asset["plan_color"] = source["plan_color"]
        if source.get("soc_entity"):
            asset["soc_entity"] = _entity(source["soc_entity"], "asset.soc_entity")
        for key, domain in (("vehicle_control_entity", "switch"),
                            ("vehicle_current_entity", "number")):
            if source.get(key):
                selected_entity = _entity(source[key], "asset." + key)
                if selected_entity.split(".", 1)[0] != domain:
                    raise ValueError(f"asset.{key}: expected {domain} entity")
                asset[key] = selected_entity
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
        if source.get("temporary") is not None:
            if type(source["temporary"]) is not bool:
                raise ValueError("asset.temporary: expected boolean")
            if source["temporary"]:
                asset["temporary"] = True
        if source.get("expires_at") is not None:
            if not asset.get("temporary"):
                raise ValueError("asset.expires_at: only temporary assets can expire")
            raw = _text(source["expires_at"], "asset.expires_at")
            try:
                instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("asset.expires_at: expected ISO time") from exc
            if instant.tzinfo is None or instant.utcoffset() is None:
                raise ValueError("asset.expires_at: timezone required")
            asset["expires_at"] = instant.isoformat()
        if asset.get("temporary") and "expires_at" not in asset:
            raise ValueError("asset.temporary: expiry required")
        if source.get("expected_connection_at") is not None:
            arrival = _text(source["expected_connection_at"], "asset.expected_connection_at")
            try:
                moment = datetime.fromisoformat(arrival.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("asset.expected_connection_at: invalid ISO timestamp") from exc
            if moment.tzinfo is None or moment.utcoffset() is None:
                raise ValueError("asset.expected_connection_at: timezone required")
            asset["expected_connection_at"] = moment.isoformat()
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
                          "energy_entity", "session_entity", "min_current_a", "max_current_a",
                          "phase_count", "control_owner", "physical_commissioned",
                          "phase_ids", "voltage_v", "current_step_a", "fixed_current_a",
                          "circuit_id", "circuit_limit_a", "current_control_entity",
                          "current_readback_entity", "plan_color"), "charger")
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
        if source.get("plan_color") is not None:
            if source["plan_color"] not in PLAN_COLORS:
                raise ValueError("charger.plan_color: invalid palette color")
            charger["plan_color"] = source["plan_color"]
        owner = source.get("control_owner", "external")
        if owner not in ("external", "multicharge"):
            raise ValueError("charger.control_owner: expected external/multicharge")
        if "physical_commissioned" in source and type(source["physical_commissioned"]) is not bool:
            raise ValueError("charger.physical_commissioned: expected boolean")
        commissioned = source.get("physical_commissioned", False)
        if commissioned and owner != "multicharge":
            raise ValueError("charger: physical commissioning requires MultiCharge owner")
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
        for key in ("min_current_a", "max_current_a", "voltage_v",
                    "current_step_a", "fixed_current_a", "circuit_limit_a"):
            if source.get(key) is not None:
                charger[key] = _number(source[key], "charger." + key)
        if source.get("phase_ids") is not None:
            phases = source["phase_ids"]
            if not isinstance(phases, list) or not phases or (
                len(phases) != len(set(phases))
                or any(p not in ("L1", "L2", "L3") for p in phases)
            ):
                raise ValueError("charger.phase_ids: expected unique L1/L2/L3")
            charger["phase_ids"] = list(phases)
        if source.get("circuit_id"):
            charger["circuit_id"] = _text(source["circuit_id"], "charger.circuit_id")
        if owner == "multicharge" and source["kind"] == "variable_current":
            if not ctl.get("phase_limits_a"):
                raise ValueError("charger: commissioned variable current requires verified site phase limits")
            if not all(key in charger for key in (
                "phase_count", "phase_ids", "voltage_v", "current_step_a",
                "min_current_a", "max_current_a", "circuit_id", "circuit_limit_a"
            )) or not str(source.get("current_control_entity", "")).startswith("number.") or not str(
                source.get("current_readback_entity", "")
            ).startswith("sensor."):
                raise ValueError("charger: controlled current requires verified phases, circuit, setpoint and independent current sensor")
            if charger["voltage_v"] < 200 or charger["voltage_v"] > 260:
                raise ValueError("charger.voltage_v: expected verified line-neutral voltage")
        if (source.get("current_readback_entity")
                and source.get("current_readback_entity") ==
                source.get("current_control_entity")):
            raise ValueError("charger: independent current sensor required")
        if owner == "multicharge" and ctl.get("phase_limits_a"):
            if not charger.get("phase_ids") or not charger.get("voltage_v"):
                raise ValueError("charger: verified phase wiring and voltage required")
            if source["kind"] == "on_off" and not charger.get("fixed_current_a"):
                raise ValueError("charger: on/off current required for phase protection")
            if (source["kind"] == "on_off"
                    and charger.get("fixed_current_a") is not None
                    and charger["fixed_current_a"] * charger["voltage_v"]
                    * len(charger["phase_ids"]) + 1e-9
                    < charger["rated_power_kw"] * 1000):
                raise ValueError("charger: phase current understates nominal electrical load")
        for key in ("control_entity", "connected_entity", "power_entity", "energy_entity",
                    "session_entity", "current_control_entity", "current_readback_entity"):
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
                phase_count=charger.get("phase_count"),
                phase_ids=tuple(charger.get("phase_ids", ())),
                voltage_v=charger.get("voltage_v"),
                current_step_a=charger.get("current_step_a"),
                fixed_current_a=charger.get("fixed_current_a"),
                circuit_id=charger.get("circuit_id"),
                circuit_limit_a=charger.get("circuit_limit_a"))
        chargers.append(charger)

    circuits = {}
    for c in chargers:
        if c.get("circuit_id"):
            previous = circuits.setdefault(c["circuit_id"], c.get("circuit_limit_a"))
            if previous != c.get("circuit_limit_a"):
                raise ValueError("chargers sharing a circuit must share one binding current limit")
    assignments = [c["asset"] for c in chargers if "asset" in c]
    if len(assignments) != len(set(assignments)):
        raise ValueError("asset assigned to more than one charger")

    # Each exact physical charger input/command must be attributable to one
    # logical Charger. Shared raw entities cannot silently create duplicate
    # command owners, occupancy or kWh attribution inside MultiCharge.
    physical_sources = {}
    for charger in chargers:
        for role in (
            "control_entity", "connected_entity", "power_entity", "energy_entity",
            "session_entity", "current_control_entity", "current_readback_entity"
        ):
            entity = charger.get(role)
            if not entity:
                continue
            previous = physical_sources.setdefault(entity, (charger["id"], role))
            if previous != (charger["id"], role):
                raise ValueError(
                    f"charger.{role}: entity also bound as {previous[0]}.{previous[1]}"
                )
    # Each vehicle command endpoint names exactly one logical asset.
    # These are source bindings only: the single EVSE executor still controls
    # physical charging; no second vehicle command path is added here.
    vehicle_controls = {}
    for asset in assets:
        for field in ("vehicle_control_entity", "vehicle_current_entity"):
            entity = asset.get(field)
            if entity:
                previous = vehicle_controls.setdefault(entity, asset["id"])
                if previous != asset["id"] or entity in physical_sources:
                    raise ValueError(
                        f"asset.{field}: source already bound to another physical role"
                    )
    assign_default_plan_colors(assets)
    assign_default_plan_colors(chargers)
    return {"controller": controller, "assets": assets, "chargers": chargers}


def effective_configuration(entry):
    """One authority: expert JSON/YAML overrides historic UI options.

    The native Config Entry, its ID and its HA device/recorder history remain
    in place when an installed UI configuration switches to expert YAML.
    """
    if entry.data.get("source") in ("yaml", "json"):
        return validate_configuration(deepcopy(entry.data["configuration"]))
    return validate_configuration(deepcopy(
        entry.options.get("configuration", entry.data["configuration"])
    ))


def configuration_revision(config):
    """Stable optimistic lock for native settings; not a planner revision."""
    return sha256(dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]


def apply_settings_change(configuration, scope, target_id, changes, action="save"):
    """Narrow user-preference editor through the one native Config Entry authority.

    Physical ownership, commissioning, wiring and source device capabilities
    are deliberately NOT editable from this everyday surface.
    """
    if not isinstance(changes, dict) or not changes:
        raise ValueError("settings changes must contain values")
    allowed = {
        "controller": {
            "name", "max_parallel", "max_power_kw", "phase_limits_a",
            "price_entity", "solar_entity", "binding_entity", "mode",
            "plan_label_mode", "plan_color_by", "show_indicative_forecast",
        },
        "asset": {
            "name", "kind", "soc_entity", "capacity_kwh", "target_soc",
            "max_charge_kw", "requested_kwh", "requested_duration_minutes",
            "ready_by", "ready_by_repeat", "charge_efficiency", "priority",
            "temporary", "expires_at", "expected_connection_at",
            "plan_color",
        },
        "charger": {"name", "asset", "plan_color"},
    }
    if scope not in allowed or set(changes) - allowed[scope]:
        raise ValueError("settings field not editable in this scope")
    if action not in ("save", "create", "delete"):
        raise ValueError("unsupported settings action")
    cfg = deepcopy(configuration)
    if scope == "controller":
        if action != "save" or target_id != cfg["controller"]["id"]:
            raise ValueError("controller identity is immutable")
        target = cfg["controller"]
    else:
        if not isinstance(target_id, str) or not target_id.strip():
            raise ValueError("stable logical ID required")
        collection = cfg["assets" if scope == "asset" else "chargers"]
        target = next((row for row in collection if row["id"] == target_id), None)
        if action == "create":
            if scope != "asset" or target is not None:
                raise ValueError("only unassigned chargeable assets can be created")
            target = {"id": target_id}
            collection.append(target)
        elif action == "delete":
            if scope != "asset" or target is None:
                raise ValueError("only existing unassigned assets can be deleted")
            collection.remove(target)
            return validate_configuration(cfg)
        elif target is None:
            raise ValueError("unknown logical object")
    for name, value in changes.items():
        if value is None or value == "":
            if name == "name":
                raise ValueError("name cannot be empty")
            target.pop(name, None)
        else:
            target[name] = value
    if scope == "charger" and changes.get("asset"):
        # One selected Charger per vehicle. Reassignment is one atomic
        # configuration edit, not delete/recreate or a second ownership store.
        for old in cfg["chargers"]:
            if old["id"] != target_id and old.get("asset") == changes["asset"]:
                old.pop("asset", None)
    return validate_configuration(cfg)


def is_plan_presentation_only_change(before, after):
    """Allow card display settings without unloading any active physical writer."""
    if before == after:
        return False

    def without_visual(cfg):
        rest = deepcopy(cfg)
        for row in (*rest["assets"], *rest["chargers"]):
            row.pop("plan_color", None)
            row.pop("name", None)
        # Type is currently taxonomy only: no planner or electrical capability
        # changes. Keep native asset type edits safe for active EVSE sessions.
        for asset in rest["assets"]:
            asset.pop("kind", None)
        for key in ("name", "plan_label_mode", "plan_color_by",
                    "show_indicative_forecast"):
            rest["controller"].pop(key, None)
        return rest
    return without_visual(before) == without_visual(after)


def is_in_place_runtime_preference_change(before, after):
    """Reconcile edits to existing native preferences without stopping other EVSEs.

    Physical topology, source subscriptions, object registration and writer
    identity are structural and continue through the normal guarded reload.
    This classifier never authorizes the edit: the settings writer separately
    checks physical idle and source evidence before persisting changes.
    """
    if before == after:
        return False

    def structure(cfg):
        result = deepcopy(cfg)
        for field in ("name", "plan_label_mode", "plan_color_by",
                      "show_indicative_forecast", "mode", "max_parallel",
                      "max_power_kw", "phase_limits_a"):
            result["controller"].pop(field, None)
        for asset in result["assets"]:
            for field in ("name", "kind", "plan_color", "capacity_kwh",
                          "target_soc", "max_charge_kw", "requested_kwh",
                          "requested_duration_minutes", "ready_by",
                          "ready_by_repeat", "charge_efficiency", "priority",
                          "temporary", "expires_at", "expected_connection_at"):
                asset.pop(field, None)
        for charger in result["chargers"]:
            for field in ("name", "plan_color", "asset"):
                charger.pop(field, None)
        return result

    return structure(before) == structure(after)


# Expert JSON is only an adapter to the existing canonical Config Entry validator.
# Every command remains subject to the executor's physical admission/readback.
def normalize_expert_json(value):
    """Map human-readable direct JSON to one validated configuration authority."""
    if not isinstance(value, dict):
        raise ValueError("expert JSON: expected object")
    if "Charger" not in value and "ChargingAsset" not in value:
        return validate_configuration(value)
    _allowed(value, ("Controller", "Charger", "ChargingAsset"), "expert JSON")

    def rows(key):
        raw = value.get(key, [])
        if isinstance(raw, dict):
            raw = [raw]
        if not isinstance(raw, list):
            raise ValueError(f"{key}: expected object or array")
        return raw

    def entity(source, key, domains, required=False):
        raw = source.get(key)
        if raw is None or raw == "":
            if required:
                raise ValueError(f"{key}: required Home Assistant entity")
            return None
        selected = _entity(raw, key)
        if selected.split(".", 1)[0] not in domains:
            raise ValueError(f"{key}: expected {', '.join(domains)} entity")
        return selected

    controller = value.get("Controller") or {}
    _allowed(controller, (
        "ID", "Name", "Mode", "Max-parallel", "Max-power-kW",
        "Phase-limits-A", "Price-entity", "Solar-entity",
        "Power-envelope-entity", "Plan-label-mode", "Plan-color-by",
        "Show-indicative-forecast",
    ), "Controller")
    cfg = default_configuration(controller.get("Name") or "Home charging")
    ctl = cfg["controller"]
    if controller.get("ID"):
        ctl["id"] = _text(controller["ID"], "Controller.ID")
    for key, field in (
        ("Mode", "mode"), ("Max-parallel", "max_parallel"),
        ("Max-power-kW", "max_power_kw"), ("Phase-limits-A", "phase_limits_a"),
        ("Plan-label-mode", "plan_label_mode"), ("Plan-color-by", "plan_color_by"),
        ("Show-indicative-forecast", "show_indicative_forecast"),
    ):
        if key in controller:
            ctl[field] = controller[key]
    for key, field in (
        ("Price-entity", "price_entity"), ("Solar-entity", "solar_entity"),
        ("Power-envelope-entity", "binding_entity"),
    ):
        selected = entity(controller, key, ("sensor",))
        if selected is not None:
            ctl[field] = selected

    asset_ids = {}
    for source in rows("ChargingAsset"):
        _allowed(source, (
            "ID", "Name", "Asset type", "Vehicle-Charging-startstop-entity",
            "Vehicle-Charging-amp-entity", "Vehicle-soc-sensor",
            "Usable-capacity-kWh", "Target-SoC-percent", "Max-charge-kW",
            "Requested-kWh", "Requested-duration-minutes", "Ready-by",
            "Ready-by-repeat", "Charging-efficiency", "Priority",
            "Temporary", "Expires-at", "Expected-connection-at", "Plan-color",
        ), "ChargingAsset")
        name = _text(source.get("Name"), "ChargingAsset.Name")
        uid = _text(source.get("ID") or _slug(name), "ChargingAsset.ID")
        kind = source.get("Asset type", "Véhicule")
        kinds = {"Véhicule": "car", "Vehicle": "car", "car": "car",
                 "bicycle": "bicycle", "motorcycle": "motorcycle",
                 "scooter": "scooter", "other": "other"}
        if kind not in kinds:
            raise ValueError("ChargingAsset.Asset type: unsupported kind")
        asset = {"id": uid, "name": name, "kind": kinds[kind]}
        for key, field, domains in (
            ("Vehicle-Charging-startstop-entity", "vehicle_control_entity", ("switch",)),
            ("Vehicle-Charging-amp-entity", "vehicle_current_entity", ("number",)),
            ("Vehicle-soc-sensor", "soc_entity", ("sensor",)),
        ):
            selected = entity(source, key, domains)
            if selected is not None:
                asset[field] = selected
        for key, field in (
            ("Usable-capacity-kWh", "capacity_kwh"),
            ("Target-SoC-percent", "target_soc"),
            ("Max-charge-kW", "max_charge_kw"),
            ("Requested-kWh", "requested_kwh"),
            ("Requested-duration-minutes", "requested_duration_minutes"),
            ("Ready-by", "ready_by"), ("Ready-by-repeat", "ready_by_repeat"),
            ("Charging-efficiency", "charge_efficiency"),
            ("Priority", "priority"), ("Temporary", "temporary"),
            ("Expires-at", "expires_at"),
            ("Expected-connection-at", "expected_connection_at"),
            ("Plan-color", "plan_color"),
        ):
            if key in source:
                asset[field] = source[key]
        cfg["assets"].append(asset)
        for identity in (uid, name):
            if identity in asset_ids and asset_ids[identity] != uid:
                raise ValueError("ChargingAsset: ambiguous name or ID")
            asset_ids[identity] = uid

    for source in rows("Charger"):
        _allowed(source, (
            "ID", "Name", "Charging-Session-sensor",
            "Charging-startstop-entity", "Charging-amp-entity",
            "Charging-current-readback-sensor", "Charging-power-sensor",
            "Charging-energy-sensor", "Charging-connected-sensor",
            "Rated-power-kW", "ChargingAsset", "Control-kind",
            "Control-owner", "Physical-commissioned", "Phase-count",
            "Phase-IDs", "Voltage-V", "Min-current-A", "Max-current-A",
            "Current-step-A", "Fixed-current-A", "Circuit-ID",
            "Circuit-limit-A", "Plan-color",
        ), "Charger")
        name = _text(source.get("Name"), "Charger.Name")
        uid = _text(source.get("ID") or _slug(name), "Charger.ID")
        charger = {
            "id": uid, "name": name,
            "kind": source.get("Control-kind", "on_off"),
            "rated_power_kw": source.get("Rated-power-kW", 3.6),
            "control_owner": source.get("Control-owner", "external"),
            "physical_commissioned": source.get("Physical-commissioned", False),
        }
        for key, field, domains, required in (
            ("Charging-startstop-entity", "control_entity", ("switch",), True),
            ("Charging-amp-entity", "current_control_entity", ("number",), False),
            ("Charging-current-readback-sensor", "current_readback_entity", ("sensor",), False),
            ("Charging-Session-sensor", "session_entity",
             ("sensor", "binary_sensor"), False),
            ("Charging-power-sensor", "power_entity", ("sensor",), False),
            ("Charging-energy-sensor", "energy_entity", ("sensor",), False),
            ("Charging-connected-sensor", "connected_entity",
             ("sensor", "binary_sensor"), False),
        ):
            selected = entity(source, key, domains, required)
            if selected is not None:
                charger[field] = selected
        for key, field in (
            ("Phase-count", "phase_count"), ("Phase-IDs", "phase_ids"),
            ("Voltage-V", "voltage_v"), ("Min-current-A", "min_current_a"),
            ("Max-current-A", "max_current_a"), ("Current-step-A", "current_step_a"),
            ("Fixed-current-A", "fixed_current_a"), ("Circuit-ID", "circuit_id"),
            ("Circuit-limit-A", "circuit_limit_a"), ("Plan-color", "plan_color"),
        ):
            if key in source:
                charger[field] = source[key]
        selected = source.get("ChargingAsset")
        if selected:
            if selected not in asset_ids:
                raise ValueError("Charger.ChargingAsset: unknown ChargingAsset")
            charger["asset"] = asset_ids[selected]

        # The expert route must not turn a guessed 3.6 kW default into
        # electrical commissioning. An owned charger needs explicit measured
        # limits and independent readback, even if commissioning is still false.
        if charger["control_owner"] == "multicharge":
            required_controller = ("Max-power-kW", "Phase-limits-A")
            required_charger = (
                "Rated-power-kW", "Phase-count", "Phase-IDs", "Voltage-V",
                "Circuit-ID", "Circuit-limit-A", "Charging-connected-sensor",
                "Charging-power-sensor",
            )
            missing = [key for key in required_controller if key not in controller]
            missing += [key for key in required_charger if key not in source]
            if charger["kind"] == "on_off" and "Fixed-current-A" not in source:
                missing.append("Fixed-current-A")
            if charger["kind"] == "variable_current":
                missing += [key for key in (
                    "Charging-amp-entity", "Charging-current-readback-sensor",
                    "Min-current-A", "Max-current-A", "Current-step-A",
                ) if key not in source]
            if missing:
                raise ValueError(
                    "Charger: owned physical control requires verified "
                    "configuration for " + ", ".join(missing)
                )
        cfg["chargers"].append(charger)
    return validate_configuration(cfg)

def _slug(name):
    """Use the same stable ID policy as the existing HA beginner wizard."""
    from re import sub
    return sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
