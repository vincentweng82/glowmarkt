"""The Glowmarkt integration."""
import logging
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    BRIGHT_APP_ID,
    CONF_USERNAME,
    CONF_PASSWORD,
    API_URL,
    AUTH_URL
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Glowmarkt from a config entry."""
    coordinator = GlowmarktDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


class GlowmarktDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Glowmarkt data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Glowmarkt",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.entry = entry
        self.token = None
        self.resource_id = entry.data.get("resource_id")
        self.resource_type = entry.data.get("resource_type", "kWh")
        self.resource_name = entry.data.get("resource_name", "")  # 添加资源名称
        self.is_cost_resource = "cost" in self.resource_name.lower()

    def _authenticate(self):
        """Authenticate with the Glowmarkt API and retrieve a token."""
        username = self.entry.data[CONF_USERNAME]
        password = self.entry.data[CONF_PASSWORD]

        headers = {
            "applicationId": BRIGHT_APP_ID,
            "Content-Type": "application/json"
        }
        payload = {"username": username, "password": password}
        response = requests.post(AUTH_URL, json=payload, headers=headers)
        response.raise_for_status()

        self.token = response.json()["token"]

    def _get_catchup_data(self):
        """Call the catchup endpoint to fetch historical data that may have been uploaded late."""
        if not self.token:
            self._authenticate()

        headers = {
            "applicationId": BRIGHT_APP_ID,
            "Authorization": f"Bearer {self.token}"
        }
        url = f"{API_URL}/resource/{self.resource_id}/catchup"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 401:
                _LOGGER.warning("Catchup token expired, re-authenticating")
                self._authenticate()
                headers["Authorization"] = f"Bearer {self.token}"
                response = requests.get(url, headers=headers)

            response.raise_for_status()
            data = response.json()
            _LOGGER.info(f"Catchup data retrieved: {len(data.get('data', []))} entries")
            return data.get("data", [])
        except Exception as err:
            _LOGGER.error(f"Failed to fetch catchup data: {err}")
            return []

    def _merge_readings(self, original, catchup):
        """Merge catchup readings into original readings, overriding zeros."""
        merged = {}

        for item in original:
            if isinstance(item, list) and len(item) >= 2:
                ts, value = item[0], item[1]
                merged[ts] = value

        for item in catchup:
            if isinstance(item, list) and len(item) >= 2:
                ts, value = item[0], item[1]
                if ts not in merged or merged[ts] == 0:
                    merged[ts] = value

        # 返回按时间戳排序的合并结果（二维数组形式）
        return sorted([[ts, merged[ts]] for ts in merged])

    def _get_usage_data(self):
        """Fetch usage data from the Glowmarkt API."""
        if not self.token:
            self._authenticate()

        headers = {
            "applicationId": BRIGHT_APP_ID,
            "Authorization": f"Bearer {self.token}"
        }
        # 动态计算BST偏移
        london_tz = ZoneInfo("Europe/London")
        now_localized = datetime.now(london_tz)
        utc_offset = now_localized.utcoffset()

        # 判断是否为夏令时（BST）
        offset_minutes = -60 if utc_offset.total_seconds() == 3600 else 0

        # 计算时间范围
        now = datetime.now(timezone.utc)
        end = now

        # 今天0点35分（UTC）
        boundary = now.replace(hour=0, minute=35, second=0, microsecond=0)

        if now < boundary:
            # 如果当前时间小于今天00:35，start就是前一天的00:29
            start = (now - timedelta(days=1)).replace(hour=0, minute=29, second=0, microsecond=0)
        else:
            # 否则start是今天0点0分0秒
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)


        from_str = start.strftime("%Y-%m-%dT%H:%M:%S")
        to_str = end.strftime("%Y-%m-%dT%H:%M:%S")

        url = f"{API_URL}/resource/{self.resource_id}/readings?from={from_str}&to={to_str}&period=PT30M&offset={offset_minutes}&function=sum"

        response = requests.get(url, headers=headers)
        if response.status_code == 401:
            _LOGGER.warning("Token expired, re-authenticating")
            self._authenticate()
            headers["Authorization"] = f"Bearer {self.token}"
            response = requests.get(url, headers=headers)

        response.raise_for_status()
        api_data = response.json()

        readings = api_data.get("data", [])
        units = api_data.get("units", self.resource_type)

        # 若 readings 中有 0，则调用 catchup 接口并合并
        if any(isinstance(r, list) and len(r) > 1 and r[1] == 0 for r in readings):
            _LOGGER.info("Detected zero in readings. Fetching catchup data...")
            catchup_data = self._get_catchup_data()
            readings = self._merge_readings(readings, catchup_data)

        if not readings or not isinstance(readings[0], list) or len(readings[0]) < 2:
            raise UpdateFailed("API response has no usable readings")

        return {
            "readings": readings,
            "timestamp": readings[-1][0] if readings else None,
            "units": units,
            "cumulative": sum(r[1] for r in readings if isinstance(r, list) and len(r) > 1),
            "resource_type": self.resource_type,
        }



            
    def _get_tariff_data(self):
        """Get tariff information from API."""
        headers = {
            "applicationId": BRIGHT_APP_ID,
            "Authorization": f"Bearer {self.token}"
        }
        url = f"{API_URL}/resource/{self.resource_id}/tariff"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _async_update_data(self):
        """Fetch and return the latest data."""
        try:
            data = await self.hass.async_add_executor_job(self._get_usage_data)
            
            # 只有电力资源获取电价信息
            if self.resource_type == "kWh":
                try:
                    tariff_data = await self.hass.async_add_executor_job(self._get_tariff_data)
                    data["tariff"] = tariff_data.get("data", [{}])[0]  # 取第一个tariff数据
                except Exception as e:
                    _LOGGER.warning(f"Failed to get tariff info: {e}")
                    data["tariff"] = None
            
            return data
        except Exception as err:
            raise UpdateFailed(f"Update failed: {err}")
