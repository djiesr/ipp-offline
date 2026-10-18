"""The Internet Printing Protocol (IPP) integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import IPPConfigEntry, IPPDataUpdateCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: IPPConfigEntry) -> bool:
    """Set up IPP from a config entry."""
    coordinator = IPPDataUpdateCoordinator(hass, entry)
    # Not async_config_entry_first_refresh(): a powered-off printer must not
    # make the setup fail. Only real IPP errors still do.
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady from coordinator.last_exception

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: IPPConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
