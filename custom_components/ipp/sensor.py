"""Support for IPP sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, override

from pyipp import Marker, Printer

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import ATTR_LOCATION, PERCENTAGE, EntityCategory
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    ATTR_COMMAND_SET,
    ATTR_INFO,
    ATTR_MARKER_HIGH_LEVEL,
    ATTR_MARKER_LOW_LEVEL,
    ATTR_MARKER_TYPE,
    ATTR_SERIAL,
    ATTR_STATE_MESSAGE,
    ATTR_STATE_REASON,
    ATTR_URI_SUPPORTED,
)
from .coordinator import IPPConfigEntry, IPPDataUpdateCoordinator
from .entity import IPPEntity

STATE_OFFLINE = "offline"


@dataclass(frozen=True, kw_only=True)
class IPPSensorEntityDescription(SensorEntityDescription):
    """Describes IPP sensor entity."""

    value_fn: Callable[[Printer], StateType | datetime]
    attributes_fn: Callable[[Printer], dict[Any, StateType]] = lambda _: {}
    exists_fn: Callable[[Printer], bool] = lambda _: True
    # Stays available and reports STATE_OFFLINE while the printer is off.
    reports_offline: bool = False


def _get_marker_attributes_fn(
    marker_index: int, attributes_fn: Callable[[Marker], dict[Any, StateType]]
) -> Callable[[Printer], dict[Any, StateType]]:
    return lambda printer: attributes_fn(printer.markers[marker_index])


def _get_marker_value_fn(
    marker_index: int, value_fn: Callable[[Marker], StateType | datetime]
) -> Callable[[Printer], StateType | datetime]:
    return lambda printer: value_fn(printer.markers[marker_index])


PRINTER_SENSORS: tuple[IPPSensorEntityDescription, ...] = (
    IPPSensorEntityDescription(
        key="printer",
        name=None,
        translation_key="printer",
        device_class=SensorDeviceClass.ENUM,
        options=["idle", "printing", "stopped", STATE_OFFLINE],
        reports_offline=True,
        attributes_fn=lambda printer: {
            ATTR_INFO: printer.info.printer_info,
            ATTR_SERIAL: printer.info.serial,
            ATTR_LOCATION: printer.info.location,
            ATTR_STATE_MESSAGE: printer.state.message,
            ATTR_STATE_REASON: printer.state.reasons,
            ATTR_COMMAND_SET: printer.info.command_set,
            ATTR_URI_SUPPORTED: ",".join(printer.info.printer_uri_supported),
        },
        value_fn=lambda printer: printer.state.printer_state,
    ),
    IPPSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda printer: printer.booted_at,
    ),
)

PAGE_COUNT_SENSORS: tuple[IPPSensorEntityDescription, ...] = (
    IPPSensorEntityDescription(
        key="pages_completed",
        translation_key="pages_completed",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda printer: "pages_completed" in printer.counters.supported,
        value_fn=lambda printer: printer.counters.pages_completed,
    ),
    IPPSensorEntityDescription(
        key="impressions_completed",
        translation_key="impressions_completed",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda printer: "impressions_completed" in printer.counters.supported,
        value_fn=lambda printer: printer.counters.impressions_completed,
    ),
    IPPSensorEntityDescription(
        key="media_sheets_completed",
        translation_key="media_sheets_completed",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda printer: (
            "media_sheets_completed" in printer.counters.supported
        ),
        value_fn=lambda printer: printer.counters.media_sheets_completed,
    ),
    IPPSensorEntityDescription(
        key="impressions_completed_monochrome",
        translation_key="impressions_completed_monochrome",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda printer: (
            "monochrome" in printer.counters.impressions_completed_col
        ),
        value_fn=lambda printer: printer.counters.impressions_completed_col.get(
            "monochrome"
        ),
    ),
    IPPSensorEntityDescription(
        key="impressions_completed_full_color",
        translation_key="impressions_completed_full_color",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda printer: (
            "full-color" in printer.counters.impressions_completed_col
        ),
        value_fn=lambda printer: printer.counters.impressions_completed_col.get(
            "full-color"
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IPPConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up IPP sensor based on a config entry."""
    coordinator = entry.runtime_data
    # The status sensor can always be created; the others depend on what the
    # printer reports (markers, counters), so they need its data.
    async_add_entities(
        [
            IPPSensor(coordinator, description)
            for description in PRINTER_SENSORS
            if description.reports_offline
        ],
        True,
    )

    if coordinator.data is not None:
        async_add_entities(_printer_data_sensors(coordinator), True)
        return

    # Printer offline since startup: add those sensors once it first answers.
    unsub: CALLBACK_TYPE | None = None

    @callback
    def _add_when_online() -> None:
        nonlocal unsub
        if coordinator.data is None or unsub is None:
            return
        unsub()
        unsub = None
        async_add_entities(_printer_data_sensors(coordinator), True)

    @callback
    def _unsub_on_unload() -> None:
        if unsub is not None:
            unsub()

    unsub = coordinator.async_add_listener(_add_when_online)
    entry.async_on_unload(_unsub_on_unload)


def _printer_data_sensors(coordinator: IPPDataUpdateCoordinator) -> list[SensorEntity]:
    """Return the sensors built from the printer data."""
    assert coordinator.data is not None
    sensors: list[SensorEntity] = [
        IPPSensor(
            coordinator,
            description,
        )
        for description in PRINTER_SENSORS
        if not description.reports_offline
    ]

    for index, marker in enumerate(coordinator.data.markers):
        sensors.append(
            IPPSensor(
                coordinator,
                IPPSensorEntityDescription(
                    key=f"marker_{index}",
                    name=marker.name,
                    translation_key="marker",
                    native_unit_of_measurement=PERCENTAGE,
                    state_class=SensorStateClass.MEASUREMENT,
                    attributes_fn=_get_marker_attributes_fn(
                        index,
                        lambda marker: {
                            ATTR_MARKER_HIGH_LEVEL: marker.high_level,
                            ATTR_MARKER_LOW_LEVEL: marker.low_level,
                            ATTR_MARKER_TYPE: marker.marker_type,
                        },
                    ),
                    value_fn=_get_marker_value_fn(
                        index,
                        lambda marker: marker.level if marker.level >= 0 else None,
                    ),
                ),
            )
        )

    sensors.extend(
        IPPSensor(coordinator, description)
        for description in PAGE_COUNT_SENSORS
        if description.exists_fn(coordinator.data)
    )

    return sensors


class IPPSensor(IPPEntity, SensorEntity):
    """Defines an IPP sensor."""

    entity_description: IPPSensorEntityDescription

    @property
    @override
    def available(self) -> bool:
        """Return if the entity is available."""
        if self.entity_description.reports_offline:
            return self.coordinator.last_update_success
        return super().available

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the entity."""
        if self.coordinator.data is None:
            return {}
        return self.entity_description.attributes_fn(self.coordinator.data)

    @property
    @override
    def native_value(self) -> StateType | datetime:
        """Return the state of the sensor."""
        if not self.printer_online:
            return STATE_OFFLINE if self.entity_description.reports_offline else None
        return self.entity_description.value_fn(self.coordinator.data)
