"""API client for Hoymiles Cloud."""
import asyncio
import logging
import time
import hashlib
import json
from typing import Any, Dict, List, Optional

import aiohttp

from .const import (
    API_AUTH_URL,
    API_STATIONS_URL,
    API_REAL_TIME_DATA_URL,
    API_DTU_URL,
    API_MICROINVERTERS_URL,
    API_MICRO_DETAIL_URL,
    API_DTU_DETAIL_URL
)

_LOGGER = logging.getLogger(__name__)


class HoymilesAPI:
    """Hoymiles Cloud API client."""

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password  # Store password directly - will be hashed when needed
        self._token = None
        self._token_expires_at = 0
        self._token_valid_time = 7200  # Default token validity in seconds

    def is_token_expired(self) -> bool:
        """Check if the token is expired."""
        return time.time() >= self._token_expires_at

    async def authenticate(self) -> bool:
        """Authenticate with the Hoymiles API."""
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            # Based on testing, MD5 hashing of the password is sufficient for authentication
            md5_password = hashlib.md5(self._password.encode()).hexdigest()
            
            # If MD5 doesn't work, you can try the combined hash format from HAR analysis:
            # second_part = "detsiHMyw54xS3UBlJCzLHzPgKv6VTDCrt3QxlyUigg="
            # hashed_password = f"{md5_password}.{second_part}"
            
            data = {
                "user_name": self._username,
                "password": md5_password,
            }
            
            async with self._session.post(
                API_AUTH_URL, headers=headers, json=data
            ) as response:
                resp = await response.json()
                
                if resp.get("status") == "0" and resp.get("message") == "success":
                    self._token = resp.get("data", {}).get("token")
                    self._token_expires_at = time.time() + self._token_valid_time
                    return True
                else:
                    _LOGGER.error(
                        "Authentication failed: %s - %s", 
                        resp.get("status"), 
                        resp.get("message")
                    )
                    return False
        except Exception as e:
            _LOGGER.error("Error during authentication: %s", e)
            raise

