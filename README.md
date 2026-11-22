# Robotix MultiCharge

[![Validation](https://github.com/npinguin/robotix-multicharge/actions/workflows/validate.yml/badge.svg)](https://github.com/npinguin/robotix-multicharge/actions/workflows/validate.yml)
[![GitHub stars](https://img.shields.io/github/stars/npinguin/robotix-multicharge?style=flat)](https://github.com/npinguin/robotix-multicharge/stargazers)
[![MIT License](https://img.shields.io/github/license/npinguin/robotix-multicharge)](LICENSE)

**Charge smarter. Share available power across your vehicles and chargers.**

Robotix MultiCharge is an open-source Home Assistant integration being built to coordinate charging for electric cars, e-bikes and other compatible rechargeable assets. The goal: make smart use of electricity prices, solar energy, available power and charging deadlines—without locking you to a vehicle, charger or energy provider.

> **HACS TEST candidate v0.1.5 — not field-qualified.** This version retains the guarded v0.1.4 charging runtime and adds an admin-only whole-configuration YAML editor with a native Home Assistant Options Flow, independent validation, explicit review/save/cancel and immutable physical ownership guards. Charging ownership still defaults to `external`, mode to `Off` and physical commissioning to `false`. Do not transfer live EVSE control until physical exclusivity, source integrity, electrical limits, STOP/readback and rollback are validated.

## What we're building

- **Multi-asset charging** — coordinate different charging needs under one power budget.
- **Ready when you need it** — per-asset charge targets, priorities and deadlines.
- **Energy-aware scheduling** — optional electricity prices, solar surplus and site power limits.
- **Capability-driven chargers** — safe on/off or variable-current control only when the hardware supports it.
- **Real status** — physical charger readback, clear quality/availability and trustworthy plans.
- **Works on its own** — choose optional data sources from native Home Assistant integrations.

## Simple in Home Assistant

The planned everyday experience has five sections:

| View | Purpose |
| --- | --- |
| **Overview** | What is charging, what comes next and what needs attention |
| **Charging Plan** | Today/tomorrow 15-minute timeline: proposed/accepted charging, actual power, deadline and optional energy/price context |
| **Chargeable Assets** | Battery level, target, deadline, priority and remaining need |
| **Chargers** | Connection, power, actual state, active assignment and safe controls |
| **Settings** | Guided source selection, limits, diagnostics and expert YAML import |

In the v0.1.5 TEST candidate, native Site → Charger → Asset → Sources → Verify setup and the bundled five-tab card are source-tested. A single specialist planner proposes bounded 15-minute slots. Only the one guarded executor can apply qualified automatic slots or manual Force Charge through native switch/current services; independent readback is required for confirmation. Confirmed accepted slots are separated from proposals and native Recorder actuals. Explicit intent evidence is retained through native HA storage to prevent silent restart/replay after an unknown or interrupted session. YAML and UI use one validated configuration authority. **The source now includes durable completed-session receipts, bounded fully qualified session costing, admin-validated inline preferences, temporary guest expiry, native command sensors and safe STOP. Real HA/browser/hardware acceptance, unqualified advanced settings and exhaustive session/recovery verification remain OPEN; this code is not field approved.** The plan query is readable by authenticated HA household users; writes remain admin-authorized, and YAML-managed settings stay read-only.

The stable core concepts are `ChargeableAsset`, `Charger` and `ChargeController`. A physical device stays owned by its native Home Assistant integration; MultiCharge only represents the logical charging role.

## Built-in Home Assistant dashboard

After the integration loads (from guided setup **or** direct expert JSON),
Home Assistant automatically registers **Robotix MultiCharge** in the left
sidebar at `/robotix-multicharge`. No Lovelace dashboard creation, card
editing or manual resource registration is necessary. The panel uses the
one existing source-backed five-view card: **Overview**, **Charging Plan**,
**Chargeable Assets**, **Chargers** and **Settings**.

The dashboard is visible to **all authenticated Home Assistant users**;
charging commands and settings changes remain protected by the native admin
authorization, and JSON-managed settings are read-only. The optional
`robotix-multicharge-card` Lovelace card remains available for users who
wish to embed the same view elsewhere, but it is no longer the only UX.
The sidebar panel is registered only while MultiCharge is installed and its
UI is enabled; it is removed on successful unload without altering other
Home Assistant dashboards or the Robotix Mobility navigation.

## Expert JSON — direct setup, no wizard

Expert users **do not need to complete the five setup screens**. The entire
configuration lives in a single plain JSON file. In the existing Home Assistant
`configuration.yaml`, add one native include:

```yaml
robotix_multicharge: !include multicharge.json
```

Create `/config/multicharge.json` containing only this object:

```json
{
  "Controller": {"ID": "home", "Name": "Home charging"},
  "Charger": [
    {
      "Name": "Garage charger",
      "Charging-Session-sensor": "sensor.garage_session",
      "Charging-startstop-entity": "switch.garage_charging",
      "Charging-amp-entity": "number.garage_current",
      "ChargingAsset": "Family car"
    }
  ],
  "ChargingAsset": [
    {
      "Name": "Family car",
      "Asset type": "Véhicule",
      "Vehicle-Charging-startstop-entity": "switch.car_charging",
      "Vehicle-Charging-amp-entity": "number.car_charging_current",
      "Vehicle-soc-sensor": "sensor.car_battery_level"
    }
  ]
}
```

The above entity IDs **illustrate the JSON shape**, not verified bindings
for a particular installation. Replace them with actual HA entity IDs.

**Minimal JSON:** One `Charger` requires only `Name` and
`Charging-startstop-entity` (a native `switch.*`). All other fields and
`ChargingAsset` are optional; each group may be an object or an array.
`Controller` is optional and defaults to `home`, `Home charging`, one
parallel charging point and mode `Off`. The planning fallback of 3.6 kW
per charger is **not an electrically verified rating or commissioning limit**.
Provide optional `Rated-power-kW` only with measured hardware data; physical
commands still require the existing separate protections and exclusive ownership.

The exact mapping is:

| Expert JSON | Canonical owned concept |
| --- | --- |
| `Charger.Name` / optional `ID` | Stable logical Charger name/ID |
| `Charging-Session-sensor` | Optional raw source for the charging session (not silently interpreted as kWh) |
| `Charging-startstop-entity` | Native Charger switch; never activated by import |
| `Charging-amp-entity` | Charger current setpoint reference (`number.*`) |
| `ChargingAsset.Name` / optional `ID` | Stable logical ChargeableAsset |
| `Asset type` | `Véhicule` → `car` (other canonical kinds also supported) |
| `Vehicle-Charging-startstop-entity` | Optional vehicle-owned switch binding |
| `Vehicle-Charging-amp-entity` | Optional vehicle-owned current setpoint binding |
| `Vehicle-soc-sensor` | Optional vehicle battery SoC source (`sensor.*`) |

To supply measured performance, optional additional Charger keys are
`Charging-power-sensor`, `Charging-energy-sensor`, and
`Charging-connected-sensor`. These are independent sources. An optional
`Charging-Session-sensor` has explicit source-quality/readback attributes on
the logical Charger **Connection** entity, but its active/paused/idle state
is not proof of physical cable, confirmed vehicle identity, charging power,
energy or permission to issue commands. Vehicle command bindings are retained
as passive source references: there is no second vehicle physical writer.

### Expert configuration for a qualified site

The **v0.1.3+ source schema** additionally maps normal charging intent and
installation-only electrical configuration through the *same*
`normalize_expert_json → validate_configuration → Config Entry` path:

| Owner | Expert JSON keys |
| --- | --- |
| Controller | `Mode`, `Max-power-kW`, `Max-parallel`, `Phase-limits-A` (L1/L2/L3 map), `Price-entity`, `Solar-entity`, `Power-envelope-entity`, `Plan-label-mode`, `Plan-color-by`, `Show-indicative-forecast` |
| ChargingAsset | `Requested-kWh` **or** `Requested-duration-minutes`, `Usable-capacity-kWh`, `Target-SoC-percent`, `Max-charge-kW`, `Ready-by`, `Ready-by-repeat`, `Priority`, `Charging-efficiency`, `Temporary`, `Expires-at`, `Expected-connection-at`, `Plan-color` |
| Charger | `Control-kind` (on_off/variable_current), `Control-owner` (external/multicharge), `Physical-commissioned`, `Rated-power-kW`, `Phase-count`, `Phase-IDs`, `Voltage-V`, `Fixed-current-A` or `Min-current-A`/`Max-current-A`/`Current-step-A`, `Circuit-ID`, `Circuit-limit-A`, `Charging-current-readback-sensor`, `Plan-color` and physical source bindings |

**All keys are optional for an external-owned charger except its name and
switch reference.** A Charger without vehicle assignment remains valid.
A Controller-only JSON document is valid for an empty setup. Adding
`Control-owner: multicharge` requires an explicit measured rating, site
power/phase limits, charger phase/circuit/current limits, independent source
readback and a qualified native control binding. It is rejected if these
fields are incomplete or inconsistent; the default 3.6 kW value is never
accepted as an assumed commissioned rating.

For example, the following *structural* values illustrate a **non-actuating**
on/off configuration. They are **not measured limits, real entity mappings
or approval to control physical hardware**:

```json
{
  "Controller": {
    "Name": "Home charging",
    "Mode": "Off",
    "Max-power-kW": 3.0,
    "Phase-limits-A": {"L1": 16}
  },
  "Charger": {
    "ID": "workshop_plug",
    "Name": "Workshop plug",
    "Control-kind": "on_off",
    "Control-owner": "multicharge",
    "Physical-commissioned": false,
    "Rated-power-kW": 0.5,
    "Charging-startstop-entity": "switch.workshop_charging",
    "Charging-connected-sensor": "binary_sensor.workshop_connected",
    "Charging-power-sensor": "sensor.workshop_power",
    "Phase-count": 1,
    "Phase-IDs": ["L1"],
    "Voltage-V": 230,
    "Fixed-current-A": 3,
    "Circuit-ID": "workshop",
    "Circuit-limit-A": 10
  }
}
```

Only after independent physical commissioning and proven exclusive command
handoff may an installer explicitly set `Physical-commissioned: true`.
That setting is a **declaration**, not a test result: the executor additionally
checks live connection, phase/circuit capacity, available site budget,
persistent intent, current session identity, exclusive ownership and
independent power/current readback before confirming any start. No import
silently changes an EVSE's current physical owner. Source changes require
a controlled reimport/restart and a verified safe STOP/rollback when an
existing commissioned charger is active. Do not use this expert schema with the immutable v0.1.2 release.

Upon HA restart, the native startup importer reads the JSON through Home
Assistant's built-in `!include`, validates every key and source domain, and
creates the **same one native Config Entry** that the wizard would create.
No `Add Integration` wizard is required. An existing wizard installation is
adopted in place: no removal, re-pair or second Config Entry, and historical
HA device/Recorder identity is retained for unchanged IDs. Keep `Controller.ID`
and explicit Charger/Asset `ID` values stable (the wizard defaults its
Controller ID to `home`). The imported JSON owns settings until explicitly
switched away from import: native Options and inline settings do not overwrite
it. A missing authoritative startup file fails closed.

Existing structured expert YAML remains compatible, but is **not a prerequisite**
for this JSON bypass. The YAML include line is Home Assistant's one-line file
reference only, not an instruction to express the configuration in YAML.

### Configuring a real Home Assistant site from YAML

MultiCharge can import **one** validated expert YAML source without adding another integration entry. For an existing Home Assistant installation, put an expert package such as `/config/packages/multicharge.yaml` under the native `homeassistant.packages` include, combining any existing source `template:` definitions with the top-level `robotix_multicharge:` configuration. For example, the relevant part of `/config/configuration.yaml` is:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Keep the existing controller `id` when converting from a GUI-created entry (the wizard default is `home`). Check configuration and restart Home Assistant. The importer adopts the existing Config Entry, preserving its identity. Check every actual source entity in Developer Tools, and keep `mode: Off`, `control_owner: external` and `physical_commissioned: false` before any field qualification. When a site is **file-managed** (an authoritative YAML package or JSON include), edit that **existing file** through Home Assistant File Editor or the established site deployment workflow; the MultiCharge card remains read-only for it. Do not duplicate `robotix_multicharge:` in separate files.

### Edit complete MultiCharge configuration inside Home Assistant

For a **GUI-managed** MultiCharge Config Entry, an administrator can now open **MultiCharge → Settings → Edit YAML**. The full currently saved canonical MultiCharge configuration is loaded into a data-only YAML editor inside the five-view card. Choose **Complete configuration** to replace all Charger/Asset rows exactly (including explicit removals), or **Scoped changes** to merge only specified IDs while preserving omitted assets and chargers. Click **Continue / review** to have Home Assistant validate the whole candidate; inspect the actual added/changed/removed IDs and fields, then **Apply reviewed changes**, **Back to YAML** or **Cancel**. The UI does not modify any configuration until the official HA **Options Flow** approves the confirmed reviewed draft. No second file, store, writer or charging command is introduced.

The editor preserves the existing controller ID, rejects unknown/duplicate YAML keys, stale edits, commissioning changes and physical owner transfer, and requires safe runtime/readback before physical wiring or association changes. HA configuration reloads preserve stable logical identities; actively controlled equipment is never silently reconfigured. The editor accepts **MultiCharge configuration data only** (controller/assets/chargers, optionally wrapped in `robotix_multicharge:`) or supported expert Controller/Charger/ChargingAsset JSON fields in Complete mode. It does **not** create or modify unrelated HA `template:` sensors, automation packages or external providers: keep those in their normal HA native owner files. Once a YAML/JSON file owns the Config Entry, the in-card YAML is intentionally read-only to avoid conflicting configuration authorities.

## Community HACS TEST installation and closing-iteration evidence

Robotix MultiCharge is a **single MIT-licensed community integration**. It installs
from source; no precompiled runtime, paid Robotix services or separate mirror.

For the `v0.1.5` TEST candidate, after the corresponding GitHub prerelease is published, open HACS in Home Assistant and add
`https://github.com/npinguin/robotix-multicharge` as a **custom Integration
repository**, enable prerelease/beta versions where applicable, and install
the `v0.1.5` TEST prerelease. Restart Home Assistant. For the GUI wizard,
open **Settings → Devices & services → Add integration → Robotix MultiCharge**;
for an expert YAML/JSON include, Home Assistant imports or adopts the **existing**
Config Entry automatically and you should **not add a second entry**.
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
- [Functional use cases and acceptance](https://github.com/npinguin/robotix-multicharge/issues/1)
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
