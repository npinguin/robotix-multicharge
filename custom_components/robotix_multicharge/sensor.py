"""Native logical status entities, never duplicated source devices.

The read-only planning runtime remains physically uncommissioned. One bounded
source refresh per minute; entity state updates stay on the HA event loop.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    cfg = runtime.configuration
    entities = [_LogicalReadinessSensor("controller", cfg["controller"], runtime)]
    entities.extend(
        _LogicalReadinessSensor("asset", row, runtime) for row in cfg["assets"]
    )
    entities.extend(
        _LogicalReadinessSensor("charger", row, runtime) for row in cfg["chargers"]
    )
    entities.append(_PlanStatusSensor(cfg["controller"], runtime))
    async_add_entities(entities)


class _NativeMultiChargeSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, kind: str, data: dict, runtime) -> None:
        self.kind = kind
        self.data = data
        self.runtime = runtime
        self._unsubscribe = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{kind}/{data['id']}")},
            "name": data["name"],
            "manufacturer": "Robotix",
            "model": {
                "controller": "ChargeController",
                "charger": "Charger",
                "asset": "ChargeableAsset",
            }[kind],
        }

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._unsubscribe = self.runtime.subscribe(self._refresh)
        self._refresh()

    @callback
    def _refresh(self):
        self._update_value()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        await super().async_will_remove_from_hass()

    def _update_value(self):
        raise NotImplementedError


class _LogicalReadinessSensor(_NativeMultiChargeSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, kind: str, data: dict, runtime) -> None:
        super().__init__(kind, data, runtime)
        self._attr_name = "Readiness"
        self._attr_unique_id = f"{DOMAIN}:{kind}:{data['id']}:readiness"
        self._update_value()

    def _update_value(self):
        self._attr_native_value = "not_commissioned"
        assessment = self.runtime.assessment
        self._attr_extra_state_attributes = {
            "logical_id": self.data["id"],
            "concept": self._attr_device_info["model"],
            "operational": False,
            "planning_status": (
                assessment.plan.status if assessment is not None else "unavailable"
            ),
        }


class _PlanStatusSensor(_NativeMultiChargeSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, controller: dict, runtime) -> None:
        super().__init__("controller", controller, runtime)
        self._attr_name = "Plan status"
        self._attr_unique_id = f"{DOMAIN}:controller:{controller['id']}:plan_status"
        self._update_value()

    def _update_value(self):
        summary = self.runtime.summary()
        self._attr_native_value = summary["status"]
        self._attr_extra_state_attributes = {
            "mode": self.runtime.configuration["controller"]["mode"],
            "revision": summary.get("revision"),
            "reason_by_charger": summary.get("reason_by_charger", {}),
            "coverage_by_charger": summary.get("coverage_by_charger", {}),
            "planned_kwh_by_charger": summary.get("planned_kwh_by_charger", {}),
            "read_only": True,
            "physical_actuation_authorized": False,
        }