#############################################################################################
# Functions to geht Stations, DTUs, Microinverters and Inverters
#############################################################################################

    async def get_stations(self) -> Dict[str, str]:
        """Get all stations for the authenticated user."""
        if not self._token:
            _LOGGER.debug("No token available, authenticating first")
            await self.authenticate()
            
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._token,
        }
        
        data = {
            "page_size": 10,
            "page_num": 1,
        }
        
        try:
            _LOGGER.debug("Sending request to get stations with token: %s...", self._token[:20] if self._token else "None")
            async with self._session.post(
                API_STATIONS_URL, headers=headers, json=data
            ) as response:
                resp_text = await response.text()
                _LOGGER.debug("Full stations response: %s", resp_text)
                
                resp = json.loads(resp_text)
                
                if resp.get("status") == "0" and resp.get("message") == "success":
                    stations = {}
                    stations_data = resp.get("data", {}).get("list", [])
                    _LOGGER.debug("Raw stations data: %s", stations_data)
                    
                    if not stations_data:
                        _LOGGER.warning("API returned success but stations list is empty")
                        
                    for station in stations_data:
                        station_id = str(station.get("id"))
                        station_name = station.get("name")
                        _LOGGER.debug("Adding station: %s - %s", station_id, station_name)
                        stations[station_id] = station_name
                        
                    _LOGGER.debug("Returning stations dictionary: %s", stations)
                    return stations
                else:
                    _LOGGER.error(
                        "Failed to get stations: %s - %s", 
                        resp.get("status"), 
                        resp.get("message")
                    )
                    return {}
        except Exception as e:
            _LOGGER.error("Error getting stations: %s", e)
            raise

    async def get_dtus(self, station_id: str) -> List[any]:
        """Get all dtus for the authenticated user."""
        if not self._token:
            _LOGGER.debug("No token available, authenticating first")
            await self.authenticate()
            
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._token,
        }
        
        data = {
            "sid": int(station_id),
            "page_size": 1000,
            "page_num": 1,
            "show_warn": 0
        }

        try:
            _LOGGER.debug("Sending request to get dtus with token: %s...", self._token[:20] if self._token else "None")
            async with self._session.post(
                API_DTU_URL, headers=headers, json=data
            ) as response:
                resp_text = await response.text()
                _LOGGER.debug("Full dtus response: %s", resp_text)
                
                resp = json.loads(resp_text)
                
                if resp.get("status") == "0" and resp.get("message") == "success":
                    dtus = []
                    dtus_data = resp.get("data", {}).get("list", [])
                    _LOGGER.debug("Raw dtus data: %s", dtus_data)
                    
                    if not dtus_data:
                        _LOGGER.warning("API returned success but dtus list is empty")
                        
                    for dtu in dtus_data:
                        dtu_id = str(dtu.get("id"))
                        dtu_name = dtu.get("model_no")
                        _LOGGER.debug("Adding dtus: %s - %s", dtu_id, dtu_name)
                        dtus.append({
                            'id': dtu_id,
                            'name': dtu_name
                        })
                        
                    _LOGGER.debug("Returning dtus dictionary: %s", dtus)
                    return dtus
                else:
                    _LOGGER.error(
                        "Failed to get dtus: %s - %s", 
                        resp.get("status"), 
                        resp.get("message")
                    )
                    return {}
        except Exception as e:
            _LOGGER.error("Error getting dtus: %s", e)
            raise

    async def get_microinverters(self, station_id: str) -> List[any]:
        """Get all microinverters for the authenticated user."""
        if not self._token:
            _LOGGER.debug("No token available, authenticating first")
            await self.authenticate()
            
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._token,
        }
        
        data = {
            "sid": int(station_id),
            "page_size": 1000,
            "page_num": 1,
            "show_warn": 0
        }

        try:
            _LOGGER.debug("Sending request to get microinverters with token: %s...", self._token[:20] if self._token else "None")
            async with self._session.post(
                API_MICROINVERTERS_URL, headers=headers, json=data
            ) as response:
                resp_text = await response.text()
                _LOGGER.debug("Full microinverters response: %s", resp_text)
                
                resp = json.loads(resp_text)
                
                if resp.get("status") == "0" and resp.get("message") == "success":
                    microinverters = []
                    microinverters_data = resp.get("data", {}).get("list", [])
                    _LOGGER.debug("Raw microinverters data: %s", microinverters_data)
                    
                    if not microinverters_data:
                        _LOGGER.warning("API returned success but microinverters list is empty")
                        
                    for microinverter in microinverters_data:
                        microinverter_id = str(microinverter.get("id"))
                        microinverter_name = microinverter.get("init_hard_no")
                        _LOGGER.debug("Adding microinverters: %s - %s", microinverter_id, microinverter_name)
                        microinverters.append({
                            'id': microinverter_id,
                            'name': microinverter_name
                        })
                        
                    _LOGGER.debug("Returning microinverters dictionary: %s", microinverters)
                    return microinverters
                else:
                    _LOGGER.error(
                        "Failed to get microinverters: %s - %s", 
                        resp.get("status"), 
                        resp.get("message")
                    )
                    return {}
        except Exception as e:
            _LOGGER.error("Error getting microinverters: %s", e)
            raise

