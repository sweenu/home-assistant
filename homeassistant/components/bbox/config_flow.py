"""Config flow for Bbox."""

from typing import Any

import pybbox
import requests
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_BASE, CONF_HOST

from .const import DEFAULT_HOST, DOMAIN


class BboxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Bbox."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                await self._test_connection(user_input[CONF_HOST])
            except ConnectionError:
                errors[CONF_BASE] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Bbox ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_HOST, default=DEFAULT_HOST): str,
                }
            ),
            errors=errors,
        )

    async def _test_connection(self, host: str) -> None:
        """Test connection to the Bbox."""
        try:
            bbox = pybbox.Bbox(ip=host)
            await self.hass.async_add_executor_job(bbox.get_all_connected_devices)
        except requests.exceptions.HTTPError as err:
            raise ConnectionError(f"Cannot connect to Bbox: {err}") from err
