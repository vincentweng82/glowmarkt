"""Sensor platform for Glowmarkt integration."""
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfVolume,
)
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy


from .const import (
    DOMAIN,
    ATTR_CUMULATIVE_USAGE,
    ATTR_UNITS,
    ATTR_TIMESTAMP,
    CONF_RESOURCE_ID
)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Glowmarkt sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    resource_type = entry.data.get("resource_type", "kWh")
    resource_name = entry.data.get("resource_name", "").lower()

    sensors = [
        GlowmarktCumulativeUsageSensor(coordinator, entry),
        GlowmarktPeriodUsageSensor(coordinator, entry)
    ]
    
    # Electricity resources
    if resource_type == "kWh":
        sensors.extend([
            ElectricityStandingChargeSensor(coordinator, entry),
            ElectricityRateSensor(coordinator, entry),
            ElectricityCostSensor(coordinator, entry)  # Always add for electricity
        ])
    elif resource_type == "m³":
        sensors.append(GlowmarktVolumeSensor(coordinator, entry))
        
    async_add_entities(sensors)

class GlowmarktSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Glowmarkt sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Glowmarkt {entry.data[CONF_RESOURCE_ID]}",
            "manufacturer": "Hildebrand",
            "model": "Glowmarkt",
        }

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{self._entry.entry_id}_{self._attr_name.lower().replace(' ', '_')}"

class GlowmarktPeriodUsageSensor(GlowmarktSensor):
    """Representation of Glowmarkt 30-minute period usage sensor."""
    
    _attr_name = "30 Minute Usage"
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    
    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._last_non_zero_value = None
        self._last_timestamp = None
    
    @property
    def native_value(self):
        """Return the last non-zero 30-minute usage value."""
        if self.coordinator.data is None:
            return self._last_non_zero_value or 0
        
        readings = self.coordinator.data.get("readings", [])
        if not readings:
            return self._last_non_zero_value or 0
        
        # 查找最后一个非零值
        for timestamp, value in reversed(readings):
            if value != 0:
                self._last_non_zero_value = value
                self._last_timestamp = timestamp
                return value
        
        # 如果没有找到非零值，返回之前存储的值
        return self._last_non_zero_value or 0
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            "timestamp": self._last_timestamp,
            "units": self.coordinator.data.get("units", "kWh") if self.coordinator.data else "kWh",
        }
        return attrs
    
class GlowmarktCumulativeUsageSensor(GlowmarktSensor):
    """Representation of Glowmarkt cumulative usage sensor."""

    _attr_name = "Cumulative Usage(today)"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    @property
    def native_value(self):
        """Return the cumulative usage."""
        if self.coordinator.data is None:
            return None

        # 修改：根据资源类型返回累计值
        if "cost" in self.coordinator.data.get("resource_type", ""):
            return self.coordinator.data.get("cumulative_cost")
        return self.coordinator.data.get("cumulative")

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        resource_type = self.coordinator.data.get("resource_type", "kWh")
        if resource_type == "m³":
            return UnitOfVolume.CUBIC_METERS
        elif resource_type == "cost":
            return "GBP"
        return UnitOfEnergy.KILO_WATT_HOUR

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.coordinator.data is None:
            return None

        return {
            ATTR_TIMESTAMP: self.coordinator.data.get("timestamp"),
            ATTR_UNITS: self.coordinator.data.get("units"),
        }