#############################################################################################
# Functions for REAL_TIME_DATA Stations, DTUs and Microinverters
#############################################################################################

    async def get_real_time_data_station(self, station_id: str) -> Dict[str, Any]:
        """Get real-time data for a station."""
        if not self._token:
            await self.authenticate()
            
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._token,
        }
        
        data = {
            "sid": int(station_id),
        }
        
        try:
            async with self._session.post(
                API_REAL_TIME_DATA_URL, headers=headers, json=data
            ) as response:
                # Log raw text to better diagnose field availability across accounts/devices
                resp_text = await response.text()
                try:
                    resp = json.loads(resp_text)
                except json.JSONDecodeError:
                    _LOGGER.debug("Real-time station %s data non-JSON response: %s", station_id, resp_text)
                    raise
                _LOGGER.debug("Real-time station %s data response: %s", station_id, json.dumps(resp, ensure_ascii=False))
                
                if resp.get("status") == "0" and resp.get("message") == "success":
                    return resp.get("data", {})
                else:
                    _LOGGER.error(
                        "Failed to get real-time station %s data: %s - %s",
                        station_id,
                        resp.get("status"), 
                        resp.get("message")
                    )
                    return {}
        except Exception as e:
            _LOGGER.error("Error getting real-time station %s data: %s", station_id, e)
            raise

    async def get_real_time_data_dtu(self, station_id: str, dtu_id: str) -> Dict[str, Any]:
        """Get real-time dtu data for a station."""
        if not self._token:
            await self.authenticate()
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._token,
        }
        
        data = {
            "id": int(dtu_id),
            "sid": int(station_id),
        }
        
        # Initial data for the dtu
        dtu_data = {}
        
        try:
            async with self._session.post(
                API_DTU_DETAIL_URL, headers=headers, json=data
            ) as response:
                # Log raw text to better diagnose field availability across accounts/devices
                resp_text = await response.text()
                try:
                    resp = json.loads(resp_text)
                except json.JSONDecodeError:
                    _LOGGER.debug("Real-time dtu %s data non-JSON response: %s", dtu_id, resp_text)
                    raise
                _LOGGER.debug("Real-time dtu %s data response: %s", dtu_id, json.dumps(resp, ensure_ascii=False))
                
                if resp.get("status") == "0" and resp.get("message") == "success":
                    dtu_data = resp.get("data", {})
                
                else:
                    _LOGGER.error(
                        "Failed to get real-time dtu %s data: %s - %s",
                        dtu_id,
                        resp.get("status"), 
                        resp.get("message")
                    )
                    return dtu_data

        except Exception as e:
            _LOGGER.error("Error getting real-time dtu %s data: %s", dtu_id, e)
            raise
        
        # Get the missing DTU Datas from another URL
        data = {
            "sid": int(station_id),
            "page_size": 1000,
            "page_num": 1,
            "show_warn": 0
        }
        
        try:
            async with self._session.post(
                API_DTU_URL, headers=headers, json=data
            ) as response:
                # Log raw text to better diagnose field availability across accounts/devices
                resp_text = await response.text()
                try:
                    resp = json.loads(resp_text)
                except json.JSONDecodeError:
                    _LOGGER.debug("Real-time dtu %s extend data non-JSON response: %s", dtu_id, resp_text)
                    raise
                _LOGGER.debug("Real-time dtu extend data response: %s", json.dumps(resp, ensure_ascii=False))
                
                if resp.get("status") == "0" and resp.get("message") == "success":
                    dtus_data_list = resp.get("data", {}).get("list", [])
                    
                    for dtu_single_data in dtus_data_list:
                        if dtu_id == str(dtu_single_data.get("id")):
                            dtu_data["warn_data"] = dtu_single_data.get("warn_data")
                            dtu_data["model_no"] = dtu_single_data.get("model_no")
                
                else:
                    _LOGGER.error(
                        "Failed to get real-time dtu %s extend data: %s - %s",
                        dtu_id,
                        resp.get("status"), 
                        resp.get("message")
                    )
                    return dtu_data
        
        except Exception as e:
            _LOGGER.error("Error getting real-time dtu %s extend data: %s", dtu_id, e)
            raise
        
        return dtu_data

    async def get_real_time_data_microinverter(self, station_id: str, microinverter_id: str) -> Dict[str, Any]:
        """Get real-time data for a microinverter."""
        if not self._token:
            await self.authenticate()
            
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._token,
        }
        
        data = {
            "id": int(microinverter_id),
            "sid": int(station_id),
        }
        
        try:
            async with self._session.post(
                API_MICRO_DETAIL_URL, headers=headers, json=data
            ) as response:
                # Log raw text to better diagnose field availability across accounts/devices
                resp_text = await response.text()
                try:
                    resp = json.loads(resp_text)
                except json.JSONDecodeError:
                    _LOGGER.debug("Real-time microinverter %s data non-JSON response: %s", microinverter_id, resp_text)
                    raise
                _LOGGER.debug("Real-time microinverter %s data response: %s", microinverter_id, json.dumps(resp, ensure_ascii=False))
                
                if resp.get("status") == "0" and resp.get("message") == "success":
                    return resp.get("data", {})
                else:
                    _LOGGER.error(
                        "Failed to get real-time microinverter %s data: %s - %s",
                        microinverter_id,
                        resp.get("status"), 
                        resp.get("message")
                    )
                    return {}
        except Exception as e:
            _LOGGER.error("Error getting real-time microinverter %s data: %s", microinverter_id, e)
            raise
