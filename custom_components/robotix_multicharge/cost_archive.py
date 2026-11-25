"""Native Recorder retention of qualified charging cost intervals.

Hourly rates are derived from the existing history calculation, not a billing
ledger. Civil midnight inside an hour is retained as two exact minute slices.
"""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from math import isclose, isfinite
from re import fullmatch

from .history import _cost_bucket, _add_cost_bucket

_METRICS = {"expected": "expected_seconds", "observed": "observed_seconds",
            "energy": "observed_energy_kwh", "unpriced": "unpriced_energy_kwh",
            "unattributed": "unattributed_energy_kwh"}


def hour_slices(first, last):
    result = {}
    cursor = first.astimezone(timezone.utc)
    while cursor < last:
        hour = cursor.replace(minute=0, second=0, microsecond=0)
        end = min(last, hour+timedelta(hours=1))
        result[cursor.isoformat()] = (cursor, end)
        cursor = end
    return result


def _part(first, last):
    hour = first.replace(minute=0, second=0, microsecond=0)
    if any(edge.second or edge.microsecond for edge in (first, last)):
        raise ValueError("archive requires minute-aligned boundaries")
    a, b = int((first-hour).total_seconds()/60), int((last-hour).total_seconds()/60)
    if not 0 <= a < b <= 60:
        raise ValueError("archive slice must fit one UTC hour")
    return hour, f"{a:02d}_{b:02d}"


def _prefix(entry_id):
    return "robotix_multicharge:cost_v1_"+sha256(entry_id.encode()).hexdigest()[:24]+"_"


def _owner(kind, uid):
    return "s" if kind == "controller" else kind[0]+sha256(uid.encode()).hexdigest()[:24]


def owner_map(cfg, bindings, receipts):
    owners = {"s": ("controller", "site")}
    for kind, rows in (("charger", cfg["chargers"]), ("asset", cfg["assets"])):
        for row in rows:
            owners[_owner(kind, row["id"])] = (kind, row["id"])
    for uid in bindings:
        owners[_owner("charger", uid)] = ("charger", uid)
    for row in receipts:
        if row.get("asset_id"):
            uid = row["asset_id"]
            owners[_owner("asset", uid)] = ("asset", uid)
    return owners


def archived_owner_map(entry_id, metadata, known):
    """Recover original IDs from native metadata; verify the ID hash.

    A removed Asset/Charger may no longer occur in the recent control
    receipts. Its Recorder metadata is already the durable owner provenance.
    Never use today's mapping or a display name as a substitute.
    """
    owners = dict(known)
    prefix = _prefix(entry_id)
    for stat_id, (_, info) in metadata.items():
        if not stat_id.startswith(prefix):
            continue
        match = fullmatch(r"\d\d_\d\d_([ac][0-9a-f]{24})_expected", stat_id[len(prefix):])
        if not match:
            continue
        owner = match.group(1)
        kind = "asset" if owner.startswith("a") else "charger"
        name = info.get("name")
        marker = "MultiCharge "+kind+" "
        if not isinstance(name, str) or not name.startswith(marker) or not name.endswith(" expected"):
            continue
        uid = name[len(marker):-len(" expected")]
        if uid and _owner(kind, uid) == owner:
            owners.setdefault(owner, (kind, uid))
    return owners


def archive_records(entry_id, slices, projections):
    """Actual hourly mean rates with explicit owner and valuation count markers."""
    result = {}
    prefix = _prefix(entry_id)
    for key, groups in projections.items():
        first, last = slices[key]
        hour, part = _part(first, last)
        seconds = (last-first).total_seconds()

        def record(owner, metric, value, unit, name):
            stat_id = prefix+part+"_"+owner+"_"+metric
            series = result.setdefault(stat_id, {"unit": unit, "name": name, "rows": []})
            series["rows"].append({"start": hour, "mean": value})

        count = 0
        for kind, owners in groups.items():
            for uid, bucket in owners.items():
                count += 1
                owner = _owner(kind, uid)
                label = "MultiCharge "+kind+" "+uid+" "
                for metric, field in _METRICS.items():
                    coverage = field.endswith("_seconds")
                    value = bucket[field]/(seconds if coverage else seconds/3600)
                    record(owner, metric, value, None if coverage else "kW", label+metric)
                for (currency, basis), (cost, energy) in bucket["valuations"].items():
                    suffix = currency.lower()+"_"+basis
                    record(owner, "cost_"+suffix, cost/(seconds/3600), currency+"/h", label+"cost "+suffix)
                    record(owner, "priced_"+suffix, energy/(seconds/3600), "kW", label+"priced power "+suffix)
                record(owner, "pairs", len(bucket["valuations"]), None, label+"valuation count")
        record("s", "owners", count, None, "MultiCharge archived owners")
    return result


