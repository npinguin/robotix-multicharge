# Contracts and interfaces — bootstrap candidate

Typed definitions in the integration's domain.py, contracts.py and interfaces.py are candidate source contracts, not yet HA-published APIs.

| Surface | Type | Requirements |
| --- | --- | --- |
| Price input | PriceProvider / PriceSlot | Aware UTC intervals, validated effective price and coverage, negative rates allowed |
| Asset input | AssetProvider / ChargeDemand | Freshness/provenance, unknown distinct from 0, explicit kWh when SoC absent |
| Charger input | ChargerProvider / Charger | Physical capability and measured readback independent from requested command |
| Power input | PowerProvider / PowerEnvelope | Optional, revisioned time-bound allocation; advisory or binding; 0 kW stops |
| Plan output | ChargePlan / PlannedChargeSlot | Controller revision, source quality and intervals; planned != measured |
| Physical output | ChargeActuator | Single authorized writer, intent/ack != physical readback |
| Read-only output | PlanConsumer | Flexibility visibility for independent energy supervision |

No HA binding wizard, charging scheduler, per-phase solver, current regulation, executor, public entities, EMS dispatch or hardware acceptance exists yet. Those require separate code and tests within the active development batch.

## Charging-plan timeline read model (candidate)

A single bounded, read-only backend query, not another plan publication engine, will serve the future chart. Input: `controller_uid`, optional `charger_uid` / `asset_uid`, aware `start` / `end`, quarter resolution. Output: source revision, generation timestamp, timezone-aware slots with UTC offsets, proposal/acceptance state, planned power/energy, optional price and binding available capacity, observed actual power/energy with source/quality and interval coverage, deadlines, infeasibility reasons and explicit missing values. Query must be bounded, authenticated, read-only and resilient to unknown/unavailable data; all physical actuation remains through the exclusive backend owner. A short summary is published through native sensor entities and actual history through native Recorder, not by dumping a full 48-hour forecast into sensor attributes.

Community uses this exact read model for a bundled, responsive 15-minute Charge Plan graph (Today/Tomorrow) at group and charger level. Any external house EMS remains an optional reader/supervisor of the same authoritative charging plan rather than a replacement planner. **Design contract only** until implemented and tested.
