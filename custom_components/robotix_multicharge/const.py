"""Integration identity; no site-specific configuration."""

DOMAIN = "robotix_multicharge"
NAME = "Robotix MultiCharge"

# Canonical product policy and nominal setup proposals (not wiring evidence).
DEFAULT_POWER_ADJUSTMENT_INTERVAL_MINUTES = 5
NOMINAL_PHASE_COUNT = 1
NOMINAL_PHASE_VOLTAGE_V = 230.0
MIN_AC_CURRENT_A = 6.0

# Defaults for absent asset policy preferences, not observed vehicle facts.
DEFAULT_ASSET_PRIORITY = 0
DEFAULT_CONTINUOUS_CHARGING = False
DEFAULT_OPPORTUNISTIC_KIND = "off"