def decode_archive(entry_id, slices, raw, owners, *, allow_recompose=True):
    """Reject incomplete writes and never infer absent statistics."""
    prefix = _prefix(entry_id)
    indexed = {}
    for stat_id, rows in raw.items():
        if not stat_id.startswith(prefix):
            continue
        match = fullmatch(r"(\d\d_\d\d)_(s|[ac][0-9a-f]{24})_(.+)", stat_id[len(prefix):])
        if not match:
            continue
        part, owner, metric = match.groups()
        for row in rows:
            stamp, value = row.get("start"), row.get("mean")
            if (type(stamp) not in (int, float) or type(value) not in (int, float)
                    or not isfinite(stamp) or not isfinite(value)):
                continue
            indexed.setdefault(stamp, {}).setdefault(part, {}).setdefault(owner, {})[metric] = value

    def decode_part(series, seconds):
        if not series or series.get("s", {}).get("owners") != len(series):
            return None
        groups = {"controller": {}, "charger": {}, "asset": {}}
        valid = True
        for owner, metrics in series.items():
            bucket = _cost_bucket()
            if not set(_METRICS) <= metrics.keys():
                valid = False
                break
            for metric, field in _METRICS.items():
                bucket[field] = metrics[metric]*(seconds if field.endswith("_seconds") else seconds/3600)
            pairs = {}
            for metric, value in metrics.items():
                match = fullmatch(r"cost_([a-z]{3})_(effective|spot|variable_reference)", metric)
                if match:
                    currency, basis = match.groups()
                    priced = metrics.get("priced_"+currency+"_"+basis)
                    if priced is None or priced < 0:
                        valid = False
                        break
                    pairs[(currency.upper(), basis)] = [value*seconds/3600, priced*seconds/3600]
            if (not valid or metrics.get("pairs") != len(pairs)
                    or any(value < 0 for field, value in bucket.items() if field != "valuations")
                    or bucket["observed_seconds"] > bucket["expected_seconds"]+0.001
                    or abs(sum(pair[1] for pair in pairs.values())+bucket["unpriced_energy_kwh"]
                           -bucket["observed_energy_kwh"]) > 0.00001):
                valid = False
                break
            bucket["valuations"] = pairs
            if owner in owners:
                kind, uid = owners[owner]
                groups[kind][uid] = bucket
        return groups if valid and "site" in groups["controller"] else None

    result = {}
    for key, (first, last) in slices.items():
        hour, part = _part(first, last)
        candidates = indexed.get(hour.timestamp(), {})
        exact = decode_part(candidates.get(part), (last-first).total_seconds())
        if exact is not None:
            result[key] = exact
            continue
        if not allow_recompose:
            continue
        # Timezone changes can turn two archived partial UTC-hour slices
        # into one full hour. Only a unique, complete, non-overlapping
        # partition is evidence; never prorate a larger interval.
        lower, upper = map(int, part.split("_"))
        qualified = []
        for candidate, series in candidates.items():
            a, b = map(int, candidate.split("_"))
            if lower <= a < b <= upper and candidate != part:
                groups = decode_part(series, (b-a)*60)
                if groups is not None:
                    qualified.append((a, b, groups))
        paths = {lower: [()]}
        for a, b, groups in sorted(qualified, key=lambda item: item[:2]):
            if a not in paths:
                continue
            destination = paths.setdefault(b, [])
            for chain in paths[a]:
                if len(destination) < 2:
                    destination.append((*chain, (a, groups)))
        if len(paths.get(upper, [])) == 1:
            result[key] = merge_slices(dict(paths[upper][0]))
    return result


def pending_archive_snapshot(queue):
    """JSON-safe write-ahead retry evidence; only unacknowledged native writes."""
    return {
        day: {
            "start": row["start"].isoformat(), "end": row["end"].isoformat(),
            "projections": {
                key: {
                    kind: {
                        uid: {**bucket, "valuations": [
                            [currency, basis, cost, energy]
                            for (currency, basis), (cost, energy) in bucket["valuations"].items()
                        ]}
                        for uid, bucket in owners.items()
                    }
                    for kind, owners in groups.items()
                }
                for key, groups in row["projections"].items()
            },
        }
        for day, row in queue.items()
    }


