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
