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


def reconcile_power_bindings(previous, configuration, at, *, field="power_entity"):
    """Retain binding metadata, not measured values, in the existing Store.

    On legacy migration the current source is the only known binding; no
    earlier undocumented changes can be reconstructed. Later remaps start
    at their actual runtime application time, including deletion tombstones.
    """
    at = at.astimezone(timezone.utc)
    current = {c["id"]: c.get(field) for c in configuration["chargers"]}
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



def _observed_runs(states, first, last, now):
    """Continuous positive-power observations, not command/session receipts.

    A real zero-to-positive transition establishes a start; a qualified
    positive-to-zero transition establishes an observed end. Missing samples,
    stale spans, source boundaries and window edges never become STOP proof.
    """
    last = min(last, now)
    samples = sorted((item for state in states if (item := _sample(state))),
                     key=lambda item: item[0])
    if first >= last or not samples:
        return []
    # Duplicate timestamps with conflicting values are ambiguous.
    by_stamp = {}
    for stamp, value in samples:
        if stamp in by_stamp and by_stamp[stamp] != value:
            by_stamp[stamp] = None
        else:
            by_stamp[stamp] = value
    samples = sorted(by_stamp.items())
    result = []
    run = None
    previous = None

    def finish(ended_known=False, ongoing=False):
        nonlocal run
        if run and run["segments"]:
            run["end_known"] = ended_known
            run["ongoing"] = ongoing
            result.append(run)
        run = None

    for i, (stamp, value) in enumerate(samples):
        if stamp > last:
            break
        if stamp < first and i+1 < len(samples) and samples[i+1][0] <= first:
            previous = (stamp, value)
            continue
        right = min(samples[i+1][0] if i+1 < len(samples) else last, last)
        left = max(first, stamp)
        if left > last:
            break
        fresh_end = min(right, stamp + MAX_OBSERVATION_AGE)
        if value is None or fresh_end < left:
            finish()
            previous = (stamp, None)
            continue
        if value <= 0.05:
            if run:
                finish(ended_known=run["segments"][-1][1] == stamp and stamp <= last)
            previous = (stamp, value)
            continue
        if run and run["segments"][-1][1] != left:
            finish()
        if run is None:
            known = (stamp >= first and previous is not None
                     and previous[1] is not None and previous[1] <= 0.05
                     and stamp - previous[0] <= MAX_OBSERVATION_AGE)
            run = {"start_known": known, "segments": []}
        if fresh_end > left:
            run["segments"].append((left, fresh_end, value))
        if fresh_end < right:
            finish()
            previous = (stamp, None)
        else:
            previous = (stamp, value)
        if right == last and (i+1 == len(samples) or samples[i+1][0] > last):
            finish(ongoing=last == now and fresh_end == last)
    finish()
    return result


def _run_valuation(segments, price_slots):
    """Exact overlap of measured power segments with one quote per instant.

    Reference, spot and effective series can produce a read-only estimate;
    none of these estimates is a billed cost or budget-control input.
    """
    quotes = []
    for row in price_slots:
        try:
            if (row.basis not in ("effective", "variable_reference", "spot")
                    or not isfinite(row.effective_price_per_kwh)
                    or row.start.utcoffset() is None or row.end.utcoffset() is None
                    or not row.currency or row.end <= row.start):
                continue
            quotes.append((row.start.astimezone(timezone.utc),
                           row.end.astimezone(timezone.utc), row))
        except (AttributeError, TypeError, ValueError, OverflowError):
            continue
    total = 0.0
    kinds = set()
    for start, end, power in segments:
        overlapping = [(a, b, row) for a, b, row in quotes if a < end and b > start]
        edges = sorted({start, end} | {
            edge for a, b, _ in overlapping for edge in (a, b) if start < edge < end
        })
        for left, right in zip(edges, edges[1:]):
            matched = [row for a, b, row in overlapping if a <= left and b >= right]
            if len(matched) != 1:
                return None
            price = matched[0]
            kinds.add((price.currency, price.basis))
            total += power * (right-left).total_seconds()/3600 * price.effective_price_per_kwh
    if len(kinds) != 1 or not isfinite(total):
        return None
    currency, basis = next(iter(kinds))
    return {"estimated_cost": round(total, 6),
            "estimated_cost_currency": currency, "estimated_cost_basis": basis}


