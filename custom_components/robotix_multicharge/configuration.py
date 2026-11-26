"""One source-neutral configuration schema for native UI and expert JSON/YAML.

This module never reads Home Assistant state or sends physical commands.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from json import dumps
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from math import ceil, floor, isfinite
from re import fullmatch

from .domain import ChargeableAsset, Charger, ChargeController
from .const import DEFAULT_POWER_ADJUSTMENT_INTERVAL_MINUTES

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
        raise ValueError(f"{name}: expected a number, received {type(value).__name__}")
    result = float(value)
    if not isfinite(result) or result < 0 or (not zero and result == 0):
        raise ValueError(f"{name}: invalid amount; expected a finite {'nonnegative' if zero else 'positive'} number, received {result!r}")
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


WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _local_clock(value, field):
    """A local wall-clock minute, never an implicit UTC instant."""
    if not isinstance(value, str) or fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value) is None:
        raise ValueError(f"{field}: expected HH:MM local time")
    return value


def _ready_day_times(source, field="asset.ready_by_weekdays"):
    if not isinstance(source, dict) or not source:
        raise ValueError(f"{field}: select at least one weekday")
    if set(source) - set(WEEKDAYS):
        raise ValueError(f"{field}: invalid weekday")
    return {day: _local_clock(source[day], field + "." + day)
            for day in WEEKDAYS if day in source}


def _charging_windows(source, field="asset.charging_windows"):
    if not isinstance(source, dict) or not source:
        raise ValueError(f"{field}: select at least one weekday")
    if set(source) - set(WEEKDAYS):
        raise ValueError(f"{field}: invalid weekday")
    normalized = {}
    for day in WEEKDAYS:
        if day not in source:
            continue
        window = source[day]
        _allowed(window, ("start", "end"), field + "." + day)
        start = _local_clock(window.get("start"), field + "." + day + ".start")
        end = _local_clock(window.get("end"), field + "." + day + ".end")
        if start == end:
            raise ValueError(f"{field}: start/end cannot be the same")
        normalized[day] = {"start": start, "end": end}
    return normalized


def apply_new_asset_defaults(row, *, site_time_zone=None, now=None):
    """Creation-only preference defaults; legacy target repair has no timezone.

    No physical source, battery capacity, efficiency or command is inferred.
    Existing persisted settings are never defaulted by validation or reload.
    """
    car_soc_goal = (
        row.get("kind", "car") == "car"
        and all(row.get(key) is None for key in (
            "requested_kwh", "requested_duration_minutes", "requested_budget_amount",
        ))
    )
    if car_soc_goal and row.get("target_soc") is None:
        row["target_soc"] = 80
    if (car_soc_goal and not row.get("temporary") and site_time_zone
            and not any(key in row for key in (
                "ready_by", "ready_by_repeat", "ready_by_weekdays",
            ))):
        zone = ZoneInfo(site_time_zone)
        local = (now or datetime.now(timezone.utc)).astimezone(zone)
        row["ready_by"] = local.replace(
            hour=6, minute=0, second=0, microsecond=0,
        ).isoformat()
        row["ready_by_repeat"] = "daily"
    return row

def apply_new_charger_defaults(row):
    """A selected switch makes Active the default on explicit UI creation."""
    if "control_owner" not in row:
        row["control_owner"] = (
            "multicharge" if str(row.get("control_entity", "")).startswith("switch.")
            else "external"
        )
    return row


def default_configuration(name="Home charging"):
    return {"controller": {"id": "home", "name": name, "max_parallel": 1},
            "assets": [], "chargers": []}


def validate_configuration(value):
    """Return normalized, safe-to-persist settings or fail with a useful reason."""
    _allowed(value, ("controller", "assets", "chargers"), "configuration")
    ctl = value.get("controller")
    _allowed(ctl, ("id", "name", "max_parallel", "max_power_kw",
                   "price_entity", "site_power_entity", "solar_entity",
                   "solar_power_entity", "home_power_entity",
                   "grid_power_entity", "solar_surplus_entity",
                   "current_price_entity", "export_price_entity",
                   "solar_source_kind", "grid_power_direction",
                   "binding_entity", "mode", "phase_limits_a",
                   "plan_label_mode", "plan_color_by", "show_indicative_forecast",
                   "power_adjustment_interval_minutes"), "controller")
    cid = _text(ctl.get("id", "home"), "controller.id")
    parallel = ctl.get("max_parallel", 1)
    if isinstance(parallel, bool) or not isinstance(parallel, int) or parallel < 1:
        raise ValueError(f"controller.max_parallel: expected positive integer, received {parallel!r}")
    interval = ctl.get("power_adjustment_interval_minutes", DEFAULT_POWER_ADJUSTMENT_INTERVAL_MINUTES)
    if type(interval) is not int or not 1 <= interval <= 1440:
        raise ValueError("controller.power_adjustment_interval_minutes: expected whole minutes (1..1440)")
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
    solar_kind = ctl.get("solar_source_kind", "intervals" if ctl.get("solar_entity") else "none")
    if solar_kind not in ("none", "intervals", "grid_export", "direct_surplus"):
        raise ValueError("controller.solar_source_kind: unsupported native source")
    grid_direction = ctl.get("grid_power_direction", "import_positive")
    if grid_direction not in ("import_positive", "export_positive"):
        raise ValueError("controller.grid_power_direction: invalid meter sign")
    if solar_kind == "intervals" and not ctl.get("solar_entity"):
        raise ValueError("controller: interval Solar requires solar_entity")
    if solar_kind == "grid_export" and not ctl.get("grid_power_entity"):
        raise ValueError("controller: grid-export Solar requires grid_power_entity")
    if solar_kind == "direct_surplus" and not ctl.get("solar_surplus_entity"):
        raise ValueError("controller: direct surplus requires solar_surplus_entity")
    controller = {"id": cid, "name": _text(ctl.get("name"), "controller.name"),
                  "max_parallel": parallel, "mode": mode,
                  "power_adjustment_interval_minutes": interval,
                  "plan_label_mode": label_mode, "plan_color_by": color_by,
                  "show_indicative_forecast": show_forecast}
    # Unselected energy features are not new persistent authority. Preserve
    # legacy Config Entries that later bind a qualified solar interval source.
    if "solar_source_kind" in ctl or ctl.get("solar_entity"):
        controller["solar_source_kind"] = solar_kind
    if "grid_power_direction" in ctl or ctl.get("grid_power_entity"):
        controller["grid_power_direction"] = grid_direction
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
    for key in (
        "price_entity", "site_power_entity", "solar_entity", "binding_entity",
        "solar_power_entity", "home_power_entity", "grid_power_entity",
        "solar_surplus_entity", "current_price_entity", "export_price_entity",
    ):
        if ctl.get(key):
            entity_id = _entity(ctl[key], "controller." + key)
            if not entity_id.startswith("sensor."):
                raise ValueError(f"controller.{key}: native sensor required")
            controller[key] = entity_id
    ChargeController(uid=cid, name=controller["name"],
                     max_parallel=parallel, max_group_power_kw=controller.get("max_power_kw"),
                     phase_limits_a=controller.get("phase_limits_a"))

    errors = []
    assets = []
    ids = set()
    if not isinstance(value.get("assets", []), list):
        raise ValueError("assets: expected list")
    for index, source in enumerate(value.get("assets", [])):
        try:
            _allowed(source, ("id", "name", "kind", "soc_entity",
                              "soc_stale_entity", "vehicle_control_entity", "vehicle_current_entity",
                              "capacity_kwh", "target_soc", "max_charge_kw",
                              "requested_kwh", "requested_duration_minutes",
                              "requested_budget_amount", "requested_budget_currency", "ready_by",
                              "ready_by_repeat", "ready_by_weekdays", "charging_windows",
                "continuous_charging",
                "minimum_soc_pct", "maximum_price_per_kwh", "price_currency",
                "low_price_trigger_per_kwh", "low_soc_trigger_pct",
                "opportunistic_kind", "opportunistic_level_pct",
                "earliest_start_at",
                "charge_efficiency", "priority",
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
            if source.get("soc_stale_entity"):
                entity_id = _entity(source["soc_stale_entity"], "asset.soc_stale_entity")
                if not entity_id.startswith("binary_sensor."):
                    raise ValueError("asset.soc_stale_entity: native binary_sensor required")
                if not source.get("soc_entity"):
                    raise ValueError("asset.soc_stale_entity: select a SoC sensor first")
                asset["soc_stale_entity"] = entity_id
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
            if source.get("requested_budget_amount") is not None:
                asset["requested_budget_amount"] = _number(
                    source["requested_budget_amount"],
                    "asset.requested_budget_amount",
                )
                currency = source.get("requested_budget_currency", "EUR")
                if (not isinstance(currency, str) or
                        fullmatch(r"[A-Z]{3}", currency) is None):
                    raise ValueError("asset.requested_budget_currency: ISO-4217 required")
                asset["requested_budget_currency"] = currency
            elif source.get("requested_budget_currency") is not None:
                raise ValueError("asset.requested_budget_currency: amount required")
            finite_goals = sum(key in asset for key in (
                "requested_kwh", "requested_duration_minutes",
                "requested_budget_amount",
            ))
            if finite_goals > 1:
                raise ValueError("asset: choose kWh, duration OR money")
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
            # Legacy weekly is readable for exact time-zone migration on user edit.
            repeat = source.get("ready_by_repeat", "none")
            if repeat not in ("none", "daily", "specific_days", "weekly"):
                raise ValueError("asset.ready_by_repeat: unsupported recurrence")
            if repeat in ("daily", "weekly") and "ready_by" not in asset:
                raise ValueError("asset.ready_by_repeat: Ready By anchor required")
            if source.get("ready_by_weekdays") is not None:
                asset["ready_by_weekdays"] = _ready_day_times(
                    source["ready_by_weekdays"])
            if repeat == "specific_days" and not asset.get("ready_by_weekdays"):
                raise ValueError("asset.ready_by_weekdays: specific days required")
            if source.get("charging_windows") is not None:
                asset["charging_windows"] = _charging_windows(
                    source["charging_windows"])
            if source.get("continuous_charging") is not None:
                if type(source["continuous_charging"]) is not bool:
                    raise ValueError("asset.continuous_charging: expected boolean")
                asset["continuous_charging"] = source["continuous_charging"]
            for field in ("minimum_soc_pct", "low_soc_trigger_pct",
                          "opportunistic_level_pct"):
                if source.get(field) is None:
                    continue
                level = _number(source[field], "asset." + field, zero=True)
                if level > 100:
                    raise ValueError("asset." + field + ": outside 0..100")
                asset[field] = level
            for field in ("maximum_price_per_kwh", "low_price_trigger_per_kwh"):
                if source.get(field) is None:
                    continue
                quote = source[field]
                if type(quote) not in (float, int) or not isfinite(quote):
                    raise ValueError("asset." + field + ": finite price required")
                asset[field] = float(quote)
            if source.get("opportunistic_kind") is not None:
                if source["opportunistic_kind"] not in ("off", "type1", "type2"):
                    raise ValueError("asset.opportunistic_kind: off/type1/type2")
                asset["opportunistic_kind"] = source["opportunistic_kind"]
            if (asset.get("opportunistic_kind") in ("type1", "type2")
                    and "maximum_price_per_kwh" not in asset):
                raise ValueError("asset.opportunistic_kind: price cap required")
            if (any(k in asset for k in (
                    "maximum_price_per_kwh", "low_price_trigger_per_kwh"))
                    or source.get("price_currency") is not None):
                currency = source.get("price_currency")
                if (not isinstance(currency, str)
                        or fullmatch(r"[A-Z]{3}", currency) is None):
                    raise ValueError("asset.price_currency: ISO-4217 required")
                asset["price_currency"] = currency
            if (asset.get("minimum_soc_pct") is not None
                    and asset.get("target_soc") is not None
                    and asset["minimum_soc_pct"] > asset["target_soc"]):
                raise ValueError("asset.minimum_soc_pct: must not exceed target")
            if source.get("earliest_start_at") is not None:
                raw_start = _text(source["earliest_start_at"], "asset.earliest_start_at")
                try:
                    start = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise ValueError("asset.earliest_start_at: invalid ISO") from exc
                if start.utcoffset() is None:
                    raise ValueError("asset.earliest_start_at: timezone required")
                asset["earliest_start_at"] = start.isoformat()
            if source.get("ready_by_repeat") is not None:
                asset["ready_by_repeat"] = repeat
            ChargeableAsset(uid=uid, name=asset["name"], kind=asset["kind"],
                            usable_capacity_kwh=asset.get("capacity_kwh"),
                            target_soc_pct=asset.get("target_soc"),
                            max_charge_kw=asset.get("max_charge_kw"))
            assets.append(asset)
        except ValueError as exc:
            identifier = source.get("id") if isinstance(source, dict) else None
            label = f" ({identifier})" if isinstance(identifier, str) else ""
            errors.append(f"assets[{index}]{label}: {exc}")

    chargers = []
    charger_ids = set()
    if not isinstance(value.get("chargers", []), list):
        raise ValueError("chargers: expected list")
    for index, source in enumerate(value.get("chargers", [])):
        try:
            _allowed(source, ("id", "name", "kind", "rated_power_kw", "asset",
                              "control_entity", "connected_entity", "power_entity",
                              "connected_states", "disconnected_states",
                              "energy_entity", "session_entity", "min_current_a", "max_current_a",
                              "phase_count", "control_owner", "physical_commissioned",
                              "phase_ids", "voltage_v", "current_step_a", "fixed_current_a",
                              "circuit_id", "circuit_limit_a", "current_control_entity",
                              "current_readback_entity", "min_charging_power_kw",
                              "max_charging_power_kw", "plan_color", "dedicated_asset_id"), "charger")
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
            legacy = source.get("physical_commissioned")
            if legacy is True and owner != "multicharge":
                raise ValueError("charger: physical commissioning requires MultiCharge owner")
            # A legacy uncommissioned writer never becomes active on upgrade.
            if owner == "multicharge" and legacy is False:
                owner = "external"
            if owner == "multicharge" and not str(source.get("control_entity", "")).startswith("switch."):
                raise ValueError("charger: managed control requires a native switch")
            charger["control_owner"] = owner
            # Compatibility projection, not an independent user setting.
            charger["physical_commissioned"] = owner == "multicharge"
            if ("connected_states" in source or "disconnected_states" in source):
                entity = source.get("connected_entity")
                if not isinstance(entity, str) or not entity.startswith("sensor."):
                    raise ValueError("charger: raw status mapping requires native sensor")
                for field in ("connected_states", "disconnected_states"):
                    labels = source.get(field)
                    if (not isinstance(labels, list)
                            or not 1 <= len(labels) <= 24
                            or any(not isinstance(label, str)
                                   or not label.strip() for label in labels)):
                        raise ValueError(f"charger.{field}: expected 1..24 state labels")
                    normalized = [label.strip().casefold() for label in labels]
                    if len(normalized) != len(set(normalized)):
                        raise ValueError(f"charger.{field}: duplicate source status")
                    charger[field] = normalized
                if set(charger["connected_states"]) & set(charger["disconnected_states"]):
                    raise ValueError("charger: ambiguous overlapping status mapping")
            if source.get("phase_count") is not None:
                p = source["phase_count"]
                if isinstance(p, bool) or not isinstance(p, int) or p not in (1, 2, 3):
                    raise ValueError("charger.phase_count: expected 1, 2 or 3")
                charger["phase_count"] = p
            for key in ("min_current_a", "max_current_a", "voltage_v",
                        "current_step_a", "fixed_current_a", "circuit_limit_a",
                        "min_charging_power_kw", "max_charging_power_kw"):
                if source.get(key) is not None:
                    charger[key] = _number(source[key], "charger." + key)
            if ("min_charging_power_kw" in charger
                    or "max_charging_power_kw" in charger):
                if charger["kind"] != "variable_current":
                    raise ValueError("charger power preferences require adjustable current")
                phase_count = charger.get("phase_count")
                chosen_min = charger.get("min_charging_power_kw", 0)
                chosen_max = charger.get("max_charging_power_kw", charger["rated_power_kw"])
                if chosen_min > chosen_max or chosen_max > charger["rated_power_kw"]:
                    raise ValueError("charger charging power limits exceed hardware envelope")
                # User preferences do not require conversion until actual current control.
                if phase_count is not None and charger.get("voltage_v"):
                    factor = charger["voltage_v"] * phase_count / 1000
                    # Persist user intent independently of live native number metadata.
                    # If explicit bounds exist, validate the complete declared envelope.
                    physical_min = charger.get("min_current_a", 0) * factor
                    physical_max = min(charger["rated_power_kw"],
                                       charger.get("max_current_a", charger["rated_power_kw"]/factor) * factor)
                    chosen_min = charger.get("min_charging_power_kw", physical_min)
                    chosen_max = charger.get("max_charging_power_kw", physical_max)
                    if (chosen_min < physical_min - 1e-6
                            or chosen_max > physical_max + 1e-6
                            or chosen_min > chosen_max + 1e-6):
                        raise ValueError("charger charging power limits exceed hardware envelope")
                    if all(key in charger for key in ("min_current_a", "max_current_a", "current_step_a")):
                        minimum, maximum = charger["min_current_a"], charger["max_current_a"]
                        step = charger["current_step_a"]
                        first = max(0, ceil((chosen_min / factor - minimum) / step - 1e-9))
                        last = min(
                            floor((maximum - minimum) / step + 1e-9),
                            floor((chosen_max / factor - minimum) / step + 1e-9),
                        )
                        if first > last:
                            raise ValueError("charger power envelope has no supported current step")
            if source.get("phase_ids") is not None:
                phases = source["phase_ids"]
                if not isinstance(phases, list) or not phases or (
                    len(phases) != len(set(phases))
                    or any(p not in ("L1", "L2", "L3") for p in phases)
                ):
                    raise ValueError("charger.phase_ids: expected unique L1/L2/L3")
                charger["phase_ids"] = list(phases)
                if charger.get("phase_count") is None:
                    charger["phase_count"] = len(phases)
            if source.get("circuit_id"):
                charger["circuit_id"] = _text(source["circuit_id"], "charger.circuit_id")
            if owner == "multicharge" and source["kind"] == "variable_current":
                if not str(source.get("current_control_entity", "")).startswith("number."):
                    raise ValueError("charger: variable current control requires a native number entity")
                if source.get("current_readback_entity") and not str(
                        source["current_readback_entity"]).startswith("sensor."):
                    raise ValueError("charger: independent current sensor required for that readback binding")
                if charger.get("voltage_v") is not None and not 200 <= charger["voltage_v"] <= 260:
                    raise ValueError("charger.voltage_v: expected declared line-neutral voltage")
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
            if source.get("dedicated_asset_id") is not None:
                dedicated = _text(source["dedicated_asset_id"], "charger.dedicated_asset_id")
                selected = next((a for a in assets if a["id"] == dedicated), None)
                if (dedicated != charger.get("asset") or not selected
                        or selected.get("temporary") or not charger.get("connected_entity")):
                    raise ValueError("dedicated assignment requires the selected permanent asset and connection source")
                charger["dedicated_asset_id"] = dedicated
            Charger(uid=uid, name=charger["name"], controller_uid=cid,
                    control_kind=charger["kind"], rated_power_kw=charger["rated_power_kw"],
                    min_current_a=charger.get("min_current_a"),
                    max_current_a=charger.get("max_current_a"),
                    phase_count=charger.get("phase_count"),
                    phase_ids=tuple(charger.get("phase_ids", ())),
                    voltage_v=charger.get("voltage_v"),
                    current_step_a=charger.get("current_step_a"),
                    min_charging_power_kw=charger.get("min_charging_power_kw"),
                    max_charging_power_kw=charger.get("max_charging_power_kw"),
                    fixed_current_a=charger.get("fixed_current_a"),
                    circuit_id=charger.get("circuit_id"),
                    circuit_limit_a=charger.get("circuit_limit_a"))
            chargers.append(charger)
        except ValueError as exc:
            identifier = source.get("id") if isinstance(source, dict) else None
            label = f" ({identifier})" if isinstance(identifier, str) else ""
            errors.append(f"chargers[{index}]{label}: {exc}")

    if errors:
        raise ValueError("\n".join(errors))

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
            # One native EVSE status may describe both connection and session
            # for the SAME charger; it is never shared between physical owners.
            shared_status = (previous[0] == charger["id"] and
                             {previous[1], role} == {"connected_entity", "session_entity"})
            if previous != (charger["id"], role) and not shared_status:
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


def energy_dashboard_suggestions(preferences):
    """Read optional HA Energy Dashboard entity associations, never its settings.

    HA's own configured solar/grid *power* sensors are suggestions, not
    inferred electrical capability, future tariffs or charging permission.
    Multiple grid/solar connections cannot be silently combined or guessed.
    """
    if not isinstance(preferences, dict):
        return {}
    sources = preferences.get("energy_sources", [])
    if not isinstance(sources, list):
        return {}
    choices = {}
    for kind, field in (("solar", "solar_power_entity"),
                        ("grid", "grid_power_entity")):
        matching = [row for row in sources if isinstance(row, dict)
                    and row.get("type") == kind]
        if len(matching) == 1:
            proposed = matching[0].get("stat_rate")
            if isinstance(proposed, str) and fullmatch(
                    r"sensor\.[a-z0-9_]+", proposed):
                choices[field] = proposed
    grid = [row for row in sources if isinstance(row, dict)
            and row.get("type") == "grid"]
    if len(grid) == 1:
        for attr, destination in (
            ("entity_energy_price", "current_price_entity"),
            ("entity_energy_price_export", "export_price_entity"),
        ):
            proposed = grid[0].get(attr)
            if isinstance(proposed, str) and fullmatch(
                    r"sensor\.[a-z0-9_]+", proposed):
                choices[destination] = proposed
    # Home-wide demand is not the sum of HA per-device counters. Never guess
    # a home power sensor from device_consumption or PV/energy kWh statistics.
    return choices


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


def charger_activation_reason(charger):
    """Only control_owner authorizes activation; reject inconsistent legacy input.

    Validated configuration derives physical_commissioned solely from owner.
    This invariant guard is not a second commissioning workflow.
    """
    if charger.get("control_owner") != "multicharge":
        return "EXTERNAL_WRITER_OWNS_CHARGER"
    if charger.get("physical_commissioned", True) is not True:
        return "PHYSICAL_COMMISSIONING_REQUIRED"
    return None


def charger_is_active(charger):
    return charger_activation_reason(charger) is None


def forecast_tariff_source(controller):
    """Forecast selection, distinct from an explicitly selected live tariff."""
    return controller.get("price_entity") or controller.get("current_price_entity")


def configuration_json(config):
    """Lossless human-editable JSON projection of the one validated Config Entry.

    This is transport and presentation only: no extra file, store, defaults,
    independent owner, or permission to bypass guarded physical commissioning.
    """
    return dumps(validate_configuration(config), indent=2, ensure_ascii=False)


def configuration_revision(config):
    """Stable optimistic lock for native settings; not a planner revision."""
    return sha256(dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]


def apply_settings_change(configuration, scope, target_id, changes, action="save", *,
                          site_time_zone="UTC"):
    """Narrow user-preference editor through the one native Config Entry authority.

    Physical ownership, commissioning, wiring and source device capabilities
    are deliberately NOT editable from this everyday surface.
    """
    if not isinstance(changes, dict) or not changes:
        raise ValueError("settings changes must contain values")
    allowed = {
        "controller": {
            "name", "max_parallel", "max_power_kw", "phase_limits_a",
            "power_adjustment_interval_minutes",
            "price_entity", "solar_entity", "site_power_entity",
            "solar_power_entity", "home_power_entity", "grid_power_entity",
            "solar_surplus_entity", "current_price_entity", "export_price_entity",
            "solar_source_kind", "grid_power_direction",
            "binding_entity", "mode",
            "plan_label_mode", "plan_color_by", "show_indicative_forecast",
        },
        "asset": {
            "name", "kind", "soc_entity", "soc_stale_entity", "capacity_kwh", "target_soc",
            "max_charge_kw", "requested_kwh", "requested_duration_minutes",
                          "requested_budget_amount", "requested_budget_currency",
            "ready_by", "ready_by_repeat", "ready_by_weekdays", "charging_windows",
            "continuous_charging",
            "minimum_soc_pct", "maximum_price_per_kwh", "price_currency",
            "low_price_trigger_per_kwh", "low_soc_trigger_pct",
            "opportunistic_kind", "opportunistic_level_pct",
            "earliest_start_at",
            "charge_efficiency", "priority",
            "temporary", "expires_at", "expected_connection_at",
            "plan_color",
        },
        "charger": {"name", "asset", "plan_color", "dedicated_asset_id",
                    "min_charging_power_kw", "max_charging_power_kw"},
    }
    # Atomic native Guest/Asset onboarding: assigning a presently unassigned
    # Charger is one Config Entry revision, never a second relation registry.
    create_charger_id = changes.get("assign_charger_id")
    if create_charger_id is not None and not (
            scope == "asset" and action == "create"
            and isinstance(create_charger_id, str)
            and create_charger_id.strip()):
        raise ValueError("assign_charger_id: only on Asset create")
    accepted_changes = {k: v for k, v in changes.items()
                        if k != "assign_charger_id"}
    if scope not in allowed or set(accepted_changes) - allowed[scope]:
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
    # Switching the selected vehicle on ONE Charger is an atomic change:
    # its previous vehicle is unassigned by replacement, not an active
    # physical identity transfer. The native settings writer separately
    # verifies charger idle, no open session and independent zero power
    # BEFORE committing. No intermediate "None" user step is required.
    if scope == "asset" and action in ("save", "create"):
        # Three finite intents share ONE Config Entry and cannot silently
        # coexist; target SoC remains a separate long-term vehicle preference.
        if changes.get("requested_budget_amount") is not None:
            target.pop("requested_kwh", None)
            target.pop("requested_duration_minutes", None)
            if not changes.get("requested_budget_currency"):
                changes = {**changes, "requested_budget_currency":
                           target.get("requested_budget_currency", "EUR")}
        elif changes.get("requested_kwh") is not None or (
                changes.get("requested_duration_minutes") is not None):
            target.pop("requested_budget_amount", None)
            target.pop("requested_budget_currency", None)
    for name, value in accepted_changes.items():
        if value is None or value == "":
            if name == "name":
                raise ValueError("name cannot be empty")
            target.pop(name, None)
        else:
            target[name] = value
    if scope == "asset" and action == "create":
        apply_new_asset_defaults(target, site_time_zone=site_time_zone)
        if create_charger_id is not None:
            chosen = next((c for c in cfg["chargers"]
                           if c["id"] == create_charger_id), None)
            if chosen is None:
                raise ValueError("unknown_free_charger")
            if chosen.get("asset") is not None:
                raise ValueError("charger_occupied")
            chosen["asset"] = target_id
    if scope == "charger" and changes.get("asset"):
        # One selected Charger per vehicle. Reassignment is one atomic
        # configuration edit, not delete/recreate or a second ownership store.
        for old in cfg["chargers"]:
            if old["id"] != target_id and old.get("asset") == changes["asset"]:
                old.pop("asset", None)
                old.pop("dedicated_asset_id", None)
    if scope == "charger" and "asset" in changes and "dedicated_asset_id" not in changes:
        if target.get("dedicated_asset_id") != target.get("asset"):
            target.pop("dedicated_asset_id", None)
    return validate_configuration(cfg)



def apply_dashboard_structure(configuration, scope, target_id, changes, action="save", *,
                              site_time_zone="UTC"):
    """Compose one object-scoped dashboard edit, then validate entire Config Entry.

    The UI sends individual typed fields, never a JSON document. This is an
    ephemeral prospective copy, not an alternate owner or settings database.
    Physical authorization belongs to the shared serialized HA writer.
    """
    if scope not in ("controller", "asset", "charger") or action not in (
            "save", "create", "delete"):
        raise ValueError("unsupported dashboard change")
    if not isinstance(changes, dict) or len(changes) > 32:
        raise ValueError("dashboard changes must contain bounded fields")
    if (not isinstance(target_id, str) or not target_id
            or len(target_id) > 100):
        raise ValueError("stable dashboard object ID required")
    forbidden = {"id", "physical_commissioned"}
    if forbidden & changes.keys():
        raise ValueError("ownership and identity cannot change in dashboard editor")
    cfg = deepcopy(configuration)
    if scope == "controller":
        if action != "save" or target_id != cfg["controller"]["id"]:
            raise ValueError("controller identity is immutable")
        target = cfg["controller"]
    else:
        items = cfg["assets" if scope == "asset" else "chargers"]
        target = next((x for x in items if x["id"] == target_id), None)
        if action == "create":
            if target is not None:
                raise ValueError("dashboard identity already exists")
            target = {"id": target_id}
            items.append(target)
        elif target is None:
            raise ValueError("dashboard object does not exist")
        elif action == "delete":
            if changes:
                raise ValueError("delete does not accept field updates")
            if scope == "asset" and any(
                    c.get("asset") == target_id for c in cfg["chargers"]):
                raise ValueError("unassign the vehicle before deletion")
            items.remove(target)
            return validate_configuration(cfg)
    if action != "delete":
        if scope == "charger" and "control_owner" in changes:
            target.pop("physical_commissioned", None)
        for key, value in changes.items():
            if not isinstance(key, str) or key.startswith("_"):
                raise ValueError("invalid dashboard field")
            if value is None or value == "":
                if key in ("name", "kind", "rated_power_kw"):
                    raise ValueError("required dashboard field cannot be cleared")
                target.pop(key, None)
            else:
                target[key] = value
        # The existing native row-level editor already implements atomic
        # reassign and single-target goal semantics; preserve those rules.
        if scope == "charger" and "asset" in changes:
            selected = changes["asset"]
            if selected:
                for old in cfg["chargers"]:
                    if old["id"] != target_id and old.get("asset") == selected:
                        old.pop("asset", None)
                        old.pop("dedicated_asset_id", None)
            if "dedicated_asset_id" not in changes and target.get("dedicated_asset_id") != target.get("asset"):
                target.pop("dedicated_asset_id", None)
        if scope == "asset" and changes.get("requested_budget_amount") is not None:
            target.pop("requested_kwh", None)
            target.pop("requested_duration_minutes", None)
        elif scope == "asset" and (
                changes.get("requested_kwh") is not None
                or changes.get("requested_duration_minutes") is not None):
            target.pop("requested_budget_amount", None)
            target.pop("requested_budget_currency", None)
        if scope == "asset" and action == "create":
            apply_new_asset_defaults(target, site_time_zone=site_time_zone)
        if scope == "charger" and action == "create":
            apply_new_charger_defaults(target)
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
                      "max_power_kw", "phase_limits_a",
                      "power_adjustment_interval_minutes"):
            result["controller"].pop(field, None)
        for asset in result["assets"]:
            for field in ("name", "kind", "plan_color", "capacity_kwh",
                          "target_soc", "max_charge_kw", "requested_kwh",
                          "requested_duration_minutes", "requested_budget_amount",
                           "requested_budget_currency", "ready_by",
                          "ready_by_repeat", "ready_by_weekdays", "charging_windows",
            "continuous_charging",
            "minimum_soc_pct", "maximum_price_per_kwh", "price_currency",
            "low_price_trigger_per_kwh", "low_soc_trigger_pct",
            "opportunistic_kind", "opportunistic_level_pct",
            "earliest_start_at",
            "charge_efficiency", "priority",
                          "temporary", "expires_at", "expected_connection_at"):
                asset.pop(field, None)
        for charger in result["chargers"]:
            for field in ("name", "plan_color", "asset",
                          "min_charging_power_kw", "max_charging_power_kw",
                          "control_owner", "physical_commissioned", "dedicated_asset_id"):
                charger.pop(field, None)
        return result

    return structure(before) == structure(after)


def assert_expert_authority_change(before, after):
    """Explicit authenticated control intent may change; preserve owned identities.

    This checks intent only. The serialized runtime writer separately protects
    outstanding commands/sessions and any required structural reload.
    """
    previous = {row["id"]: row for row in before["chargers"]}
    revised = {row["id"]: row for row in after["chargers"]}
    for uid, old in previous.items():
        if uid not in revised and old.get("control_owner") == "multicharge":
            raise ValueError(
                f"charger {old['name']} ({uid}): return to monitoring before removal"
            )



def prepare_expert_yaml_revision(current, document, mode="merge", *, site_time_zone="UTC"):
    """Prepare one YAML/JSON editor draft for the existing native Config Entry.

    Merge patches only provided logical IDs and leaves every other source and
    identity intact. Replace explicitly removes omitted objects. The editor
    cannot commission or transfer any physical charging writer.
    """
    before = validate_configuration(current)
    if mode not in ("merge", "replace"):
        raise ValueError("yaml update mode must be merge or replace")
    if not isinstance(document, dict):
        raise ValueError("expert YAML must contain a mapping")
    if "robotix_multicharge" in document:
        if set(document) != {"robotix_multicharge"}:
            raise ValueError(
                "Only robotix_multicharge may be imported here; HA template "
                "sensors and other packages must stay in Home Assistant YAML"
            )
        document = document["robotix_multicharge"]
    if not isinstance(document, dict):
        raise ValueError("robotix_multicharge must be a mapping")
    if any(key in document for key in ("Controller", "Charger", "ChargingAsset")):
        if mode != "replace":
            raise ValueError("Controller/Charger/ChargingAsset format requires replace mode")
        candidate = normalize_expert_json(document)
    else:
        _allowed(document, ("controller", "assets", "chargers"), "expert YAML")
        if mode == "replace":
            if "controller" not in document:
                raise ValueError("complete replacement requires controller")
            candidate = validate_configuration({
                "controller": document["controller"],
                "assets": document.get("assets", []),
                "chargers": document.get("chargers", []),
            })
        else:
            candidate = deepcopy(before)
            if "controller" in document:
                if not isinstance(document["controller"], dict):
                    raise ValueError("controller: expected mapping")
                candidate["controller"].update(document["controller"])
            for group in ("assets", "chargers"):
                if group not in document:
                    continue
                if not isinstance(document[group], list):
                    raise ValueError(f"{group}: expected list")
                rows = candidate[group]
                ids = set()
                for supplied in document[group]:
                    if not isinstance(supplied, dict):
                        raise ValueError(f"{group}: expected mapping")
                    key = _text(supplied.get("id"), f"{group}.id")
                    if key in ids:
                        raise ValueError(f"{group}: duplicate ID in YAML")
                    ids.add(key)
                    existing = next((row for row in rows if row["id"] == key), None)
                    if existing is None:
                        rows.append(deepcopy(supplied))
                    else:
                        if group == "chargers" and "control_owner" in supplied and "physical_commissioned" not in supplied:
                            existing.pop("physical_commissioned", None)
                        existing.update(deepcopy(supplied))
            candidate = validate_configuration(candidate)

    candidate = apply_new_import_defaults(
        before, candidate, site_time_zone=site_time_zone,
        raw_assets=document.get("assets", []),
    )
    if candidate["controller"]["id"] != before["controller"]["id"]:
        raise ValueError("controller ID cannot change in UI; preserve existing HA history")
    assert_expert_authority_change(before, candidate)
    return candidate


def apply_new_import_defaults(before, candidate, *, site_time_zone="UTC", raw_assets=()):
    """Creation defaults once; omitted goals on repeated input retain saved values.

    Explicit null target in a native expert editor is different from omission.
    Explicit ready_by_repeat=none is the existing schedule removal contract.
    """
    candidate = deepcopy(candidate)
    existing = {row["id"]: row for row in before.get("assets", [])}
    clear_target = {row["id"] for row in raw_assets
                    if isinstance(row, dict) and "id" in row
                    and "target_soc" in row and row["target_soc"] is None}
    schedule_fields = ("ready_by", "ready_by_repeat", "ready_by_weekdays")
    for asset in candidate["assets"]:
        prior = existing.get(asset["id"])
        if prior is None:
            if asset.get("soc_entity") and asset["id"] not in clear_target:
                apply_new_asset_defaults(asset, site_time_zone=site_time_zone)
            continue
        if asset["id"] not in clear_target and asset.get("soc_entity") and all(asset.get(key) is None for key in (
            "target_soc", "requested_kwh", "requested_duration_minutes",
            "requested_budget_amount",
        )) and prior.get("target_soc") is not None:
            asset["target_soc"] = prior["target_soc"]
        if not any(key in asset for key in schedule_fields):
            for key in schedule_fields:
                if key in prior:
                    asset[key] = deepcopy(prior[key])
    return validate_configuration(candidate)


# Expert JSON is only an adapter to the existing canonical Config Entry validator.
# Every command remains subject to the executor's physical admission/readback.
def normalize_expert_json(value):
    """Map human-readable direct JSON to one validated configuration authority."""
    if not isinstance(value, dict):
        raise ValueError("expert JSON: expected object")
    if not any(key in value for key in ("Controller", "Charger", "ChargingAsset")):
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
        "Power-adjustment-interval-minutes",
        "Phase-limits-A", "Price-entity", "Solar-entity",
        "Power-envelope-entity", "Plan-label-mode", "Plan-color-by",
        "Show-indicative-forecast",
        "Solar-power-entity", "Home-power-entity", "Grid-power-entity",
        "Solar-surplus-entity", "Current-price-entity", "Export-price-entity",
        "Solar-source-kind", "Grid-power-direction",
    ), "Controller")
    cfg = default_configuration(controller.get("Name") or "Home charging")
    ctl = cfg["controller"]
    if controller.get("ID"):
        ctl["id"] = _text(controller["ID"], "Controller.ID")
    for key, field in (
        ("Mode", "mode"), ("Max-parallel", "max_parallel"),
        ("Power-adjustment-interval-minutes", "power_adjustment_interval_minutes"),
        ("Max-power-kW", "max_power_kw"), ("Phase-limits-A", "phase_limits_a"),
        ("Plan-label-mode", "plan_label_mode"), ("Plan-color-by", "plan_color_by"),
        ("Show-indicative-forecast", "show_indicative_forecast"),
        ("Solar-source-kind", "solar_source_kind"),
        ("Grid-power-direction", "grid_power_direction"),
    ):
        if key in controller:
            ctl[field] = controller[key]
    for key, field in (
        ("Price-entity", "price_entity"), ("Solar-entity", "solar_entity"),
        ("Solar-power-entity", "solar_power_entity"),
        ("Home-power-entity", "home_power_entity"),
        ("Grid-power-entity", "grid_power_entity"),
        ("Solar-surplus-entity", "solar_surplus_entity"),
        ("Current-price-entity", "current_price_entity"),
        ("Export-price-entity", "export_price_entity"),
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
            "Vehicle-soc-stale-binary-sensor", "Usable-capacity-kWh", "Target-SoC-percent", "Max-charge-kW",
            "Requested-kWh", "Requested-duration-minutes", "Ready-by",
            "Requested-budget-amount", "Requested-budget-currency",
            "Ready-by-repeat", "Ready-by-weekdays", "Charging-windows",
            "Continuous-charging",
            "Minimum-SoC-pct", "Maximum-price-per-kWh", "Price-currency",
            "Low-price-trigger-per-kWh", "Low-SoC-trigger-pct",
            "Opportunistic-kind", "Opportunistic-level-pct", "Earliest-start-at",
            "Charging-efficiency", "Priority",
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
            ("Vehicle-soc-stale-binary-sensor", "soc_stale_entity", ("binary_sensor",)),
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
            ("Requested-budget-amount", "requested_budget_amount"),
            ("Requested-budget-currency", "requested_budget_currency"),
            ("Ready-by", "ready_by"), ("Ready-by-repeat", "ready_by_repeat"),
            ("Ready-by-weekdays", "ready_by_weekdays"),
            ("Charging-windows", "charging_windows"),
            ("Continuous-charging", "continuous_charging"),
            ("Minimum-SoC-pct", "minimum_soc_pct"),
            ("Maximum-price-per-kWh", "maximum_price_per_kwh"),
            ("Price-currency", "price_currency"),
            ("Low-price-trigger-per-kWh", "low_price_trigger_per_kwh"),
            ("Low-SoC-trigger-pct", "low_soc_trigger_pct"),
            ("Opportunistic-kind", "opportunistic_kind"),
            ("Opportunistic-level-pct", "opportunistic_level_pct"),
            ("Earliest-start-at", "earliest_start_at"),
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
            "Charging-connected-states", "Charging-disconnected-states",
        ), "Charger")
        name = _text(source.get("Name"), "Charger.Name")
        uid = _text(source.get("ID") or _slug(name), "Charger.ID")
        charger = {
            "id": uid, "name": name,
            "kind": source.get("Control-kind", "on_off"),
            "rated_power_kw": source.get("Rated-power-kW", 3.6),
            "control_owner": source.get("Control-owner", "external"),
            **({"physical_commissioned": source["Physical-commissioned"]}
               if "Physical-commissioned" in source else {}),
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
        for key, field in (
            ("Charging-connected-states", "connected_states"),
            ("Charging-disconnected-states", "disconnected_states"),
        ):
            if key in source:
                charger[field] = source[key]
        selected = source.get("ChargingAsset")
        if selected:
            if selected not in asset_ids:
                raise ValueError("Charger.ChargingAsset: unknown ChargingAsset")
            charger["asset"] = asset_ids[selected]

        # Never infer a nominal rating for an explicitly managed load.
        if charger["control_owner"] == "multicharge" and "Rated-power-kW" not in source:
            raise ValueError("Charger: managed control requires verified user-supplied rated power")
        cfg["chargers"].append(charger)
    return validate_configuration(cfg)

def _slug(name):
    """Use the same stable ID policy as the existing HA beginner wizard."""
    from re import sub
    return sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
