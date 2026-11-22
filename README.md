# Robotix MultiCharge

[![Validation](https://github.com/npinguin/robotix-multicharge/actions/workflows/validate.yml/badge.svg)](https://github.com/npinguin/robotix-multicharge/actions/workflows/validate.yml)
[![GitHub stars](https://img.shields.io/github/stars/npinguin/robotix-multicharge?style=flat)](https://github.com/npinguin/robotix-multicharge/stargazers)
[![MIT License](https://img.shields.io/github/license/npinguin/robotix-multicharge)](LICENSE)

**Charge smarter. Share available power across your vehicles and chargers.**

Robotix MultiCharge is an open-source Home Assistant integration being built to coordinate charging for electric cars, e-bikes and other compatible rechargeable assets. The goal: make smart use of electricity prices, solar energy, available power and charging deadlines—without locking you to a vehicle, charger or energy provider.

> **Early development — do not use to control charging equipment.** The current `dev` branch contains a read-only quarter-hour proposal engine, source-quality checks and native logical plan diagnostics, but no qualified physical executor or five-tab chart. No public installable TEST or STABLE release is available yet. Features described below are goals, not claims about the current release.

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

The current development Config Flow creates a site record, while Options Flow exposes basic asset/charger fields; **the approved Site → Charger → Asset → Sources → Verify wizard is not built yet**. YAML structural validation and one read-only Readiness diagnostic per logical device exist, but have **not passed actual Home Assistant runtime qualification**. The complete beginner experience, chart and physical charging are not operational; the engine currently exposes read-only proposals through a bounded administrative HA query. UI and optional YAML must share a single validated configuration authority. Physical device identities remain with their native Home Assistant integrations.

The stable core concepts are `ChargeableAsset`, `Charger` and `ChargeController`. A physical device stays owned by its native Home Assistant integration; MultiCharge only represents the logical charging role.

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
