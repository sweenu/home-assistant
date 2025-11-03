"""Tests for the Bbox sensor platform."""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
import requests

from homeassistant.components.bbox.sensor import PLATFORM_SCHEMA, setup_platform
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import CONF_MONITORED_VARIABLES, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util


@pytest.mark.parametrize(
    ("sensor_type", "expected_value"),
    [
        ("down_max_bandwidth", 100000.0),
        ("up_max_bandwidth", 50000.0),
        ("current_down_bandwidth", 50000.0),
        ("current_up_bandwidth", 25000.0),
        ("number_of_reboots", 5),
    ],
)
async def test_sensor_values(
    hass: HomeAssistant,
    sensor_config: dict,
    mock_bbox_api: MagicMock,
    mock_add_entities: MagicMock,
    sensor_type: str,
    expected_value: float,
) -> None:
    """Test sensor values for different sensor types."""
    # Setup platform with specific sensor type
    sensor_config[SENSOR_DOMAIN][CONF_MONITORED_VARIABLES] = [sensor_type]
    setup_platform(hass, sensor_config[SENSOR_DOMAIN], mock_add_entities)

    # Verify entity was added
    assert mock_add_entities.called
    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 1

    # Update entity and check value
    entity = entities[0]
    entity.update()
    assert entity._attr_native_value == expected_value


async def test_uptime_sensor(
    hass: HomeAssistant,
    sensor_config: dict,
    mock_bbox_api: MagicMock,
    mock_add_entities: MagicMock,
) -> None:
    """Test uptime sensor."""
    sensor_config[SENSOR_DOMAIN][CONF_MONITORED_VARIABLES] = ["uptime"]
    setup_platform(hass, sensor_config[SENSOR_DOMAIN], mock_add_entities)

    assert mock_add_entities.called
    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 1

    entity = entities[0]
    entity.update()

    # Uptime should be current time minus uptime seconds
    expected_time = dt_util.utcnow() - timedelta(seconds=3600)
    # Compare timestamps without microseconds to avoid precision issues
    assert entity._attr_native_value.replace(microsecond=0) == expected_time.replace(
        microsecond=0
    )
    assert entity._attr_device_class == "timestamp"


async def test_sensor_attributes(
    hass: HomeAssistant,
    sensor_config: dict,
    mock_bbox_api: MagicMock,
    mock_add_entities: MagicMock,
) -> None:
    """Test sensor attributes."""
    sensor_config[SENSOR_DOMAIN][CONF_MONITORED_VARIABLES] = ["down_max_bandwidth"]
    setup_platform(hass, sensor_config[SENSOR_DOMAIN], mock_add_entities)

    assert mock_add_entities.called
    entities = mock_add_entities.call_args[0][0]
    entity = entities[0]

    assert entity._attr_attribution == "Powered by Bouygues Telecom"
    assert entity._attr_name == "Test Bbox Maximum Download Bandwidth"
    assert entity.entity_description.device_class == "data_rate"
    assert entity.entity_description.native_unit_of_measurement == "Mbit/s"


async def test_uptime_sensor_attributes(
    hass: HomeAssistant,
    sensor_config: dict,
    mock_bbox_api: MagicMock,
    mock_add_entities: MagicMock,
) -> None:
    """Test uptime sensor attributes."""
    sensor_config[SENSOR_DOMAIN][CONF_MONITORED_VARIABLES] = ["uptime"]
    setup_platform(hass, sensor_config[SENSOR_DOMAIN], mock_add_entities)

    assert mock_add_entities.called
    entities = mock_add_entities.call_args[0][0]
    entity = entities[0]

    assert entity._attr_attribution == "Powered by Bouygues Telecom"
    assert entity._attr_name == "Test Bbox Uptime"
    assert entity._attr_device_class == "timestamp"


async def test_setup_platform_all_sensors(
    hass: HomeAssistant,
    sensor_config: dict,
    mock_bbox_api: MagicMock,
    mock_add_entities: MagicMock,
) -> None:
    """Test setup platform with all sensor types."""
    setup_platform(hass, sensor_config[SENSOR_DOMAIN], mock_add_entities)

    assert mock_add_entities.called
    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 6  # All 6 sensor types


async def test_setup_platform_api_failure(
    hass: HomeAssistant,
    sensor_config: dict,
    mock_bbox_api: MagicMock,
    mock_add_entities: MagicMock,
) -> None:
    """Test setup platform with API failure."""
    # Mock both API calls to fail
    mock_bbox_api.get_ip_stats.side_effect = requests.exceptions.HTTPError("API Error")
    mock_bbox_api.get_bbox_info.side_effect = requests.exceptions.HTTPError("API Error")

    setup_platform(hass, sensor_config[SENSOR_DOMAIN], mock_add_entities)

    # Entities are still created even when API fails initially
    # The failure is handled gracefully and entities will show as unavailable
    assert mock_add_entities.called
    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 6  # All 6 sensor types are created


async def test_async_setup_component(
    hass: HomeAssistant,
    mock_bbox_api: MagicMock,
) -> None:
    """Test async setup component with sensor platform."""
    await async_setup_component(
        hass,
        "sensor",
        {
            "sensor": [
                {
                    "platform": "bbox",
                    "monitored_variables": [
                        "down_max_bandwidth",
                        "up_max_bandwidth",
                        "current_down_bandwidth",
                        "current_up_bandwidth",
                        "uptime",
                        "number_of_reboots",
                    ],
                }
            ]
        },
    )
    await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 6


async def test_platform_schema() -> None:
    """Test platform schema validation."""
    config = {
        CONF_MONITORED_VARIABLES: [
            "down_max_bandwidth",
            "up_max_bandwidth",
            "current_down_bandwidth",
            "current_up_bandwidth",
            "number_of_reboots",
            "uptime",
        ],
        CONF_NAME: "Test Bbox",
        "platform": "bbox",
    }

    validated = PLATFORM_SCHEMA(config)
    assert validated[CONF_MONITORED_VARIABLES] == config[CONF_MONITORED_VARIABLES]
    assert validated[CONF_NAME] == "Test Bbox"

    # Test with default name
    config = {
        CONF_MONITORED_VARIABLES: ["down_max_bandwidth"],
        "platform": "bbox",
    }

    validated = PLATFORM_SCHEMA(config)
    assert validated[CONF_NAME] == "Bbox"
