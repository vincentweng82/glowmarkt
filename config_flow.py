"""Config flow for Glowmarkt integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

import requests

from .const import (
    DOMAIN,
    BRIGHT_APP_ID,
    CONF_USERNAME,
    CONF_PASSWORD,
    API_URL,
    AUTH_URL,
    CONF_RESOURCE_ID,
    CONF_RESOURCE_TYPE
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class GlowmarktConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Glowmarkt."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                # Authenticate and fetch resources
                token = await self.hass.async_add_executor_job(
                    self._authenticate, username, password
                )

                resources = await self.hass.async_add_executor_job(
                    self._get_resources, token
                )

                if not resources:
                    raise ValueError("No resources found")

                # Create entries for each electricity and gas resource
                for resource_id, resource_data in resources.items():
                    # 修改：同时识别消费和成本资源
                    if resource_data['baseUnit'] in ['kWh', 'm³'] or 'cost' in resource_data['name'].lower():
                        await self.async_set_unique_id(resource_id)
                        self._abort_if_unique_id_configured()

                        return self.async_create_entry(
                            title=f"Glowmarkt - {resource_data['name']}",
                            data={
                                CONF_USERNAME: username,
                                CONF_PASSWORD: password,
                                CONF_RESOURCE_ID: resource_id,
                                "resource_type": resource_data['baseUnit'] if resource_data['baseUnit'] else "cost",
                                "resource_name": resource_data['name']  # 添加资源名称用于识别成本资源
                            },
                        )

                raise ValueError("No electricity, gas or cost resources found")

            except Exception as e:
                _LOGGER.exception("Authentication failed: %s", e)
                errors["base"] = "auth_failed"

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    def _authenticate(self, username, password):
        """Get token."""
        headers = {
            "applicationId": BRIGHT_APP_ID,
            "Content-Type": "application/json",
        }
        payload = {"username": username, "password": password}
        response = requests.post(AUTH_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["token"]

    def _get_resources(self, token):
        """Fetch available resources."""
        headers = {
            "applicationId": BRIGHT_APP_ID,
            "token": token,
        }
        response = requests.get(f"{API_URL}/resource", headers=headers)
        response.raise_for_status()
        resources = response.json()
        
        # 修改：返回更详细的资源信息，包括名称和类型
        return {
            r["resourceId"]: {
                "name": r["name"],
                "baseUnit": r.get("baseUnit", ""),
                "resourceTypeId": r.get("resourceTypeId", ""),
            }
            for r in resources
        }