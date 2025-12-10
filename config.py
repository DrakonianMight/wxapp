# File: config.py
"""Configuration constants for the weather app"""

DEFAULT_LAT = -27.4705  # Brisbane
DEFAULT_LON = 153.0260

# Static BASE parameters for forecast data
BASE_HOURLY_PARAMS = [
    'shortwave_radiation', 
    'temperature_2m', 
    'cloud_cover',
    'wind_speed_10m', 
    'wind_direction_10m', 
    'wind_gusts_10m',
    'relative_humidity_2m',
    'dewpoint_2m'
]

DAILY_PARAMS = ['temperature_2m_max', 'temperature_2m_min']

# Color mapping for forecast models
DETERMINISTIC_MODEL_COLORS = {
    'ecmwf_ifs': '#FF5733', 
    'ecmwf_aifs025': '#C70039', 
    'bom_access_global': '#33FF57', 
    'gfs_global': '#AAAAAA', 
    'cma_grapes_global': '#8A2BE2', 
    'ukmo_global_deterministic_10km': '#00FFFF'
}

ENSEMBLE_MODEL_COLORS = {
    'ecmwf_ifs_ensemble': '#FF8C42',
    'gfs_ensemble': '#B8B8B8',
    'bom_access_global_ensemble': '#5FFF8C'
}

# Y-axis titles for variables
YAXIS_TITLES = {
    'shortwave_radiation': 'Shortwave Radiation (W/m²)',
    'wind_speed_10m': 'Wind Speed at 10m (m/s)',
    'wind_direction_10m': 'Wind Direction at 10m (°)',
    'wind_gusts_10m': 'Wind Gusts at 10m (m/s)',
    'temperature_2m': 'Temperature at 2m (°C)',
    'cloud_cover': 'Cloud Cover (%)',
    'relative_humidity_2m': 'Relative Humidity at 2m (%)',
    'dewpoint_2m': 'Dewpoint Temperature at 2m (°C)',
    'temperature_2m_max': 'Max Temperature at 2m (°C)',
    'temperature_2m_min': 'Min Temperature at 2m (°C)',
    'surface_pressure': 'Surface Pressure (hPa)',
    'precipitation': 'Precipitation (mm)',
}
