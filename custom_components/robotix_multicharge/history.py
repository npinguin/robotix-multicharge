"""Real read-only Home Assistant Recorder telemetry for quarter-hour actuals.

No fabricated historical values. Incomplete, stale or missing source periods
are returned as unknown and never coerced into zero delivered energy.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import isfinite

QUARTER = timedelta(minutes=15)
MAX_OBSERVATION_AGE = timedelta(minutes=30)


def reconcile_power_bindings(previous, configuration, at):
    """Retain binding metadata, not measured values, in the existing Store.

    On legacy migration the current source is the only known binding; no
    earlier undocumented changes can be reconstructed. Later remaps start
    at their actual runtime application time, including deletion tombstones.
    """
    at = at.astimezone(timezone.utc)
    current = {c["id"]: c.get("power_entity") for c in configuration["chargers"]}
    if previous is None:
        return {uid: [{"start": None, "entity": entity}]
                for uid, entity in current.items()}
    bindings = deepcopy(previous)
    if not isinstance(bindings, dict):
        raise ValueError("invalid stored power bindings")
    for uid, epochs in bindings.items():
        if not isinstance(uid, str) or not isinstance(epochs, list) or not epochs or len(epochs) > 256:
            raise ValueError("invalid stored power binding epochs")
        last = None
        for index, epoch in enumerate(epochs):
            if not isinstance(epoch, dict) or set(epoch) != {"start", "entity"}:
                raise ValueError("invalid power binding epoch")
            entity = epoch["entity"]
            if entity is not None and (not isinstance(entity, str) or "." not in entity):
                raise ValueError("invalid power binding source")
            stamp = epoch["start"]
            if stamp is None and index == 0:
                continue
            moment = datetime.fromisoformat(stamp)
            if moment.utcoffset() is None or (last is not None and moment <= last):
                raise ValueError("invalid power binding timestamp")
            if moment > at:
                raise ValueError("future power binding timestamp")
            last = moment
    for uid in set(bindings) | set(current):
        entity = current.get(uid)
        epochs = bindings.setdefault(uid, [])
        if not epochs or epochs[-1]["entity"] != entity:
            change = {"start": at.isoformat(), "entity": entity}
            if epochs and epochs[-1]["start"] == change["start"]:
                epochs[-1] = change
            else:
                epochs.append(change)
            bindings[uid] = epochs[-256:]
    return bindings


def _binding_for_interval(epochs, start, end):
    """A whole interval must belong to one known native source."""
    selected = None
    for epoch in epochs:
        edge = datetime.fromisoformat(epoch["start"]) if epoch["start"] else None
        if edge is not None and start < edge < end:
            return None
        if edge is None or edge <= start:
            selected = epoch["entity"]
    return selected


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
    stamps = [value[0] for value in observations]
    series = []
    slot = datetime.fromtimestamp(
        (int(first.timestamp()) + 899) // 900 * 900, timezone.utc
    )
    while slot + QUARTER <= min(last, now):
        finish = slot + QUARTER
        first_event = bisect_right(stamps, slot)
        active = observations[first_event - 1] if first_event else None
        events = observations[first_event:bisect_left(stamps, finish)]
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


def _session_asset_at_time(receipts, charger_id, start, end):
    """Only an independently closed, whole-quarter session proves attribution.

    Current charger.asset is explicitly NOT consulted; no retroactive relabeling
    after swapping a vehicle or deleting its persistent profile.
    """
    matched = []
    for receipt in receipts:
        if (receipt.get("charger_id") != charger_id
                or receipt.get("physical_stop_confirmed") is not True):
            continue
        try:
            since = datetime.fromisoformat(receipt["started_at"])
            until = datetime.fromisoformat(receipt["ended_at"])
        except (KeyError, ValueError, TypeError):
            continue
        if (since.tzinfo is None or until.tzinfo is None
                or since.utcoffset() is None or until.utcoffset() is None):
            continue
        if since <= start and until >= end:
            matched.append(receipt.get("asset_id"))
    return matched[0] if len(matched) == 1 else None


def _estimated_session_variable_cost(states, receipt, price_slots, now):
    """Indicative variable cost from real Recorder power samples, never a bill.

    Integrate observed native power across *each* covered tariff boundary.
    This does not spread the final session kWh uniformly over unknown time
    periods, nor replace the independent metered-energy session receipt.
    Any source gap stays unknown. No optional Robotix or Finance integration.
    """
    if (receipt.get("physical_stop_confirmed") is not True
            or receipt.get("energy_quality") != "measured"):
        return None
    metered = receipt.get("actual_energy_kwh")
    if (isinstance(metered, bool)
            or not isinstance(metered, (int, float))
            or not isfinite(metered) or metered < 0):
        return None
    try:
        start = datetime.fromisoformat(receipt["started_at"])
        end = datetime.fromisoformat(receipt["ended_at"])
        if (start.utcoffset() is None or end.utcoffset() is None
                or now.utcoffset() is None):
            return None
        start, end, at = (
            value.astimezone(timezone.utc) for value in (start, end, now)
        )
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
        return None
    if not start < end <= at or end - start > timedelta(hours=48):
        return None
    observed = sorted(
        (item for state in states if (item := _sample(state)) is not None),
        key=lambda item: item[0],
    )
    if not observed or any(
        first[0] == second[0] for first, second in zip(observed, observed[1:])
    ):
        return None
    # Convert provider-local aware timestamps to UTC before ordering.
    # Python's local-zone comparison can otherwise collapse distinct fold=0
    # and fold=1 instants on a 25-hour DST fallback day.
    tariffs = []
    try:
        for slot in price_slots:
            if (slot.start.utcoffset() is None
                    or slot.end.utcoffset() is None
                    or slot.basis != "effective"
                    or not isfinite(slot.effective_price_per_kwh)):
                return None
            left = slot.start.astimezone(timezone.utc)
            right = slot.end.astimezone(timezone.utc)
            if left >= right:
                return None
            if left < end and right > start:
                tariffs.append((left, right, slot))
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None
    tariffs.sort(key=lambda row: row[0])
    if not tariffs:
        return None
    currencies = {slot.currency for _, _, slot in tariffs}
    if len(currencies) != 1 or not next(iter(currencies)):
        return None
    if any(first[1] > second[0]
           for first, second in zip(tariffs, tariffs[1:])):
        return None
    boundaries = sorted(
        {start, end}
        | {stamp for stamp, _ in observed if start < stamp < end}
        | {edge for left, right, _ in tariffs for edge in (left, right)
           if start < edge < end}
    )
    cost = 0.0
    measured_kwh = 0.0
    for left, right in zip(boundaries, boundaries[1:]):
        candidates = [slot for from_utc, to_utc, slot in tariffs
                      if from_utc <= left and to_utc >= right]
        if len(candidates) != 1:
            return None
        readings = [reading for reading in observed if reading[0] <= left]
        if not readings:
            return None
        stamp, power_kw = readings[-1]
        if (power_kw is None or stamp > left
                or right - stamp > MAX_OBSERVATION_AGE):
            return None
        energy_kwh = power_kw * (right - left).total_seconds() / 3600
        measured_kwh += energy_kwh
        cost += energy_kwh * candidates[0].effective_price_per_kwh
    if not isfinite(cost) or not isfinite(measured_kwh):
        return None
    return {
        "estimated_variable_cost": round(cost, 6),
        "estimated_variable_cost_currency": next(iter(currencies)),
        "estimated_variable_cost_energy_kwh": round(measured_kwh, 6),
        "estimated_variable_cost_quality":
            "observed_power_integral_effective_tariff",
        "estimated_variable_cost_basis": "indicative_variable_energy_only",
    }


async def read_actual_history(hass, configuration, start, end, *,
                              charger_id=None, asset_id=None,
                              session_receipts=(), price_slots=(),
                              include_valuations=False, power_bindings=None):
    """Query the installed native Recorder once for exact configured chargers."""
    now = datetime.now(timezone.utc)
    first, last = start.astimezone(timezone.utc), end.astimezone(timezone.utc)

    bindings = (power_bindings if power_bindings is not None else
                {c["id"]: [{"start": None, "entity": c.get("power_entity")}]
                 for c in configuration["chargers"]})
    selected = [c["id"] for c in configuration["chargers"]
                if charger_id is None or c["id"] == charger_id]
    if charger_id is not None and charger_id in bindings and not selected:
        selected = [charger_id]

    def reply(rows, quality, historical=None):
        if not include_valuations:
            return rows, quality
        valued = {}
        if historical is not None and price_slots:
            for receipt in session_receipts:
                charger = receipt.get("charger_id")
                if (charger not in selected
                        or charger_id is not None and charger_id != charger
                        or asset_id is not None and asset_id != receipt.get("asset_id")):
                    continue
                try:
                    started = datetime.fromisoformat(receipt["started_at"])
                    ended = datetime.fromisoformat(receipt["ended_at"])
                    if (started.utcoffset() is None or ended.utcoffset() is None
                            or started < first or ended > min(last, now)):
                        continue
                except (KeyError, ValueError, TypeError, OverflowError):
                    continue
                source = _binding_for_interval(bindings.get(charger, ()), started, ended)
                if not source:
                    continue
                evidence = _estimated_session_variable_cost(
                    historical.get(source, []), receipt, price_slots, now,
                )
                if evidence is not None:
                    valued[(charger, receipt["started_at"],
                            receipt["ended_at"])] = evidence
        return rows, quality, valued
    if not selected:
        return reply([], "NO_MATCHING_CHARGER")
    # Include only sources which were actually mapped during this request.
    # Query the existing native Recorder once, even across a remap.
    entities = sorted({
        epoch["entity"] for uid in selected
        for index, epoch in enumerate(bindings.get(uid, ()))
        if epoch["entity"]
        and (epoch["start"] is None or datetime.fromisoformat(epoch["start"]) < last)
        and (index + 1 == len(bindings[uid])
             or datetime.fromisoformat(bindings[uid][index + 1]["start"]) > first)
    })
    if not entities:
        return reply([], "POWER_METER_NOT_CONFIGURED")
    if last <= first or last - first > timedelta(hours=49):
        raise ValueError("historical view must be bounded to two civil days (<=49h)")
    if first >= now:
        return reply([], "FUTURE_ONLY")
    if "recorder" not in hass.config.components:
        return reply([], "RECORDER_NOT_LOADED")
    try:
        from homeassistant.components.recorder import get_instance, history

        # Use the Recorder's own executor, preserving the native DB lifecycle.
        historical = await get_instance(hass).async_add_executor_job(
            history.get_significant_states,
            hass, first, min(last, now), entities,
            None, True, False, False, False, False,
        )
    except (ImportError, RuntimeError, ValueError, OSError, KeyError):
        return reply([], "RECORDER_UNAVAILABLE")
    # Integrate each physical source once; only then assign the measured
    # quarter to the logical Charger that owned that source at that time.
    empty = _quarter_actuals([], first, last, now)
    by_source = {
        entity: {row["start"]: row for row in _quarter_actuals(
            historical.get(entity, []), first, last, now)}
        for entity in entities
    }
    result = []
    for uid in selected:
        epochs = bindings.get(uid, ())
        for unknown in empty:
            since = datetime.fromisoformat(unknown["start"])
            until = datetime.fromisoformat(unknown["end"])
            source = _binding_for_interval(epochs, since, until)
            row = dict(by_source.get(source, {}).get(unknown["start"], unknown))
            attributed = (_session_asset_at_time(session_receipts, uid, since, until)
                          if source else None)
            row.update({
                "charger_id": uid, "asset_id": attributed,
                "asset_provenance": (
                    "confirmed_closed_session" if attributed is not None
                    else "unattributed_charger_actual"
                ),
            })
            if asset_id is None or asset_id == attributed:
                result.append(row)
    if not result:
        return reply([], (
            "NO_CONFIRMED_ASSET_HISTORY" if asset_id is not None
            else "NO_RECORDED_QUARTERS"
        ), historical)
    if any(row["quality"] != "measured_power_integral" for row in result):
        return reply(result, "INCOMPLETE_POWER_HISTORY", historical)
    return reply(result, "MEASURED_POWER_HISTORY", historical)
