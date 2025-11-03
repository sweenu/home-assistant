"""Support for French FAI Bouygues Bbox routers."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

import pybbox
import requests
import voluptuous as vol

from homeassistant.components.device_tracker import (
    DOMAIN as DEVICE_TRACKER_DOMAIN,
    PLATFORM_SCHEMA as DEVICE_TRACKER_PLATFORM_SCHEMA,
    ScannerEntity,
)
from homeassistant.components.device_tracker.legacy import (
    AsyncSeeCallback,
    DeviceScanner,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle, dt as dt_util

from .const import DEFAULT_HOST

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=60)

PLATFORM_SCHEMA = DEVICE_TRACKER_PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string}
)


async def async_setup_scanner(
    hass: HomeAssistant,
    config: ConfigType,
    async_see_devices: AsyncSeeCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> bool:
    """Set up the Bbox device tracker."""
    host = config[CONF_HOST]
    scanner = BboxDeviceScanner(hass, host)

    # Perform initial scan
    await scanner.async_update()

    # Report devices using the legacy see callback
    for device in scanner.last_results.values():
        await async_see_devices(
            mac=device.mac,
            host_name=device.name,
            location_name=device.ip,
        )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Bbox device tracker from a config entry."""
    scanner = BboxDeviceScanner(hass, entry.data[CONF_HOST])

    # Perform initial scan
    await scanner.async_update()

    entities = [
        BboxDeviceEntity(scanner, device) for device in scanner.last_results.values()
    ]
    async_add_entities(entities)


def get_scanner(hass: HomeAssistant, config: ConfigType) -> DeviceScanner | None:
    """Validate the configuration and return a Bbox scanner."""
    scanner = BboxDeviceScanner(hass, config[DEVICE_TRACKER_DOMAIN][CONF_HOST])
    return scanner if scanner.success_init else None


@dataclass
class Device:
    """Represents a device on the network."""

    mac: str
    name: str
    ip: str
    last_update: datetime


class BboxDeviceScanner(DeviceScanner):
    """Scanner for devices connected to the bbox."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize the scanner."""
        self.hass = hass
        self.host = host
        self.last_results: dict[str, Device] = {}

        # Perform initial scan
        self.success_init = self._update_info()

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()
        return self.last_results.values()

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        return self.last_results[device].name

    async def async_update(self) -> None:
        """Update device information."""
        assert self.hass is not None
        await self.hass.async_add_executor_job(self._update_info)

    @Throttle(MIN_TIME_BETWEEN_SCANS)
    def _update_info(self):
        """Check the Bbox for devices.

        Returns boolean if scanning successful.
        """
        _LOGGER.debug("Scanning")

        try:
            box = pybbox.Bbox(ip=self.host)
            result = box.get_all_connected_devices()
        except requests.exceptions.HTTPError as err:
            _LOGGER.error("Error scanning devices: %s", err)
            self.last_results = {}
            return False

        now = dt_util.now()
        last_results = {}
        for device in result:
            if device["active"] != 1:
                continue
            last_results[device["macaddress"]] = Device(
                device["macaddress"],
                device["hostname"],
                device["ipaddress"],
                now,
            )

        self.last_results = last_results

        _LOGGER.debug("Scan successful")
        return True


class BboxDeviceEntity(ScannerEntity):
    """Representation of a Bbox device."""

    _attr_should_poll = False
    _attr_mac_address: str
    _attr_name: str
    _attr_ip_address: str
    _last_update: datetime

    def __init__(self, scanner: BboxDeviceScanner, device_data: Device) -> None:
        """Initialize a Bbox device."""
        self._scanner = scanner
        self._device_data = device_data
        self._attr_unique_id = device_data.mac
        self._attr_mac_address = device_data.mac
        self._attr_name = device_data.name
        self._attr_ip_address = device_data.ip
        self._last_update = device_data.last_update

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network."""
        return self._attr_mac_address in self._scanner.last_results

    async def async_update(self) -> None:
        """Update the entity."""
        await self._scanner.async_update()

        # Update device data with latest scan
        if device := self._scanner.last_results[self._attr_mac_address]:
            self._device_data = device
            self._attr_name = device.name
            self._attr_ip_address = device.ip
            self._last_update = device.last_update
