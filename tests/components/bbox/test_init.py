"""Tests for the Bbox config entry setup."""

from unittest.mock import patch

from homeassistant.components.bbox import async_setup_entry, async_unload_entry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_setup_entry_success(hass: HomeAssistant) -> None:
    """Test successful setup of a config entry."""
    config_entry = MockConfigEntry(
        domain="bbox",
        data={CONF_HOST: "192.168.1.254"},
        unique_id="192.168.1.254",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"
    ) as mock_forward:
        result = await async_setup_entry(hass, config_entry)

        assert result is True
        mock_forward.assert_called_once_with(config_entry, ["device_tracker", "sensor"])


async def test_unload_entry_success(hass: HomeAssistant) -> None:
    """Test successful unloading of a config entry."""
    config_entry = MockConfigEntry(
        domain="bbox",
        data={CONF_HOST: "192.168.1.254"},
        unique_id="192.168.1.254",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ) as mock_unload_platforms:
        result = await async_unload_entry(hass, config_entry)

        assert result is True
        mock_unload_platforms.assert_called_once_with(
            config_entry, ["device_tracker", "sensor"]
        )


async def test_unload_entry_failure(hass: HomeAssistant) -> None:
    """Test unsuccessful unloading of a config entry."""
    config_entry = MockConfigEntry(
        domain="bbox",
        data={CONF_HOST: "192.168.1.254"},
        unique_id="192.168.1.254",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=False,
    ):
        result = await async_unload_entry(hass, config_entry)

        assert result is False
