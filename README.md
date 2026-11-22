# Robotix MultiCharge

**Intelligent multi-asset charging for Home Assistant.**

Robotix MultiCharge is a standalone community integration for coordinated charging of electric cars and other compatible chargeable assets. It is designed to combine charging needs, available power, prices, solar surplus and deadlines using native Home Assistant integrations.

## Model
- **ChargeableAsset** — the object requiring energy (car-first; bicycles and other compatible assets are possible).
- **Charger** — a verified physical charge point with explicit capabilities.
- **ChargeController** — one coordinated charge planner over its assigned Chargers.

One physical write owner per Charger, one scheduler per Controller. Price, grid, asset and charger providers are optional native Home Assistant bindings; no proprietary provider is required.

## Engineering status
**Inert architectural bootstrap — NOT operating charging software.** The config entry has no devices, entities, planner or physical commands. Never install this candidate to control hardware.

- [Architecture / ownership](docs/ARCHITECTURE.md)
- [Contracts / interfaces](docs/INTERFACES.md)
- Local syntax: `python -m compileall -q custom_components tests`
- Local regression: `python -m unittest discover -s tests -v`

The HACS integration domain is `robotix_multicharge`. No release or hardware activation is authorized. MIT licensed.