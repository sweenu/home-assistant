"""Tests for the Bbox config flow."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from homeassistant.components.bbox.config_flow import BboxConfigFlow
from homeassistant.components.bbox.const import DEFAULT_HOST, DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


@pytest.fixture
def mock_bbox_api():
    """Mock the pybbox API."""
    with patch("homeassistant.components.bbox.config_flow.pybbox") as mock_pybbox:
        mock_box = MagicMock()
        mock_pybbox.Bbox.return_value = mock_box
        yield mock_box


async def test_user_flow_success(hass: HomeAssistant, mock_bbox_api) -> None:
    """Test successful user flow."""
    mock_bbox_api.get_all_connected_devices.return_value = []

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Bbox ({DEFAULT_HOST})"
    assert result["data"] == {"host": DEFAULT_HOST}


async def test_user_flow_custom_host(hass: HomeAssistant, mock_bbox_api) -> None:
    """Test user flow with custom host."""
    mock_bbox_api.get_all_connected_devices.return_value = []

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"host": "192.168.2.1"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bbox (192.168.2.1)"
    assert result["data"] == {"host": "192.168.2.1"}


async def test_user_flow_connection_error(hass: HomeAssistant, mock_bbox_api) -> None:
    """Test user flow with connection error."""
    mock_bbox_api.get_all_connected_devices.side_effect = requests.exceptions.HTTPError(
        "Connection failed"
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_version(hass: HomeAssistant) -> None:
    """Test config flow version."""
    flow = BboxConfigFlow()
    flow.hass = hass
    assert flow.VERSION == 1
