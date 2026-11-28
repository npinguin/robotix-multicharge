"""Real read-only Home Assistant Recorder telemetry for quarter-hour actuals.

No fabricated historical values. Incomplete, stale or missing source periods
are returned as unknown and never coerced into zero delivered energy.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from copy import deepcopy
from datetime import datetime, time, timedelta, timezone
from functools import cached_property
from zoneinfo import ZoneInfo
from math import isfinite

from .configuration import forecast_tariff_source

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


def reconcile_tariff_bindings(previous, configuration, at):
    """Same epoch contract as physical meter sources, no price data in Store."""
    ctl = configuration["controller"]
    return reconcile_power_bindings(previous, {"chargers": [{
        "id": "site", "price_entity": forecast_tariff_source(ctl),
    }]}, at, field="price_entity")


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


class _RecorderSamples:
    """Request-local, lazy indexes of one exact native Recorder result.

    No cross-query cache: a late Recorder sample, changed binding, new receipt
    or new request is never hidden. Each physical source is normalized once
    for the quarter, civil-day, receipt and observed-run projections.
    """

    def __init__(self, states):
        self.states = states

    def __iter__(self):
        return iter(self.states)

    @cached_property
    def power_index(self):
        samples = _power_samples(self.states)
        return samples, [stamp for stamp, _ in samples]

    @cached_property
    def energy_index(self):
        samples = _energy_samples(self.states)
        stamps = [stamp for stamp, _ in samples]
        unique = all(a != b for a, b in zip(stamps, stamps[1:]))
        return samples, stamps, unique


def _power_index(states):
    if isinstance(states, _RecorderSamples):
        return states.power_index
    samples = _power_samples(states)
    return samples, [stamp for stamp, _ in samples]


def _power_samples(states):
    """One normalization rule for all historical power projections."""
    if isinstance(states, _RecorderSamples):
        return states.power_index[0]
    samples = {}
    for state in states:
        reading = _sample(state)
        if reading is None:
            continue
        stamp, value = reading
        # An ambiguous timestamp stays unknown even after a third reading.
        samples[stamp] = (None if stamp in samples and samples[stamp] != value
                          else value)
    return sorted(samples.items())


def _quarter_actuals(states, first, last, now):
    """Integrate the same qualified spans used for session and civil costs."""
    last = min(last, now)
    spans = _power_spans(states, first, last)
    edges = [a for a, _, _ in spans]
    series = []
    slot = first.replace(minute=(first.minute//15)*15, second=0, microsecond=0)
    if slot < first:
        slot += QUARTER
    while slot + QUARTER <= last:
        finish = slot + QUARTER
        energy, observed = _interval_power_evidence(spans, edges, slot, finish)
        valid = abs(observed-QUARTER.total_seconds()) < 0.001
        series.append({
            "start": slot.isoformat(), "end": finish.isoformat(),
            "actual_power_kw": round(energy * 4, 6) if valid else None,
            "actual_energy_kwh": round(energy, 6) if valid else None,
            "quality": "measured_power_integral" if valid else "unknown",
        })
        slot = finish
    return series

def receipt_overlaps(receipt, start, end):
    """Use original aware session boundaries, never current owner mapping."""
    try:
        return (datetime.fromisoformat(receipt["started_at"]) < end
                and datetime.fromisoformat(receipt["ended_at"]) >= start)
    except (KeyError, ValueError, TypeError, OverflowError):
        return False


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
    # Reuse the same complete native-power and interval valuation paths as
    # all other session/plan cost projections. Keep the stricter independent
    # receipt and effective-only requirements of this existing public field.
    if any(getattr(row, "basis", None) != "effective" for row in price_slots):
        return None
    segments = _covered_power_segments(states, start, end)
    if not segments:
        return None
    value = _run_valuation(segments, price_slots)
    if value is None:
        return None
    measured_kwh = sum(power*(right-left).total_seconds()/3600
                       for left, right, power in segments)
    if not isfinite(measured_kwh):
        return None
    return {
        "estimated_variable_cost": value["estimated_cost"],
        "estimated_variable_cost_currency": value["estimated_cost_currency"],
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
    samples = _power_samples(states)
    if first >= last or not samples:
        return []
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


def _run_valuation(segments, price_slots, *, partition=None):
    """Exact overlap of measured power with the shared unique price partition."""
    if not segments:
        return None
    try:
        normalized = [
            (a.astimezone(timezone.utc), b.astimezone(timezone.utc), power)
            for a, b, power in segments
            if a.utcoffset() is not None and b.utcoffset() is not None
            and isfinite(power) and power >= 0
        ]
        if len(normalized) != len(segments) or any(a >= b for a, b, _ in normalized):
            return None
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None
    if partition is None:
        spans = _price_spans(price_slots, min(a for a, _, _ in normalized),
                             max(b for _, b, _ in normalized))
        starts = [a for a, _, _ in spans]
    else:
        spans, starts = partition
    total = 0.0
    kinds = set()
    for start, end, power in normalized:
        index = max(0, bisect_right(starts, start)-1)
        while index < len(spans) and spans[index][0] < end:
            a, b, quote = spans[index]
            left, right = max(a, start), min(b, end)
            if left < right:
                if quote is None:
                    return None
                kinds.add((quote.currency, quote.basis))
                total += power*(right-left).total_seconds()/3600*quote.effective_price_per_kwh
            index += 1
    if len(kinds) != 1 or not isfinite(total):
        return None
    currency, basis = next(iter(kinds))
    return {"estimated_cost": round(total, 6),
            "estimated_cost_currency": currency, "estimated_cost_basis": basis}


def planned_costs(slots, price_slots, at, *, until=None):
    """Single read-only valuation of proposed executable plan, by stable owner.

    Only future energy in the current planner's actual slots is counted.
    Conditional alternatives and accepted historical slots are not added.
    Unknown/mixed prices never become a zero or a deceptively complete total.
    """
    groups = {"controller": {"site": []}, "charger": {}, "asset": {}}
    for row in slots:
        start, end = max(at, row.start), min(until, row.end) if until else row.end
        power = getattr(row, "expected_power_kw", row.power_kw)
        if end <= start or power <= 0:
            continue
        segment = (start, end, power)
        groups["controller"]["site"].append(segment)
        groups["charger"].setdefault(row.charger_uid, []).append(segment)
        if row.asset_uid is not None:
            groups["asset"].setdefault(row.asset_uid, []).append(segment)
    # All owner groups are subsets of the same site segments. Reuse the
    # exact UTC quote partition, retaining each group's own quality.
    site = groups["controller"]["site"]
    partition = None
    if site and all(a.utcoffset() is not None and b.utcoffset() is not None
                    for a, b, _ in site):
        spans = _price_spans(
            price_slots, min(a.astimezone(timezone.utc) for a, _, _ in site),
            max(b.astimezone(timezone.utc) for _, b, _ in site),
        )
        partition = (spans, [a for a, _, _ in spans])
    result = {}
    for kind, owners in groups.items():
        result[kind] = {}
        for uid, segments in owners.items():
            energy = sum(power * (end-start).total_seconds()/3600
                         for start, end, power in segments)
            value = _run_valuation(segments, price_slots, partition=partition) if segments else None
            cost = value["estimated_cost"] if value is not None else None
            result[kind][uid] = {
                "energy_kwh": round(energy, 6),
                "cost": cost,
                "currency": value["estimated_cost_currency"] if value else None,
                "basis": value["estimated_cost_basis"] if value else None,
                "average_price_per_kwh": round(cost/energy, 6) if cost is not None and energy else None,
                "quality": "qualified_plan_estimate" if value else (
                    "no_planned_energy" if not segments else "incomplete_tariff"
                ),
            }
    return result


def _energy_samples(states):
    """Native cumulative kWh observations; invalid values split evidence."""
    if isinstance(states, _RecorderSamples):
        return states.energy_index[0]
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
    return samples


def _energy_index(states):
    if isinstance(states, _RecorderSamples):
        return states.energy_index
    samples = _energy_samples(states)
    stamps = [stamp for stamp, _ in samples]
    return samples, stamps, all(a != b for a, b in zip(stamps, stamps[1:]))


def _meter_delta(states, power_states, start, end, now, ongoing):
    """Use cumulative kWh only with known idle boundaries and no meter reset."""
    samples, stamps, unique = _energy_index(states)
    if not samples or not unique:
        return None
    baseline_index = bisect_right(stamps, start)-1
    if baseline_index < 0:
        return None
    a, initial = samples[baseline_index]
    if initial is None or start-a > MAX_OBSERVATION_AGE:
        return None
    if a < start:
        idle = _covered_power_segments(power_states, a, start)
        if not idle or any(power > 0.05 for _, _, power in idle):
            return None
    if ongoing:
        final_index = bisect_right(stamps, end)-1
        if (final_index <= baseline_index or end-stamps[final_index] > MAX_OBSERVATION_AGE):
            return None
        b, final = samples[final_index]
    else:
        final_index = bisect_left(stamps, end)
        if final_index >= len(stamps) or stamps[final_index] > min(now, end+MAX_OBSERVATION_AGE):
            return None
        b, final = samples[final_index]
        if b > end:
            idle = _covered_power_segments(power_states, end, b)
            if not idle or any(power > 0.05 for _, _, power in idle):
                return None
    values = [value for _, value in samples[baseline_index:final_index+1]]
    if (final is None or any(value is None for value in values)
            or any(y < x-0.00001 for x, y in zip(values, values[1:]))):
        return None
    return {"meter_energy_kwh": round(max(0, final-initial), 6),
            "meter_baseline_at": a.isoformat(),
            "meter_observed_at": b.isoformat()}


def _unowned_run_parts(run, owned):
    """Retain external portions without counting any owned receipt twice."""
    original = run["segments"]
    remaining = []
    for start, end, power in original:
        pieces = [(start, end)]
        for left, right in owned:
            clipped = []
            for a, b in pieces:
                if left >= b or right <= a:
                    clipped.append((a, b))
                else:
                    if a < left:
                        clipped.append((a, left))
                    if right < b:
                        clipped.append((right, b))
            pieces = clipped
        for a, b in pieces:
            if remaining and remaining[-1][-1][1] == a:
                remaining[-1].append((a, b, power))
            else:
                remaining.append([(a, b, power)])
    return [{
        "segments": segments,
        "start_known": run["start_known"] and segments[0][0] == original[0][0],
        "end_known": run["end_known"] and segments[-1][1] == original[-1][1],
        "ongoing": run["ongoing"] and segments[-1][1] == original[-1][1],
    } for segments in remaining]


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
            runs = _observed_runs(historical.get(entity, ()), start, end, now)
            for run in (part for observed in runs for part in _unowned_run_parts(observed, owned)):
                segments = run["segments"]
                a, b = segments[0][0], segments[-1][1]
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
                        if meter:
                            baseline = datetime.fromisoformat(meter["meter_baseline_at"])
                            observed = datetime.fromisoformat(meter["meter_observed_at"])
                            if (_binding_for_interval(energy_bindings.get(uid, ()), baseline, observed)
                                    != meter_source or
                                    _binding_for_interval(epochs, baseline, max(b, observed)) != entity):
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


def _quotes_at_binding(hass, historical, epochs, current_entity, current, first, last):
    """Use each original tariff source only during its recorded binding epoch.

    Do not value a former source's intervals using the current provider or
    let its future forecasts spill across a remap. A boundary within a quote
    is clipped to the actual change instant, never extrapolated.
    """
    result = []
    for i, epoch in enumerate(epochs):
        entity = epoch["entity"]
        if not entity:
            continue
        begin = max(first, datetime.fromisoformat(epoch["start"])) if epoch["start"] else first
        end = min(last, datetime.fromisoformat(epochs[i+1]["start"])) if i+1 < len(epochs) else last
        if begin >= end:
            continue
        quotes = _historical_reference_quotes(
            hass, historical, entity,
            current if entity == current_entity and i+1 == len(epochs) else (),
            begin, end,
        )
        for row in quotes:
            left = max(begin, row.start.astimezone(timezone.utc))
            right = min(end, row.end.astimezone(timezone.utc))
            if left < right:
                result.append(type(row)(
                    start=left, end=right, effective_price_per_kwh=row.effective_price_per_kwh,
                    currency=row.currency, basis=row.basis,
                ))
    return tuple(result)


def _covered_power_segments(states, start, end):
    """Return complete coverage only, using the canonical power partition."""
    if end <= start:
        return None
    spans = _power_spans(states, start, end)
    return spans if spans and all(power is not None for _, _, power in spans) else None

def _receipt_view_metrics(historical, bindings, selected, first, last, now,
                          receipts, active_sessions, quotes, asset_id, energy_bindings=None):
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
                # The cost estimator's denominator is the same observed power
                # integral, not an independent meter delta with different coverage.
                metrics["observed_energy_kwh"] = round(measured, 6)
                if energy is None:
                    metrics["average_power_kw"] = round(measured*60/duration, 6)
                metrics.update(_run_valuation(segments, quotes) or {})
            elif energy_bindings and uid in energy_bindings:
                # Same source/ownership/price reconciliation as civil costs.
                # No peak power from cumulative energy or guessed time split.
                bucket = daily_costs(
                    historical, bindings, {"chargers": [{"id": uid}], "assets": []},
                    a, b, quotes, energy_bindings=energy_bindings,
                    selected_chargers={uid},
                )["charger"][uid]
                measured = bucket["observed_energy_kwh"]
                complete = abs(bucket["observed_seconds"]-(b-a).total_seconds()) < 0.001
                # Independent session receipt can reveal an incompatible
                # integral. Do not label conflicting energy as full coverage.
                if type(energy) in (int, float) and isfinite(energy) and abs(measured-energy) > 0.0001:
                    complete = False
                if complete:
                    metrics["observed_energy_kwh"] = round(measured, 6)
                    if energy is None:
                        metrics["average_power_kw"] = round(measured*60/duration, 6)
                    metrics["energy_evidence"] = "reconciled_native_meter"
                pairs = bucket["valuations"]
                if len(pairs) == 1:
                    (currency, basis), (cost, priced) = next(iter(pairs.items()))
                    if complete and bucket["unpriced_energy_kwh"] < 0.000001:
                        metrics.update(estimated_cost=round(cost, 6),
                                       estimated_cost_currency=currency,
                                       estimated_cost_basis=basis)
                    elif priced > 0:
                        metrics.update(estimated_covered_cost=round(cost, 6),
                                       estimated_covered_energy_kwh=round(priced, 6),
                                       estimated_cost_currency=currency,
                                       estimated_cost_basis=basis)
        result[(uid, receipt["started_at"], receipt.get("ended_at"))] = metrics
    return result


def session_financial_evidence(row, phase, observed_only=False):
    """One owner-qualified cost and priced-energy projection for all session views."""
    uid = row["charger_id"]
    asset = (None if observed_only or (phase == "last"
             and row.get("physical_stop_confirmed") is not True)
             else row.get("asset_id"))
    evidence = row
    verified = (not observed_only and phase == "last"
                and row.get("physical_stop_confirmed") is True
                and row.get("cost_quality") == "qualified_effective_tariff")
    if verified:
        cost, currency, basis = row.get("cost"), row.get("currency"), "effective"
        energy = row.get("actual_energy_kwh")
        quality = "qualified_effective_tariff"
    else:
        cost = evidence.get("estimated_cost")
        currency = evidence.get("estimated_cost_currency")
        basis = evidence.get("estimated_cost_basis")
        energy = evidence.get("observed_energy_kwh")
        if cost is None:
            cost = evidence.get("estimated_variable_cost")
            currency = evidence.get("estimated_variable_cost_currency")
            basis = "effective" if cost is not None else None
            energy = evidence.get("estimated_variable_cost_energy_kwh")
        quality = "reference_estimate"
        if cost is None and evidence.get("estimated_covered_cost") is not None:
            cost = evidence["estimated_covered_cost"]
            energy = evidence.get("estimated_covered_energy_kwh")
            currency = evidence.get("estimated_cost_currency")
            basis = evidence.get("estimated_cost_basis")
            quality = "partial_observation"
        if observed_only and not row.get("complete_observed_window"):
            quality = "partial_observation"
    if (type(cost) not in (int, float) or not isfinite(cost)
            or not currency or not basis):
        cost, currency, basis, quality = None, None, None, "unknown"
    projection = {
        "charger_id": uid, "asset_id": asset,
        "started_at": row["started_at"], "ended_at": row.get("ended_at"),
        "cost": None if quality == "partial_observation" else cost,
        "covered_cost": cost, "currency": currency, "basis": basis,
        "quality": quality, "energy_kwh": energy,
        "average_price_per_kwh": (
            round(cost/energy, 6) if cost is not None
            and type(energy) in (int, float) and isfinite(energy) and energy > 0 else None),
    }
    return projection


def session_costs(receipts, active_sessions, observed, estimates, metrics):
    """Select the current/last cost evidence on each existing logical owner.

    An external observation has no inferred vehicle identity. Cost estimates
    retain their own measured denominator; receipts are never rewritten.
    """
    groups = {"controller": {"site": {"active": [], "last": []}},
              "charger": {}, "asset": {}}

    def add(row, phase, observed_only=False):
        uid = row["charger_id"]
        key = (uid, row["started_at"], row.get("ended_at"))
        projection = session_financial_evidence(
            {**row, **metrics.get(key, {}), **estimates.get(key, {})},
            phase, observed_only,
        )
        asset = projection["asset_id"]
        if phase == "active":
            groups["controller"]["site"][phase].append(projection)
        groups["charger"].setdefault(uid, {"active": [], "last": []})[phase].append(projection)
        if asset is not None:
            groups["asset"].setdefault(asset, {"active": [], "last": []})[phase].append(projection)

    for uid, row in active_sessions.items():
        add({**row, "charger_id": uid}, "active")
    # Only the latest closed receipt per owner contributes to this summary.
    # Older receipts remain in the durable history and interval valuations.
    latest = {}
    for index, row in enumerate(receipts):
        ended = datetime.fromisoformat(row["ended_at"])
        owners = [("charger", row["charger_id"])]
        if row.get("physical_stop_confirmed") is True and row.get("asset_id") is not None:
            owners.append(("asset", row["asset_id"]))
        for owner in owners:
            if owner not in latest or ended > latest[owner][0]:
                latest[owner] = (ended, index, row)
    selected = {index: row for _, index, row in latest.values()}
    for index in sorted(selected):
        add(selected[index], "last")
    for row in observed:
        if row.get("ongoing"):
            add(row, "active", True)
        elif row.get("end_known"):
            add(row, "last", True)

    result = {}
    for kind, owners in groups.items():
        result[kind] = {}
        for uid, phases in owners.items():
            result[kind][uid] = {}
            for phase, rows in phases.items():
                if not rows:
                    continue
                if phase == "last":
                    if kind != "controller":
                        result[kind][uid][phase] = max(
                            rows, key=lambda r: datetime.fromisoformat(r["ended_at"]))
                    continue
                if kind != "controller" and len(rows) == 1:
                    result[kind][uid][phase] = rows[0]
                    continue
                valued = [r for r in rows if r["covered_cost"] is not None]
                kinds = {(r["currency"], r["basis"]) for r in valued}
                compatible = len(kinds) == 1
                complete = compatible and all(r["cost"] is not None for r in rows)
                currency, basis = next(iter(kinds)) if compatible else (None, None)
                subtotal = round(sum(r["covered_cost"] for r in valued), 6) if compatible else None
                cost = subtotal if complete else None
                covered = [r["energy_kwh"] for r in valued]
                covered_energy = (round(sum(covered), 6) if covered and all(
                    type(v) in (int, float) and isfinite(v) for v in covered) else None)
                energies = [r["energy_kwh"] for r in rows]
                energy = (round(sum(energies), 6) if all(
                    type(v) in (int, float) and isfinite(v) for v in energies) else None)
                result[kind][uid][phase] = {
                    "cost": cost, "covered_cost": subtotal, "currency": currency, "basis": basis,
                    "energy_kwh": energy, "covered_energy_kwh": covered_energy,
                    "quality": "reference_estimate" if complete else "incomplete_coverage",
                    "average_price_per_kwh": round(subtotal/covered_energy, 6)
                        if subtotal is not None and covered_energy else None,
                    "session_count": len(rows), "scope": "observed_sessions_only",
                }
    return result


def civil_cost_days(at, zone):
    """Exact UTC boundaries of local civil days in the current calendar year."""
    local = at.astimezone(ZoneInfo(zone))
    day = local.date().replace(month=1, day=1)
    result = {}
    while day <= local.date():
        start = datetime.combine(day, time.min, local.tzinfo).astimezone(timezone.utc)
        end = datetime.combine(day+timedelta(days=1), time.min, local.tzinfo).astimezone(timezone.utc)
        result[day.isoformat()] = (start, min(end, at))
        day += timedelta(days=1)
    return result


def _cost_bucket():
    return {"expected_seconds": 0.0, "observed_seconds": 0.0,
            "observed_energy_kwh": 0.0, "unpriced_energy_kwh": 0.0,
            "unattributed_energy_kwh": 0.0, "valuations": {}}


def _add_cost_bucket(target, source):
    for key in target.keys() - {"valuations"}:
        target[key] += source[key]
    for key, value in source["valuations"].items():
        bucket = target["valuations"].setdefault(key, [0.0, 0.0])
        bucket[0] += value[0]
        bucket[1] += value[1]


def _power_spans(states, first, last):
    """Partition a bounded native source timeline into known and unknown spans.

    A state can support at most MAX_OBSERVATION_AGE after its last update.
    Missing or duplicate conflicting readings remain explicit gaps.
    """
    if first >= last:
        return []
    samples, stamps = _power_index(states)
    # Older samples cannot contribute either a fresh value or an internal
    # expiry boundary. Limit edge construction to this actual interval.
    relevant = stamps[bisect_left(stamps, first-MAX_OBSERVATION_AGE):bisect_left(stamps, last)]
    edges = sorted({first, last} | {edge for stamp in relevant
                    for edge in (stamp, stamp+MAX_OBSERVATION_AGE)
                    if first < edge < last})
    spans = []
    for a, b in zip(edges, edges[1:]):
        index = bisect_right(stamps, a)-1
        value = None
        if index >= 0 and b-stamps[index] <= MAX_OBSERVATION_AGE:
            value = samples[index][1]
        spans.append((a, b, value))
    return spans


def _price_spans(quotes, first, last):
    """Qualified, unique source quote at each boundary, including explicit gaps."""
    rows = []
    for row in quotes:
        try:
            a = row.start.astimezone(timezone.utc)
            b = row.end.astimezone(timezone.utc)
            if (row.start.utcoffset() is None or row.end.utcoffset() is None
                    or b <= a or row.basis not in ("effective", "spot", "variable_reference")
                    or not isfinite(row.effective_price_per_kwh) or not row.currency):
                continue
        except (AttributeError, TypeError, ValueError, OverflowError):
            continue
        if a < last and b > first:
            rows.append((a, b, row))
    # Sweep once across the clipped quote boundaries. Distinct row indices
    # keep duplicate/overlapping observations ambiguous, including identical prices.
    opens, closes = {}, {}
    for index, (a, b, row) in enumerate(rows):
        opens.setdefault(max(first, a), []).append((index, row))
        closes.setdefault(min(last, b), []).append(index)
    edges = sorted({first, last} | opens.keys() | closes.keys())
    active = {}
    result = []
    for a, b in zip(edges, edges[1:]):
        for index in closes.get(a, ()):
            active.pop(index, None)
        active.update(opens.get(a, ()))
        result.append((a, b, next(iter(active.values())) if len(active) == 1 else None))
    return result


def _source_claims(bindings, first, last):
    """Physical source ownership intervals, including historical remaps."""
    claims = {}
    for uid, epochs in bindings.items():
        for i, epoch in enumerate(epochs):
            if not epoch["entity"]:
                continue
            a = max(first, datetime.fromisoformat(epoch["start"])) if epoch["start"] else first
            b = min(last, datetime.fromisoformat(epochs[i+1]["start"])) if i+1 < len(epochs) else last
            if a < b:
                claims.setdefault(epoch["entity"], []).append((uid, a, b))
    return claims


def _meter_gap_blocks(historical, meter_epochs, uid, start, end,
                      meter_claims, other_claims, spans, span_edges, price_spans,
                      attribution, cache):
    """Exact whole meter increments repair missing energy coverage, not power.

    No interpolation at a tariff, source, session or archive boundary. A
    multi-price increment remains unpriced; an ambiguous session is not
    attributed. Fully covered power intervals retain the existing estimate.
    """
    blocks = []
    for epoch in meter_epochs:
        entity = epoch["entity"]
        if not entity:
            continue
        if entity not in cache:
            samples, stamps, unique = _energy_index(historical.get(entity, ()))
            # Duplicate stamps, including conflicting readings, cannot bound
            # an independently measured interval.
            cache[entity] = (samples, stamps) if unique else ([], [])
        samples, stamps = cache[entity]
        # Bounded indexed slice: a high-frequency native meter must not be
        # rescanned from the start of the day for each quarter/hour.
        relevant = samples[bisect_left(stamps, start):bisect_right(stamps, end)]
        for (a, initial), (b, final) in zip(relevant, relevant[1:]):
            if (not start <= a < b <= end or initial is None or final is None
                    or final < initial
                    or _binding_for_interval(meter_epochs, a, b) != entity
                    or any(left < b and right > a for left, right in other_claims)
                    or any(other != uid and left < b and right > a
                           for other, left, right in meter_claims.get(entity, ()))):
                continue
            known, observed = _interval_power_evidence(spans, span_edges, a, b)
            delta = final-initial
            if observed >= (b-a).total_seconds() or known > delta+0.00001:
                continue  # preserve complete power evidence or expose conflict
            prices = [p for left, right, p in price_spans if left < b and right > a]
            signatures = {(p.currency, p.basis, p.effective_price_per_kwh)
                          for p in prices if p is not None}
            price = (prices[0] if prices and all(p is not None for p in prices)
                     and len(signatures) == 1 else None)
            overlapping = [(left, right, asset) for left, right, asset in attribution
                           if left < b and right > a]
            asset = (overlapping[0][2] if len(overlapping) == 1
                     and overlapping[0][0] <= a and overlapping[0][1] >= b else None)
            blocks.append((a, b, delta, price, asset))
    # A repeated source epoch can reference the same samples. Retain each
    # physical increment once; overlapping source claims were rejected above.
    return sorted({(a, b): (a, b, e, p, uid)
                   for a, b, e, p, uid in blocks}.values(), key=lambda row: row[0])


def _interval_power_evidence(spans, edges, first, last):
    """Measured power integral and seconds, not a filled/assumed gap."""
    energy, observed = 0.0, 0.0
    for index in range(max(0, bisect_right(edges, first)-1), len(spans)):
        a, b, power = spans[index]
        if a >= last:
            break
        seconds = (min(b, last)-max(a, first)).total_seconds()
        if power is not None and seconds > 0:
            observed += seconds
            energy += power*seconds/3600
    return energy, observed


def reconciled_quarter_history(historical, bindings, energy_bindings, selected,
                               receipts, asset_id, first, last, now):
    """One physical quarter per owner; exact native meter repair only.

    A recovered average is labelled as energy-derived, never represented
    as an independently measured instantaneous power. Unknown source
    remaps, shared owners, resets and cross-quarter meter deltas stay gaps.
    """
    empty = _quarter_actuals([], first, last, now)
    receipts_by_charger = {}
    for receipt in receipts:
        receipts_by_charger.setdefault(receipt.get("charger_id"), []).append(receipt)
    power_claims = _source_claims(bindings, first, last)
    meter_claims = _source_claims(energy_bindings, first, last)
    power_cache, meter_cache, by_source = {}, {}, {}
    result = []
    for uid in selected:
        epochs = bindings.get(uid, ())
        meter_epochs = energy_bindings.get(uid, ())
        for unknown in empty:
            since = datetime.fromisoformat(unknown["start"])
            until = datetime.fromisoformat(unknown["end"])
            source = _binding_for_interval(epochs, since, until)
            meter = _binding_for_interval(meter_epochs, since, until)
            overlaps = [(a, b) for other, a, b in power_claims.get(source, ())
                        if other != uid and a < until and b > since]
            row = dict(unknown)
            if source and not overlaps:
                if source not in by_source:
                    by_source[source] = {r["start"]: r for r in _quarter_actuals(
                        historical.get(source, ()), first, last, now)}
                row = dict(by_source[source].get(unknown["start"], unknown))
            # An ambiguous power remap or overlapping physical owner is not
            # repaired by assigning its kWh to an arbitrary logical owner.
            remap = any(epoch["start"] is not None and
                        since < datetime.fromisoformat(epoch["start"]) < until
                        for epoch in epochs)
            if (row["quality"] != "measured_power_integral" and meter
                    and not overlaps and not remap):
                if source not in power_cache:
                    spans = _power_spans(historical.get(source, ()), first, last)
                    power_cache[source] = (spans, [r[0] for r in spans])
                spans, edges = power_cache[source]
                blocks = _meter_gap_blocks(
                    historical, meter_epochs, uid, since, until, meter_claims,
                    overlaps, spans, edges, (), (), meter_cache,
                )
                energy, observed = _interval_power_evidence(spans, edges, since, until)
                for a, b, delta, _, _ in blocks:
                    already, seconds = _interval_power_evidence(spans, edges, a, b)
                    energy += delta-already
                    observed += (b-a).total_seconds()-seconds
                if blocks and abs(observed-(until-since).total_seconds()) < 0.001:
                    row.update(actual_energy_kwh=round(energy, 6),
                               actual_power_kw=round(energy*4, 6),
                               quality="measured_energy_delta")
            attributed = (_session_asset_at_time(receipts_by_charger.get(uid, ()), uid, since, until)
                          if (source or meter) and not overlaps and not remap else None)
            row.update(charger_id=uid, asset_id=attributed,
                       asset_provenance=("confirmed_closed_session" if attributed is not None
                                         else "unattributed_charger_actual"))
            if asset_id is None or asset_id == attributed:
                result.append(row)
    return result


def daily_costs(historical, bindings, configuration, first, last, quotes,
                receipts=(), active_sessions=None, *, energy_bindings=None,
                selected_chargers=None, session_partition=None):
    """Project one civil day from native power and the original tariff intervals.

    Every physical span is counted once at Charger/Site, then attributed to
    an asset only on a confirmed session interval. No session-average
    proration, assumed idle, duplicated native ledger or current assignment.
    """
    cfg_chargers = {row["id"] for row in configuration["chargers"]}
    cfg_assets = {row["id"] for row in configuration["assets"]}
    groups = {"controller": {"site": _cost_bucket()}, "charger": {},
              "asset": {uid: _cost_bucket() for uid in cfg_assets}}
    if last <= first:
        return groups
    price_spans = _price_spans(quotes, first, last)
    price_edges = [row[0] for row in price_spans]
    sessions = {}
    for row in (*receipts, *(dict(row, charger_id=uid)
                              for uid, row in (active_sessions or {}).items())):
        if not row.get("asset_id") or (row.get("ended_at") is not None
                and row.get("physical_stop_confirmed") is not True):
            continue
        try:
            a = datetime.fromisoformat(row["started_at"])
            b = datetime.fromisoformat(row["ended_at"]) if row.get("ended_at") else last
            if a.utcoffset() is None or b.utcoffset() is None:
                continue
            a, b = a.astimezone(timezone.utc), b.astimezone(timezone.utc)
            if a < b and a < last and b > first:
                sessions.setdefault(row["charger_id"], []).append((a, b, row["asset_id"]))
        except (KeyError, TypeError, ValueError, OverflowError):
            continue

    # A physical source may be reused sequentially, never charged twice for
    # overlapping historic claims. Keep the exclusive portions and disclose
    # ambiguous periods as missing coverage, without assigning an arbitrary owner.
    claims = _source_claims(bindings, first, last)
    energy_bindings = energy_bindings or {}
    meter_claims = _source_claims(energy_bindings, first, last)
    meter_cache = {}
    power_cache = {}

    def record_energy(bucket, energy, price, asset, uid, a, b):
        # Optional, ephemeral drilldown uses the VERY SAME physical pieces
        # counted at site/charger level. Never split a meter increment or
        # choose between overlapping session claims.
        session_bucket = None
        if session_partition is not None:
            matches = [row for row in session_partition.get(uid, ())
                       if row["first"] <= a and b <= row["last"]]
            if len(matches) == 1:
                session_bucket = matches[0]["bucket"]
                session_bucket["observed_seconds"] += (b-a).total_seconds()
        if energy == 0:
            return  # verified zero has no tariff requirement
        targets = [bucket]
        if session_bucket is not None:
            targets.append(session_bucket)
        if asset is not None:
            targets.append(groups["asset"].setdefault(asset, _cost_bucket()))
        else:
            bucket["unattributed_energy_kwh"] += energy
        for target in targets:
            target["observed_energy_kwh"] += energy
            if price is None:
                target["unpriced_energy_kwh"] += energy
            else:
                key = (price.currency, price.basis)
                value = target["valuations"].setdefault(key, [0.0, 0.0])
                value[0] += energy*price.effective_price_per_kwh
                value[1] += energy
    for uid in sorted(cfg_chargers | set(bindings)):
        if selected_chargers is not None and uid not in selected_chargers:
            continue
        bucket = groups["charger"].setdefault(uid, _cost_bucket())
        epochs = bindings.get(uid, ()) or ({"start": None, "entity": None},)
        attribution = sessions.get(uid, ())
        owner_edges = sorted({edge for a, b, _ in attribution for edge in (a, b)
                              if first < edge < last} | {edge
                              for row in (session_partition or {}).get(uid, ())
                              for edge in (row["first"], row["last"]) if first < edge < last})
        for i, epoch in enumerate(epochs):
            start = max(first, datetime.fromisoformat(epoch["start"])) if epoch["start"] else first
            end = min(last, datetime.fromisoformat(epochs[i+1]["start"])) if i+1 < len(epochs) else last
            entity = epoch["entity"]
            if start >= end:
                continue
            # A retired charger's final None epoch is a deletion tombstone,
            # while a configured charger without a source is missing evidence.
            if not entity and uid not in cfg_chargers and i+1 == len(epochs):
                continue
            bucket["expected_seconds"] += (end-start).total_seconds()
            if not entity:
                continue
            if entity not in power_cache:
                spans = _power_spans(historical.get(entity, ()), first, last)
                power_cache[entity] = (spans, [row[0] for row in spans])
            spans, span_edges = power_cache[entity]
            index = max(0, bisect_right(span_edges, start)-1)
            other_claims = [(a, b) for other, a, b in claims.get(entity, ()) if other != uid
                            and a < end and b > start]
            claim_edges = sorted({edge for a, b in other_claims for edge in (a, b)})
            blocks = _meter_gap_blocks(
                historical, energy_bindings.get(uid, ()), uid, start, end,
                meter_claims, other_claims, spans, span_edges, price_spans,
                attribution, meter_cache,
            )
            block_starts = [row[0] for row in blocks]
            block_edges = sorted({edge for a, b, *_ in blocks for edge in (a, b)})
            for a, b, energy, price, asset in blocks:
                bucket["observed_seconds"] += (b-a).total_seconds()
                record_energy(bucket, energy, price, asset, uid, a, b)
            for left, right, power in spans[index:]:
                if left >= end:
                    break
                a, b = max(left, start), min(right, end)
                if a >= b or power is None:
                    continue
                # Split at exact physical/session/tariff boundaries; the
                # measured power remains constant only inside this span.
                edges = sorted({a, b} | {
                    edge for edge in claim_edges[bisect_right(claim_edges, a):bisect_left(claim_edges, b)]
                } | {
                    edge for edge in owner_edges[bisect_right(owner_edges, a):bisect_left(owner_edges, b)]
                } | {
                    edge for edge in price_edges[bisect_right(price_edges, a):bisect_left(price_edges, b)]
                } | {
                    edge for edge in block_edges[bisect_right(block_edges, a):bisect_left(block_edges, b)]
                })
                for x, y in zip(edges, edges[1:]):
                    if any(left < y and right > x for left, right in other_claims):
                        continue
                    block_index = bisect_right(block_starts, x)-1
                    if block_index >= 0 and blocks[block_index][1] >= y:
                        continue  # this exact native meter increment was already counted
                    bucket["observed_seconds"] += (y-x).total_seconds()
                    energy = power*(y-x).total_seconds()/3600
                    matching = [asset for since, until, asset in attribution
                                if since <= x and until >= y]
                    asset = matching[0] if len(matching) == 1 else None
                    price_index = bisect_right(price_edges, x)-1
                    price = price_spans[price_index][2] if price_index >= 0 else None
                    record_energy(bucket, energy, price, asset, uid, x, y)
        _add_cost_bucket(groups["controller"]["site"], bucket)
    # Asset attribution completeness depends on all site observations, not
    # only the periods where an asset could already be identified.
    site = groups["controller"]["site"]
    for bucket in groups["asset"].values():
        bucket["expected_seconds"] = site["expected_seconds"]
        bucket["observed_seconds"] = site["observed_seconds"]
        bucket["unattributed_energy_kwh"] = site["unattributed_energy_kwh"]
    # A fully observed zero-energy day is a real zero only if the currency
    # is known; it must not introduce a second basis into a charged period.
    known_prices = {(price.currency, price.basis) for _, _, price in price_spans if price}
    if len(known_prices) == 1:
        key = next(iter(known_prices))
        for owners in groups.values():
            for bucket in owners.values():
                if (bucket["expected_seconds"] > 0
                        and abs(bucket["expected_seconds"]-bucket["observed_seconds"]) < 0.001
                        and bucket["observed_energy_kwh"] == 0):
                    bucket["valuations"][key] = [0.0, 0.0]
    return groups


def session_day_partition(historical, bindings, configuration, first, last, quotes,
                          receipts, active_sessions, observed, energy_bindings):
    """One raw-day projection and session portions with explicit residuals.

    Historic aggregate archives do not fabricate raw session details. Each
    counted physical segment belongs to at most one non-overlapping session.
    Full-session meter/receipt totals remain separately available.
    """
    partition = {}
    for row in [*receipts, *active_sessions.values(), *observed]:
        uid = row.get("charger_id")
        try:
            a = max(first, datetime.fromisoformat(row["started_at"]))
            b = min(last, datetime.fromisoformat(row["ended_at"])) if row.get("ended_at") else last
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not uid or a >= b:
            continue
        bucket = _cost_bucket()
        bucket["expected_seconds"] = (b-a).total_seconds()
        partition.setdefault(uid, []).append({
            "first": a, "last": b, "bucket": bucket,
            "key": (uid, row["started_at"], row.get("ended_at")),
        })
    raw = daily_costs(historical, bindings, configuration, first, last, quotes,
                      receipts, active_sessions, energy_bindings=energy_bindings,
                      session_partition=partition)
    day = first.isoformat()[:10]
    bounds = {day: (first, last)}
    groups = civil_period_costs(bounds, {day: raw})
    details = {}
    for uid, rows in partition.items():
        for row in rows:
            bucket = row["bucket"]
            scope = {"controller": {"site": bucket}, "charger": {}, "asset": {}}
            details[row["key"]] = civil_period_costs(bounds, {day: scope})["controller"]["site"]["today"]
    # The residual is physical energy not allocated to one unique interval;
    # it must remain visible rather than inventing a historical session.
    residual = {}
    for uid, periods in groups["charger"].items():
        total = periods["today"]
        assigned = sum(details[row["key"]]["observed_energy_kwh"] for row in partition.get(uid, ()))
        remainder = round(total["observed_energy_kwh"]-assigned, 6)
        residual[uid] = remainder if total["observed_seconds"] > 0 else None
    return {"groups": groups, "session_portions": details, "unallocated_energy_kwh": residual}


def civil_period_costs(days, available):
    """Merge day evidence without inventing missing dates, currency or prices."""
    if not days:
        return {}
    today = next(reversed(days))
    periods = {
        "today": [today],
        "month": [day for day in days if day[:7] == today[:7]],
        "year": list(days),
    }
    owners = {"controller": {"site"}, "charger": set(), "asset": set()}
    for day in available.values():
        for kind, values in day.items():
            owners[kind].update(values)
    result = {kind: {} for kind in owners}
    for kind, ids in owners.items():
        for uid in ids:
            result[kind][uid] = {}
            for period, keys in periods.items():
                bucket = _cost_bucket()
                present = 0
                for day in keys:
                    if day not in available:
                        continue
                    present += 1
                    daily = available[day].get(kind, {}).get(uid)
                    if daily is not None:
                        _add_cost_bucket(bucket, daily)
                    elif kind == "asset":
                        site = available[day]["controller"]["site"]
                        bucket["expected_seconds"] += site["expected_seconds"]
                        bucket["observed_seconds"] += site["observed_seconds"]
                        bucket["unattributed_energy_kwh"] += site["unattributed_energy_kwh"]
                values = bucket["valuations"]
                # Idle days have zero monetary impact and cannot make a
                # charged period mixed merely because their quote basis differs.
                charged_values = {key: value for key, value in values.items() if value[1] > 0}
                values = charged_values or values
                currency, basis = next(iter(values)) if len(values) == 1 else (None, None)
                covered_cost, covered_energy = values[(currency, basis)] if currency else (None, None)
                complete = (present == len(keys)
                            and abs(bucket["expected_seconds"]-bucket["observed_seconds"]) < 0.001
                            and bucket["unpriced_energy_kwh"] < 0.000001
                            and (kind != "asset" or bucket["unattributed_energy_kwh"] < 0.000001)
                            and bucket["expected_seconds"] > 0)
                row = {
                    "start": days[keys[0]][0].isoformat(),
                    "end": days[keys[-1]][1].isoformat(),
                    "days_available": present, "days_expected": len(keys),
                    "cost": round(covered_cost, 6) if complete and covered_cost is not None else None,
                    "covered_cost": round(covered_cost, 6) if covered_cost is not None else None,
                    "covered_energy_kwh": round(covered_energy, 6) if covered_energy is not None else None,
                    "observed_energy_kwh": round(bucket["observed_energy_kwh"], 6),
                    "unpriced_energy_kwh": round(bucket["unpriced_energy_kwh"], 6),
                    "unattributed_energy_kwh": round(bucket["unattributed_energy_kwh"], 6),
                    "observed_seconds": round(bucket["observed_seconds"], 3),
                    "expected_seconds": round(bucket["expected_seconds"], 3),
                    "currency": currency, "basis": basis,
                    "average_price_per_kwh": round(covered_cost/covered_energy, 6)
                        if covered_cost is not None and covered_energy else None,
                    "quality": ("qualified_reference_estimate" if complete and currency else
                                "no_charging" if complete and not values else
                                "mixed_price_basis_or_currency" if len(values) > 1 else
                                "partial_coverage" if present else "history_pending"),
                }
                result[kind][uid][period] = row
    return result


def period_cost_reconciliation(period_costs):
    """Same-snapshot site reconciliation, never a second financial ledger.

    Grouping dimensions are alternatives. Only compatible covered valuations
    may be subtracted; negative tariffs remain signed and gaps remain gaps.
    The remainder is not assigned to a current vehicle or charging session.
    """
    result = {}
    for period, site in period_costs.get("controller", {}).get("site", {}).items():
        result[period] = {}
        for kind in ("asset", "charger"):
            rows = [periods[period] for periods in period_costs.get(kind, {}).values()
                    if period in periods]
            known = [row for row in rows if row.get("observed_seconds", 0) > 0]
            if site.get("observed_seconds", 0) <= 0:
                result[period][kind] = {"energy_kwh": None, "covered_cost": None,
                                        "quality": "history_pending"}
                continue
            energy = site["observed_energy_kwh"]-sum(r["observed_energy_kwh"] for r in known)
            if abs(energy) < 0.00001:
                energy = 0.0
            signature = (site.get("currency"), site.get("basis"))
            valued = [r for r in known if r.get("covered_cost") is not None]
            compatible = (site.get("covered_cost") is not None and signature[0]
                          and all((r.get("currency"), r.get("basis")) == signature
                                  or r.get("covered_energy_kwh") == 0
                                  for r in valued)
                          and all(r.get("covered_cost") is not None
                                  or abs(r["observed_energy_kwh"]-r["unpriced_energy_kwh"]) < 0.00001
                                  for r in known))
            remainder = site["covered_cost"]-sum(r["covered_cost"] for r in valued) if compatible else None
            if remainder is not None and abs(remainder) < 0.00001:
                remainder = 0.0
            result[period][kind] = {
                "energy_kwh": round(energy, 6),
                "covered_cost": round(remainder, 6) if remainder is not None else None,
                "currency": signature[0] if compatible else None,
                "basis": signature[1] if compatible else None,
                "quality": ("reconciled_observed_energy" if energy == 0 else
                            "unattributed_energy" if kind == "asset" and energy > 0 else
                            "unreconciled_observed_energy"),
            }
    return result


async def read_recorder_samples(hass, first, end, entities):
    """Exact native Recorder range, without a second history authority."""
    from homeassistant.components.recorder import get_instance, history

    return await get_instance(hass).async_add_executor_job(
        history.get_significant_states,
        hass, first, end, list(entities), None, True, False, False, False, False,
    )


async def read_actual_history(hass, configuration, start, end, *,
                              charger_id=None, asset_id=None,
                              session_receipts=(), price_slots=(),
                              include_valuations=False, power_bindings=None,
                              include_observed_sessions=False, active_sessions=None,
                              tariff_entity=None, energy_bindings=None, tariff_bindings=None,
                              financial_days=None, as_of=None, include_quarters=True,
                              read_samples=None, include_retired_chargers=False, include_session_partition=False):
    """Query native Recorder once; background finance need not build graph rows."""
    now = as_of or datetime.now(timezone.utc)
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
    energy_bindings = (energy_bindings if energy_bindings is not None else
                       {c["id"]: [{"start": None, "entity": c.get("energy_entity")}]
                        for c in configuration["chargers"]})
    selected = [c["id"] for c in configuration["chargers"]
                if charger_id is None or c["id"] == charger_id]
    if charger_id is not None and charger_id in bindings and not selected:
        selected = [charger_id]

    if financial_days is not None or (include_retired_chargers and charger_id is None):
        selected = sorted(set(selected) | set(bindings))

    # Avoid scanning years of irrelevant receipts in each measured quarter
    # or tariff partition. All overlapping owners remain in scope, including
    # ambiguous attribution and previously deleted logical assets.
    session_receipts = [
        row for row in session_receipts
        if row.get("charger_id") in selected
        and row.get("continuity_quality") != "unknown"
        and receipt_overlaps(row, history_first, history_end)
    ]

    async def reply(rows, quality, historical=None):
        if not include_valuations and not include_observed_sessions and financial_days is None:
            return rows, quality
        quotes = price_slots
        if historical is not None and tariff_bindings is not None:
            quotes = _quotes_at_binding(
                hass, historical, tariff_bindings.get("site", ()), tariff_entity,
                price_slots, history_first, history_end,
            )
        elif historical is not None and tariff_entity:
            quotes = _historical_reference_quotes(
                hass, historical, tariff_entity, price_slots, history_first, history_end,
            )
        day_projection = None
        if financial_days is not None:
            # Computation is independent of physical control and off the HA
            # event loop; the raw data came from this same Recorder query.
            def project_days():
                return {
                    day: daily_costs(
                        historical or {}, bindings, configuration, a, min(b, history_end),
                        quotes if historical is not None else (), session_receipts, active_sessions,
                        energy_bindings=energy_bindings,
                    )
                    for day, (a, b) in financial_days.items()
                    if history_first <= a <= b <= history_end
                }
            day_projection = await hass.async_add_executor_job(project_days)
            if not include_valuations and not include_observed_sessions:
                return rows, quality, day_projection
        def project_sessions():
            # Pure Recorder projections can be CPU-heavy with frequent power
            # samples; never occupy the HA event loop or its physical guards.
            valued = {}
            if historical is not None and quotes:
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
                        historical.get(source, []), receipt, tuple(
                            row for row in quotes if row.start < ended and row.end > started
                        ), now,
                    )
                    if evidence is not None:
                        valued[(charger, receipt["started_at"],
                                receipt["ended_at"])] = evidence
            if not include_observed_sessions:
                return (rows, quality, valued)
            observed = (_observed_session_rows(
                historical, bindings, selected, history_first, history_end, now,
                session_receipts, active_sessions, quotes, energy_bindings,
            ) if asset_id is None else [])
            metrics = _receipt_view_metrics(
                historical, bindings, selected, history_first, history_end, now,
                session_receipts, active_sessions, quotes, asset_id, energy_bindings,
            )
            result = (rows, quality, valued, observed, metrics)
            if include_session_partition:
                result += (session_day_partition(historical, bindings, configuration, first, history_end, quotes,
                            session_receipts, active_sessions, observed, energy_bindings),)
            return result

        if historical is None:
            result = ((rows, quality, {}, [], {}) if include_observed_sessions
                      else (rows, quality, {}))
            if include_session_partition:
                result += (None,)
        else:
            result = await hass.async_add_executor_job(project_sessions)
        return (*result, day_projection) if financial_days is not None else result
    if not selected:
        return await reply([], "NO_MATCHING_CHARGER")
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
    if history_first >= history_end:
        return await reply([], "FUTURE_ONLY")
    for uid in selected:
        for index, epoch in enumerate(energy_bindings.get(uid, ())):
            if (epoch["entity"] and epoch["entity"] not in entities
                    and (epoch["start"] is None or datetime.fromisoformat(epoch["start"]) < history_end)
                    and (index+1 == len(energy_bindings[uid])
                         or datetime.fromisoformat(energy_bindings[uid][index+1]["start"]) > history_first)):
                entities.append(epoch["entity"])
    if not entities:
        return await reply([], "POWER_METER_NOT_CONFIGURED")
    if include_observed_sessions or include_valuations or financial_days is not None:
        tariff_sources = {
            epoch["entity"] for i, epoch in enumerate((tariff_bindings or {}).get("site", ()))
            if epoch["entity"]
            and (epoch["start"] is None or datetime.fromisoformat(epoch["start"]) < history_end)
            and (i+1 == len(tariff_bindings["site"])
                 or datetime.fromisoformat(tariff_bindings["site"][i+1]["start"]) > history_first)
        }
        if tariff_bindings is None and tariff_entity:
            tariff_sources.add(tariff_entity)
        entities.extend(sorted(tariff_sources - set(entities)))
    if "recorder" not in hass.config.components:
        return await reply([], "RECORDER_NOT_LOADED")
    try:
        # The runtime can share an identical in-flight native query. The
        # projection still uses its own exact as-of, owner and binding scope.
        query_end = min(now, history_end+timedelta(microseconds=1))
        if read_samples is None:
            historical = await read_recorder_samples(hass, history_first, query_end, entities)
        else:
            historical = await read_samples(history_first, query_end, entities)
        # The same exact samples feed all projections. Their lazy indexes
        # live only until this read completes, including off-loop work.
        historical = {entity: _RecorderSamples(states) for entity, states in historical.items()}
    except (ImportError, RuntimeError, ValueError, OSError, KeyError):
        return await reply([], "RECORDER_UNAVAILABLE")
    if financial_days is not None and not include_valuations and not include_observed_sessions:
        return await reply([], "FINANCIAL_DAY", historical)
    if first >= now:
        return await reply([], "FUTURE_ONLY", historical)
    if not include_quarters:
        # Session-only reads never calculate unused chart rows. Keep raw
        # absence explicit, distinct from retained aggregate statistics.
        quality = ("SESSION_HISTORY" if any(row.states for row in historical.values())
                   else "NO_RECORDER_SAMPLES") if include_retired_chargers else "QUARTERS_NOT_REQUESTED"
        return await reply([], quality, historical)
    # The same bounded Recorder evidence feeds both measured and exact
    # energy-reconciled quarters, off the HA event loop.
    result = await hass.async_add_executor_job(
        reconciled_quarter_history, historical, bindings, energy_bindings, selected,
        session_receipts, asset_id, first, last, now,
    )
    if not result:
        return await reply([], (
            "NO_CONFIRMED_ASSET_HISTORY" if asset_id is not None
            else "NO_RECORDED_QUARTERS"
        ), historical)
    if any(row["quality"] not in ("measured_power_integral", "measured_energy_delta")
           for row in result):
        return await reply(result, "INCOMPLETE_POWER_HISTORY", historical)
    if any(row["quality"] == "measured_energy_delta" for row in result):
        return await reply(result, "MEASURED_ENERGY_HISTORY", historical)
    return await reply(result, "MEASURED_POWER_HISTORY", historical)
