# ========================================
# File: views/ensemble_view.py
"""Ensemble/Probabilistic forecast view"""
import streamlit as st
import pandas as pd
from typing import List, Dict
from collections import OrderedDict
from utils.plotting import create_ensemble_plot, create_exceedance_plot
from utils.probability import calculate_exceedance_probability
from config import ENSEMBLE_MODEL_COLORS
import plotly.graph_objects as go
import ms_extract

def check_nearby_station(lat: float, lon: float, max_distance_km: float = 1.0):
    """Check if there's a meteostat station within max_distance_km"""
    try:
        from meteostat import Stations
        # Convert km to meters for meteostat's radius parameter
        radius_meters = max_distance_km * 1000
        stations = Stations().nearby(lat, lon, radius=radius_meters).fetch(1)
        if not stations.empty:
            station = stations.iloc[0]
            # Get distance from station data (in meters if available)
            distance = station.get('distance', 0) / 1000.0 if 'distance' in station else max_distance_km
            return True, station, distance
        return False, None, None
    except Exception as e:
        st.warning(f"Could not check for nearby stations: {e}")
        return False, None, None

def render_ensemble_view(
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
    """Render the ensemble/probabilistic forecast view"""
    
    if not data_source.supports_ensemble:
        st.warning(f"The {data_source.name} data source does not support ensemble forecasts.")
        return
    
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

    # Create two columns for selections
    col1, col2 = st.columns(2)
    
    with col1:
        # Variable selection (single for ensemble)
        variable_options = list(all_variables_map.keys())
        selected_variable = st.selectbox(
            'Select Weather Variable',
            options=variable_options,
            format_func=lambda x: all_variables_map[x]['label'],
            key='ens_variable_select'
        )
    
    with col2:
        # Model selection
        available_models = data_source.get_available_models('ensemble')
        selected_models = st.multiselect(
            'Select Ensemble Models',
            options=available_models,
            default=[], 
            key='ens_model_select'
        )
    
    # Display options
    st.markdown("### Display Options")
    display_col1, display_col2 = st.columns(2)
    
    with display_col1:
        show_percentiles = st.checkbox("Show Percentile Bands", value=True, key='show_percentiles')
    
    with display_col2:
        show_members = st.checkbox("Show Individual Members", value=False, key='show_members')
    
    # Threshold analysis section
    st.markdown("### Threshold Analysis")
    enable_threshold = st.checkbox("Enable Exceedance Probability Analysis", value=False, key='enable_threshold')
    
    thresholds = []
    if enable_threshold:
        threshold_col1, threshold_col2, threshold_col3 = st.columns(3)
        
        with threshold_col1:
            threshold_1 = st.number_input(
                "Threshold 1",
                value=20.0,
                step=0.1,
                key='threshold_1'
            )
            if st.checkbox("Use Threshold 1", value=True, key='use_t1'):
                thresholds.append(threshold_1)
        
        with threshold_col2:
            threshold_2 = st.number_input(
                "Threshold 2",
                value=25.0,
                step=0.1,
                key='threshold_2'
            )
            if st.checkbox("Use Threshold 2", value=False, key='use_t2'):
                thresholds.append(threshold_2)
        
        with threshold_col3:
            threshold_3 = st.number_input(
                "Threshold 3",
                value=30.0,
                step=0.1,
                key='threshold_3'
            )
            if st.checkbox("Use Threshold 3", value=False, key='use_t3'):
                thresholds.append(threshold_3)
    
    if not selected_models:
        st.warning("Please select at least one ensemble model.")
        return
    
    # Get data
    selected_data_type = all_variables_map[selected_variable]['type']
    
    # Fetch data (cached)
    @st.cache_data(ttl=3600)
    def get_cached_ensemble_data(lat, lon, site, variables, data_type, models, source_name):
        return data_source.get_ensemble_data(lat, lon, site, variables, data_type, models)
    
    with st.spinner(f"Fetching ensemble forecast for {site}..."):
        df_forecast = get_cached_ensemble_data(
            lat, lon, site, [selected_variable], selected_data_type, selected_models, data_source.name
        )
    
    if df_forecast.empty:
        st.warning("No ensemble forecast data retrieved.")
        return
    
    # Check for nearby observation station
    has_nearby_station, station_info, distance = check_nearby_station(lat, lon, max_distance_km=obs_distance_km)
    df_obs = None
    
    if has_nearby_station and selected_data_type == 'hourly':
        st.info(f"📍 Observation station '{station_info['name']}' found {distance:.2f} km away")
        
        # Fetch observation data
        from data_sources.meteostat_obs import MeteostatObsDataSource
        obs_source = MeteostatObsDataSource()
        
        @st.cache_data(ttl=3600)
        def get_cached_obs_data(lat, lon, site, variables, data_type, previous_days):
            return obs_source.get_deterministic_data(lat, lon, site, variables, data_type, [], previous_days)
        
        with st.spinner("Fetching observation data..."):
            df_obs = get_cached_obs_data(
                lat, lon, site, [selected_variable], selected_data_type, previous_days=7
            )
            
        if df_obs is not None and not df_obs.empty:
            st.success(f"✓ Loaded {len(df_obs)} observation records")
        else:
            st.warning("No observation data available for this location/timeframe")
    
    # Create ensemble plot
    st.subheader(f'Ensemble Forecast for {site}')
    fig = create_ensemble_plot(
        df_forecast,
        selected_variable,
        selected_models,
        ENSEMBLE_MODEL_COLORS,
        show_percentiles=show_percentiles,
        show_members=show_members,
        df_obs=df_obs,
        timezone=timezone
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Create exceedance probability plot if enabled
    if enable_threshold and thresholds:
        st.subheader('Exceedance Probability Analysis')
        
        # Calculate exceedance probabilities
        df_exceedance = pd.DataFrame(index=df_forecast.index)
        for threshold in thresholds:
            df_exceed = calculate_exceedance_probability(
                df_forecast, selected_variable, threshold, selected_models
            )
            df_exceedance = pd.concat([df_exceedance, df_exceed], axis=1)
        
        fig_exceed = create_exceedance_plot(
            df_exceedance,
            selected_variable,
            thresholds,
            selected_models,
            ENSEMBLE_MODEL_COLORS
        )
        st.plotly_chart(fig_exceed, use_container_width=True)
        
        st.caption(f"Showing probability (%) that {selected_variable} exceeds the specified thresholds")
    
    caption = f"Data type: **{selected_data_type.capitalize()}** | Source: **{data_source.name}**"
    if df_obs is not None and not df_obs.empty:
        caption += f" | Observations: **Meteostat ({station_info['name']})**"
    st.caption(caption)
