# Architecture, native HA experience and ownership

## Scope and three concepts

Robotix MultiCharge coordinates electric charging. **Car-first, not car-only.** It is not an inverter, home-battery or general home EMS controller.

| Concept | Owns | Does not own |
| --- | --- | --- |
| `ChargeableAsset` | Stable charging identity, energy need, target and deadline | Vehicle OEM/device or the original SoC source |
| `Charger` | Stable logical charge point, verified capability, exclusive charging command/readback when enabled | Original physical HA Device Registry identity |
| `ChargeController` | One coordinated charger plan and safe group allocation | Whole-home EMS or unrelated devices |

A Charger belongs to one Controller. Configured asset assignment, actual occupation and physically identified asset are different facts. Source HA devices remain owned by their native integrations; MultiCharge does not reparent or impersonate them. Multiple Controllers cannot independently spend the same shared power envelope.

## Configuration: simple by default, YAML for experts

**Default:** HA Config Flow and Options Flow with guided setup: Controller, Charger, ChargeableAsset, sources, binding validation. Users can add a car and charger without writing YAML.

**Expert option:** one declarative YAML import, validated by exactly the same schema. YAML remains the authoritative source when chosen (read-only in the UI); the UI owns its own configuration when chosen. No second runtime YAML/Jinja calculator, competing config stores, or copied Home Assistant source registry. Import into a native HA Config Entry. **This is planned, not yet implemented in the bootstrap.**

Proposed future YAML form (illustration, **not yet supported**):

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
  - id: car
    name: Family car
    kind: car
    soc_entity: sensor.car_battery
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

## Native HA UX: useful, but no duplicate control plane

- **Overview:** active charger(s), next session, remaining energy, available charging capacity and warnings.
- **ChargeableAsset:** actual SoC/quality, target, Ready By, remaining demand, selected Charger.
- **Charger:** connection, measured power/energy, verified control capability, status and safe actions.
- **ChargeController:** active mode, cap/concurrency, plan status and coverage, attention and next activity.
- **Settings:** guided mapping, safe limits, meaningful diagnostics, expert import.
- **Dashboards:** usable first through native HA devices/entities, selectors, cards, buttons and sensors. Add a tiny optional overview card only if native cards cannot show a coherent daily journey; no UI-owned scheduler or rule engine.

Current bootstrap still has **no actual charging devices, entities, planner or actuator**. Future release screenshots must come from tested real HA instances; missing information stays unknown, not zero or fabricated readiness.

Unique logical device IDs use `(robotix_multicharge, concept/id)` with stable per-property entity unique IDs. Runtime SoC/power updates never trigger structural/device registry rebuilds. `via_device` must not be used to represent semantic ownership, assignment or planning. Native source devices retain their IDs/history.

## Planner, safety and optional energy supervision

```text
HA sources (prices, grid/PV, SoC, charger observations)
      -> explicit qualified bindings / freshness
ChargeableAsset demand + Charger capabilities
      -> ChargeController: one revisioned charge plan
      <-> optional external supervisor: binding time/phase envelopes
      -> exclusive physical writer per Charger, with actual readback
```

The Controller is the specialized charging optimizer. An external house EMS may read demand, plans, actual results and send binding capacity or urgent stop restrictions; it never writes an already-owned Charger or replaces the charging planner. A stale previously active binding restriction fails safe. No external product is required in standalone mode.

A smart plug remains qualified on/off only. Phase/current limits must be verified; a HA service acknowledgment does not prove physical execution. Hardware and installation protections remain independent and authoritative. No charging actuator exists in the bootstrap.

## Acceptance

Prove native UI and YAML parity, structural identity persistence, unknown/quality, source binding, restart/unload/rollback, 1/2/4/10 mixed charger planning, deadline/solar/price/DST scenarios, external envelope expiry and emergency stop, exact HA command/readback and qualified real hardware before claiming Feature Complete.
