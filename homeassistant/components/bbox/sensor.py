"""Support for Bbox Bouygues Modem Router."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

import pybbox
import requests
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_MONITORED_VARIABLES,
    CONF_NAME,
    UnitOfDataRate,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, StateType
from homeassistant.util import Throttle

from .const import ATTRIBUTION

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Bbox"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)


class BboxData:
    """Get data from the Bbox."""

    def __init__(self, host: str | None = None) -> None:
        """Initialize the data object."""
        self.ip_stats: dict[str, Any] = {}
        self.router_info: dict[str, Any] = {}
        self.host = host

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self) -> bool:
        """Get the latest data from the Bbox."""
        try:
            bbox = pybbox.Bbox(ip=self.host) if self.host else pybbox.Bbox()
            self.ip_stats = bbox.get_ip_stats()
            self.router_info = bbox.get_bbox_info()
        except requests.exceptions.HTTPError as error:
            _LOGGER.error(error)
            self.ip_stats = {}
            self.router_info = {}
            return False
        return True


@dataclass(frozen=True, kw_only=True)
class BboxSensorEntityDescription(SensorEntityDescription):
    """Describes Bbox sensor entity."""

    value_fn: Callable[[BboxData], StateType]


SENSOR_DESCRIPTIONS: tuple[BboxSensorEntityDescription, ...] = (
    BboxSensorEntityDescription(
        key="down_max_bandwidth",
        translation_key="down_max_bandwidth",
        icon="mdi:download",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        value_fn=lambda data: round(data.ip_stats["rx"]["maxBandwidth"] / 1000, 2),
    ),
    BboxSensorEntityDescription(
        key="up_max_bandwidth",
        translation_key="up_max_bandwidth",
        icon="mdi:upload",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        value_fn=lambda data: round(data.ip_stats["tx"]["maxBandwidth"] / 1000, 2),
    ),
    BboxSensorEntityDescription(
        key="current_down_bandwidth",
        translation_key="down_stream",
        icon="mdi:download",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        value_fn=lambda data: round(data.ip_stats["rx"]["bandwidth"] / 1000, 2),
    ),
    BboxSensorEntityDescription(
        key="current_up_bandwidth",
        translation_key="up_stream",
        icon="mdi:upload",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        value_fn=lambda data: round(data.ip_stats["tx"]["bandwidth"] / 1000, 2),
    ),
    BboxSensorEntityDescription(
        key="number_of_reboots",
        translation_key="number_of_reboots",
        icon="mdi:restart",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.router_info["device"]["numberofboots"],
    ),
    BboxSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        icon="mdi:clock",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda data: data.router_info["device"]["uptime"],
    ),
)

SENSOR_KEYS: list[str] = [desc.key for desc in SENSOR_DESCRIPTIONS]

PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_MONITORED_VARIABLES): vol.All(
            cv.ensure_list, [vol.In(SENSOR_KEYS)]
        ),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Bbox sensors from a config entry."""
    try:
        bbox_data = BboxData(entry.data.get("host"))
        await hass.async_add_executor_job(bbox_data.update)
    except requests.exceptions.HTTPError as error:
        _LOGGER.error(error)
        return

    async_add_entities(
        (
            BboxSensor(bbox_data, entry.title, description)
            for description in SENSOR_DESCRIPTIONS
        ),
        update_before_add=True,
    )


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Bbox sensor."""
    bbox_data = BboxData()
    try:
        bbox_data.update()
    except requests.exceptions.HTTPError as error:
        _LOGGER.error(error)
        return

    name = config[CONF_NAME]
    monitored_variables = config[CONF_MONITORED_VARIABLES]

    add_entities(
        (
            BboxSensor(bbox_data, name, description)
            for description in SENSOR_DESCRIPTIONS
            if description.key in monitored_variables
        ),
        update_before_add=True,
    )


class BboxSensor(SensorEntity):
    """Implementation of a Bbox sensor."""

    entity_description: BboxSensorEntityDescription
    _attr_attribution = ATTRIBUTION

    def __init__(
        self, bbox_data: BboxData, name: str, description: BboxSensorEntityDescription
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._attr_name = f"{name} {description.name}"
        self.bbox_data = bbox_data

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.bbox_data)

    def update(self) -> None:
        """Get the latest data from Bbox and update the state."""
        self.bbox_data.update()
