# Architecture and user experience

## Purpose and ownership

Robotix MultiCharge is an independent Home Assistant integration for coordinating electrical charging. It starts with cars but can support other rechargeable mobility assets when their real charging capabilities are known.

| Logical object | Responsibility |
| --- | --- |
| `ChargeController` | One coordinated plan for a group of charge points and a configured charging power ceiling |
| `Charger` | The logical charge point, its supported controls, assigned asset and physical readback |
| `ChargeableAsset` | The object needing energy, its requested amount, target and Ready By deadline |

One Controller coordinates its Chargers. A Charger has one authorized physical command owner. A logical association is not evidence that a particular vehicle is physically connected or identified.

The original Home Assistant integrations keep ownership of the physical devices, source data and their entity IDs. MultiCharge exposes stable logical charging devices without copying or reparenting the source devices.

## Configuration

**Recommended:** native Config Flow and Options Flow, with guided steps for controller → chargers → assets → optional sources → verification. Clear names and safe defaults for beginners.

**Expert:** optional declarative YAML import. The YAML representation and UI use the same schema, field meanings and validation. The active configuration has one owner: YAML when imported or HA Options when UI-authored. There is no YAML/Jinja planning engine or duplicate settings store.

Illustrative expert configuration (shape is under development; not yet qualified in HA):

```yaml
# configuration.yaml
robotix_multicharge: !include multicharge.yaml

# multicharge.yaml
controller:
  id: home
  name: Home charging
  max_parallel: 2
  max_power_kw: 11
assets:
  - id: family_car
    name: Family car
    kind: car
    soc_entity: sensor.family_car_battery
    target_soc: 80
chargers:
  - id: driveway
    name: Driveway
    kind: variable_current
    rated_power_kw: 11
    phase_count: 3
    min_current_a: 6
    max_current_a: 16
    power_entity: sensor.driveway_power
```

Config/Options Flow code, YAML structural validation and read-only logical setup devices have been committed. Real HA setup, import/reload, Options editing and rollback still require qualification. On `dev`, physical actuation is source-tested but remains gated by explicit owner selection, verified capabilities, a commissioning declaration and real independent readback. No field commissioning is approved.

## User experience and native entities

| View | Primary task |
| --- | --- |
| **Overview** | See what is charging, what comes next and what needs attention |
| **Charging Plan** | View today/tomorrow planned vs measured charging and readiness |
| **Chargeable Assets** | Manage energy needs, targets, deadlines and source quality |
| **Chargers** | See connection, assignment, capabilities and true hardware feedback |
| **Settings** | Guided setup, source mapping, strategy, limits and diagnostics |

The six requested modes are Automatic, Solar, Economy, Ready By, Force Charge and Off. A manual command still obeys the configured limits and physical equipment protections.

Expose stable native HA device and entity IDs for the three logical concepts. Ordinary HA dashboards and automations must remain possible even without a bespoke card. A dedicated chart is justified for the future interval timeline; no second planner or data store belongs in the frontend.

Logical identity and selected source bindings change only through deliberate structural edits. Live SoC, energy, current and availability updates never rebuild device registry topology. Missing and unknown must never be rendered as zero or as a successful charge.

## Charging plan timeline

A single responsive, bundled timeline will be usable at ChargeController level and filtered by Charger or ChargeableAsset.

- 15-minute slots for today and tomorrow in the HA timezone, including 23/25-hour daylight-saving days. A vehicle gets prospective charged kW slots **only when the Charger is currently physically connected and the vehicle identity is verified or user-confirmed for this exact current connection**. A saved charger preference is not a connection or identity assertion. Unplugged vehicles remain saved/pending without future power bars; historical actuals remain visible.
- Proposed plan, accepted plan and **measured** actuals distinguished, with power (kW), energy (kWh) and source freshness. Give the user a **Color by Vehicle / Color by Charger** identity toggle with stable colors derived from immutable IDs (never array index). Keep these identity hues consistent across both days, renames and rebinds; encode Proposed/Accepted/Measured separately by opacity, stroke/pattern and explicit label, not a single shared color. The chart shows the selected vehicle **and** Charger for each slot, and does not double-count physical measured kW.
- Ready By and expected shortfall clearly indicated; optional electricity price and solar/context sources when available.
- A simple mobile view, accessible labels, readable legends and explicit unavailable/unknown states.
- Future slots queried through one bounded, read-only plan view; measured history from native HA telemetry and Recorder. Do not rewrite 48-hour plan arrays into giant sensor attributes or compute a new plan in the chart.