def _meter_delta(states, power_states, start, end, now, ongoing):
    """Use cumulative kWh only with known idle boundaries and no meter reset."""
    samples = []
    for state in states:
        try:
            stamp = state.last_updated
            if stamp.utcoffset() is None:
                continue
            factor = {"Wh": 0.001, "kWh": 1.0}[state.attributes["unit_of_measurement"]]
            value = float(state.state)*factor
            if not isfinite(value) or value < 0:
                value = None
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
            stamp = getattr(state, "last_updated", None)
            if not isinstance(stamp, datetime) or stamp.utcoffset() is None:
                continue
            value = None
        samples.append((stamp.astimezone(timezone.utc), value))
    samples.sort(key=lambda row: row[0])
    if not samples or len({row[0] for row in samples}) != len(samples):
        return None
    before = [row for row in samples if row[0] <= start]
    after = [row for row in samples if end <= row[0] <= min(now, end+MAX_OBSERVATION_AGE)]
    if not before:
        return None
    a, initial = before[-1]
    if initial is None or start-a > MAX_OBSERVATION_AGE:
        return None
    if a < start:
        idle = _covered_power_segments(power_states, a, start)
        if not idle or any(power > 0.05 for _, _, power in idle):
            return None
    if ongoing:
        recent = [row for row in samples if start < row[0] <= end]
        if not recent or end-recent[-1][0] > MAX_OBSERVATION_AGE:
            return None
        b, final = recent[-1]
    elif after:
        b, final = after[0]
        if b > end:
            idle = _covered_power_segments(power_states, end, b)
            if not idle or any(power > 0.05 for _, _, power in idle):
                return None
    else:
        return None
    values = [value for stamp, value in samples if a <= stamp <= b]
    if (final is None or any(value is None for value in values)
            or any(y < x-0.00001 for x, y in zip(values, values[1:]))):
        return None
    return {"meter_energy_kwh": round(max(0, final-initial), 6),
            "meter_observed_at": b.isoformat()}


def _observed_session_rows(historical, bindings, selected, first, last, now,
                           receipts, active_sessions, price_slots, energy_bindings=None):
    """Project native charging observations using existing source epochs.

    Never duplicate an executor-owned receipt or infer vehicle identity from
    the current selected asset. A clipped run is an observed portion only.
    """
    rows = []
    last = min(last, now)
    for uid in selected:
        owned = []
        for receipt in [*receipts, *active_sessions.values()]:
            if receipt.get("charger_id") != uid:
                continue
            try:
                a = datetime.fromisoformat(receipt["started_at"])
                b = datetime.fromisoformat(receipt["ended_at"]) if receipt.get("ended_at") else now
                if a.utcoffset() is not None and b.utcoffset() is not None:
                    owned.append((a, b))
            except (ValueError, TypeError, KeyError):
                continue
        epochs = bindings.get(uid, ())
        for i, epoch in enumerate(epochs):
            entity = epoch["entity"]
            if not entity:
                continue
            start = max(first, datetime.fromisoformat(epoch["start"])) if epoch["start"] else first
            end = min(last, datetime.fromisoformat(epochs[i+1]["start"])) if i+1 < len(epochs) else last
            if start >= end:
                continue
            for run in _observed_runs(historical.get(entity, ()), start, end, now):
                segments = run["segments"]
                a, b = segments[0][0], segments[-1][1]
                if any(left < b and right > a for left, right in owned):
                    continue
                hours = sum((right-left).total_seconds()/3600 for left, right, _ in segments)
                kwh = sum(power*(right-left).total_seconds()/3600 for left, right, power in segments)
                complete = run["start_known"] and (run["end_known"] or run["ongoing"])
                estimate = _run_valuation(segments, price_slots)
                meter = None
                if complete and energy_bindings:
                    meter_source = _binding_for_interval(energy_bindings.get(uid, ()), a, b)
                    if meter_source:
                        meter = _meter_delta(historical.get(meter_source, ()),
                                             historical.get(entity, ()), a, b, now, run["ongoing"])
                        if meter and _binding_for_interval(energy_bindings.get(uid, ()), a,
                                                            datetime.fromisoformat(meter["meter_observed_at"])) != meter_source:
                            meter = None
                rows.append({
                    "charger_id": uid, "asset_id": None,
                    "started_at": a.isoformat(), "ended_at": b.isoformat(),
                    "start_known": run["start_known"], "end_known": run["end_known"],
                    "ongoing": run["ongoing"], "complete_observed_window": complete,
                    "observed_energy_kwh": round(kwh, 6),
                    "observed_duration_minutes": round(hours*60, 3),
                    "average_power_kw": round(kwh/hours, 6),
                    "peak_power_kw": round(max(power for _, _, power in segments), 6),
                    "energy_quality": "observed_power_integral",
                    "estimated_cost": None, **(estimate or {}), **(meter or {}),
                })
    return sorted(rows, key=lambda row: (row["ended_at"], row["charger_id"]))



