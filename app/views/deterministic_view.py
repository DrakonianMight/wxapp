# ========================================
# File: views/deterministic_view.py
"""Deterministic forecast view"""
import streamlit as st
import pandas as pd
from typing import List, Dict
from collections import OrderedDict
from utils.plotting import create_deterministic_plot
from config import DETERMINISTIC_MODEL_COLORS
import ms_extract

def check_nearby_station(lat: float, lon: float, max_distance_km: float = 1.0):
    """Check if there's a meteostat station within max_distance_km"""
    try:
        from meteostat import Stations
        # Convert km to meters for meteostat's radius parameter
        radius_meters = max_distance_km * 1000
        stations = Stations().nearby(lat, lon, radius=radius_meters).fetch(1)
        print(stations)
        if not stations.empty:
            station = stations.iloc[0]
            # Get distance from station data (in meters if available)
            distance = station.get('distance', 0) / 1000.0 if 'distance' in station else max_distance_km
            return True, station, distance
        return False, None, None
    except Exception as e:
        st.warning(f"Could not check for nearby stations: {e}")
        return False, None, None

def render_deterministic_view(
    data_source,
    lat: float,
    lon: float,
    site: str,
    custom_hourly_params: List[str],
    base_hourly_params: List[str],
    daily_params: List[str],
    obs_distance_km: float = 2.0,
    timezone: str = 'UTC'
):
    """Render the deterministic forecast view"""
    
    # Combine base and custom parameters
    hourly_params = base_hourly_params + [p for p in custom_hourly_params if p not in base_hourly_params]
    
    # Build variables map
    all_variables_map = OrderedDict()
    
    for var in hourly_params:
        label = f'Hourly: {var}'
        if var in custom_hourly_params:
            label += ' (Custom)'
        all_variables_map[var] = {'label': label, 'type': 'hourly', 'is_obs_available': False}

    for var in daily_params:
        all_variables_map[var] = {'label': 'Daily: ' + var, 'type': 'daily', 'is_obs_available': False}

    # Variable selection
    variable_options = list(all_variables_map.keys())
    selected_columns = st.multiselect(
        'Select Weather Variables',
        options=variable_options,
        format_func=lambda x: all_variables_map[x]['label'],
        default=[], 
        key='det_column_select'
    )
    
    # Model selection
    available_models = data_source.get_available_models('deterministic')
    selected_models = st.multiselect(
        'Select Forecast Models',
        options=available_models,
        default=[], 
        key='det_model_select'
    )
    
    if not selected_columns:
        st.info("Please select at least one variable to plot.")
        return
    
    if not selected_models:
        st.warning("Please select at least one model to plot.")
        return
    
    # Get data
    first_selected_var = selected_columns[0]
    selected_data_type = all_variables_map[first_selected_var]['type']
    variables_to_fetch = [
        var for var in selected_columns 
        if all_variables_map[var]['type'] == selected_data_type
    ]
    
    # Fetch data (cached)
    @st.cache_data(ttl=3600)
    def get_cached_data(lat, lon, site, variables, data_type, models, source_name):
        return data_source.get_deterministic_data(lat, lon, site, variables, data_type, models)
    
    with st.spinner(f"Fetching deterministic forecast for {site}..."):
        df_forecast = get_cached_data(
            lat, lon, site, variables_to_fetch, selected_data_type, selected_models, data_source.name
        )
    
    if df_forecast.empty:
        st.warning("No forecast data retrieved.")
        return
    
    # Check for nearby observation station
    has_nearby_station, station_info, distance = check_nearby_station(lat, lon, max_distance_km=obs_distance_km)
    df_obs = None
    print(has_nearby_station, station_info, distance)
    if has_nearby_station:
        st.info(f"📍 Observation station '{station_info['name']}' found {distance:.2f} km away")
        
        # Fetch observation data
        from data_sources.meteostat_obs import MeteostatObsDataSource
        obs_source = MeteostatObsDataSource()
        
        @st.cache_data(ttl=3600)
        def get_cached_obs_data(lat, lon, site, variables, data_type, previous_days):
            return obs_source.get_deterministic_data(lat, lon, site, variables, data_type, [], previous_days)
        
        with st.spinner("Fetching observation data..."):
            df_obs = get_cached_obs_data(
                lat, lon, site, variables_to_fetch, selected_data_type, previous_days=1
            )
            
        if df_obs is not None and not df_obs.empty:
            st.success(f"✓ Loaded {len(df_obs)} observation records")
        else:
            st.warning("No observation data available for this location/timeframe")
    
    # Create plot
    st.subheader(f'Deterministic Forecast for {site}')
    fig = create_deterministic_plot(
        df_forecast,
        selected_columns,
        all_variables_map,
        DETERMINISTIC_MODEL_COLORS,
        selected_data_type,
        df_obs=df_obs,
        timezone=timezone
    )
    st.plotly_chart(fig, use_container_width=True)
    
    caption = f"Data type: **{selected_data_type.capitalize()}** | Source: **{data_source.name}**"
    if df_obs is not None and not df_obs.empty:
        caption += f" | Observations: **Meteostat ({station_info['name']})**"
    st.caption(caption)
