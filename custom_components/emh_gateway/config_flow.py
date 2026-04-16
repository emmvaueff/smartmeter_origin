import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

import httpx


async def validate_input(hass: HomeAssistant, data: dict):
    """Validate the user input by performing a Digest-Auth request."""

    url = data[CONF_URL]
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(
                url,
                auth=httpx.DigestAuth(username, password),
                timeout=10
            )
        except Exception as err:
            raise CannotConnect from err

    if response.status_code == 401:
        raise InvalidAuth

    if response.status_code != 200:
        raise CannotConnect

    return {"title": "EMH Gateway"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for the integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_URL: user_input[CONF_URL],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        "scan_interval": DEFAULT_SCAN_INTERVAL,
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_URL): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""
