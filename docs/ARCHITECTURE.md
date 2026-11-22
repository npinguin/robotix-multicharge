# Architecture and ownership

## Scope
Robotix MultiCharge coordinates electrical charging; car-first, expandable to other compatible rechargeable assets. It is not a general home EMS, battery/inverter manager or generic asset framework.

## Core concepts
| Concept | Owns | Does not own |
| --- | --- | --- |
| ChargeableAsset | Stable charging identity, profile, goal and energy need | OEM integration, battery management, observed source facts |
| Charger | Stable logical charge point, accepted source binding, physical capability and command/readback owner | Source HA device identity or unrelated hardware |
| ChargeController | One planner, coordinated scheduling and charging admission for its Chargers | Whole-house scheduling, battery/inverter or other loads |

A Charger belongs to exactly one ChargeController. Asset assignment, EVSE occupancy and positively proven identity are distinct. Native HA integrations own their original device and entity IDs.

## Boundary
Native HA providers (asset SoC, charger telemetry, prices, grid/PV) -> exact bindings + freshness -> ChargeController plan -> optional time-bounded binding power allocation -> one writer per Charger -> native EVSE command + actual readback.

An external energy supervisor may consume the charge plan, allocate time/phase bounded power and request urgent load reduction; it cannot directly write a Charger already owned by MultiCharge. Missing/expired binding allocation must never silently restore unlimited charging. Zero kW means hold. The standalone mode has its own explicit safe power configuration.

## Rules
- One fact authority, one plan per Controller, one physical writer per Charger.
- Requested, accepted, actual and unknown remain distinct.
- Only explicit structural changes rebind sources; telemetry cannot rebuild HA Device Registry topology.
- Variable current and phase limits require verified installation and EVSE capability. A smart plug only supports on/off and must be suitable for sustained load.
- No site/provider assumptions or mandatory external product.
- Bootstrap registers no executor; physical writes require later opt-in, admission, real readback, stop, restart and hardware qualification.