def _historical_reference_quotes(hass, historical, entity, current, first, last):
    """Only explicit native historical tariff intervals, never a settled bill.

    A changed/revised price for the same interval remains ambiguous instead
    of silently replacing an earlier quote. Current selected source history
    is a reference valuation, not proof that it was the billing tariff.
    """
    from .source_evidence import intervals_from_state
    unique = {}
    for state in historical.get(entity, ()):
        try:
            stamp = state.last_updated
            if stamp.utcoffset() is None or stamp > last:
                continue
            quotes, quality = intervals_from_state(hass, state, "price", stamp)
            if quality != "OK":
                continue
        except (AttributeError, TypeError, ValueError, OverflowError, KeyError):
            continue
        for row in quotes:
            if row.end > first and row.start < last and stamp < row.end:
                unique[(row.start, row.end, row.currency, row.basis,
                        row.effective_price_per_kwh)] = row
    for row in current:
        if row.end > first and row.start < last:
            unique[(row.start, row.end, row.currency, row.basis,
                    row.effective_price_per_kwh)] = row
    return tuple(unique.values())


def _covered_power_segments(states, start, end):
    """A complete, timestamp-qualified power trajectory within a known receipt."""
    samples = sorted((item for state in states if (item := _sample(state))),
                     key=lambda item: item[0])
    if not samples or end <= start:
        return None
    stamps = [row[0] for row in samples]
    if len(set(stamps)) != len(stamps):
        return None
    idx = bisect_right(stamps, start)
    active = samples[idx-1] if idx else None
    events = samples[idx:bisect_left(stamps, end)]
    cursor = start
    segments = []
    for next_stamp, value in (*events, (end, None)):
        if (active is None or active[1] is None or active[0] > cursor
                or next_stamp-active[0] > MAX_OBSERVATION_AGE):
            return None
        if next_stamp > cursor:
            segments.append((cursor, next_stamp, active[1]))
        cursor = next_stamp
        active = (next_stamp, value)
    return segments


def _receipt_view_metrics(historical, bindings, selected, first, last, now,
                          receipts, active_sessions, quotes, asset_id):
    """Enrich the existing receipt/readback, never create a second receipt."""
    result = {}
    for receipt in [*receipts, *active_sessions.values()]:
        uid = receipt.get("charger_id")
        if uid not in selected or (asset_id is not None and receipt.get("asset_id") != asset_id):
            continue
        try:
            a = datetime.fromisoformat(receipt["started_at"])
            b = datetime.fromisoformat(receipt["ended_at"]) if receipt.get("ended_at") else now
            if a.utcoffset() is None or b.utcoffset() is None or not a < b <= now:
                continue
        except (ValueError, KeyError, TypeError, OverflowError):
            continue
        if b < first or a > last:
            continue
        duration = (b-a).total_seconds()/60
        metrics = {"elapsed_minutes": round(duration, 3)}
        energy = receipt.get("actual_energy_kwh")
        if type(energy) in (int, float) and isfinite(energy) and energy >= 0:
            metrics["average_power_kw"] = round(energy*60/duration, 6)
        if a >= first and b <= last:
            source = _binding_for_interval(bindings.get(uid, ()), a, b)
            segments = _covered_power_segments(historical.get(source, ()), a, b) if source else None
            if segments:
                metrics["peak_power_kw"] = round(max(power for _, _, power in segments), 6)
                measured = sum(power*(right-left).total_seconds()/3600 for left, right, power in segments)
                if energy is None:
                    metrics["observed_energy_kwh"] = round(measured, 6)
                    metrics["average_power_kw"] = round(measured*60/duration, 6)
                metrics.update(_run_valuation(segments, quotes) or {})
        result[(uid, receipt["started_at"], receipt.get("ended_at"))] = metrics
    return result


