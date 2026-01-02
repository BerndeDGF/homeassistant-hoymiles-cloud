"""Constants for the Hoymiles Cloud integration."""

DOMAIN = "hoymiles_cloud"

# Storage constants
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_data"

# API Constants
API_BASE_URL = "https://neapi.hoymiles.com"
API_AUTH_URL = f"{API_BASE_URL}/iam/pub/0/auth/login"
API_STATIONS_URL = f"{API_BASE_URL}/pvm/api/0/station/select_by_page"
API_DTU_URL = f"{API_BASE_URL}/pvm/api/0/dev/dtu/select_by_page"
API_MICROINVERTERS_URL = f"{API_BASE_URL}/pvm/api/0/dev/micro/select_by_station"
API_REAL_TIME_DATA_URL = f"{API_BASE_URL}/pvm-data/api/0/station/data/count_station_real_data"
API_MICRO_DETAIL_URL = f"{API_BASE_URL}/pvm/api/0/dev/micro/find"
API_DTU_DETAIL_URL = f"{API_BASE_URL}/pvm/api/0/dev/dtu/find"

# Default settings
DEFAULT_SCAN_INTERVAL = 60  # seconds

# Configuration
CONF_STATION_ID = "station_id"

# Sensor types
SENSOR_TYPE_POWER = "power"
SENSOR_TYPE_ENERGY = "energy"
SENSOR_TYPE_SOC = "soc"
SENSOR_TYPE_GRID = "grid"
SENSOR_TYPE_LOAD = "load"

SETTING_TYPE_MODE = "mode"
SETTING_TYPE_RESERVE_SOC = "reserve_soc"

# Entity category
ENTITY_CATEGORY_DIAGNOSTIC = "diagnostic"
ENTITY_CATEGORY_CONFIG = "config"

# Units of measurement
POWER_WATT = "W"
ENERGY_WATT_HOUR = "Wh"
PERCENTAGE = "%" 