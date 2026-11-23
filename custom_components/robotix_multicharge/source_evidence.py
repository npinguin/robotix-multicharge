"""Fail-closed normalization of explicitly selected native HA source entities.

No entity-name heuristics, vendor SDKs, implicit forecasts or conversion of a
successful HA service request into physical charging success.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite

from .contracts import PowerEnvelope, PowerLimitSlot, PriceSlot


@dataclass(frozen=True)
class Evidence:
    value: float | bool | str | None
    quality: str
    observed_at: datetime | None
    reason: str


def _date(raw):
    if isinstance(raw, datetime):
        dt = raw
    elif isinstance(raw, str):
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    else:
        raise ValueError("expected aware date/time")
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)


def _state(hass, entity_id, now, max_age):
    if not entity_id:
        return None, Evidence(None, "unknown", None, "SOURCE_NOT_SELECTED")
    obj = hass.states.get(entity_id)
    if obj is None:
        return None, Evidence(None, "unavailable", None, "SOURCE_MISSING")
    try:
        # HA last_updated changes only when a value/attribute changes. Real
        # periodic reporting of an unchanged physical sensor updates
        # last_reported, which is the correct freshness evidence.
        reported = getattr(obj, "last_reported", None)
        observed = _date(reported if reported is not None else obj.last_updated)
    except (TypeError, ValueError, OverflowError, AttributeError):
        return None, Evidence(None, "invalid", None, "SOURCE_TIME_INVALID")
    if observed > now + timedelta(minutes=2):
        return None, Evidence(None, "invalid", observed, "SOURCE_TIME_FUTURE")
    if now - observed > max_age:
        return None, Evidence(None, "stale", observed, "SOURCE_STALE")
    if obj.state in ("unknown", "unavailable", None, ""):
        return None, Evidence(None, "unavailable", observed, "SOURCE_UNAVAILABLE")
    return obj, Evidence(None, "ok", observed, "OK")


def number(hass, entity_id, kind: str, now: datetime) -> Evidence:
    """Read only known W/kW, Wh/kWh and % units, keeping genuine zero."""
    max_age = timedelta(hours=2) if kind == "soc" else timedelta(minutes=30)
    obj, evidence = _state(hass, entity_id, now, max_age)
    if obj is None:
        return evidence
    units = {"soc": {"%": 1.0}, "power": {"W": 0.001, "kW": 1.0},
             "energy": {"Wh": 0.001, "kWh": 1.0},
             "current": {"A": 1.0}}
    factors = units.get(kind)
    if factors is None:
        raise ValueError("unsupported measurement type")
    factor = factors.get(obj.attributes.get("unit_of_measurement"))
    if factor is None:
        return Evidence(None, "invalid", evidence.observed_at, "UNIT_UNSUPPORTED")
    try:
        value = float(obj.state) * factor
        if not isfinite(value) or value < 0 or (kind == "soc" and value > 100):
            raise ValueError("invalid measurement")
    except (TypeError, ValueError, OverflowError):
        return Evidence(None, "invalid", evidence.observed_at, "VALUE_INVALID")
    return Evidence(round(value, 6), "ok", evidence.observed_at, "OK")


def connection(hass, entity_id: str | None, now: datetime) -> Evidence:
    obj, evidence = _state(hass, entity_id, now, timedelta(minutes=30))
    if obj is None and evidence.reason == "SOURCE_STALE":
        # A site-owned semantic cable template can remain *unchanged* in HA
        # even while its native hardware source reports an identical physical
        # state periodically. Never freshen it with now(); instead require an
        # actually fresh native source and exact matching raw source status.
        # Unknown manual-confirmation templates do NOT qualify by this path.
        bridge = hass.states.get(entity_id)
        attrs = getattr(bridge, "attributes", {}) or {}
        origin_id = attrs.get("source_entity_id")
        if (attrs.get("source_type") == "native_charger_status"
                and isinstance(origin_id, str)
                and origin_id.startswith("sensor.")
                and origin_id != entity_id):
            origin, observed = _state(
                hass, origin_id, now, timedelta(minutes=30)
            )
            if origin is None:
                return observed
            original_raw = attrs.get("raw_status")
            if (not isinstance(original_raw, str)
                    or original_raw.strip().casefold()
                    != str(origin.state).strip().casefold()):
                return Evidence(
                    None, "invalid", observed.observed_at,
                    "BRIDGE_SOURCE_STATUS_DIVERGED",
                )
            obj = bridge
            evidence = observed
    if obj is None:
        return evidence
    # A plug being ON is not proof a vehicle is physically connected. Only
    # explicitly selected binary_sensor or semantic sensor evidence qualifies.
    domain = entity_id.split(".", 1)[0]
    allowed = (
        {"on": True, "off": False} if domain == "binary_sensor"
        else {"connected": True, "disconnected": False} if domain == "sensor"
        else {}
    )
    value = allowed.get(str(obj.state).lower())
    if value is None:
        return Evidence(None, "invalid", evidence.observed_at, "CONNECTION_AMBIGUOUS")
    return Evidence(value, "ok", evidence.observed_at, "OK")



def session_status(hass, entity_id: str | None, now: datetime) -> Evidence:
    """Read independent source session state without treating it as charging power.

    A native session flag is informational: active does not prove cable,
    identity, meter delivery or authority to issue an EVSE command.
    """
    obj, evidence = _state(hass, entity_id, now, timedelta(minutes=30))
    if obj is None:
        return evidence
    domain = entity_id.split(".", 1)[0]
    value = str(obj.state).strip().lower()
    if domain == "binary_sensor":
        labels = {"on": "active", "off": "inactive"}
    elif domain == "sensor":
        labels = {
            "charging": "charging", "active": "active",
            "paused": "paused", "idle": "idle",
            "stopped": "stopped", "completed": "completed",
            "inactive": "inactive",
        }
    else:
        labels = {}
    if value not in labels:
        return Evidence(None, "invalid", evidence.observed_at, "SESSION_STATUS_AMBIGUOUS")
    return Evidence(labels[value], "ok", evidence.observed_at, "OK")

def intervals(hass, entity_id: str | None, kind: str, now: datetime):
    """Accept only a versioned, source-qualified series of real interval data.

    Expected attributes:
    kind=effective_price_kwh|solar_limit_kw, valid_until=aware ISO timestamp,
    intervals=[{start, end, value}], and price sources require currency=ISO-4217.
    No silent spot/all-in, currency or provider assumption.
    """
    obj, evidence = _state(hass, entity_id, now, timedelta(hours=24))
    if obj is None:
        return (), evidence.reason
    expected = {"price": "effective_price_kwh", "solar": "solar_limit_kw"}
    if kind not in expected:
        raise ValueError("unsupported interval kind")
    if obj.attributes.get("kind") != expected[kind]:
        return (), "INTERVAL_SEMANTICS_UNVERIFIED"
    try:
        expires = _date(obj.attributes["valid_until"])
        if expires <= now:
            return (), "INTERVAL_SOURCE_EXPIRED"
        raw = obj.attributes["intervals"]
        if not isinstance(raw, list) or len(raw) > 256:
            return (), "INTERVAL_PAYLOAD_INVALID"
        slots = []
        for item in raw:
            start, end = _date(item["start"]), _date(item["end"])
            value = float(item["value"])
            if end > expires:
                return (), "INTERVAL_EXCEEDS_VALIDITY"
            if not isfinite(value):
                raise ValueError("invalid interval")
            if kind == "price":
                slots.append(PriceSlot(start, end, value, obj.attributes["currency"]))
            else:
                slots.append(PowerLimitSlot(start, end, value))
        slots.sort(key=lambda s: s.start)
        if any(a.end > b.start for a, b in zip(slots, slots[1:])):
            return (), "INTERVAL_OVERLAP"
        return tuple(slots), "OK"
    except (KeyError, TypeError, ValueError, OverflowError):
        return (), "INTERVAL_PAYLOAD_INVALID"


def binding(hass, entity_id: str | None, now: datetime):
    """Verify an externally owned *binding* site power envelope or fail closed.

    Only explicitly selected, fresh, revisioned limits with non-overlapping
    time-covered slots qualify. Source binding is not a cryptographic
    signature or permission to actuate; execution has a separate gate.
    """
    obj, evidence = _state(hass, entity_id, now, timedelta(minutes=20))
    if obj is None:
        return None, evidence.reason
    a = obj.attributes
    if a.get("kind") != "binding_power_envelope" or a.get("authority") != "binding":
        return None, "ENVELOPE_AUTHORITY_UNVERIFIED"
    try:
        issued_at = _date(a["issued_at"])
        valid_until = _date(a["valid_until"])
        if issued_at > now or valid_until <= now:
            return None, "ENVELOPE_EXPIRED_OR_FUTURE"
        provider = a["provider_id"]
        revision = a["revision"]
        raw = a["intervals"]
        if not isinstance(raw, list) or len(raw) > 256:
            return None, "ENVELOPE_PAYLOAD_INVALID"
        slots = []
        for item in raw:
            slots.append(PowerLimitSlot(
                _date(item["start"]), _date(item["end"]),
                float(item["max_charging_kw"]),
            ))
        slots.sort(key=lambda s: s.start)
        envelope = PowerEnvelope(
            provider, revision, issued_at, valid_until, "binding", tuple(slots)
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return None, "ENVELOPE_PAYLOAD_INVALID"
    return envelope, "OK"
