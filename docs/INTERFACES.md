# Community contracts — development candidate

The integration's `domain.py`, `contracts.py` and `interfaces.py` currently define **candidate** Python types. They are not a released, compatible or Home Assistant-published API.

| Public-facing concern | Candidate interface | Intended invariant |
| --- | --- | --- |
| Charging assets | `ChargeableAsset` / `ChargeDemand` | Stable identity; explicit need, target, deadline and unknown source state |
| Charger capability | `Charger` / `ChargerProvider` | Observed and configured capabilities separated from requested commands |
| Prices | `PriceProvider` / `PriceSlot` | Zoned intervals, explicit currency, validated coverage and possible negative prices; no fixed country or all-in price inference |
| Available charging power | `PowerProvider` / `PowerEnvelope` | Optional, bounded time-based limit; no assumption that missing means unlimited |
| Charge plan | `ChargeController` / `ChargePlan` | Revisioned interval proposals/acceptance; planned does not mean actual |
| Hardware execution | `ChargeActuator` | Exclusive authorized writer; validated limits and independent readback |
| Read-only visualization | `PlanConsumer` | Plan status/intervals for the native charging dashboard |

## Charging Plan read view

The planned 15-minute Today/Tomorrow chart needs one bounded, read-only query on the Controller's plan. It must identify the controller and optional charger/asset filter, timezone-aware interval and plan revision. Its response will distinguish proposed/accepted power, actual measured power/energy, data quality, source coverage, relevant deadline and optional price or solar context.

Use native lightweight HA summary entities and Recorder for measured history. Do not replicate the planner or persist whole future timelines as large frequently rewritten sensor attributes.

