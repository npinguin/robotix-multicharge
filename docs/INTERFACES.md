# Community contracts — development candidate

The integration's `domain.py`, `contracts.py` and `interfaces.py` currently define **candidate** Python types. They are not a released, compatible or Home Assistant-published API.

| Public-facing concern | Candidate interface | Intended invariant |
| --- | --- | --- |
| Charging assets | `ChargeableAsset` / `ChargeDemand` | Stable identity; explicit need, target, deadline and unknown source state |
| Charger capability | `Charger` / `ChargerProvider` | Observed and configured capabilities separated from requested commands |
| Prices | `PriceProvider` / `PriceSlot` | Zoned intervals, validated coverage and possible negative prices |
| Available charging power | `PowerProvider` / `PowerEnvelope` | Optional, bounded time-based limit; no assumption that missing means unlimited |
| Charge plan | `ChargeController` / `ChargePlan` | Revisioned interval proposals/acceptance; planned does not mean actual |
| Hardware execution | `ChargeActuator` | Exclusive authorized writer; validated limits and independent readback |
| Read-only visualization | `PlanConsumer` | Plan status/intervals for the native charging dashboard |

## Charging Plan read view

The planned 15-minute Today/Tomorrow chart needs one bounded, read-only query on the Controller's plan. It must identify the controller and optional charger/asset filter, timezone-aware interval and plan revision. Its response will distinguish proposed/accepted power, actual measured power/energy, data quality, source coverage, relevant deadline and optional price or solar context.

Use native lightweight HA summary entities and Recorder for measured history. Do not replicate the planner or persist whole future timelines as large frequently rewritten sensor attributes.

**Status:** contract shape is a development target. Native HA binding, planner, chart, actuator and hardware acceptance are not yet implemented or qualified. See [functional use cases](https://github.com/npinguin/robotix-multicharge/issues/1).