def restore_pending_archive(snapshot):
    """Validate exact original civil slices before adopting a durable retry."""
    if not isinstance(snapshot, dict):
        raise ValueError("invalid pending archive")
    result = {}
    for day, row in snapshot.items():
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("invalid pending archive day")
        first, last = datetime.fromisoformat(row["start"]), datetime.fromisoformat(row["end"])
        if (first.utcoffset() is None or last.utcoffset() is None
                or not timedelta(0) < last-first <= timedelta(hours=26)
                or first.second or first.microsecond or last.second or last.microsecond):
            raise ValueError("invalid pending archive interval")
        first, last = first.astimezone(timezone.utc), last.astimezone(timezone.utc)
        slices = hour_slices(first, last)
        projections = {}
        if not isinstance(row["projections"], dict) or not row["projections"]:
            raise ValueError("missing pending archive slices")
        for key, groups in row["projections"].items():
            if key not in slices or set(groups) != {"controller", "charger", "asset"}:
                raise ValueError("invalid pending archive slice")
            checked = {}
            for kind, owners in groups.items():
                if not isinstance(owners, dict):
                    raise ValueError("invalid archive owners")
                checked[kind] = {}
                for uid, bucket in owners.items():
                    if not isinstance(uid, str) or not uid or set(bucket) != set(_cost_bucket()):
                        raise ValueError("invalid archive bucket")
                    restored = _cost_bucket()
                    for field in restored.keys()-{"valuations"}:
                        value = bucket[field]
                        if type(value) not in (int, float) or not isfinite(value) or value < 0:
                            raise ValueError("invalid archive amount")
                        restored[field] = value
                    for currency, basis, cost, energy in bucket["valuations"]:
                        if (not isinstance(currency, str) or not fullmatch(r"[A-Z]{3}", currency)
                                or basis not in ("effective", "spot", "variable_reference")
                                or (currency, basis) in restored["valuations"]
                                or any(type(v) not in (int, float) or not isfinite(v)
                                       for v in (cost, energy)) or energy < 0):
                            raise ValueError("invalid archive valuation")
                        restored["valuations"][(currency, basis)] = [cost, energy]
                    if (restored["observed_seconds"] > restored["expected_seconds"]+0.001
                            or abs(sum(v[1] for v in restored["valuations"].values())
                                   +restored["unpriced_energy_kwh"]
                                   -restored["observed_energy_kwh"]) > 0.00001):
                        raise ValueError("invalid archive coverage")
                    checked[kind][uid] = restored
            if set(checked["controller"]) != {"site"}:
                raise ValueError("invalid archive controller")
            projections[key] = checked
        result[day] = {"start": first, "end": last, "projections": projections}
    return result


def archive_projection_matches(original, restored):
    """Native mean-rate conversion can round; ownership and value must match."""
    if original.keys() != restored.keys():
        return False
    def same(a, b):
        return isclose(a, b, rel_tol=1e-9, abs_tol=1e-6)
    for kind, owners in original.items():
        if owners.keys() != restored[kind].keys():
            return False
        for uid, bucket in owners.items():
            observed = restored[kind][uid]
            if (bucket.keys() != observed.keys()
                    or bucket["valuations"].keys() != observed["valuations"].keys()
                    or any(not same(value, observed[field])
                           for field, value in bucket.items() if field != "valuations")
                    or any(not all(same(a, b) for a, b in zip(pair, observed["valuations"][key]))
                           for key, pair in bucket["valuations"].items())):
                return False
    return True


def merge_slices(projections):
    result = {"controller": {}, "charger": {}, "asset": {}}
    for groups in projections.values():
        for kind, owners in groups.items():
            for uid, bucket in owners.items():
                _add_cost_bucket(result[kind].setdefault(uid, _cost_bucket()), bucket)
    return result


async def read_archive(hass, entry_id, days, cfg, bindings, receipts, *, allow_recompose=True):
    """Bounded native statistic read; None is unavailable, {} is absent."""
    if not entry_id or "recorder" not in hass.config.components:
        return None
    slices = {key: pair for first, last in days.values()
              for key, pair in hour_slices(first, last).items()}
    if not slices:
        return {}
    try:
        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.statistics import get_metadata, statistics_during_period
        recorder = get_instance(hass)
        prefix = _prefix(entry_id)
        owners = owner_map(cfg, bindings, receipts)

        def read():
            metadata = get_metadata(hass, statistic_source="robotix_multicharge")
            ids = {uid for uid in metadata if uid.startswith(prefix)}
            if not ids:
                return {}
            first = min(a for a, _ in slices.values()).replace(minute=0)
            last = max(b for _, b in slices.values())
            end = last.replace(minute=0)+timedelta(hours=1)
            raw = statistics_during_period(hass, first, end, ids, "hour", None, {"mean"})
            return decode_archive(entry_id, slices, raw,
                                  archived_owner_map(entry_id, metadata, owners),
                                  allow_recompose=allow_recompose)

        return await recorder.async_add_executor_job(read)
    except (ImportError, RuntimeError, ValueError, OSError, KeyError):
        return None


def write_archive(hass, entry_id, slices, projections):
    """Queue native statistics; never write charging control state."""
    if not entry_id or "recorder" not in hass.config.components:
        return
    from homeassistant.components.recorder.models import StatisticMeanType
    from homeassistant.components.recorder.statistics import async_add_external_statistics
    for stat_id, series in archive_records(entry_id, slices, projections).items():
        async_add_external_statistics(hass, {
            "statistic_id": stat_id, "source": "robotix_multicharge",
            "name": series["name"], "unit_of_measurement": series["unit"],
            "unit_class": None, "mean_type": StatisticMeanType.ARITHMETIC, "has_sum": False,
        }, series["rows"])