The source contains a deterministic 15-minute proposal planner, an admin-only bounded native HA query and one source-tested five-tab UI with separate proposed, accepted and actual signals. A single guarded actuator handles selected native switch and adjustable-current commands and 15-minute Automatic/Solar/Economy/Ready By execution; manual Force Charge and Off use the same writer. It requires explicit exclusive ownership, commissioning, qualified source/capability/phase/circuit evidence and independent power/current readback. The implementation now also includes native completed-session receipts, conservative tariff costing, an admin-validated Config Entry preferences editor, safe native STOP button, temporary guest expiry and stable historic session attribution. **Source and simulated HA-service tests are not actual HA/browser or EVSE commissioning. Another provider may still retain physical authority; full session recovery, user permission scope, all five rendered views and complete UC01–UC29 end-to-end qualification remain OPEN.**

## Planning, physical execution and safety

```text
Native HA sources (charger, asset, price, solar, available site power)
    -> validated binding and source freshness
ChargeableAsset needs + Charger capabilities
    -> ChargeController: coordinated charging plan
    -> one authorized Charger actuator
    -> independent actual hardware readback
```

The configured power budget, circuit and charger limits are binding safety constraints, not soft suggestions. Missing or stale safety-critical capacity is never treated as unlimited. A verified on/off switch cannot be represented as variable-current control. A command acknowledgment is not proof of actual physical power change.

The installed equipment and built-in charger protections remain authoritative. Any physical execution must remain disabled until real hardware and fail-safe behavior are qualified.

## Acceptance and tracking