**Status:** the `dev` source now implements explicitly selected HA observations, a bounded admin-only `robotix_multicharge/get_plan` read query and deterministic **proposed-only** 15-minute planning. It does **not** implement plan acceptance, physical command execution/readback, complete source/provider qualification, actual charge-session history, the fully qualified actionable five-tab experience or the full native Home Assistant lifecycle qualification. A source-tested optional card now reads proposed slots and currently qualified live observations, but its browser behavior has not been accepted in HA. See [functional use cases](https://github.com/npinguin/robotix-multicharge/issues/1).

## Contract-first implementer specification — candidate, not yet public API

The existing `domain.py`, `contracts.py` and `interfaces.py` are Python sketches, NOT an HA-public, tested or version-frozen interface. Extend them **in place**, with exactly the three existing logical concepts. Do not invent a second state bus, store, planner, brand-specific adapter core or compatibility facade. Standalone must work with ordinary HA integrations and without any other Robotix product.

### Canonical ownership and publish/read boundary

| Truth | Owner | Implementation acceptance |
| --- | --- | --- |
| Raw device identity, physical protocol, original controls/measurements | Native HA source integration | Reference by qualified registry identity; leave original devices/entities and history unchanged |
| Accepted charging-source binding and normalized charging meaning | MultiCharge charging specialization | Explicit source selection, timestamp, units, quality, capability and provenance; never guess by friendly name |
| Demand and policy | Exactly one selected authority per asset | Target or explicit kWh/duration, deadline, priority, revision and status; no duplicate target setters |
| Quarter-hour plan | One `ChargeController` | Per-Charger/Asset plan revision and coverage; signed grid/PV constraints and verified circuit/phase ceilings; explain infeasible targets |
| Physical EVSE commands | One qualified physical writer per exact Charger command scope | Authentication/permission, unique request/owner, capability, serialized execution, protected STOP and correlated observed readback |
| UI and outside consumers | Read-only canonical plan/observations plus guarded actions | No UI-owned facts/price math/plan engine, no raw service bypass and no mandatory external product |

### Required gaps to close in current candidate types

| Existing candidate | Required semantics / explicit test |
| --- | --- |
| `ChargeableAsset` / `AssetObservation` | Stable identity, explicitly selected source identity, fresh/stale/unknown, provenance (OEM/manual/qualified estimate), actual SoC separate from target and estimated; connection and assignment separate |
| `ChargeDemand` | **kWh XOR duration** with zero demand distinct from unavailable; user strategy, source/revision, one-off and recurring Ready By, timezone/resolved occurrence, priority, feasibility and shortage |
| `Charger` / `ChargerObservation` | Exact source, actual connection/charging/power/energy with coverage and source quality; on/off or verified current range and phase/circuit capability, owner/effective command admission |
| `PriceSlot` / `PriceProvider` | Explicit ISO-4217 currency, period, provenance and verified source/quality/coverage; effective price basis vs spot price; allow negative prices and distinct qualified tariffs per Charger; reject mixed currencies in one Charger plan |
| `PowerEnvelope` | Revision/issued/validity, binding/advisory, **complete applicable time and phase slots**, explicit zero hold, site/circuit/charger cap, stale/missing/fail-safe behavior. Current `current()` validity check must never imply unrestricted grant without a matching qualified slot |
| `ChargePlan` / `PlannedChargeSlot` | Deterministic UTC quarter boundaries and HA-local display offset, per-asset/Charger revision/slot, proposed vs accepted vs unavailable, forecast-only value and coverage, feasibility/deadline/shortfall; actual data never taken from plan |
| `ChargeActuator` / `CommandOutcome` | START/STOP/Off and valid setpoint only for confirmed capability; owner/actor/resource/request ID, permission, idempotency and conflicting pending/unknown blocking. Current `confirmed` timestamp is insufficient: require correlated, independent physical source observation reaching requested outcome |
| `PlanConsumer` | Pure read-only, authenticated, version/capability negotiation and bounded filtering, no command method masquerading as plan subscription |

Six public user modes: **Automatic, Solar, Economy, Ready By, Force Charge, Off**. Each has explicit backend eligibility and fallback/unavailable reason; Force Charge does not bypass any protection or binding power cap.

### Native HA contracts for independently installed consumers

- Source-neutral native HA entities for new logical properties and qualifying control actions. Stable unique IDs keyed on logical IDs and semantic property, never mutable names. No copied historical controls.
- **One bounded, read-only future-plan query**, proposed HA WebSocket message type `robotix_multicharge/get_plan`, with `schema_major:1`, exact `controller_id`, optional `charger_id` or `asset_id`, aware `start` and `end`, maximum 48h. Return `schema_major`, `revision`, `generated_at`, `valid_until`, `timezone`, `status`, `coverage`, `quality`, a bounded array of UTC time slots containing separate planned and measured values and optional source-qualified price/available capacity, deadline/shortfall and explanatory reason. Explicit authorization and scope checks. This is an interface *proposal* until target-HA testing freezes the name and schema; do not ship an incompatible second query.
- Native HA/Recorder holds measured history; technical kWh publication is scoped to exact charger/asset/interval/session and deduplicable. Monetary valuation is optional based on a qualified price authority; no generic second finance ledger.
- GUI Config Flow/Options Flow, optionally YAML import to the **same** validated Config Entry, one authority selected per installation; deterministic update/reload/unload/rollback, invalid fields explained, no ghost devices.
- Version/capabilities and major incompatibility, permissions, source absence/recovery, provider reload, safe no-data scenarios have explicit behavior. Generic HA public contracts only, no direct Python imports from another integration.

### Mandatory negative integration tests

Accepted HA action without physical readback ≠ confirmed; unqualified source ≠ zero/connected/safe; no dual writer or plan; no stale binding envelope going fail-open; on/off plug cannot modulate; no registry reparenting; dynamic asset rename retains history; consumer/chart may not re-optimize or substitute forecast for actual; unsupported mode must show unavailable; no hidden required provider or external product. Verify 1/2/4/10 chargers and event-storm/physical command suppression.

**Traceability:** UC01–UC29 and the UX baseline remain in [public Issue #1](https://github.com/npinguin/robotix-multicharge/issues/1) and [Architecture](ARCHITECTURE.md#fixed-five-tab-ux--approved-no-drift-implementation-specification). No extra tracking spreadsheet. **Status:** implementation/qualification of these surfaces is OPEN; passing source CI tests only the current candidate types.
