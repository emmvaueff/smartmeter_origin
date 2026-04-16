from __future__ import annotations

import logging
import httpx
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


class SmartmeterCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from the EMH Gateway endpoint."""

    def __init__(self, hass: HomeAssistant, url: str, username: str, password: str, scan_interval: int):
        """Initialize the coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            name="EMH Gateway Coordinator",
            update_interval=timedelta(seconds=scan_interval),
        )

        self.url = url
        self.username = username
        self.password = password

    async def _async_update_data(self):
        """Fetch data from the smart meter."""

        async with httpx.AsyncClient(verify=False) as client:
            try:
                response = await client.get(
                    self.url,
                    auth=httpx.DigestAuth(self.username, self.password),
                    timeout=10,
                )
            except Exception as err:
                raise UpdateFailed(f"Connection error: {err}") from err

        if response.status_code != 200:
            raise UpdateFailed(f"Unexpected status code: {response.status_code}")

        try:
            data = response.json()
        except Exception as err:
            raise UpdateFailed(f"Invalid JSON: {err}") from err

        return data
