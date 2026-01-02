"""Sensor platform for Hoymiles Cloud integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timezone

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfMass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN
)
from .hoymiles_api import HoymilesAPI

_LOGGER = logging.getLogger(__name__)


def safe_int_convert(value: Any) -> int:
    """Safely convert a value to int, handling various edge cases.
    
    Args:
        value: Input value that can be int, float, str, bool, None, or '-'.
        
    Returns:
        int: Converted integer value. Returns 0 for invalid/missing data.
        
    Handles:
        - Float strings like '22706.0' by converting to float first
        - Missing data represented as '-', None, or empty string
        - Whitespace-only strings
        - Boolean values (True -> 1, False -> 0)
    """
    if value is None or value == '-' or value == '':
        return 0
    
    # Handle whitespace-only strings
    if isinstance(value, str) and value.strip() == '':
        return 0
    
    # Handle boolean values
    if isinstance(value, bool):
        return int(value)
    
    try:
        # Handle float strings like '22706.0' by converting to float first
        return int(float(value))
    except (ValueError, TypeError) as e:
        _LOGGER.debug("Unexpected value during int conversion: %s, error: %s", value, e)
        return 0

def safe_float_convert(value: Any) -> float:
    """Safely convert a value to float, handling various edge cases.
    
    Args:
        value: Input value that can be int, float, str, bool, None, or '-'.
        
    Returns:
        float: Converted float value. Returns 0.0 for invalid/missing data.
        
    Handles:
        - Missing data represented as '-', None, or empty string
        - Whitespace-only strings
        - Boolean values (True -> 1.0, False -> 0.0)
        - Integer and string representations of numbers
    """
    if value is None or value == '-' or value == '':
        return 0.0
    
    # Handle whitespace-only strings
    if isinstance(value, str) and value.strip() == '':
        return 0.0
    
    # Handle boolean values
    if isinstance(value, bool):
        return float(value)
    
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        _LOGGER.debug("Unexpected value during float conversion: %s, error: %s", value, e)
        return 0.0

def parse_timestamp(timestamp_str: str | None) -> datetime | None:
    """Parse timestamp string from the API.

    The API returns naive timestamps (without timezone info) that represent
    the local time. We need to interpret them in the Home Assistant timezone
    and convert to UTC for proper display.
    """
    if not timestamp_str:
        return None
    try:
        # Parse the naive datetime string
        naive_dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

        # Assume the timestamp is in Home Assistant's configured timezone
        # and convert it to UTC-aware datetime
        local_aware_dt = naive_dt.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        return dt_util.as_utc(local_aware_dt)
    except (ValueError, TypeError) as e:
        _LOGGER.warning("Failed to parse timestamp: %s, error: %s", timestamp_str, e)
        return None


@dataclass
class HoymilesSensorDescription(SensorEntityDescription):
    """Class describing Hoymiles sensor entities."""

    value_fn: Optional[Callable[[Dict], StateType]] = None
    available_fn: Optional[Callable[[Dict], bool]] = None


SENSORS = [
    # Battery state
    HoymilesSensorDescription(
        key="battery_soc",
        name="Battery State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: safe_int_convert(data.get("real_time_data", {}).get("reflux_station_data", {}).get("bms_soc")),
    ),
    
    # Environmental factors
    HoymilesSensorDescription(
        key="co2_emission_reduction",
        name="CO2 Emission Reduction",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: safe_int_convert(data.get("real_time_data", {}).get("co2_emission_reduction", 0)),
    ),
    HoymilesSensorDescription(
        key="plant_tree",
        name="Equivalent Trees Planted",
        value_fn=lambda data: safe_int_convert(data.get("real_time_data", {}).get("plant_tree", 0)),
    ),

    # Energy production - cumulative values
    HoymilesSensorDescription(
        key="today_energy",
        name="Today's Energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: safe_int_convert(data.get("real_time_data", {}).get("today_eq", 0)),
    ),
    HoymilesSensorDescription(
        key="month_energy",
        name="Month Energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: safe_int_convert(data.get("real_time_data", {}).get("month_eq", 0)),
    ),
    HoymilesSensorDescription(
        key="year_energy",
        name="Year Energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: safe_int_convert(data.get("real_time_data", {}).get("year_eq", 0)),
    ),
    HoymilesSensorDescription(
        key="total_energy",
        name="Total Energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: safe_int_convert(data.get("real_time_data", {}).get("total_eq", 0)),
    ),
    
    # Daily energy flows                                                                                                              
    HoymilesSensorDescription(
        key="battery_charge_energy_today",
        name="Battery Charge Energy Today",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: safe_int_convert(data.get("real_time_data", {}).get("reflux_station_data", {}).get("bms_in_eq", 0)),
    ),
    HoymilesSensorDescription(
        key="battery_discharge_energy_today",
        name="Battery Discharge Energy Today",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: safe_int_convert(data.get("real_time_data", {}).get("reflux_station_data", {}).get("bms_out_eq", 0)),
    ),

    # System status information
    HoymilesSensorDescription(
        key="last_update_time",
        name="Last Data Update Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: parse_timestamp(data.get("real_time_data", {}).get("data_time")),
    ),
]


DTUS = [
    # Hard- / Software version
    HoymilesSensorDescription(
        key="init_soft_ver",
        name="Software Version",
        value_fn=lambda data: data.get("real_time_data", {}).get("init_soft_ver"),
    ),
    HoymilesSensorDescription(
        key="init_hard_ver",
        name="Hardware Version",
        value_fn=lambda data: data.get("real_time_data", {}).get("init_hard_ver"),
    ),
    HoymilesSensorDescription(
        key="model_no",
        name="Model",
        value_fn=lambda data: data.get("real_time_data", {}).get("model_no"),
    ),
        HoymilesSensorDescription(
        key="sn_no",
        name="SN",
        value_fn=lambda data: data.get("real_time_data", {}).get("sn"),
    ),

    # Connections
    HoymilesSensorDescription(
        key="connected_station_name",
        name="Plant / Station",
        value_fn=lambda data: data.get("real_time_data", {}).get("station_name"),
    ),

    # Connect / Disconnect status
    HoymilesSensorDescription(
        key="warn_data_connect",
        name="Connection Status",
        value_fn=lambda data: (
            "Offline" if data.get("real_time_data", {}).get("warn_data", {}).get("connect") is False else
            "Online" if data.get("real_time_data", {}).get("warn_data", {}).get("connect") is True else
            "unknown"
        ),
    ),
]


MICROINVERTERS = [
    # Hard- / Software version
    HoymilesSensorDescription(
        key="init_soft_ver",
        name="Software Version",
        value_fn=lambda data: data.get("real_time_data", {}).get("init_soft_ver"),
    ),
    HoymilesSensorDescription(
        key="init_hard_ver",
        name="Hardware Version",
        value_fn=lambda data: data.get("real_time_data", {}).get("init_hard_ver"),
    ),
    HoymilesSensorDescription(
        key="init_hard_no",
        name="Model",
        value_fn=lambda data: data.get("real_time_data", {}).get("init_hard_no"),
    ),
    HoymilesSensorDescription(
        key="sn_no",
        name="SN",
        value_fn=lambda data: data.get("real_time_data", {}).get("sn"),
    ),

    # Connections
    HoymilesSensorDescription(
        key="connected_dtu_sn",
        name="Connected DTU",
        value_fn=lambda data: data.get("real_time_data", {}).get("dtu_sn"),
    ),
    HoymilesSensorDescription(
        key="connected_station_name",
        name="Plant / Station",
        value_fn=lambda data: data.get("real_time_data", {}).get("station_name"),
    ),

    # Connect / Disconnect status
    HoymilesSensorDescription(
        key="warn_data_connect",
        name="Connection Status",
        value_fn=lambda data: (
            "Offline" if data.get("real_time_data", {}).get("warn_data", {}).get("connect") is False else
            "Online" if data.get("real_time_data", {}).get("warn_data", {}).get("connect") is True else
            "unknown"
        ),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hoymiles Cloud sensor entries."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    stations = data["stations"]
    microinverters = data["microinverters"]
    dtus = data["dtus"]

    entities = []

    # For each station, create all standard sensors first
    for station_id, station_name in stations.items():
        # Add standard sensors from SENSORS
        for description in SENSORS:
            entities.append(
                HoymilesSensor(
                    coordinator=coordinator,
                    description=description,
                    station_id=station_id,
                    station_name=station_name,
                )
            )
        
        for micro_station_id, microinverter_data in microinverters.items():
            if station_id == micro_station_id:
                for data in microinverter_data:
                    for description in MICROINVERTERS:
                        entities.append(
                            HoymilesMicroInverter(
                                coordinator=coordinator,
                                description=description,
                                micro_id=data['id'],
                                micro_name=data['name'],
                            )
                        )
        
        for dtu_station_id, dtu_data in dtus.items():
            if station_id == dtu_station_id:
                for data in dtu_data:
                    for description in DTUS:
                        entities.append(
                            HoymilesMicroInverter(
                                coordinator=coordinator,
                                description=description,
                                micro_id=data['id'],
                                micro_name=data['name'],
                            )
                        )
    
    async_add_entities(entities)


class HoymilesSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Hoymiles sensor."""

    entity_description: HoymilesSensorDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: HoymilesSensorDescription,
        station_id: str,
        station_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._station_id = station_id
        self._station_name = station_name
        
        # Set unique ID and name
        self._attr_unique_id = f"{DOMAIN}_{station_id}_{description.key}"
        self._attr_name = f"{station_name} {description.name}"
        
        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, station_id)},
            "name": station_name,
            "manufacturer": "Hoymiles",
            "model": "Solar Inverter System",
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
            
        try:
            station_data = self.coordinator.data.get(self._station_id, {})
            if self.entity_description.value_fn:
                return self.entity_description.value_fn(station_data)
            return None
        except (KeyError, ValueError, TypeError) as e:
            _LOGGER.error("Error getting sensor value: %s", e)
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        station_data = self.coordinator.data.get(self._station_id, {})
        
        # Check if we have the minimum data required
        key_prefix = self.entity_description.key.split("_")[0]
        
        # Check if specific availability function is defined
        if self.entity_description.available_fn:
            return self.entity_description.available_fn(station_data)
            
        return True

class HoymilesMicroInverter(CoordinatorEntity, SensorEntity):
    """Representation of a Hoymiles sensor."""

    entity_description: HoymilesSensorDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: HoymilesSensorDescription,
        micro_id: str,
        micro_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._micro_id = micro_id
        self._micro_name = micro_name
        
        # Set unique ID and name
        self._attr_unique_id = f"{DOMAIN}_{micro_id}_{description.key}"
        self._attr_name = f"{micro_name} {description.name}"
        
        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, micro_id)},
            "name": micro_name,
            "manufacturer": "Hoymiles",
            "model": "Solar Inverter System",
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
            
        try:
            micro_data = self.coordinator.data.get(self._micro_id, {})
            if self.entity_description.value_fn:
                return self.entity_description.value_fn(micro_data)
            return None
        except (KeyError, ValueError, TypeError) as e:
            _LOGGER.error("Error getting sensor value: %s", e)
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        micro_data = self.coordinator.data.get(self._micro_id, {})
        
        # Check if we have the minimum data required
        key_prefix = self.entity_description.key.split("_")[0]
        
        # Check if specific availability function is defined
        if self.entity_description.available_fn:
            return self.entity_description.available_fn(micro_data)
            
        return True
