# Robotix MultiCharge

[![Validation](https://github.com/npinguin/robotix-multicharge/actions/workflows/validate.yml/badge.svg)](https://github.com/npinguin/robotix-multicharge/actions/workflows/validate.yml)
[![GitHub stars](https://img.shields.io/github/stars/npinguin/robotix-multicharge?style=flat)](https://github.com/npinguin/robotix-multicharge/stargazers)
[![MIT License](https://img.shields.io/github/license/npinguin/robotix-multicharge)](LICENSE)

**Charge smarter. Share available power across your vehicles and chargers.**

Robotix MultiCharge is an open-source Home Assistant integration being built to coordinate charging for electric cars, e-bikes and other compatible rechargeable assets. The goal: make smart use of electricity prices, solar energy, available power and charging deadlines—without locking you to a vehicle, charger or energy provider.

> **HACS TEST v0.1.13 — independent Community integration, not STABLE or field-qualified.** This increment adds device-owned native Home Assistant inputs/actions automatically on the logical ChargeController, Charger and ChargeableAsset, with everyday charging controls in the integrated dashboard and **optional native Home Assistant Configure** (Charging site, Chargers, Chargeable assets, Energy & prices, Expert YAML/JSON). No mandatory wizard is needed at installation. **External, uncommissioned variable-current Chargers can be mapped without invented min/max Amps**; electrical limits become mandatory only before separate physical ownership/commissioning. The native Expert editor retains invalid text and displays the precise rejection reason. Newly added car profiles default to an editable 80% target; recurring Ready By schedules and variable-current Charger min/max/set kW are supported where the hardware qualifies. Guided setup can select Automatic mode, but **real Charger ownership remains external until explicit qualified commissioning**. Never run two physical writers on the same charger. Actual charger operation, source quality, responsive UX and every field use-case still require acceptance. No other Robotix/RHI integration is required.

## Functional product authority

**Start with the [Functional Specification and Use-Case Contract](docs/FUNCTIONAL_SPECIFICATION.md).** It is the **single canonical functional document** for MultiCharge: UC01–UC29, FLEX-01–21, FORECAST-01–12, UI-OWNER-01–10, desired resident/admin behavior, positive/negative test journeys, source-neutral installation, electrical safety, native owners and evidence requirements. The [RHI Platform Vision](https://github.com/npinguin/robotix-home-intelligence/blob/main/docs/ENGINEERING_PLATFORM_VISION.md) remains authoritative for platform boundaries. [Architecture](docs/ARCHITECTURE.md) and [Interfaces](docs/INTERFACES.md) describe implementation, not duplicate use-case authority.

**Issues/PRs are execution evidence, not functional specifications.** [Issue #1](https://github.com/npinguin/robotix-multicharge/issues/1) tracks actual remaining gaps and blockers; [PR #11](https://github.com/npinguin/robotix-multicharge/pull/11) tracks the v0.1.9 editor-repaint correction and source/browser test evidence. No UC text or UX acceptance may exist only in a PR body. Live hardware ownership, installed browser qualification, site handoff and a published HACS artifact have distinct statuses; a source-green branch is not Feature Complete.

## What we're building

- **Multi-asset charging** — coordinate different charging needs under one power budget.
- **Ready when you need it** — per-asset charge targets, priorities and deadlines.
- **Energy-aware scheduling** — optional electricity prices, solar surplus and site power limits.
- **Capability-driven chargers** — safe on/off or variable-current control only when the hardware supports it.
- **Real status** — physical charger readback, clear quality/availability and trustworthy plans.
- **Works on its own** — choose optional data sources from native Home Assistant integrations.

### Object-oriented native charging UX (development batch)

The same five Home Assistant views now keep each setting and observation with its owning object. **Overview** presents actual state, the chosen vehicle's real SoC/kWh/minutes/EUR goal, planning/calendar actions and a safely eligible Charger STOP. **Charging Plan** combines the time-based site kW and currency-qualified price graph with Vehicle/Charger detail lanes. **Chargeable Assets** keeps Guest or Vehicle identity, scheduled weekday/local charging windows, battery/SoC source, preferences, price thresholds, history and Charger assignment on that Vehicle. **Chargers** keeps physical state, single-writer ownership, commissioning, native connection/power/energy sources, circuit/phase/current bounds, commands and original session attribution on the Charger. **Settings** owns the ChargeController: site limits, modes and all native solar/grid/tariff/meter references.

One existing **Details** disclosure on each object also shows **every persisted Config Entry key** in named groups (including unconfigured keys and future additive keys). Source selection and structural hardware changes use the guarded typed controls in MultiCharge's own dashboard and the same validated Config Entry; no Home Assistant Options detour or second preference store is required. Frontend/native settings services require a genuine HA administrator; read-only users retain observation visibility and never inherit actuation rights. Developer checks statically enforce the configuration-field-to-owning-object correspondence and installed HA tests verify actual native Registry entities and administrator authorization.

**Input stability:** Every native and in-dashboard Controller, Charger, Asset, Guest, schedule, YAML textarea and commissioning field stays open while the user focuses or enters data. Background Home Assistant sensor updates, the source-refresh coalescer and delayed get_plan responses continue updating observations without replacing the active form, erasing unsubmitted input or dismissing an iPad keyboard. There is **no inactivity-based editor timeout**. Only explicit Save, Cancel, navigation or Refresh may repaint the user's open form; rejected Save preserves the typed value and shows an in-place error. This is covered by automated source/browser regressions; actual Wessels Safari acceptance is separate.

**Release distinction:** source, isolated-HA and Chromium tests do not establish real Wessels Safari/iPad behavior, real provider readings, owner handoff or physical STOP. Immutable v0.1.12 remains the rollback TEST for the v0.1.13 external-current mapping correction; publishing TEST requires exact-dev, merged-main and artifact qualification.

### Beginner-first UX and combined charging graph (dev)

The same five-tab user experience now has direct resident-readable actions: an Asset card provides **SoC / kWh / minutes / EUR** with a single authorized **Save charging goal** transaction, plus one clearly labelled **Schedule charging** action for selected weekdays and allowed charging hours. Overview links directly to each vehicle's goal/plan, offers one-step Guest creation, and exposes STOP only when the native Charger reports safe stop capability. Less common native price limits, low-SoC policy, opportunistic strategy, power limits, source configuration and diagnostics remain discoverable on the owning card one deliberate detail step away; no extra wizard, tracker, physical writer or browser-owned preference.

The **Charging Plan** combines Wessels Mobility Basic's simple, separate-scale *power + price* overview and Today/Tomorrow/48h period choices with MultiCharge's source-neutral, dynamically rendered **one row per Vehicle/Charger pairing**. Actual (native Recorder), accepted, proposed and disconnected indicative are not the same thing and remain visually distinct. The overview never assigns anonymous actual kW to the current Vehicle, never prices missing intervals at zero and never calls spot/reference prices a bill. The 48h choice is **two actual local civil days**, which can contain 47 or 49 real hours across DST, not always 48 UTC hours. No Basic YAML, ApexCharts add-on or external dependency is required. Real HA browser/mobile and native provider acceptance is still separate from passing source tests.

### Development progress — differentiated scheduling and flexible charging

In the current independently distributed integration, the existing one-controller architecture now includes source-tested **Specific days** vehicle Ready By schedules (any selected weekdays, separate local times), optional allowed weekday/hour charging windows, and finite goals of **measured kWh, charging duration or EUR budget**, plus the existing independently adjustable kW hardware cap where safe. A Guest can be created with a normal relative expiry, while unassigned Charger-only sessions retain an optional finite goal with no invented vehicle. Native HA owner entities, the bundled five-tab card and the same guarded physical executor are the only SET/command surfaces. Readback, historical attribution and restart safety remain separate from requested intent.

**Original upstream v2.6.1 capabilities on dev:** The same Asset and 15-minute Controller planner also expose a native **continuous versus split-quarter** preference, earliest start, minimum-SoC before applying an explicit price limit, low-SoC and low-price triggers, and both original opportunistic price-cap calculations. These policies are source-checked at the physical executor as well as in proposed slots; if price, SoC or current connection becomes unqualified, the executor holds or physically stops instead of granting an unsafe override. The optional upstream **Keep charger on for preconditioning** is **not falsely claimed as supported**: ordinary on/off Charger hardware does not prove that energizing it will only precondition and not continue battery charging. An independently qualified hardware-specific safe capability and real-device acceptance are prerequisites. The existing integration never silently takes over the old physical owner.

**Financial semantics:** a euro goal uses verified `effective` €/kWh intervals and genuine native cumulative-energy meter deltas; spot-only and an ordinary price reference cannot authorize a billed-money promise. If one meter increment spans multiple fully qualified effective tariffs, the remaining budget is conservatively reduced at the highest applicable nonnegative rate, explicitly shown as an **upper bound**, not an invoice. A single EUR-budget intent has a **cumulative 24-hour charging-time ceiling**, enforced by its plan as well as its guarded physical writer, including zero/negative prices and restarts. Missing source, unqualified EVSE, stale identity or incomplete STOP/readback holds physical execution. Physical source and real browser qualification remain open; do not treat a source-green CI run as HACS STABLE, production or site-specific physical handoff.

For full positive/negative and original upstream EV Smart Charging v2.6.1 parity requirements, see the [one canonical Functional Specification](docs/FUNCTIONAL_SPECIFICATION.md); implementation and remaining gates are recorded only in [Issue #1](https://github.com/npinguin/robotix-multicharge/issues/1) and the existing [Draft PR #9](https://github.com/npinguin/robotix-multicharge/pull/9).

## Optional setup — Home Assistant Configure or MultiCharge dashboard

**One-click installation, one Config Entry.** Add the Robotix MultiCharge
integration once under Home Assistant **Settings → Devices & services**. No
Charger, vehicle, price sensor, PV sensor or multi-step wizard is required at
installation. A valid empty charging site is immediately available.

When you want to configure it, open **Settings → Devices & services →
Robotix MultiCharge → Configure**. The native Home Assistant menu offers
**Charging site**, **Chargers**, **Chargeable assets**, **Energy & prices**,
**Edit complete configuration (JSON/YAML)** and the existing display/physical
commissioning options. The guided routes select existing Charger/Asset records
by name or add new ones, prefill saved values, and use native HA entity selectors.
The expert form shows the **complete actual Config Entry** as one large editable
JSON/YAML text area with a single **Save**. There is no Review wizard or
separate JSON/YAML file. Closing a form without saving leaves the entry intact.

The bundled **MultiCharge dashboard** remains an equally valid configuration
route with typed object-level editing and **Settings → Edit YAML → Save**.
Both surfaces write to the **same validated Home Assistant Config Entry**;
nothing is imported into `configuration.yaml`, `/config/packages`, templates,
a second planner or a parallel settings store. Home Assistant authorization,
schema validation, stale-revision detection and physical ownership protection
remain server-side. Configuring sources does **not** commission or command
hardware. Existing imported file-owned configurations remain read-only.

The automatic sidebar at `/robotix-multicharge` uses the same five
tabs for novice and expert use:

- **Overview:** actual status, source quality, strategy and direct vehicle
  assignment for each Charger without opening Details, plus STOP where allowed.
- **Charging Plan:** source-qualified measured, accepted, proposed and indicative
  15-minute timelines in locally bundled ApexCharts, with independently labelled
  tariff information. Unavailable measurements are never fabricated.
- **Chargeable Assets:** create or remove vehicles and persistent Guests, set
  one-time or repeating Ready By schedules, SoC/kWh/minutes/EUR goals, price
  limits, battery capacity and charge speed, native OEM SoC and health sources.
- **Chargers:** create/remove Charger objects, assign vehicles directly on the
  card, manage controlled one-off sessions, and edit all native cable, power,
  energy, current, electrical phase and circuit bindings inside foldable Details.
  Newly configured Chargers remain external/monitor-only until expressly
  qualified for single physical writer ownership.
- **Settings:** Controller site name, strategy, site power and parallel limits,
  Solar, tariff, whole-home and grid native entity sources, meter direction,
  safety, diagnostics and **Edit YAML → Save**.

Every accepted Controller, Charger and ChargeableAsset field is available as a
**typed in-dashboard field**, with native Home Assistant source candidates
taken from real entities, not fictional sensors. Edits go through one
administrator-authorized, revision-checked WebSocket writer, the one validated
HA Config Entry, existing safe structural reconciliation and observed readback.
The UI never activates an EVSE merely by changing a source. Residents may see
the same state but may not change configuration or send physical commands.

Native HA Devices and diagnostic/configuration and preference Entities are
still automatically registered with stable IDs for interoperability. These
are projections of the same source, not a second configuration workflow or
a prerequisite to editing from the dashboard.

**Compatibility and ownership:** Existing externally imported historical
YAML/JSON configurations remain readable and preserve their original authority
and Recorder/device identities. They are not silently overwritten by this
dashboard. A site wishing to migrate must use an explicitly qualified,
identity-preserving transition. Sites using another physical charging writer
keep MultiCharge external/monitor-only until independent idle, electrical
limits, current/power readback and sole-writer checks are satisfied. This is
not a claim that the household has already passed those physical tests.

## Community HACS TEST installation and closing-iteration evidence

Robotix MultiCharge is a **single MIT-licensed community integration**. It installs
from source; no precompiled runtime, paid Robotix services or separate mirror.

For a published HACS TEST candidate (v0.1.8 is the immutable rollback baseline), after its GitHub prerelease is available, open HACS in Home Assistant and add
`https://github.com/npinguin/robotix-multicharge` as a **custom Integration
repository**, enable prerelease/beta versions where applicable, and install
the published TEST prerelease. Restart Home Assistant and use the MultiCharge dashboard to configure all objects; do not create a second integration entry.
The source ZIP attached to GitHub Releases has the same runtime files and a
SHA256 sidecar; HACS normally installs from the matching immutable tag.

The `v0.1.3+` guarded runtime includes a persistent **Pause charging /
Resume charging** control for a qualified MultiCharge-owned Charger. Pause
stores the hold before requesting an independently confirmed physical STOP.
Resume is administrator-authorized, requires an observed physically idle
Charger, and **does not automatically start charging**; only a later eligible
quarter or explicitly approved manual START may do that. Failed STOP or
unverified delivery remains held. These changes are **not** present in the previous immutable v0.1.2 TEST.

During testing, the native Charger device exposes current connection and
physical readback. Select the actual vehicle and use **Confirm connected
vehicle** after each real connection, then use real modes/commands and observe
independent physical readback. This is not a demo or simulation path.
Never let MultiCharge and another integration both command the same EVSE.
Select and verify one physical writer in the advanced Charger configuration,
with tested phase/circuit ceilings, input evidence and STOP behavior.

For each unexpected result, open the integration in **Settings → Devices &
services**, select **Download diagnostics**, and capture the relevant Home
Assistant debug log and reproducible user steps. The diagnostics export
contains planner outcomes, source quality, current-session identity,
command/readback receipts and qualified charging history, with aliased local
identifiers. Inspect private diagnostics and logs before sharing publicly.
Record the issue, exact TEST version, mode, selected hardware, expected versus
observed result and diagnostics in the existing MultiCharge Issue #1. A green source CI or prerelease publication is not proof of successful
real-site physical acceptance.

## Development and documentation

- [Architecture, UI and ownership](docs/ARCHITECTURE.md)
- [Candidate contracts and interfaces](docs/INTERFACES.md)
- [Canonical functional specification — UC01–UC29 and extensions](docs/FUNCTIONAL_SPECIFICATION.md)
- [Development gaps and acceptance evidence](https://github.com/npinguin/robotix-multicharge/issues/1)
- [Open development issues](https://github.com/npinguin/robotix-multicharge/issues)

Source checks (no Home Assistant installation needed):

```bash
python -m compileall -q custom_components tests
python -m unittest discover -s tests -v
```

Green source CI does **not** authorize physical charging or claim Home Assistant/Marketplace qualification.

## Help the project grow

If you'd like to see an independent, provider-neutral smart charger integration succeed:

- **[Star this repository](https://github.com/npinguin/robotix-multicharge/stargazers)** so others can discover it.
- **[Share an idea or report an issue](https://github.com/npinguin/robotix-multicharge/issues)**, ideally with a charger type, desired result and reproducible evidence.
- **[Buy the maker a coffee](https://buymeacoffee.com/npinguin)** to help with development and hardware testing. Support is always optional.

No donation, account or external product is required to use the eventual integration.

## License

[MIT](LICENSE). Independently authored, community-first and provider-neutral.
