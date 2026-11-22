"""Native HA Recorder charging-power history; no planned-as-actual data."""
from __future__ import annotations

import logging
from bisect import bisect_right
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from math import isfinite

_LOGGER = logging.getLogger(__name__)
QUARTER = timedelta(minutes=15)
MAX_AGE = timedelta(minutes=30)
MAX_RECORDS = 20000


def measured_quarters(rows, start, end, now):
    """Integrate only recorded, sufficiently fresh native source power samples."""
    if any(t.tzinfo is None or t.utcoffset() is None for t in (start, end, now)):
        raise ValueError("timezone-aware bounds required")
    start, end, now = (t.astimezone(timezone.utc) for t in (start, end, now))
    if not start < end or end - start > timedelta(hours=48):
        raise ValueError("history interval must be positive and at most 48h")
    samples = []
    for row in rows:
        when = getattr(row, "last_updated", None)
        if not isinstance(when, datetime) or when.tzinfo is None:
            continue
        at = when.astimezone(timezone.utc)
        if at > now + timedelta(minutes=2):
            continue
        attrs = getattr(row, "attributes", None)
        units = attrs.get("unit_of_measurement") if isinstance(attrs, Mapping) else None
        factor = {"W": 0.001, "kW": 1.0}.get(units)
        try:
            value = float(row.state) * factor if factor is not None else None
            if value is not None and (not isfinite(value) or value < 0):
                value = None
        except (ValueError, TypeError, OverflowError):
            value = None
        samples.append((at, value))
    samples.sort(key=lambda s: s[0])
    times = [t for t, _ in samples]
    too_many = len(samples) > MAX_RECORDS
    out = []
    begin = start
    while begin < end:
        finish = min(end, begin + QUARTER)
        actual_end = min(finish, now)
        covered = energy = 0.0
        if not too_many and actual_end > begin:
            left = bisect_right(times, begin)
            right = bisect_right(times, actual_end)
            cuts = [begin, *times[left:right], actual_end]
            for a, b in zip(cuts, cuts[1:]):
                index = bisect_right(times, a) - 1
                if index < 0 or samples[index][1] is None:
                    continue
                good_until = min(b, samples[index][0] + MAX_AGE)
                if good_until > a:
                    seconds = (good_until - a).total_seconds()
                    covered += seconds
                    energy += samples[index][1] * seconds / 3600
        seconds = (finish - begin).total_seconds()
        complete = actual_end == finish and covered >= seconds - 0.001
        out.append({
            "start": begin.isoformat(), "end": finish.isoformat(),
            "actual_power_kw": round(energy * 3600 / seconds, 6) if complete else None,
            "actual_energy_kwh": round(energy, 6) if complete else None,
            "coverage": (
                "COMPLETE" if complete else "RECORD_LIMIT" if too_many
                else "FUTURE" if begin >= now
                else "PARTIAL" if covered else "UNKNOWN"
            ),
        })
        begin = finish
    return out


async def read_native_history(hass, chargers, start, end):
    """Use HA Recorder's own executor; absence is explicit, not a fabricated zero."""
    sources = {c["id"]: c["power_entity"] for c in chargers if c.get("power_entity")}
    if not sources:
        return {"status": "POWER_SOURCE_NOT_CONFIGURED", "chargers": {}}
    if "recorder" not in hass.config.components:
        return {"status": "RECORDER_NOT_LOADED", "chargers": {}}

    from homeassistant.components.recorder import get_instance, history

    now = datetime.now(timezone.utc)
    limit = min(end.astimezone(timezone.utc), now)
    if limit <= start.astimezone(timezone.utc):
        return {"status": "FUTURE_ONLY", "chargers": {}}
    try:
        observed = await get_instance(hass).async_add_executor_job(
            history.get_significant_states, hass, start, limit,
            list(set(sources.values())), None, True, False, False, False, False,
        )
    except (RuntimeError, KeyError) as exc:
        _LOGGER.warning("MultiCharge Recorder history unavailable: %s", exc)
        return {"status": "RECORDER_UNAVAILABLE", "chargers": {}}
    return {
        "status": "RECORDED" if observed else "NO_RECORDED_STATES",
        "chargers": {
            uid: measured_quarters(observed.get(entity, ()), start, end, now)
            for uid, entity in sources.items()
        },
    }
