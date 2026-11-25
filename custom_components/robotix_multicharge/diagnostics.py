"""Home Assistant native diagnostics for a closing iteration on real charging hardware.

Download through Settings > Devices & services > Robotix MultiCharge > Diagnostics.
No new recorder, event bus or log store; source evidence and existing session
receipts remain authoritative. Export deliberately pseudonymizes local names,
HA entity IDs and logical asset identifiers; only explicit user export leaves HA.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from .const import DOMAIN


def _alias(value):
    if value is None:
        return None
    return "ref-" + sha256(str(value).encode("utf-8")).hexdigest()[:12]


def _evidence(item):
    if item is None:
        return {"value": None, "quality": "unknown", "reason": "NOT_OBSERVED",
                "observed_at": None}
    at = item.observed_at
    return {"value": item.value, "quality": item.quality, "reason": item.reason,
            "observed_at": at.isoformat() if at is not None else None}


def _by_id(rows):
    return {_alias(key): value for key, value in rows.items()}


def _action(row):
    return {
        key: (_alias(value) if key in ("charger_id", "asset_id", "request_id",
                                      "meter_entity", "target_id") else value)
        for key, value in row.items()
        if key not in ("name", "title")
    }


def build_diagnostics(runtime, entry, captured_at=None):
    """Structured, bounded facts for user-initiated incident export.

    Preserve negative/error evidence and unknown vs measured zero. No raw site,
    vehicle names or entity IDs; no copied HA state attributes or credentials.
    """
    when = captured_at or datetime.now(timezone.utc)
    cfg = runtime.configuration
    planning = runtime.assessment
    forecast = runtime.forecast_assessment
    obs = runtime.observations
    return {
        "schema_major": 1,
        "captured_at": when.astimezone(timezone.utc).isoformat(),
        "integration": {
            "domain": DOMAIN,
            "entry_source": getattr(entry, "source", None),
            "config_entry_schema_version": getattr(entry, "version", None),
            "active": runtime.active,
            "configuration_revision": runtime.live_state()["configuration_revision"],
        },
        "controller": {
            "id": _alias(cfg["controller"]["id"]),
            "mode": cfg["controller"]["mode"],
            "max_parallel": cfg["controller"]["max_parallel"],
            "power_adjustment_interval_minutes": cfg["controller"].get("power_adjustment_interval_minutes", 5),
            "pending_cost_archive_days": len(runtime._archive_pending),
            "pending_cost_archive_unreadable": runtime._archive_unreadable is not None,
            "max_power_kw": cfg["controller"].get("max_power_kw"),
            "phase_limits_a": cfg["controller"].get("phase_limits_a"),
            "bindings": {
                field: _alias(value) for field, value in cfg["controller"].items()
                if field.endswith("_entity")
            },
        },
        "chargers": [{
            "id": _alias(item["id"]),
            "kind": item["kind"],
            "rated_power_kw": item["rated_power_kw"],
            "voltage_v": item.get("voltage_v"),
            "configured_current": {key: item.get(key) for key in ("min_current_a", "max_current_a", "current_step_a")},
            "effective_current": {key: runtime.executor.effective_charger(item).get(key) for key in ("min_current_a", "max_current_a", "current_step_a")},
            "min_charging_power_kw": item.get("min_charging_power_kw"),
            "max_charging_power_kw": item.get("max_charging_power_kw"),
            "phase_count": item.get("phase_count"),
            "phase_ids": item.get("phase_ids"),
            "circuit_limit_a": item.get("circuit_limit_a"),
            "control_owner": item.get("control_owner", "external"),
            "physical_commissioned": item.get("physical_commissioned", False),
            "assigned_asset": _alias(item.get("asset")),
            "dedicated_asset": _alias(item.get("dedicated_asset_id")),
            "bindings": {
                field: _alias(value) for field, value in item.items()
                if field.endswith("_entity")
            },
        } for item in cfg["chargers"]],
        "assets": [{
            "id": _alias(item["id"]),
            "kind": item.get("kind"),
            "temporary": bool(item.get("temporary")),
            "has_soc_binding": bool(item.get("soc_entity")),
            "has_soc_target": item.get("target_soc") is not None,
            "has_budget_request": item.get("requested_budget_amount") is not None,
            "has_energy_request": item.get("requested_kwh") is not None,
            "has_duration_request": item.get("requested_duration_minutes") is not None,
            "has_deadline": bool(item.get("ready_by") or item.get("ready_by_weekdays")),
            "has_capacity": item.get("capacity_kwh") is not None,
            "has_efficiency": item.get("charge_efficiency") is not None,
            "deadline_repeat": item.get("ready_by_repeat", "none"),
        } for item in cfg["assets"]],
        "observations": {
            "sources": {
                key: _alias(value) if key == "tariff_source" else value
                for key, value in obs.get("sources", {}).items()
            },
            "chargers": {
                _alias(uid): {key: _evidence(readings.get(key))
                              for key in ("connected", "power_kw", "session")}
                for uid, readings in obs.get("chargers", {}).items()
            },
            "assets": {
                _alias(uid): {
                    "soc": _evidence(readings.get("soc")),
                    "effective_power_kw": _evidence(readings.get("effective_power_kw")),
                    "power_charger": _alias(readings.get("power_charger_id")),
                } for uid, readings in obs.get("assets", {}).items()
            },
        },
        "planning": {
            "status": planning.plan.status if planning else "unavailable",
            "revision": planning.plan.revision if planning else None,
            "generated_at": (
                planning.plan.generated_at.isoformat() if planning else None
            ),
            "forecast_status": forecast.plan.status if forecast else "not_available",
            "excluded": _by_id(runtime.excluded),
            "forecast_excluded": _by_id(runtime.forecast_excluded),
            "forecast_reasons": _by_id(forecast.reasons) if forecast else {},
            "forecast_coverage": _by_id(forecast.coverage) if forecast else {},
            "forecast_shortfall_kwh": _by_id(forecast.shortfall_kwh) if forecast else {},
            "goal_assessments": {
                _alias(uid): {**goal, "asset_id": _alias(goal["asset_id"])}
                for uid, goal in runtime.goal_assessments.items()
            },
            "reasons": _by_id(planning.reasons) if planning else {},
            "coverage": _by_id(planning.coverage) if planning else {},
            "shortfall_kwh": _by_id(planning.shortfall_kwh) if planning else {},
            "proposed_kwh": _by_id(planning.proposed_kwh) if planning else {},
        },
        "connection_identity": {
            _alias(c["id"]): {
                "status": "confirmed" if receipt else "unconfirmed",
                "asset_id": _alias(receipt["asset_id"]) if receipt else None,
                "connection_started_at": receipt["connected_at"] if receipt else None,
                "confirmed_at": receipt["confirmed_at"] if receipt else None,
                "basis": receipt.get("basis") if receipt else None,
            }
            for c in cfg["chargers"]
            for receipt in [runtime.executor.connection_confirmation(c, when)]
        },
        "execution": {
            "action_health": runtime.live_state()["action_health"],
            "persistence_verified": runtime.executor._persistence_verified,
            "quarantined_chargers": sorted(
                _alias(uid) for uid in runtime.executor._quarantine
            ),
            "capabilities": _by_id(runtime.executor.capabilities()),
            "outcomes": {
                _alias(uid): _action(result)
                for uid, result in runtime.executor.snapshot().items()
            },
            "active_sessions": {
                _alias(uid): _action(result)
                for uid, result in runtime.executor.session_snapshot().items()
            },
            "completed_sessions": [
                _action(row) for row in runtime.executor.completed_sessions()
            ],
        },
        "finance_retention": {
            "pending_days": len(runtime._archive_pending),
            "projected_days": len(runtime._daily_costs),
            "pending_slices": sum(len(rows) for rows in runtime._archive_pending.values()),
        },
        "settings_action": (
            _action(runtime.settings_action_snapshot())
            if runtime.settings_action_snapshot() else None
        ),
    }


async def async_get_config_entry_diagnostics(hass, entry):
    """Standard HA diagnostics download; no extra service or public endpoint."""
    from homeassistant.components.diagnostics import async_redact_data

    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime is None:
        return {"schema_major": 1, "domain": DOMAIN, "runtime": "not_loaded"}
    # Defensive final redaction also catches future secret fields added to
    # narrow diagnostic records. IDs and entity names are already aliased.
    return async_redact_data(
        build_diagnostics(runtime, entry),
        {"token", "password", "secret", "api_key", "access_token",
         "refresh_token", "client_secret", "authorization"},
    )
