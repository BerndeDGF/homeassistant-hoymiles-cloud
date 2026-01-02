"""Select platform for Hoymiles Cloud Custom Mode settings."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import asyncio
import json

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN
)
from .hoymiles_api import HoymilesAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hoymiles Cloud custom mode select entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    stations = data["stations"]
    microinverters = data["microinverters"]
    dtus = data["dtus"]
    api = data["api"]
    
    entities = []
    
    async_add_entities(entities)
