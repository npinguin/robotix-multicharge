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

Config/Options Flow code, YAML structural validation and read-only logical setup devices have been committed. Real HA setup, import/reload, Options editing and rollback still require qualification. No current code can start charging.

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

- 15-minute slots for today and tomorrow in the HA timezone, including 23/25-hour daylight-saving days.
- Proposed plan, accepted plan and **measured** actuals distinguished, with power (kW), energy (kWh) and source freshness.
- Ready By and expected shortfall clearly indicated; optional electricity price and solar/context sources when available.
- A simple mobile view, accessible labels, readable legends and explicit unavailable/unknown states.
- Future slots queried through one bounded, read-only plan view; measured history from native HA telemetry and Recorder. Do not rewrite 48-hour plan arrays into giant sensor attributes or compute a new plan in the chart.

The planner and chart are **not implemented** in the current source. Illustrative plots are not commissioning evidence.

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