The [functional use case matrix and qualification checklist](https://github.com/npinguin/robotix-multicharge/issues/1) are maintained in one issue. Include 1/2/4/10 charger scenarios; no-SoC, missing price and meter sources; time zones/DST; deadline feasibility; unsafe or rejected commands; real readback; configuration persistence; and HA restart/unload/rollback.

This document describes public implementation boundaries, not confidential project integration plans. Do not mark source CI, mock screens or an unqualified package Feature Complete.

## Fixed five-tab UX — approved no-drift implementation specification

**Visual reference:** owner-approved five-screen presentation in the 2026-11-22 conversation. It is the design acceptance target, not permission to create a new layout. Target **≥99% fidelity** to the approved appearance; it is NOT measured or achieved yet. Engineers without the earlier conversation use the explicit screen anatomy below, then capture the original illustrated reference before any quantified claim. Real screenshots, equal seeded data and owner review determine final acceptance.

**Exactly these five tabs in this order:** **Overview → Charging Plan → Chargeable Assets → Chargers → Settings**. One self-contained frontend experience included with the community integration, enabled by default for ordinary HA frontend installations with a supported opt-out. No sixth product screen, alternative dashboard, redundant scheduler or external frontend dependency. Native HA devices/entities also remain independently usable in ordinary dashboards.

| Tab | Visible screen anatomy in the approved order | Required interaction |
| --- | --- | --- |
| **Overview** | Site title + mode badge; one row of **three compact equal KPIs**: active chargers, total **actual** power in kW, qualified current price/currency per kWh; stacked compact chargeable-asset rows with icon, actual battery→target or unknown/manual demand, progress, status badge, Ready By and charger; divider; **Next action** with one clear recommendation/attention | Show **Automatic, Solar, Economy, Ready By, Force Charge, Off** as daily modes. An unqualified mode is visibly unavailable with reason, never silently selectable |
| **Charging Plan** | Title; **Today/Tomorrow** switch; **All Chargers / selected Charger or Asset** filter; intuitive full-width 15-minute power chart with **Color by Vehicle / Color by Charger**, stable and accessible per-ID hues and identity legend; distinct proposed/accepted/measured patterns and qualified-price line; divider; **Next planned session** and **Reason** | A future vehicle slot is drawn only for an actually connected **and current-connection identified/explicitly confirmed** vehicle, never merely a saved preference. Show vehicle↔Charger, time, kW and source reason; unplugged Assets remain waiting outside the active chart, past measured sessions persist, UTC/HA-local DST 92/96/100 slots respected; no fake future actuals, cost or double allocation |
| **Chargeable Assets** | Title + configured count; stacked expandable asset cards, including unplugged/Guest; name/icon, vehicle intent/readiness, 2-column Battery/Target/Ready By/selected Charger, priority/source provenance, Add | Persist identity, SoC/targets/finite kWh/duration/deadline regardless of cable. Make Assign/Change/Unassign an **idle-only** routine operation. Vehicle is selected on **at most one** Charger and only counted in active charging after separate real connection and session-identity verification |
| **Chargers** | Title + configured count; cards for all physical Chargers even when no vehicle is registered; observed connection, actual kW, control capability, **selected vs confirmed connected vehicle** and Details | Show independent native connection/readback and selected assignment. Allow a safe idle-only change or No vehicle, require current-plug identity confirmation for active vehicle planning. A Charger with a connected unknown vehicle may offer only an explicit finite manual unattributed session if qualified. Unsafe/active reassignment blocked; leave vendor device untouched |
| **Settings** | Title + setup badge; six items in this **exact** order: **Charging site**, **Sources & bindings**, **Charging strategy**, **Safety & limits**, **Integrations**, **Advanced & YAML** | Beginner wizard **Site → Charger → Asset → Sources → Verify**; inline selectors/validation, advanced progressive disclosure; optional expert YAML import to the same validated configuration authority |

**Visual rules:** compact rounded HA-theme cards, consistent density and spacing, readable units and headings, restrained badges, simple meaningful icons and accessible colors/legends. First-view attention and action before low-level diagnostics. No giant hero, multi-step unrelated dialogs, banners or expert-only material on beginner home screen. One bundled lightweight frontend implementation; no extra framework or frontend-owned planner.

**Screenshot acceptance matrix:** fixed populated fixture (2 assets/3 chargers), empty fresh install, unknown/stale source, missing price, infeasible deadline, pending/unknown command; mobile **390×844**, tablet **1024×768**, desktop **1600×900**; light/dark. Inspect scrolling, focus, touch, axes and labels, true card order, conditional states, actual readback, error presentation. Capture original approved reference and the real HA rendering in the same state and viewport. Changes to this screen contract require owner approval recorded in existing Issue #1 BEFORE changing the implementation.

## Native logical devices — no historical facades

One stable logical HA Device Registry identity per product Controller/Charger/ChargeableAsset ID; native source devices retain their identifiers, entity registry entries and Recorder history. Never duplicate original physical devices or copy provider entities/controls into a new logical device. No legacy EVSC entity aliases or bridge sensors, no semantic parentage with HA `via_device`. Source observations only update runtime values; structural changes require explicit validated configuration revisions.

| Logical device | Canonical specialist properties/actions at Feature Complete | Excluded |
| --- | --- | --- |
| **ChargeController** | Site-wide mode, electrical group/phase/circuit budget, active-eligible charging candidate allocation, 15-minute proposed/accepted/actual plan/reasons, aggregate verified actual kW and scheduling priority | Vehicle SoC and connection identity, raw charger duplicate, secondary energy planner, giant 48h sensor payload |
| **Charger** | Stable source/physical connection/occupancy, verified capabilities/phase/circuit/current, exact native command ownership and readback, own charging session and meter/provenance, **one saved asset assignment (nullable)** plus separate **current-connection identity evidence** | Battery demand/SoC truth, inference that selected saved Asset is physically plugged in, reparented vendor device or second EVSE writer |
| **ChargeableAsset** | Stable registered Vehicle/Guest identity, OEM/manual/unknown SoC provenance, portable target/kWh/duration/Ready By/priority/remaining measured need, expiry; selected Charger as **derived, read-only relation** and waiting/connected/active state | Physical switch, duplicate writable assignment, a second OEM truth, second energy planner, direct wire control |

Normal HA sensors/selects/buttons must be independently usable in user dashboards and automations, with current values and safe role-based admission. A single `Readiness` diagnostic is a valid canonical property; the current constant `not_commissioned` is development-only and must become true runtime evidence. No permanent placeholders, unqualified control buttons or silently renamed unique IDs.

## Owner-approved functional clarification: interchangeable vehicles, independent Chargers and chart colors

Recorded in the **existing [Issue #1](https://github.com/npinguin/robotix-multicharge/issues/1)**, 22 November 2026; this expressly updates the previously fixed identity color treatment **only**, not the five-tab anatomy or product design baseline. The only authoritative saved Asset↔Charger assignment is `charger.asset` in the existing Config Entry: zero/one per Charger, zero/one Charger per Asset. Both devices live independently. Unplugged vehicles and unassigned Chargers remain usable and visible. The currently connected car's identity requires separate current-plug proof or explicit user confirmation. Idle-only ordinary selection changes must not implicitly stop/energize equipment; active/unknown affected Chargers reject rebind until separately confirmed stopped. Preserve asset-owned demand, independently measured remaining kWh, immutable session-time attribution and source identities. A connected but unknown Charger may offer an explicitly bounded anonymous **manual** session without inventing a vehicle record, but not future vehicle-colored auto slots.

The Charging Plan colors an identity dimension **per Vehicle or per Charger** with stable distinguishable theme-aware hues keyed by canonical IDs. Proposed, physically accepted and measured are independent statuses rendered with a second non-color-only pattern/weight/opacity/legend; no one-color blue overlay of all planned Chargers. Pending disconnected vehicles appear as a compact non-energy waiting status, not kW bars. Actual elapsed history may show now-disconnected vehicles. Accessible responsive tests cover 0/1/2/4/10 chargers; known/unidentified/Guest, disconnected, moving car, light/dark, and exact HA screenshot widths. The full end-to-end FLEX-01–21 matrix is part of UC01–UC29 in Issue #1. No changed implementation or passing field qualification is implied by this documentation change.

## Implementation and release gates

**G1 Contract first:** for every UC01–UC29, specify one owner, stable identity, canonical input/source quality, public read/write surface, failure behavior and executable test. Versioned generic HA interface; no duplicate sources, command writers, schedules, ledgers or UX inferencing.

**G2 Complete functionality in this dev batch:** guided HA setup + optional YAML parity, validated sources, targets/deadlines/priority, six qualified strategies, one group planner (1/2/4/10 chargers), true physical control/readback, persistence, canonical logical entities, one bounded read-only chart query and the above exact five-tab frontend.

**G3 Targeted tests during coding:** negative safety/ownership, different phase/current limits, 23/25-hour days, missing/partial prices, signed PV/net, source staleness, no-SoC, source rebind, event storms/duplicate commands, command timeout, restart/unload, identity/history and headless operation.

**G4 Feature Complete before full qualification:** all 29 scenarios, five rendered UX tabs and source/negative/permission behavior complete with no open agreed functional debt. Green syntax/unit tests do not meet G4.

**G5 Qualify exact candidate:** HACS/Hassfest, actual HA setup/reload/unload/upgrades/rollback, frontend browser screenshots at the three viewports, provider interoperability, owner-safe physical commissioning and explicit release permission. Public HACS TEST must follow the validated exact-`main` governance path. Keep the existing Draft PR on `dev` for the ongoing agreed batch.

**Present status (2026-11-22): the same `dev` batch now includes verified source/config schema, phase/circuit-aware stepped planning, native switch/current commands and independent readback, quarter-hour admission for Automatic/Solar/Economy/Ready By, guarded Force Charge/Off, a bounded accepted/proposed/actual query and native storage replay hold. These are development/source-tested capabilities only. Actual HA/browser and hardware qualification, complete session/UX editing and exact-candidate release gates remain OPEN.
