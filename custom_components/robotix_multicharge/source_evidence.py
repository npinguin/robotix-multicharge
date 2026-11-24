"""Fail-closed normalization of explicitly selected native HA source entities.

No entity-name heuristics, vendor SDKs, implicit forecasts or conversion of a
successful HA service request into physical charging success.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


def soc_with_health(hass, soc_entity, stale_entity, now) -> Evidence:
    """One native SoC with optional independent OEM stale/validity evidence.

    A stale flag is not a value source; a stale numeric SoC must never become
    a trustworthy target or remaining-demand signal.
    """
    reading = number(hass, soc_entity, "soc", now)
    if not stale_entity:
        return reading
    if not isinstance(stale_entity, str) or not stale_entity.startswith(
            "binary_sensor."):
        return Evidence(None, "invalid", None, "SOC_HEALTH_DOMAIN_INVALID")
    state, flag = _state(hass, stale_entity, now, timedelta(hours=2))
    if state is None:
        return Evidence(None, flag.quality, flag.observed_at,
                        "SOC_HEALTH_" + flag.reason)
    if state.state == "on":
        return Evidence(None, "stale", flag.observed_at, "SOC_OEM_DATA_STALE")
    if state.state != "off":
        return Evidence(None, "invalid", flag.observed_at, "SOC_HEALTH_AMBIGUOUS")
    return reading


def live_power(hass, entity_id: str | None, now: datetime, *,
               signed=False) -> Evidence:
    """Instantaneous native HA W/kW power, never energy (Wh/kWh) or forecasts.

    Limit observation age to two minutes for live energy decisions and display.
    Signed grid import/export power is permitted only when sign semantics
    are explicitly selected in the charging-site configuration.
    """
    obj, evidence = _state(hass, entity_id, now, timedelta(minutes=2))
    if obj is None:
        return evidence
    factor = {"W": 0.001, "kW": 1.0}.get(
        obj.attributes.get("unit_of_measurement")
    )
    if factor is None:
        return Evidence(None, "invalid", evidence.observed_at, "POWER_UNIT_UNVERIFIED")
    try:
        value = float(obj.state) * factor
        if not isfinite(value) or (value < 0 and not signed):
            raise ValueError("power reading not physically valid")
    except (TypeError, ValueError, OverflowError):
        return Evidence(None, "invalid", evidence.observed_at, "POWER_VALUE_INVALID")
    return Evidence(round(value, 6), "ok", evidence.observed_at, "OK")


def _price_unit(attrs):
    """Return currency and scale to currency/kWh; no guessed currencies."""
    unit = attrs.get("unit_of_measurement")
    if not isinstance(unit, str) or unit.count("/") != 1:
        return None, None
    currency, denominator = unit.split("/", 1)
    scale = {"Wh": 1000.0, "kWh": 1.0, "MWh": 0.001}.get(denominator)
    if scale is None:
        return None, None
    if currency == "€":
        currency = "EUR"
    elif currency in ("cEUR", "€ct", "ct€", "c€"):
        currency, scale = "EUR", scale / 100
    elif currency == "c" and attrs.get("price_in_cents") is True:
        # Nordpool HACS uses c for EUR, Øre/Öre for other currencies.
        currency, scale = "EUR", scale / 100
    elif currency in ("Øre", "Öre", "ct"):
        declared = attrs.get("currency")
        if declared not in ("DKK", "NOK", "SEK", "EUR"):
            return None, None
        currency, scale = declared, scale / 100
    if (len(currency) != 3 or not currency.isascii() or not currency.isupper()
            or not currency.isalpha() or attrs.get("currency", currency) != currency):
        return None, None
    return currency, scale


def live_price(hass, entity_id: str | None, now: datetime):
    """Indicative current native HA tariff, not a future pricing schedule.

    Return a separately qualified currency and never infer billing basis.
    The actual effective tariff receipts still require covered price slots.
    """
    obj, evidence = _state(hass, entity_id, now, timedelta(minutes=20))
    if obj is None:
        return evidence, None
    currency, scale = _price_unit(obj.attributes)
    if scale is None:
        return Evidence(None, "invalid", evidence.observed_at,
                        "PRICE_UNIT_UNVERIFIED"), None
    try:
        value = float(obj.state) * scale
        if not isfinite(value):
            raise ValueError("invalid price")
    except (TypeError, ValueError, OverflowError):
        return Evidence(None, "invalid", evidence.observed_at,
                        "PRICE_VALUE_INVALID"), None
    return Evidence(round(value, 8), "ok", evidence.observed_at,
                    "CURRENT_PRICE_ONLY"), currency


def connection(hass, entity_id: str | None, now: datetime, *,
               connected_states=None, disconnected_states=None) -> Evidence:
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
        else {"connected": True, "disconnected": False, "manual_confirmed": True} if domain == "sensor"
        else {}
    )
    if connected_states is not None or disconnected_states is not None:
        if (domain != "sensor"
                or not isinstance(connected_states, list)
                or not isinstance(disconnected_states, list)
                or not connected_states or not disconnected_states):
            return Evidence(None, "invalid", evidence.observed_at,
                            "CONNECTION_MAPPING_INVALID")
        positive = {label.casefold() for label in connected_states}
        negative = {label.casefold() for label in disconnected_states}
        if positive & negative:
            return Evidence(None, "invalid", evidence.observed_at,
                            "CONNECTION_MAPPING_AMBIGUOUS")
        allowed = {**dict.fromkeys(positive, True),
                   **dict.fromkeys(negative, False)}
    raw = str(obj.state).strip().casefold()
    if raw in ("fault", "faulted", "error", "reserved"):
        return Evidence(None, "invalid", evidence.observed_at, "CONNECTION_PROVIDER_BLOCKED")
    value = allowed.get(raw)
    if value is None:
        return Evidence(None, "invalid", evidence.observed_at, "CONNECTION_AMBIGUOUS")
    return Evidence(value, "ok", evidence.observed_at,
                    "USER_CONFIRMED_CONNECTION" if raw == "manual_confirmed" and value else "OK")



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
            "inactive": "inactive", "running": "charging",
            "suspended": "paused", "suspended_ev": "paused", "suspendedev": "paused",
            "suspended_evse": "paused", "suspendedevse": "paused",
            "finishing": "stopped", "preparing": "stopped", "available": "idle",
            "fault": "fault", "faulted": "fault", "error": "fault",
            "reserved": "unavailable",
        }
    else:
        labels = {}
    if value not in labels:
        return Evidence(None, "invalid", evidence.observed_at, "SESSION_STATUS_AMBIGUOUS")
    reason = {"suspended_ev": "SUSPENDED_EV", "suspendedev": "SUSPENDED_EV",
              "suspended_evse": "SUSPENDED_EVSE", "suspendedevse": "SUSPENDED_EVSE",
              "reserved": "PROVIDER_RESERVED"}.get(value, "OK")
    return Evidence(labels[value], "ok", evidence.observed_at, reason)

def _native_spot_price_intervals(obj, now):
    """Read native raw_today/raw_tomorrow without a Robotix template bridge.

    This layout is used by some HA-native price providers. Prices are SPOT
    estimates for Economy ranking only, never qualified all-in session cost.
    Every value carries a source-declared ISO currency/energy unit.
    """
    attrs = obj.attributes
    currency, multiplier = _price_unit(attrs)
    if multiplier is None:
        return (), "INTERVAL_CURRENCY_OR_UNIT_UNVERIFIED"
    raw_today = attrs.get("raw_today")
    raw_tomorrow = attrs.get("raw_tomorrow")
    if not isinstance(raw_today, list) or raw_tomorrow is not None and not isinstance(
            raw_tomorrow, list):
        return (), "INTERVAL_PAYLOAD_INVALID"
    raw = [*raw_today, *((raw_tomorrow or []) if attrs.get("tomorrow_valid") is not False else [])]
    if not raw or len(raw) > 256:
        return (), "INTERVAL_PAYLOAD_INVALID"
    try:
        slots = [
            PriceSlot(
                _date(row["start"]), _date(row["end"]),
                float(row["value"]) * multiplier, currency, basis="spot",
            )
            for row in raw
        ]
        slots.sort(key=lambda x: x.start)
        if any(a.end > b.start for a, b in zip(slots, slots[1:])):
            return (), "INTERVAL_OVERLAP"
        if slots[-1].end <= now:
            return (), "INTERVAL_SOURCE_EXPIRED"
        return tuple(slots), "OK"
    except (KeyError, TypeError, ValueError, OverflowError):
        return (), "INTERVAL_PAYLOAD_INVALID"


def _native_all_in_reference_intervals(hass, obj, now, *, split_prices=False,
                                       coverage_details=None):
    """Use full native electricity-price days without a Robotix bridge.

    A provider that explicitly publishes timestamped all_in EUR/kWh values
    supplies *variable reference* prices. These can order Economy plans;
    neither name nor values establish billed tariffs or historical settlement.
    """
    attrs = obj.attributes
    if attrs.get("unit_of_measurement") not in ("EUR/kWh", "€/kWh"):
        return (), "INTERVAL_CURRENCY_OR_UNIT_UNVERIFIED"
    if attrs.get("currency", "EUR") != "EUR":
        return (), "INTERVAL_CURRENCY_OR_UNIT_UNVERIFIED"
    if attrs.get("snapshot_stale") not in (None, False):
        return (), "INTERVAL_SOURCE_STALE"
    raw_today = attrs.get("prices_today" if split_prices else "today")
    raw_tomorrow = attrs.get("prices_tomorrow" if split_prices else "tomorrow")
    stamp_key, price_key = ("time", "price") if split_prices else ("start", "all_in")
    if not isinstance(raw_today, list) or not raw_today:
        return (), "INTERVAL_PAYLOAD_INVALID"
    zone_name = attrs.get("time_zone") or getattr(
        getattr(hass, "config", None), "time_zone", None
    )
    if not isinstance(zone_name, str) or not zone_name:
        return (), "INTERVAL_TIMEZONE_UNVERIFIED"
    try:
        zone = ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError, ValueError):
        return (), "INTERVAL_TIMEZONE_UNVERIFIED"
    local_today = now.astimezone(zone).date()
    def normalize_day(day, local_date):
        # Commit a day only after every interval and the civil-day boundaries
        # have passed validation. Never carry partly validated tomorrow slots.
        if not isinstance(day, list):
            return (), "INTERVAL_PAYLOAD_INVALID"
        count = len(day)
        if count not in (23, 24, 25, 92, 96, 100):
            return (), "INTERVAL_COVERAGE_INCOMPLETE"
        step = timedelta(minutes=15) if count >= 90 else timedelta(hours=1)
        next_date = local_date + timedelta(days=1)
        expected_start = datetime(
            local_date.year, local_date.month, local_date.day, tzinfo=zone,
        ).astimezone(timezone.utc)
        expected_end = datetime(
            next_date.year, next_date.month, next_date.day, tzinfo=zone,
        ).astimezone(timezone.utc)
        if expected_end - expected_start != count * step:
            return (), "INTERVAL_COVERAGE_INCOMPLETE"
        try:
            first = _date(day[0][stamp_key])
            if first != expected_start:
                return (), "INTERVAL_TIME_INVALID"
            slots = []
            for index, row in enumerate(day):
                expected = first + index * step
                if _date(row[stamp_key]) != expected:
                    return (), "INTERVAL_COVERAGE_INCOMPLETE"
                price = float(row[price_key])
                if not isfinite(price):
                    return (), "INTERVAL_PAYLOAD_INVALID"
                slots.append(PriceSlot(
                    expected, expected + step, price, "EUR",
                    basis="variable_reference",
                ))
            if slots[-1].end != expected_end:
                return (), "INTERVAL_COVERAGE_INCOMPLETE"
            return tuple(slots), "OK"
        except (KeyError, IndexError, TypeError, ValueError, OverflowError):
            return (), "INTERVAL_PAYLOAD_INVALID"

    try:
        if not isfinite(float(obj.state)):
            return (), "INTERVAL_PAYLOAD_INVALID"
    except (TypeError, ValueError, OverflowError):
        return (), "INTERVAL_PAYLOAD_INVALID"
    today, quality = normalize_day(raw_today, local_today)
    if quality != "OK":
        return (), quality
    if today[-1].end <= now:
        return (), "INTERVAL_SOURCE_EXPIRED"
    if today[0].start > now:
        return (), "INTERVAL_COVERAGE_INCOMPLETE"
    if raw_tomorrow is None or raw_tomorrow == []:
        tomorrow, tomorrow_quality = (), "SOURCE_UNAVAILABLE"
    else:
        tomorrow, tomorrow_quality = normalize_day(
            raw_tomorrow, local_today + timedelta(days=1),
        )
    if coverage_details is not None:
        coverage_details["tomorrow_quality"] = tomorrow_quality
    return today + tomorrow, "OK"


def native_price_rows(raw, now, currency, scale, *, start="start", end="end",
                      value="price", basis="variable_reference"):
    """Normalize explicit native spans; never bridge missing intervals."""
    if not isinstance(raw, list) or not raw or len(raw) > 400:
        return (), "INTERVAL_PAYLOAD_INVALID"
    try:
        slots = sorted((PriceSlot(
            _date(row[start]), _date(row[end]), float(row[value]) * scale,
            currency, basis=basis,
        ) for row in raw), key=lambda x: x.start)
        if any(a.end > b.start for a, b in zip(slots, slots[1:])):
            return (), "INTERVAL_OVERLAP"
        if slots[-1].end <= now:
            return (), "INTERVAL_SOURCE_EXPIRED"
        return tuple(slots), "OK"
    except (KeyError, TypeError, ValueError, OverflowError):
        return (), "INTERVAL_PAYLOAD_INVALID"


async def async_native_nordpool_prices(hass, source, now):
    """Read the official Nord Pool action through the selected HA entity."""
    import asyncio
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.helpers import entity_registry as er

    entity = er.async_get(hass).async_get(source)
    if (entity is None or entity.platform != "nordpool"
            or not entity.unique_id.endswith("-current_price")
            or not entity.config_entry_id):
        return None
    provider = hass.config_entries.async_get_entry(entity.config_entry_id)
    if provider is None or provider.domain != "nordpool":
        return None
    area = entity.unique_id.removesuffix("-current_price")
    currency = provider.data.get("currency")
    if (area not in provider.data.get("areas", []) or not isinstance(currency, str)
            or len(currency) != 3 or not currency.isascii() or not currency.isupper()
            or not currency.isalpha()):
        return (), "NORDPOOL_SELECTION_UNVERIFIED"
    if not hass.services.has_service("nordpool", "get_prices_for_date"):
        return (), "NORDPOOL_ACTION_UNAVAILABLE"
    market_day = now.astimezone(ZoneInfo("Europe/Oslo")).date()
    rows = []
    for day in (market_day, market_day + timedelta(days=1)):
        try:
            async with asyncio.timeout(10):
                response = await hass.services.async_call(
                    "nordpool", "get_prices_for_date",
                    {"config_entry": provider.entry_id, "date": day.isoformat(),
                     "areas": [area], "currency": currency},
                    blocking=True, return_response=True,
                )
            data = response.get(area, []) if isinstance(response, dict) else []
            if data:
                slots, quality = native_price_rows(data, now, currency, 0.001, basis="spot")
                if quality == "OK":
                    rows.extend(slots)
        except (HomeAssistantError, TimeoutError, ValueError, TypeError, KeyError):
            # Tomorrow may be unpublished; keep today's validated curve.
            continue
    rows.sort(key=lambda row: row.start)
    if not rows or any(a.end > b.start for a, b in zip(rows, rows[1:])):
        return (), "NORDPOOL_FORECAST_UNAVAILABLE"
    return tuple(rows), "OK"


def _native_timestamp_prices(hass, obj, now):
    """ENTSO-e timestamped prices: a complete local day establishes cadence.

    No interpolation or extension across missing values.
    """
    attrs = obj.attributes
    currency, scale = _price_unit(attrs)
    if scale is None:
        return (), "INTERVAL_CURRENCY_OR_UNIT_UNVERIFIED"
    raw = attrs.get("prices")
    if not isinstance(raw, list) or not raw or len(raw) > 400:
        return (), "INTERVAL_PAYLOAD_INVALID"
    try:
        zone = ZoneInfo(hass.config.time_zone)
        points = sorted((_date(row["time"]), float(row["price"])) for row in raw)
        if len({stamp for stamp, _ in points}) != len(points):
            return (), "INTERVAL_OVERLAP"
        by_day = {}
        for stamp, _ in points:
            by_day.setdefault(stamp.astimezone(zone).date(), []).append(stamp)
        candidates = set()
        for day, stamps in by_day.items():
            first = datetime.combine(day, datetime.min.time(), tzinfo=zone).astimezone(timezone.utc)
            last = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=zone).astimezone(timezone.utc)
            for minutes in (15, 60):
                step = timedelta(minutes=minutes)
                if (len(stamps) * step == last - first and stamps[0] == first
                        and all(b-a == step for a,b in zip(stamps, stamps[1:]))):
                    candidates.add(minutes)
        if len(candidates) != 1:
            return (), "INTERVAL_RESOLUTION_UNVERIFIED"
        step = timedelta(minutes=candidates.pop())
        rows = [{"start": stamp, "end": stamp + step, "price": price}
                for stamp, price in points]
        return native_price_rows(rows, now, currency, scale)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError, ZoneInfoNotFoundError):
        return (), "INTERVAL_PAYLOAD_INVALID"


def _native_explicit_prices(obj, now):
    """Common timestamped data, including EPEX Spot and HA action templates."""
    attrs = obj.attributes
    currency, scale = _price_unit(attrs)
    if scale is None:
        return (), "INTERVAL_CURRENCY_OR_UNIT_UNVERIFIED"
    raw = attrs.get("data", attrs.get("intervals"))
    if not isinstance(raw, list) or not raw or not isinstance(raw[0], dict):
        return (), "INTERVAL_PAYLOAD_INVALID"
    row = raw[0]
    if {"start", "end", "price"} <= row.keys():
        return native_price_rows(raw, now, currency, scale)
    if {"start", "end", "value"} <= row.keys():
        return native_price_rows(raw, now, currency, scale, value="value")
    if {"start_time", "end_time"} <= row.keys():
        for field, factor in ((f"price_{currency.lower()}_per_kwh", 1.0),
                              (f"price_{currency.lower()}_per_mwh", 0.001),
                              ("price_per_kwh", 1.0),
                              ("price_ct_per_kwh", 0.01)):
            if field in row:
                return native_price_rows(raw, now, currency, factor,
                                         start="start_time", end="end_time", value=field)
    return (), "INTERVAL_SEMANTICS_UNVERIFIED"


def intervals(hass, entity_id: str | None, kind: str, now: datetime, *,
              coverage_details=None):
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
        # A native HA spot-price provider can be bound directly; it is
        # NEVER promoted to an effective/all-in monetary source.
        if kind == "price" and "raw_today" in obj.attributes:
            return _native_spot_price_intervals(obj, now)
        if (kind == "price" and "today" in obj.attributes
                and obj.attributes.get("unit_of_measurement")
                    in ("EUR/kWh", "€/kWh")):
            return _native_all_in_reference_intervals(
                hass, obj, now, coverage_details=coverage_details,
            )
        if kind == "price" and "prices_today" in obj.attributes:
            return _native_all_in_reference_intervals(
                hass, obj, now, split_prices=True, coverage_details=coverage_details,
            )
        if kind == "price" and "prices" in obj.attributes:
            return _native_timestamp_prices(hass, obj, now)
        if kind == "price" and ("data" in obj.attributes or "intervals" in obj.attributes):
            if obj.attributes.get("kind") is None:
                return _native_explicit_prices(obj, now)
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
