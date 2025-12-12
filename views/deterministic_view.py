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
    data_sources: Dict,
    lat: float,
    lon: float,
    site: str,
    custom_hourly_params: List[str],
    base_hourly_params: List[str],
    daily_params: List[str],
    obs_distance_km: float = 2.0,
    timezone: str = 'UTC'
):
    """
    Render the deterministic forecast view with support for multiple data sources
    
    Args:
        data_sources: Dictionary of {source_name: DataSource instance}
        lat, lon, site: Location information
        custom_hourly_params, base_hourly_params, daily_params: Variable lists
        obs_distance_km: Distance for observation search
        timezone: Timezone for display
    """
    
    # Collect variables from all selected data sources
    all_data_source_vars = []
    data_source_var_map = {}  # Track which source provides which variables
    
    for source_name, data_source in data_sources.items():
        try:
            source_vars = data_source.get_available_variables('hourly')
            all_data_source_vars.extend(source_vars)
            # Track source for each variable
            for var in source_vars:
                if var not in data_source_var_map:
                    data_source_var_map[var] = []
                data_source_var_map[var].append(source_name)
        except Exception as e:
            # If data source doesn't implement this or fails, continue
            pass
    
    # Remove duplicates while preserving order
    data_source_vars = list(OrderedDict.fromkeys(all_data_source_vars))
    
    # Combine base, custom, and data source parameters
    all_params = base_hourly_params + custom_hourly_params + data_source_vars
    hourly_params = list(OrderedDict.fromkeys([p for p in all_params if p]))
    
    # Build variables map with source information
    all_variables_map = OrderedDict()
    
    for var in hourly_params:
        # Determine label based on source
        if var in data_source_vars and var not in base_hourly_params and var not in custom_hourly_params:
            # Show which data sources provide this variable
            sources = data_source_var_map.get(var, [])
            if len(sources) == 1:
                label = f'Hourly: {var} (from {sources[0]})'
            else:
                label = f'Hourly: {var} (from {len(sources)} sources)'
        elif var in custom_hourly_params:
            label = f'Hourly: {var} (Custom)'
        else:
            label = f'Hourly: {var}'
        all_variables_map[var] = {'label': label, 'type': 'hourly', 'is_obs_available': False}

    for var in daily_params:
        all_variables_map[var] = {'label': 'Daily: ' + var, 'type': 'daily', 'is_obs_available': False}

    # Collect all available models from all data sources
    all_available_models = {}  # {model_key: (source_name, data_source, model)}
    
    for source_name, data_source in data_sources.items():
        models = data_source.get_available_models('deterministic')
        for model in models:
            model_key = f"{source_name}::{model}"
            all_available_models[model_key] = (source_name, data_source, model)
    
    # Simple model selection
    def format_model_display(model_key):
        source_name, _, model = all_available_models[model_key]
        return f"{model} ({source_name})"
    
    selected_model_keys = st.multiselect(
        'Select Models',
        options=list(all_available_models.keys()),
        default=[], 
        key='det_model_select',
        format_func=format_model_display
    )
    
    if not selected_model_keys:
        st.info("Please select at least one model to continue.")
        return
    
    # Simple variable selection - show all variables
    selected_variables = st.multiselect(
        'Select Variables',
        options=list(all_variables_map.keys()),
        format_func=lambda x: all_variables_map[x]['label'],
        default=[],
        key='det_var_select'
    )
    
    if not selected_variables:
        st.info("Please select at least one variable to continue.")
        return
    
    # Determine data type from first variable
    first_var = selected_variables[0]
    common_data_type = all_variables_map[first_var]['type']
    
    # Build model-variable mapping (all models get same variables)
    model_variable_selections = {}
    for model_key in selected_model_keys:
        source_name, data_source, model = all_available_models[model_key]
        
        # Get available variables for this model
        try:
            model_vars = data_source.get_model_specific_variables(model, 'deterministic')
        except Exception:
            try:
                model_vars = data_source.get_available_variables('hourly')
            except Exception:
                model_vars = []
        
        # Filter selected variables to those available for this model
        available_vars = [v for v in selected_variables if v in model_vars]
        model_variable_selections[model_key] = available_vars
    
    # Fetch data from each model with its specific variables
    all_forecast_dfs = []
    all_requested_variables = set(selected_variables)
    
    with st.spinner(f"Fetching deterministic forecasts for {site}..."):
        # Fetch from each model individually with its filtered variables
        for model_key, vars_to_fetch in model_variable_selections.items():
            if not vars_to_fetch:
                continue  # Skip models with no compatible variables
            
            source_name, data_source, model = all_available_models[model_key]
            
            # Filter to only same data type as the first variable
            vars_to_fetch = [v for v in vars_to_fetch if all_variables_map[v]['type'] == common_data_type]
            
            if not vars_to_fetch:
                continue
            
            try:
                df = data_source.get_deterministic_data(
                    lat, lon, site, vars_to_fetch, common_data_type, [model]
                )
                if not df.empty:
                    all_forecast_dfs.append(df)
            except Exception:
                pass  # Silently skip failed fetches
    
    # Combine all forecast dataframes
    if not all_forecast_dfs:
        st.warning("No forecast data retrieved.")
        return
    
    df_forecast = pd.concat(all_forecast_dfs, ignore_index=True)
    
    if df_forecast.empty:
        st.warning("No forecast data retrieved.")
        return
    
    # Build selected_columns list from all requested variables
    selected_columns = list(all_requested_variables)
    
    # Check for nearby observation station
    has_nearby_station, station_info, distance = check_nearby_station(lat, lon, max_distance_km=obs_distance_km)
    df_obs = None
    if has_nearby_station:
        st.info(f"📍 Observation station '{station_info['name']}' found {distance:.2f} km away")
        
        # Fetch observation data
        from data_sources.meteostat_obs import MeteostatObsDataSource
        obs_source = MeteostatObsDataSource()
        
        @st.cache_data(ttl=3600)
        def get_cached_obs_data(lat, lon, site, variables, data_type, previous_days, timezone):
            return obs_source.get_deterministic_data(lat, lon, site, variables, data_type, [], previous_days, timezone)
        
        # Only fetch observations for variables that meteostat supports
        obs_variables = [v for v in selected_columns if v in obs_source.get_available_variables(common_data_type)]
        
        if obs_variables:
            with st.spinner("Fetching observation data..."):
                df_obs = get_cached_obs_data(
                    lat, lon, site, obs_variables, common_data_type, previous_days=2, timezone=timezone
                )
                
            if df_obs is not None and not df_obs.empty:
                st.success(f"✓ Loaded {len(df_obs)} observation records")
            else:
                st.info("No observation data available for this location/timeframe")
        else:
            st.info("Selected variables not available from observation source")
    
    # Create plot
    st.subheader(f'Deterministic Forecast for {site}')
    fig = create_deterministic_plot(
        df_forecast,
        selected_columns,
        all_variables_map,
        DETERMINISTIC_MODEL_COLORS,
        common_data_type,
        df_obs=df_obs,
        timezone=timezone
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Build caption showing all sources used
    sources_used = set()
    for model_key in model_variable_selections.keys():
        if model_variable_selections[model_key]:  # Has variables
            source_name, _, _ = all_available_models[model_key]
            sources_used.add(source_name)
    
    caption = f"Data type: **{common_data_type.capitalize()}** | Sources: **{', '.join(sources_used)}**"
    if df_obs is not None and not df_obs.empty:
        caption += f" | Observations: **Meteostat ({station_info['name']})**"
    st.caption(caption)
