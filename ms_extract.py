#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gets historical weather data from Meteostat for given locations."""

from meteostat import Stations, Hourly
from datetime import datetime, timedelta
import pandas as pd


def get_nearest_stations(lat, lon, num_stations=1):
    """
    Retrieves the nearest weather stations to the given latitude and longitude.
    """
    stations = Stations().nearby(lat, lon).fetch(num_stations)
    return stations

def get_hourly_weather(station_ids, stations_info, previous_days=1, timezone='UTC'):
    """
    Retrieves hourly weather data for the last 30 days from the given station(s),
    including station name, latitude, and longitude.
    
    Args:
        station_ids: List of station IDs to fetch data from
        stations_info: DataFrame with station information
        previous_days: Number of days of historical data to retrieve
        timezone: Target timezone for the datetime index (default: 'UTC')
    """
    end = datetime.now()
    start = end - timedelta(days=previous_days)

    data_frames = []
    
    for station_id in station_ids:
        # Fetch only observation data (model=False excludes model/forecast data)
        data = Hourly(station_id, start, end, model=False).fetch()
        
        if not data.empty:
            # Ensure the index is timezone-aware (Meteostat returns UTC)
            if data.index.tz is None:
                data.index = data.index.tz_localize('UTC')
            
            # Convert to the selected timezone if not UTC/GMT
            # Note: 'GMT' and 'UTC' are effectively the same
            if timezone not in ['UTC', 'GMT']:
                try:
                    data.index = data.index.tz_convert(timezone)
                except Exception as e:
                    # Keep as UTC if conversion fails
                    pass
            
            station_info = stations_info.loc[station_id]
            data["station_name"] = station_info["name"]
            data["station_lat"] = station_info["latitude"]
            data["station_lon"] = station_info["longitude"]
            data["station_id"] = station_id  # Add station ID to data
            data_frames.append(data)
    
    if data_frames:
        return pd.concat(data_frames)
    return pd.DataFrame()  # Return empty DataFrame if no data found

def main(locations, previous_days=1, timezone='UTC'):
    """
    Retrieves hourly weather data for one or more locations.
    
    Args:
        locations: List of (lat, lon) tuples
        previous_days: Number of days of historical data to retrieve
        timezone: Target timezone for the datetime index (default: 'UTC')
    """
    all_data = []

    for lat, lon in locations:
        stations = get_nearest_stations(lat, lon)
        
        if stations.empty:
            continue
        
        station_ids = stations.index.tolist()

        # Retrieve weather data
        weather_data = get_hourly_weather(station_ids, stations, previous_days, timezone)
        if not weather_data.empty:
            all_data.append(weather_data)

    if all_data:
        final_data = pd.concat(all_data)
        return final_data
    else:
        return None

if __name__ == "__main__":
    # Example: Single location
    locations = [( -33.8688, 151.2093)]  # Sydney, Australia
    
    # Example: Multiple locations
    # locations = [( -33.8688, 151.2093), (-37.8136, 144.9631)]  # Sydney & Melbourne

    weather_data = main(locations)
