"""Coordinator for The Internet Printing Protocol (IPP) integration."""

from datetime import timedelta
import logging
from typing import override

from pyipp import (
    IPP,
    IPPConnectionError,
    IPPConnectionUpgradeRequired,
    IPPError,
    Printer as IPPPrinter,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_BASE_PATH, DOMAIN, REQUEST_TIMEOUT

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)

type IPPConfigEntry = ConfigEntry[IPPDataUpdateCoordinator]


class IPPDataUpdateCoordinator(DataUpdateCoordinator[IPPPrinter | None]):
    """Class to manage fetching IPP data from single endpoint.

    An unreachable printer (powered off) is a normal "offline" state, not an
    error: data keeps the last known printer snapshot (None if never seen).
    """

    config_entry: IPPConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: IPPConfigEntry) -> None:
        """Initialize global IPP data updater."""
        self.device_id = config_entry.unique_id or config_entry.entry_id
        self.online: bool | None = None
        self.ipp = IPP(
            host=config_entry.data[CONF_HOST],
            port=config_entry.data[CONF_PORT],
            base_path=config_entry.data[CONF_BASE_PATH],
            tls=config_entry.data[CONF_SSL],
            verify_ssl=config_entry.data[CONF_VERIFY_SSL],
            session=async_get_clientsession(hass, config_entry.data[CONF_VERIFY_SSL]),
            request_timeout=REQUEST_TIMEOUT,
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    @override
    async def _async_update_data(self) -> IPPPrinter | None:
        """Fetch data from IPP."""
        try:
            printer = await self.ipp.printer()
        except IPPConnectionUpgradeRequired as error:
            raise UpdateFailed(f"Invalid response from API: {error}") from error
        except IPPConnectionError as error:
            self._set_online(False, error)
            return self.data
        except IPPError as error:
            raise UpdateFailed(f"Invalid response from API: {error}") from error

        self._set_online(True)
        return printer

    def _set_online(self, online: bool, error: Exception | None = None) -> None:
        """Log only the online/offline transitions, never every failed poll."""
        if online == self.online:
            return
        self.online = online
        host = self.config_entry.data[CONF_HOST]
        if online:
            _LOGGER.info("Printer at %s is online", host)
        else:
            _LOGGER.info("Printer at %s is offline (%s)", host, error)