class ElectricityCostSensor(GlowmarktSensor):
    """Daily electricity cost including standing charge and usage."""
    
    _attr_name = "Electricity Cost(today)"
    _attr_native_unit_of_measurement = "GBP"
    _attr_icon = "mdi:cash"
    _attr_device_class = "monetary"

    @property
    def available(self) -> bool:
        """Return True if the sensor is available."""
        return (
            super().available 
            and self.coordinator.data is not None
            and self.coordinator.data.get("tariff") is not None
            and self.coordinator.data.get("cumulative") is not None
        )

    @property
    def native_value(self):
        """Calculate daily cost: standing charge + (usage * rate)."""
        if not self.available:
            return None
            
        # Get necessary data
        tariff = self.coordinator.data["tariff"]
        cumulative_usage = self.coordinator.data.get("cumulative", 0)  # Total kWh
        
        # Convert from pence to pounds
        standing_charge = tariff.get("currentRates", {}).get("standingCharge", 0) / 100  # GBP/day
        rate = tariff.get("currentRates", {}).get("rate", 0) / 100  # GBP/kWh
        
        # Calculate total daily cost
        # Assuming cumulative is today's usage (since coordinator filters for today)
        total_cost = standing_charge + (cumulative_usage * rate)
        return round(total_cost, 2)

    @property
    def extra_state_attributes(self):
        """Return detailed cost breakdown."""
        if not self.available:
            return None
            
        tariff = self.coordinator.data["tariff"]
        standing_charge = tariff.get("currentRates", {}).get("standingCharge", 0) / 100
        rate = tariff.get("currentRates", {}).get("rate", 0) / 100
        cumulative_usage = self.coordinator.data.get("cumulative", 0)
        
        return {
            "standing_charge": standing_charge,
            "rate_per_kwh": rate,
            "daily_usage_kwh": round(cumulative_usage, 3),
            "cost_breakdown": {
                "standing_charge": standing_charge,
                "usage_cost": round(cumulative_usage * rate, 2),
            },
            "calculation_date": datetime.now().strftime("%Y-%m-%d"),
            "tariff_name": tariff.get("name")
        }
        
        
class GlowmarktVolumeSensor(GlowmarktSensor):
    """Representation of Glowmarkt volume sensor (gas only)."""

    _attr_name = "Gas Volume"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS

    @property
    def native_value(self):
        """Return the gas volume."""
        if self.coordinator.data is None:
            return None

        return self.coordinator.data.get("cumulative")
        
class ElectricityStandingChargeSensor(GlowmarktSensor):
    """Representation of Electricity Standing Charge sensor."""
    
    _attr_name = "Electricity Standing Charge"
    _attr_native_unit_of_measurement = "GBP/day"
    _attr_icon = "mdi:calendar-clock"
    
    @property
    def native_value(self):
        """Return the standing charge in GBP/day."""
        if not self.coordinator.data or not self.coordinator.data.get("tariff"):
            return None
            
        # 从便士转换为英镑
        standing_charge = self.coordinator.data["tariff"].get("currentRates", {}).get("standingCharge")
        return round(standing_charge / 100, 2) if standing_charge is not None else None
    
    @property
    def extra_state_attributes(self):
        """Return additional tariff information."""
        if not self.coordinator.data or not self.coordinator.data.get("tariff"):
            return None
            
        tariff = self.coordinator.data["tariff"]
        return {
            "tariff_name": tariff.get("name"),
            "tariff_type": tariff.get("type"),
            "valid_from": tariff.get("from"),
            "source": tariff.get("source", {}).get("value")
        }

class ElectricityRateSensor(GlowmarktSensor):
    """Representation of Electricity Rate sensor."""
    
    _attr_name = "Electricity Rate"
    _attr_native_unit_of_measurement = "GBP/kWh"
    _attr_icon = "mdi:lightning-bolt"
    
    @property
    def native_value(self):
        """Return the electricity rate in GBP/kWh."""
        if not self.coordinator.data or not self.coordinator.data.get("tariff"):
            return None
            
        # 从便士转换为英镑
        rate = self.coordinator.data["tariff"].get("currentRates", {}).get("rate")
        return round(rate / 100, 4) if rate is not None else None  # 保留4位小数
    
    @property
    def extra_state_attributes(self):
        """Return tier information."""
        if not self.coordinator.data or not self.coordinator.data.get("tariff"):
            return None
            
        plan_details = self.coordinator.data["tariff"].get("plan", [{}])[0].get("planDetail", [])
        tiers = {}
        for detail in plan_details:
            if "rate" in detail:
                tiers[f"tier_{detail.get('tier', 1)}"] = detail["rate"] / 100  # 转换为GBP
        
        return tiers