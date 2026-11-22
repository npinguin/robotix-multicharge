# Robotix MultiCharge

[![Validation](https://github.com/npinguin/robotix-multicharge/actions/workflows/validate.yml/badge.svg)](https://github.com/npinguin/robotix-multicharge/actions/workflows/validate.yml)
[![GitHub stars](https://img.shields.io/github/stars/npinguin/robotix-multicharge?style=flat)](https://github.com/npinguin/robotix-multicharge/stargazers)
[![MIT License](https://img.shields.io/github/license/npinguin/robotix-multicharge)](LICENSE)

**Charge smarter. Share available power across your vehicles and chargers.**

Robotix MultiCharge is an open-source Home Assistant integration being built to coordinate charging for electric cars, e-bikes and other compatible rechargeable assets. The goal: make smart use of electricity prices, solar energy, available power and charging deadlines—without locking you to a vehicle, charger or energy provider.

> **Early development — do not install on live charging equipment.** The current `dev` branch now contains source-tested phase/circuit budgets, guarded switch and adjustable-current execution, qualified quarter-hour execution for the six strategies, independent physical readback and a stored replay-safety hold. The physical writer is external by default. **The first v0.1.0 HACS TEST is published; physical EVSE commissioning and STABLE acceptance are not approved.**

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

On `dev`, native Site → Charger → Asset → Sources → Verify setup and the bundled five-tab card are source-tested. A single specialist planner proposes bounded 15-minute slots. Only the one guarded executor can apply qualified automatic slots or manual Force Charge through native switch/current services; independent readback is required for confirmation. Confirmed accepted slots are separated from proposals and native Recorder actuals. Explicit intent evidence is retained through native HA storage to prevent silent restart/replay after an unknown or interrupted session. YAML and UI use one validated configuration authority. **The source now includes durable completed-session receipts, bounded fully qualified session costing, admin-validated inline preferences, temporary guest expiry, native command sensors and safe STOP. Real HA/browser/hardware acceptance, unqualified advanced settings and exhaustive session/recovery verification remain OPEN; this code is not field approved.** The plan query is readable by authenticated HA household users; writes remain admin-authorized, and YAML-managed settings stay read-only.

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
      "Name": "Garage White",
      "Charging-Session-sensor": "sensor.garage_white_session",
      "Charging-startstop-entity": "switch.garage_white_charging",
      "Charging-amp-entity": "number.garage_white_current",
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
`Charging-connected-sensor`. These are independent sources; a session status
sensor must never be silently treated as a cumulative or per-session energy
meter. The vehicle command bindings are **saved and represented as such**;
there is no second physical writer. Setting an entity does not authorize
MultiCharge to invoke it. Charger command ownership remains `external` and
physical commissioning is `false`.

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

## Community HACS TEST installation and closing-iteration evidence

Robotix MultiCharge is a **single MIT-licensed community integration**. It installs
from source; no precompiled runtime, paid Robotix services or separate mirror.

After a `TEST` prerelease is published, open HACS in Home Assistant, add
`https://github.com/npinguin/robotix-multicharge` as a **custom Integration
repository**, enable prerelease/beta versions where applicable, and install
the latest explicitly qualified TEST release (v0.1.2 for the expert JSON bypass). Restart Home Assistant, then
open **Settings → Devices & services → Add integration → Robotix MultiCharge**.
The source ZIP attached to GitHub Releases has the same runtime files and a
SHA256 sidecar; HACS normally installs from the matching immutable tag.

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
observed result and diagnostics in the existing MultiCharge Issue #1/PR #2
workflow. A green source CI or prerelease publication is not proof of successful
physical Wessels acceptance.

## Development and documentation

- [Architecture, UI and ownership](docs/ARCHITECTURE.md)
- [Candidate contracts and interfaces](docs/INTERFACES.md)
- [Functional use cases and acceptance](https://github.com/npinguin/robotix-multicharge/issues/1)
- [Open development issues](https://github.com/npinguin/robotix-multicharge/issues)
- [Active development PR](https://github.com/npinguin/robotix-multicharge/pull/2)

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
