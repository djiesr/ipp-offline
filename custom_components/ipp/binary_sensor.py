"""Connectivity binary sensor for IPP printers that are often powered off."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IPPConfigEntry
from .entity import IPPEntity

ONLINE_DESCRIPTION = BinarySensorEntityDescription(
    key="online",
    translation_key="online",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IPPConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the IPP connectivity sensor."""
    async_add_entities([IPPOnlineSensor(entry.runtime_data, ONLINE_DESCRIPTION)])


class IPPOnlineSensor(IPPEntity, BinarySensorEntity):
    """On when the printer answers, off when it is powered off/unreachable."""

    @property
    def available(self) -> bool:
        """Stay available to report "off" while the printer is offline."""
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        """Return True if the printer is online."""
        return self.printer_online
