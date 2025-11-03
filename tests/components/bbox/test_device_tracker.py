"""Tests for the Bbox device tracker platform."""

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
import requests

from homeassistant.components.bbox.device_tracker import (
    MIN_TIME_BETWEEN_SCANS,
    PLATFORM_SCHEMA,
    get_scanner,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType


async def test_get_scanner_success(
    hass: HomeAssistant,
    device_tracker_config: ConfigType,
    mock_bbox_api: MagicMock,
) -> None:
    """Test successful scanner initialization."""
    scanner = get_scanner(hass, device_tracker_config)
    assert scanner is not None
    assert scanner.success_init is True


async def test_get_scanner_failure(
    hass: HomeAssistant,
    device_tracker_config: ConfigType,
    mock_bbox_api: MagicMock,
) -> None:
    """Test scanner initialization failure."""
    mock_bbox_api.get_all_connected_devices.side_effect = requests.exceptions.HTTPError(
        "Connection failed"
    )

    scanner = get_scanner(hass, device_tracker_config)
    assert scanner is None


async def test_scan_devices(
    hass: HomeAssistant,
    device_tracker_config: ConfigType,
    mock_bbox_api: MagicMock,
) -> None:
    """Test scanning for devices."""
    scanner = get_scanner(hass, device_tracker_config)
    assert scanner is not None

    devices = scanner.scan_devices()
    assert devices == ["aa:bb:cc:dd:ee:ff", "ff:ee:dd:cc:bb:aa"]
    mock_bbox_api.get_all_connected_devices.assert_called_once()


async def test_get_device_name(
    hass: HomeAssistant,
    device_tracker_config: ConfigType,
    mock_bbox_api: MagicMock,
) -> None:
    """Test getting device name by MAC address."""
    scanner = get_scanner(hass, device_tracker_config)
    assert scanner is not None

    # Test existing device
    name = scanner.get_device_name("aa:bb:cc:dd:ee:ff")
    assert name == "test_device"

    # Test another existing device
    name = scanner.get_device_name("ff:ee:dd:cc:bb:aa")
    assert name == "another_device"

    # Test non-existing device
    name = scanner.get_device_name("11:22:33:44:55:66")
    assert name is None


async def test_scan_devices_with_throttling(
    hass: HomeAssistant,
    device_tracker_config: ConfigType,
    mock_bbox_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test scan devices respects throttling."""
    scanner = get_scanner(hass, device_tracker_config)
    assert scanner is not None

    # First scan should call the API
    devices = scanner.scan_devices()
    assert devices == ["aa:bb:cc:dd:ee:ff", "ff:ee:dd:cc:bb:aa"]
    assert mock_bbox_api.get_all_connected_devices.call_count == 1

    # Second scan within throttle period should not call API again
    devices = scanner.scan_devices()
    assert devices == ["aa:bb:cc:dd:ee:ff", "ff:ee:dd:cc:bb:aa"]
    assert mock_bbox_api.get_all_connected_devices.call_count == 1

    # After throttle period, API should be called again
    freezer.tick(MIN_TIME_BETWEEN_SCANS + timedelta(seconds=1))
    devices = scanner.scan_devices()
    assert devices == ["aa:bb:cc:dd:ee:ff", "ff:ee:dd:cc:bb:aa"]
    assert mock_bbox_api.get_all_connected_devices.call_count == 2


async def test_scan_devices_failure_recovery(
    hass: HomeAssistant,
    device_tracker_config: ConfigType,
    mock_bbox_api: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test device scanning failure and recovery."""
    scanner = get_scanner(hass, device_tracker_config)
    assert scanner is not None

    devices = scanner.scan_devices()
    assert devices == ["aa:bb:cc:dd:ee:ff", "ff:ee:dd:cc:bb:aa"]

    mock_bbox_api.get_all_connected_devices.side_effect = requests.exceptions.HTTPError(
        "API Error"
    )

    freezer.tick(MIN_TIME_BETWEEN_SCANS + timedelta(seconds=1))
    devices = scanner.scan_devices()
    assert devices == []

    # Recover from failure
    mock_bbox_api.get_all_connected_devices.side_effect = None

    freezer.tick(MIN_TIME_BETWEEN_SCANS + timedelta(seconds=1))
    devices = scanner.scan_devices()
    assert devices == ["aa:bb:cc:dd:ee:ff", "ff:ee:dd:cc:bb:aa"]


async def test_scan_devices_filters_inactive(
    hass: HomeAssistant,
    device_tracker_config: ConfigType,
    mock_bbox_api: MagicMock,
) -> None:
    """Test that inactive devices are filtered out."""
    # Setup mock to return mixed active/inactive devices
    mock_bbox_api.get_all_connected_devices.return_value = [
        {
            "macaddress": "aa:bb:cc:dd:ee:ff",
            "hostname": "active_device",
            "ipaddress": "192.168.1.100",
            "active": 1,
        },
        {
            "macaddress": "ff:ee:dd:cc:bb:aa",
            "hostname": "inactive_device",
            "ipaddress": "192.168.1.101",
            "active": 0,  # Should be filtered out
        },
    ]

    scanner = get_scanner(hass, device_tracker_config)
    assert scanner is not None

    devices = scanner.scan_devices()
    assert devices == ["aa:bb:cc:dd:ee:ff"]


async def test_platform_schema() -> None:
    """Test platform schema validation."""
    # Test default host
    config = {"platform": "bbox", "host": "192.168.1.254"}
    validated = PLATFORM_SCHEMA(config)
    assert validated["host"] == "192.168.1.254"

    # Test custom host
    config = {"platform": "bbox", "host": "192.168.2.1"}
    validated = PLATFORM_SCHEMA(config)
    assert validated["host"] == "192.168.2.1"
