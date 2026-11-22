"""Real read-only Home Assistant Recorder telemetry for quarter-hour actuals.

No fabricated historical values. Incomplete, stale or missing source periods
are returned as unknown and never coerced into zero delivered energy.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite

QUARTER = timedelta(minutes=15)
MAX_OBSERVATION_AGE = timedelta(minutes=30)


def _sample(state):
    """Keep invalid native readings as gaps, never bridge over unavailable."""
    try:
        stamp = state.last_updated
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            return None
        stamp = stamp.astimezone(timezone.utc)
        factor = {"W": 0.001, "kW": 1.0}[state.attributes["unit_of_measurement"]]
        value = float(state.state) * factor
        if not isfinite(value) or value < 0:
            value = None
        return stamp, value
    except (KeyError, ValueError, TypeError, AttributeError, OverflowError):
        try:
            timestamp = state.last_updated
            if timestamp.tzinfo is not None and timestamp.utcoffset() is not None:
                return timestamp.astimezone(timezone.utc), None
        except (AttributeError, TypeError, ValueError, OverflowError):
            pass
        return None


def _quarter_actuals(states, first, last, now):
    """Integrate timestamped actual power, without inventing uncovered spans."""
    observations = sorted((value for row in states if (value := _sample(row))),
                          key=lambda row: row[0])
    series = []
    slot = datetime.fromtimestamp(
        (int(first.timestamp()) + 899) // 900 * 900, timezone.utc
    )
    while slot + QUARTER <= min(last, now):
        finish = slot + QUARTER
        earlier = [o for o in observations if o[0] <= slot]
        active = earlier[-1] if earlier else None
        events = [o for o in observations if slot < o[0] < finish]
        cursor = slot
        energy = 0.0
        valid = active is not None
        for next_stamp, value in (*events, (finish, None)):
            if (active is None or active[1] is None or active[0] > cursor
                    or next_stamp - active[0] > MAX_OBSERVATION_AGE):
                valid = False
                break
            energy += active[1] * (next_stamp - cursor).total_seconds() / 3600
            cursor = next_stamp
            active = (next_stamp, value)
        series.append({
            "start": slot.isoformat(),
            "end": finish.isoformat(),
            "actual_power_kw": round(energy * 4, 6) if valid else None,
            "actual_energy_kwh": round(energy, 6) if valid else None,
            "quality": "measured_power_integral" if valid else "unknown",
        })
        slot = finish
    return series


async def read_actual_history(hass, configuration, start, end, *,
                              charger_id=None, asset_id=None):
    """Query the installed native Recorder once for exact configured chargers."""
    now = datetime.now(timezone.utc)
    first, last = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    selected = [
        c for c in configuration["chargers"]
        if (charger_id is None or c["id"] == charger_id)
        and (asset_id is None or c.get("asset") == asset_id)
    ]
    if not selected:
        return [], "NO_MATCHING_CHARGER"
    entities = [c.get("power_entity") for c in selected]
    if any(not entity for entity in entities):
        return [], "POWER_METER_NOT_CONFIGURED"
    if last <= first or last - first > timedelta(hours=48):
        raise ValueError("historical view must be bounded to 48 hours")
    if first >= now:
        return [], "FUTURE_ONLY"
    if "recorder" not in hass.config.components:
        return [], "RECORDER_NOT_LOADED"
    try:
        from homeassistant.components.recorder import get_instance, history

        # Use the Recorder's own executor, preserving the native DB lifecycle.
        historical = await get_instance(hass).async_add_executor_job(
            history.get_significant_states,
            hass, first, min(last, now), entities,
            None, True, False, False, False, False,
        )
    except (ImportError, RuntimeError, ValueError, OSError, KeyError):
        return [], "RECORDER_UNAVAILABLE"
    result = []
    for charger in selected:
        rows = _quarter_actuals(
            historical.get(charger["power_entity"], []), first, last, now
        )
        for row in rows:
            row.update({"charger_id": charger["id"],
                        "asset_id": charger.get("asset")})
            result.append(row)
    if not result:
        return [], "NO_RECORDED_QUARTERS"
    if any(row["quality"] != "measured_power_integral" for row in result):
        return result, "INCOMPLETE_POWER_HISTORY"
    return result, "MEASURED_POWER_HISTORY"
