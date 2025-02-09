import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta, timezone
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower, UnitOfEnergy, UnitOfElectricPotential, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import ConfigEntryNotReady

_LOGGER = logging.getLogger(__name__)

DOMAIN = "trasmatech_electricity"
SCAN_INTERVAL = timedelta(minutes=1)  # Fetches data every 1 minute


class TrasMaTechCoordinator(DataUpdateCoordinator):
    """Handles data retrieval from the API for all sensors."""

    def __init__(self, hass, api_url, bearer_token, meter_id):
        """Initialize the coordinator."""
        self.api_url = api_url
        self.bearer_token = bearer_token
        self.meter_id = meter_id
        super().__init__(
            hass,
            _LOGGER,
            name="TrasMaTech API",
            update_interval=SCAN_INTERVAL,  # Ensures periodic updates
        )

    async def _async_update_data(self):
        """Fetch data from the API asynchronously."""
        try:
            now = datetime.now(timezone.utc)
            end_time = now.replace(second=0, microsecond=0) - timedelta(minutes=1)
            start_time = end_time - timedelta(minutes=1)

            start_date_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_date_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            url = f"{self.api_url}telemetry/{self.meter_id}/{start_date_str}/{end_date_str}/1"
            headers = {"Authorization": f"Bearer {self.bearer_token}"}

            _LOGGER.debug(f"Fetching data from API: {url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"API request failed: {response.status}")

                    data = await response.json()

            if not data or not isinstance(data, list) or len(data) == 0:
                raise UpdateFailed("Empty or invalid API response")

            return data[0]  # Returns the latest telemetry data

        except aiohttp.ClientError as ex:
            _LOGGER.error(f"Error fetching data from API: {ex}")
            raise UpdateFailed(f"API request failed: {ex}")


class TrasMaTechTotalUsageSensor(SensorEntity):
    """Sensor for total energy consumption (kWh) based on cumulativeActivePower.max."""

    def __init__(self, coordinator, meter_id):
        self.coordinator = coordinator
        self._meter_id = meter_id
        self._attr_unique_id = f"electricity_meter_{meter_id}_energy_total_usage"
        self.entity_id = f"sensor.electricity_meter_{meter_id}_energy_total_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_last_reset = None
        self._attr_name = f"Electricity Meter {meter_id} - All Time Total Energy Usage"

    @property
    def state(self):
        """Retrieve the value from the coordinator."""
        data = self.coordinator.data
        if data and "cumulativeActivePower" in data:
            return round(data["cumulativeActivePower"]["input"]["max"], 2)
        return None


class TrasMaTechPowerSensor(SensorEntity):
    """Sensor for real-time power measurements in W and kW."""

    def __init__(self, coordinator, meter_id, sensor_type, unit):
        self.coordinator = coordinator
        self._meter_id = meter_id
        self._sensor_type = sensor_type
        self._unit = unit
        self._attr_unique_id = f"electricity_meter_{meter_id}_power_{sensor_type}_{unit.lower()}"
        self.entity_id = f"sensor.electricity_meter_{meter_id}_power_{sensor_type}_{unit.lower()}"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = unit
        self._attr_name = f"Electricity Meter {meter_id} - Power {sensor_type.capitalize()} ({unit})"

    @property
    def state(self):
        """Retrieve real-time power data from the coordinator."""
        data = self.coordinator.data
        if data and "activePower" in data:
            active_power_data = data["activePower"]["input"]
            if active_power_data:
                value = active_power_data.get(self._sensor_type, None)
                if value is not None:
                    return round(value / 1000, 2) if self._unit == "kW" else round(value, 2)
        return None


class TrasMaTechPhaseSensor(SensorEntity):
    """Sensor for voltage (V) and current (A) per phase."""

    def __init__(self, coordinator, meter_id, phase, measurement, value_type):
        self.coordinator = coordinator
        self._meter_id = meter_id
        self._phase = phase
        self._measurement = measurement
        self._value_type = value_type

        unit = "V" if measurement == "voltage" else "A"
        icon = "mdi:sine-wave" if measurement == "voltage" else "mdi:current-ac"

        self._attr_device_class = SensorDeviceClass.VOLTAGE if measurement == "voltage" else SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_name = f"Electricity Meter {meter_id} - {phase.replace('phase', 'Phase ')} {measurement.capitalize()} {value_type.capitalize()}"

        self._attr_unique_id = f"electricity_meter_{meter_id}_{phase}_{measurement}_{value_type}"
        self.entity_id = f"sensor.electricity_meter_{meter_id}_{phase}_{measurement}_{value_type}"

    @property
    def state(self):
        """Retrieve value from the coordinator."""
        data = self.coordinator.data
        if data and self._phase in data and self._measurement in data[self._phase]:
            return round(data[self._phase][self._measurement].get(self._value_type, 0), 2)
        return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up TrasMaTech Electricity sensors from the configuration entry."""
    api_url = entry.data.get("api_url")
    bearer_token = entry.data.get("token")
    meter_id = entry.data.get("meter_id")

    coordinator = TrasMaTechCoordinator(hass, api_url, bearer_token, meter_id)

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as e:
        _LOGGER.error("API request failed: %s", e)
        raise ConfigEntryNotReady from e  # Ensures Home Assistant retries later

    # 🔹 Ensure Home Assistant continues to refresh periodically
    entry.async_on_unload(coordinator.async_add_listener(lambda: None))

    async_add_entities([
        TrasMaTechTotalUsageSensor(coordinator, meter_id),
        TrasMaTechPowerSensor(coordinator, meter_id, "min", "W"),
        TrasMaTechPowerSensor(coordinator, meter_id, "max", "W"),
        TrasMaTechPowerSensor(coordinator, meter_id, "avg", "W"),
        TrasMaTechPowerSensor(coordinator, meter_id, "min", "kW"),
        TrasMaTechPowerSensor(coordinator, meter_id, "max", "kW"),
        TrasMaTechPowerSensor(coordinator, meter_id, "avg", "kW"),
        *[TrasMaTechPhaseSensor(coordinator, meter_id, phase, meas, val) for phase in ["phaseOne", "phaseTwo", "phaseThree"] for meas in ["voltage", "current"] for val in ["min", "max", "avg"]],
    ], True)
