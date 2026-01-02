"""The Hoymiles Cloud Integration."""
import asyncio
import logging
from datetime import timedelta
import json

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, STORAGE_KEY, STORAGE_VERSION
from .hoymiles_api import HoymilesAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hoymiles Cloud from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    session = async_get_clientsession(hass)
    api = HoymilesAPI(session, username, password)

    # Initialize storage
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored_data = await store.async_load() or {}
    
    # Initialize dtus and microinverters
    dtus = {}
    microinverters = {}
    
    # Ensure we have station-specific data
    stored_data.setdefault("stations", {})
    stored_data.setdefault("dtus", {})
    stored_data.setdefault("microinverters", {})
    
    # Verify authentication
    try:
        _LOGGER.debug("Attempting authentication for user: %s", username)
        auth_result = await api.authenticate()
        if not auth_result:
            _LOGGER.error("Authentication failed")
            return False
        _LOGGER.debug("Authentication successful")
    except Exception as e:
        _LOGGER.error("Authentication failed with exception: %s", e)
        return False

    # Fetch initial station data
    try:
        _LOGGER.debug("Attempting to get stations for account: %s", username)
        stations = await api.get_stations()
        _LOGGER.debug("API returned stations data: %s", stations)
        
        # Enhanced check for stations
        if not stations:
            _LOGGER.error("No stations found for this account (empty dictionary returned)")
            return False
            
        if not isinstance(stations, dict):
            _LOGGER.error("Invalid stations data type: %s, expected dict", type(stations))
            return False
            
        _LOGGER.info("Found %d station(s): %s", len(stations), list(stations.keys()))
        
        # Initialize storage for each station
        for station_id in stations:
            _LOGGER.debug("Initializing storage for station: %s (%s)", station_id, stations[station_id])
            if station_id not in stored_data["stations"]:
                stored_data["stations"][station_id] = {}
            
            # Get dtus data
            _LOGGER.debug("Attempting to get dtus for station: %s", station_id)
            dtus[station_id] = await api.get_dtus(station_id)
            _LOGGER.debug("API returned dtus data: %s", dtus)

            # Get microinverters data
            _LOGGER.debug("Attempting to get microinverters for station: %s", station_id)
            microinverters[station_id] = await api.get_microinverters(station_id)
            _LOGGER.debug("API returned microinverters data: %s", microinverters)
        
        # Save initial data
        await store.async_save(stored_data)
        
    except Exception as e:
        _LOGGER.error("Failed to get station data: %s", e)
        return False

    async def async_update_data():
        """Fetch data from API."""
        try:
            async with async_timeout.timeout(30):
                _LOGGER.debug("=== Starting coordinator data update ===")
                
                # Check if token is still valid, refresh if needed
                if api.is_token_expired():
                    _LOGGER.debug("Token expired, refreshing...")
                    await api.authenticate()
                
                # Collect data from all stations
                data = {}
                for station_id in stations:
                    _LOGGER.debug("Updating data for station %s", station_id)
                    
                    # Get real-time data from station
                    real_time_station_data = await api.get_real_time_data_station(station_id)

                    data[station_id] = {
                        "real_time_data": real_time_station_data
                    }
                    
                    # Collect data from all dtus
                    for dtu_station_id, dtus_data in dtus.items():
                        if station_id == dtu_station_id:
                            for dtu_data in dtus_data:
                                _LOGGER.debug("Updating data for dtu %s in station %s", dtu_data['id'], station_id)

                                # Get real-time data from microinverter
                                real_time_dtu_data = await api.get_real_time_data_dtu(station_id, dtu_data['id'])

                                data[dtu_data['id']] = {
                                    "real_time_data": real_time_dtu_data
                                }

                    # Collect data from all microinverters
                    for micro_station_id, microinverter_data in microinverters.items():
                        if station_id == micro_station_id:
                            for micro_data in microinverter_data:
                                _LOGGER.debug("Updating data for microinverter %s in station %s", micro_data['id'], station_id)
                                
                                # Get real-time data from microinverter
                                real_time_micro_data = await api.get_real_time_data_microinverter(station_id, micro_data['id'])

                                data[micro_data['id']] = {
                                    "real_time_data": real_time_micro_data
                                }
                
                _LOGGER.debug("=== Coordinator data update completed ===")

                return data
        except Exception as e:
            _LOGGER.error("Error updating data: %s", e)
            raise UpdateFailed(f"Error updating data: {e}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store API, stations in hass data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "stations": stations,
        "dtus": dtus,
        "microinverters": microinverters,
        "store": store,
        "stored_data": stored_data
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for config entry changes
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id) 