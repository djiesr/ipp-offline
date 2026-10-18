"""Entities for The Internet Printing Protocol (IPP) integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IPPDataUpdateCoordinator


class IPPEntity(CoordinatorEntity[IPPDataUpdateCoordinator]):
    """Defines a base IPP entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IPPDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the IPP entity."""
        super().__init__(coordinator)

        self.entity_description = description

        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
        )
        # Printer never seen yet (offline since startup): the device registry
        # keeps its previous details, they are refreshed once it is online.
        if (printer := coordinator.data) is not None:
            self._attr_device_info.update(
                DeviceInfo(
                    manufacturer=printer.info.manufacturer,
                    model=printer.info.model,
                    name=printer.info.name,
                    serial_number=printer.info.serial,
                    sw_version=printer.info.version,
                    configuration_url=printer.info.more_info,
                )
            )

    @property
    def printer_online(self) -> bool:
        """Return True when the last poll reached the printer."""
        return bool(self.coordinator.online) and self.coordinator.data is not None

    @property
    def available(self) -> bool:
        """Unavailable while the printer is offline (override where needed)."""
        return super().available and self.printer_online
