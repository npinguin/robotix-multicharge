# Community contracts — development candidate

> **Functional authority:** [FUNCTIONAL_SPECIFICATION.md](FUNCTIONAL_SPECIFICATION.md) defines the UC01–UC29, FLEX/FORECAST/UI-OWNER required user journeys and positive/negative acceptance. This document owns only implementation-facing interface constraints and candidate HA API contracts, never an independent functional backlog. Current gaps/CI/field status belong in [Issue #1](https://github.com/npinguin/robotix-multicharge/issues/1) and the existing PR/release workflow.

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

**Status:** `dev` has qualified source observations, an authenticated, bounded read-only plan/history query, source-tested 15-minute proposed/accepted/Recorder history, guarded physical switch/current commands and all six strategy execution paths, native HA Store restart intent holds, completed measured session receipts with narrowly qualified tariff costs, temporary guest expiry, native stop/sensors and an admin-validated Config Entry settings editor. This does **not** establish exclusive control of a real EVSE, actual HA/browser/hardware acceptance, end-to-end session recovery/permissions, UC01–UC29 completion or any release gate.

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

**Current `dev` action extension (candidate, not an independent service):**
`robotix_multicharge/command` accepts `pause` and `resume` in addition
to guarded `start`/`stop`/`set_current`. All use the same admin
WebSocket and single source-backed executor. Pause stores a per-Charger
control hold before physical STOP, only confirms after actual low-power
readback, persists over restart and removes both firm and indicative
scheduling for that Charger. Resume requires a verified physically idle
Charger and persistence, only removes the hold and **never sends START**.
The native Charger Pause/Resume buttons check HA administrator context;
native safe STOP remains independently available. No new role or
additional planner is introduced. The optional Charger `session_entity`
is a read-only source observation and is **not** authorization,
cable identity, power or energy evidence.


### Current dev owner fields — weekday calendars, bounded money and protected STOP

The [canonical functional specification](FUNCTIONAL_SPECIFICATION.md) owns the user-facing requirements. The implementation extends the **existing** `ChargeableAsset`, `Charger`, `ChargeController`, one Config Entry, one UTC 15-minute Planner, one guarded `NativeSwitchExecutor`, native Recorder and already-registered five-tab panel. These are development contracts, not a frozen public release.

| Native owner | Persisted fields / observed surface | Contract |
| --- | --- | --- |
| ChargeableAsset | `ready_by_repeat=none|daily|specific_days`, `ready_by_weekdays={mon:"06:45",wed:"08:30"}` | Specific days are separate local HH:MM deadlines; old `weekly` stays readable and is losslessly projected as a specific-day option on user edit |
| ChargeableAsset | `charging_windows={mon:{start:"22:00",end:"06:00"}}` | Optional permitted actual charging windows; cross-midnight uses selected start weekday, real UTC intervals and fail-closed DST; independent of Ready By |
| ChargeableAsset | `requested_kwh` XOR `requested_duration_minutes` XOR `requested_budget_amount` + `requested_budget_currency` | Exactly one finite intent, while `max_charge_kw` remains separate physical setpoint/cap; native Number and owner `Charging intention` readback |
| Charger-only | Admin-only `robotix_multicharge/command` with `action=start` and one of `energy_kwh`, `duration_minutes`, or `cost_amount` + `currency` | The same immutable command request and one writer; no fabricated vehicle or new command gateway |
| Charger | Active source-qualified receipt `budget_cost`, `budget_quality`, `budget_last_meter_value`, `budget_last_meter_at` | Only real cumulative meter increments and non-overlapping covered effective quote slots count; a meter delta spanning multiple effective prices is conservatively bounded at the largest applicable nonnegative price, never called exact settlement |
| Charger | `budget_accrued_cost`, `budget_cost_quality`, `budget_currency` on durable closed session receipt | Independent physical STOP/readback is required; `qualified_effective_meter_increments`, `conservative_effective_upper_bound`, or unknown, with original asset/Charger ID at time; no duplicate Finance ledger |
| ChargeController | One plan/revision, source quality, effective tariff coverage, proposed/accepted/measured slots | Weekday windows and money constraints use the *existing* executor/admission, not an HA automation or parallel price engine |

**Failure/permission:** invalid/non-effective budget tariff, source gap/stale meter, missing native connected/readback, inadequate wiring or exclusive owner, expiry, unavailable price, unrelated EVSE STOP blocked behind another START, single-EVSE competing commands and corrupted persisted evidence all retain explicit outcomes. The physically qualified STOP fast-path for a different already-active Charger still uses the one executor, no physical success until verified independent readback.

Developer and isolated-HA source tests do not establish real browser/provider/field acceptance. See [Issue #1](https://github.com/npinguin/robotix-multicharge/issues/1) and [Draft PR #9](https://github.com/npinguin/robotix-multicharge/pull/9) for exact head and remaining gates.

#### Original upstream price/SoC strategy owner contract

These `dev` optional Asset fields stay in the **same existing Config Entry and native HA Device**, never in a second price-policy service: `continuous_charging: bool`, `earliest_start_at: aware datetime`, `minimum_soc_pct: 0..100`, `maximum_price_per_kwh: finite number`, `price_currency: ISO-4217`, `low_price_trigger_per_kwh: finite number`, `low_soc_trigger_pct: 0..100`, `opportunistic_kind: off|type1|type2`, and `opportunistic_level_pct: 0..100`. All price policy decisions need current provider-qualified currency and full actual intervals; no invented value, new local clock scheduler or OEM write. The existing plan query exposes corresponding native owner entity references, source-quality reasons and proposed quarter slots; the guarded existing executor checks START and ongoing price/SoC policy again against physical evidence.

`ChargeDemand` carries only derived **source-qualified** minimum/low-SoC priority energy, pricing policy and continuity flags to its existing planner. A currency-budget demand additionally carries `budget_remaining_minutes` (maximum 1440 min cumulatively across physically confirmed sessions), not a second charging goal or public runtime. The 24h ceiling applies even if every approved `effective` price is 0 or negative. Physical Charger STOP remains confirmed only after independent power/current readback; a moved Asset keeps original immutable historical receipt attribution.

Upstream `Keep charger on`/preconditioning has **no generic actuator claim** in this contract. Without hardware evidence distinguishing vehicle supply/preconditioning from charging, it is intentionally unavailable. A future fully qualified native capability may be added through the same Charger interface and one writer, without EVSC runtime, second planner or exposing a private site adapter.

## Native HA contracts for independently installed consumers

- Source-neutral native HA entities for new logical properties and qualifying control actions. Stable unique IDs keyed on logical IDs and semantic property, never mutable names. No copied historical controls.
- **One bounded, read-only future-plan query**, proposed HA WebSocket message type `robotix_multicharge/get_plan`, with `schema_major:1`, exact `controller_id`, optional `charger_id` or `asset_id`, aware `start` and `end`, maximum 48h. Return `schema_major`, `revision`, `generated_at`, `valid_until`, `timezone`, `status`, `coverage`, `quality`, a bounded array of UTC time slots containing separate planned and measured values and optional source-qualified price/available capacity, deadline/shortfall and explanatory reason. Explicit authorization and scope checks. This is an interface *proposal* until target-HA testing freezes the name and schema; do not ship an incompatible second query.
- Native HA/Recorder holds measured history; technical kWh publication is scoped to exact charger/asset/interval/session and deduplicable. Monetary valuation is optional based on a qualified price authority; no generic second finance ledger.
- GUI Config Flow/Options Flow, optionally YAML import to the **same** validated Config Entry, one authority selected per installation; deterministic update/reload/unload/rollback, invalid fields explained, no ghost devices.
- Version/capabilities and major incompatibility, permissions, source absence/recovery, provider reload, safe no-data scenarios have explicit behavior. Generic HA public contracts only, no direct Python imports from another integration.

### Mandatory negative integration tests

Accepted HA action without physical readback ≠ confirmed; unqualified source ≠ zero/connected/safe; no dual writer or plan; no stale binding envelope going fail-open; on/off plug cannot modulate; no registry reparenting; dynamic asset rename retains history; consumer/chart may not re-optimize or substitute forecast for actual; unsupported mode must show unavailable; no hidden required provider or external product. Verify 1/2/4/10 chargers and event-storm/physical command suppression.

**Traceability:** The canonical UC01–UC29, FLEX/FORECAST/UI-OWNER functional scope and UX acceptance are maintained only in [Functional Specification](FUNCTIONAL_SPECIFICATION.md). [Architecture](ARCHITECTURE.md#fixed-five-tab-ux--approved-no-drift-implementation-specification) describes implementation; [Issue #1](https://github.com/npinguin/robotix-multicharge/issues/1) and the active PR track implementation and qualification evidence, not a second requirement set. No extra tracking spreadsheet. **Status:** implementation/qualification of these surfaces is OPEN; passing source CI tests only the current candidate types.