async def read_actual_history(hass, configuration, start, end, *,
                              charger_id=None, asset_id=None,
                              session_receipts=(), price_slots=(),
                              include_valuations=False, power_bindings=None,
                              include_observed_sessions=False, active_sessions=None,
                              tariff_entity=None, energy_bindings=None):
    """Query the installed native Recorder once for exact configured chargers."""
    now = datetime.now(timezone.utc)
    first, last = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if last <= first or last-first > timedelta(hours=49):
        raise ValueError("historical view must be bounded to two civil days (<=49h)")
    history_end = min(last, now)
    history_first = min(first, history_end-timedelta(hours=48)) if include_observed_sessions else first
    active_sessions = {uid: {**row, "charger_id": uid}
                       for uid, row in (active_sessions or {}).items()}

    bindings = (power_bindings if power_bindings is not None else
                {c["id"]: [{"start": None, "entity": c.get("power_entity")}]
                 for c in configuration["chargers"]})
    selected = [c["id"] for c in configuration["chargers"]
                if charger_id is None or c["id"] == charger_id]
    if charger_id is not None and charger_id in bindings and not selected:
        selected = [charger_id]

    def reply(rows, quality, historical=None):
        if not include_valuations and not include_observed_sessions:
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
        if include_observed_sessions:
            quotes = price_slots
            if historical is not None and tariff_entity:
                quotes = _historical_reference_quotes(
                    hass, historical, tariff_entity, price_slots, history_first, history_end,
                )
            observed = (_observed_session_rows(
                historical, bindings, selected, history_first, history_end, now,
                session_receipts, active_sessions, quotes, energy_bindings,
            ) if historical is not None and asset_id is None else [])
            metrics = (_receipt_view_metrics(
                historical, bindings, selected, history_first, history_end, now,
                session_receipts, active_sessions, quotes, asset_id,
            ) if historical is not None else {})
            return rows, quality, valued, observed, metrics
        return rows, quality, valued
    if not selected:
        return reply([], "NO_MATCHING_CHARGER")
    # Include only sources which were actually mapped during this request.
    # Query the existing native Recorder once, even across a remap.
    entities = sorted({
        epoch["entity"] for uid in selected
        for index, epoch in enumerate(bindings.get(uid, ()))
        if epoch["entity"]
        and (epoch["start"] is None or datetime.fromisoformat(epoch["start"]) < history_end)
        and (index + 1 == len(bindings[uid])
             or datetime.fromisoformat(bindings[uid][index + 1]["start"]) > history_first)
    })
    if not entities:
        return reply([], "POWER_METER_NOT_CONFIGURED")
    if history_first >= history_end:
        return reply([], "FUTURE_ONLY")
    power_entities = tuple(entities)
    if include_observed_sessions:
        if tariff_entity and tariff_entity not in entities:
            entities.append(tariff_entity)
        for uid in selected:
            for epoch in (energy_bindings or {}).get(uid, ()):
                if epoch["entity"] and epoch["entity"] not in entities:
                    entities.append(epoch["entity"])
    if "recorder" not in hass.config.components:
        return reply([], "RECORDER_NOT_LOADED")
    try:
        from homeassistant.components.recorder import get_instance, history

        # Use the Recorder's own executor, preserving the native DB lifecycle.
        historical = await get_instance(hass).async_add_executor_job(
            history.get_significant_states,
            hass, history_first, history_end, entities,
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
        for entity in power_entities
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
