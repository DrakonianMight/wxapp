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
    Render the ensemble/probabilistic forecast view with support for multiple data sources
    
    Args:
        data_sources: Dictionary of {source_name: DataSource instance}
        lat, lon, site: Location information
        custom_hourly_params, base_hourly_params, daily_params: Variable lists
        obs_distance_km: Distance for observation search
        timezone: Timezone for display
    """
    
    # Check if any selected source supports ensemble
    ensemble_sources = {name: ds for name, ds in data_sources.items() if ds.supports_ensemble}
    
    if not ensemble_sources:
        st.warning("None of the selected data sources support ensemble forecasts. Please select a data source with ensemble support (e.g., Open-Meteo or AWS API).")
        return
    
    # Collect variables from all ensemble-supporting data sources
    all_data_source_vars = []
    data_source_var_map = {}  # Track which source provides which variables
    
    for source_name, data_source in ensemble_sources.items():
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

    # Build model-to-variable and variable-to-model mappings
    # For each variable, track which models from which sources provide it
    variable_model_map = OrderedDict()  # {variable: [(source_name, data_source, model_name), ...]}
    model_variable_map = OrderedDict()  # {model_key: (source_name, data_source, model, [variables])}
    all_available_models = {}  # {model_key: (source_name, data_source, model)}
    
    for source_name, data_source in ensemble_sources.items():
        models = data_source.get_available_models('ensemble')
        for model in models:
            model_key = f"{source_name}::{model}"
            all_available_models[model_key] = (source_name, data_source, model)
            
            try:
                # Get variables for this model
                model_vars = data_source.get_model_specific_variables(model, 'ensemble')
                model_variable_map[model_key] = (source_name, data_source, model, model_vars)
                
                for var in model_vars:
                    if var not in variable_model_map:
                        variable_model_map[var] = []
                    variable_model_map[var].append((source_name, data_source, model))
            except Exception:
                # If can't get model-specific vars, try general variables
                try:
                    general_vars = data_source.get_available_variables('hourly')
                    model_variable_map[model_key] = (source_name, data_source, model, general_vars)
                    for var in general_vars:
                        if var not in variable_model_map:
                            variable_model_map[var] = []
                        variable_model_map[var].append((source_name, data_source, model))
                except Exception:
                    model_variable_map[model_key] = (source_name, data_source, model, [])
    
    # Create two columns for selections
    col1, col2 = st.columns(2)
    
    with col1:
        # Variable selection (multi-select)
        variable_options = [v for v in all_variables_map.keys() if v in variable_model_map]
        
        selected_variables = st.multiselect(
            'Select Weather Variables',
            options=variable_options,
            default=[],
            format_func=lambda x: all_variables_map[x]['label'],
            key='ens_variable_multiselect',
            help="Select multiple variables to plot from the selected models."
        )
    
    with col2:
        # Model selection with variable info
        def format_model_display(model_key):
            source_name, _, model, variables = model_variable_map[model_key]
            var_count = len(variables)
            return f"{model} ({source_name}) - {var_count} vars"
        
        selected_model_keys = st.multiselect(
            'Select Ensemble Models',
            options=list(all_available_models.keys()),
            default=[],
            format_func=format_model_display,
            key='ens_model_multiselect',
            help=f"{len(all_available_models)} ensemble model(s) available. Each shows variable count."
        )
    
    # Show detailed model information with variables
    if selected_model_keys or selected_variables:
        with st.expander(f"📋 Variable-Model Compatibility Matrix", expanded=True):
            if selected_model_keys and selected_variables:
                # Show which selected models support which selected variables
                st.markdown("**Selected Variables & Models:**")
                
                # Create a compatibility matrix
                for var in selected_variables:
                    st.markdown(f"**{var}**")
                    available_in = []
                    not_available_in = []
                    
                    for model_key in selected_model_keys:
                        source_name, _, model, model_vars = model_variable_map[model_key]
                        if var in model_vars:
                            available_in.append(f"{model} ({source_name})")
                        else:
                            not_available_in.append(f"{model} ({source_name})")
                    
                    if available_in:
                        st.success(f"✓ Available in: {', '.join(available_in)}")
                    if not_available_in:
                        st.warning(f"✗ NOT available in: {', '.join(not_available_in)}")
                    st.markdown("---")
            
            elif selected_model_keys:
                # Show what variables each selected model has
                st.markdown("**Variables by Selected Model:**")
                for model_key in selected_model_keys:
                    source_name, _, model, variables = model_variable_map[model_key]
                    st.markdown(f"**{model}** ({source_name}) - {len(variables)} variables")
                    if variables:
                        # Show first 10 variables
                        display_vars = variables[:10]
                        st.caption(f"  {', '.join(display_vars)}")
                        if len(variables) > 10:
                            st.caption(f"  ... and {len(variables) - 10} more")
                    else:
                        st.caption("  No variables available")
                    st.markdown("---")
            
            elif selected_variables:
                # Show which models support each selected variable
                st.markdown("**Models Supporting Selected Variables:**")
                for var in selected_variables:
                    st.markdown(f"**{var}**")
                    if var in variable_model_map:
                        models_for_var = variable_model_map[var]
                        by_source = {}
                        for source_name, _, model in models_for_var:
                            if source_name not in by_source:
                                by_source[source_name] = []
                            by_source[source_name].append(model)
                        
                        for source_name, models in by_source.items():
                            unique_models = list(OrderedDict.fromkeys(models))
                            st.caption(f"  {source_name}: {', '.join(unique_models)}")
                    st.markdown("---")
    
    # Display options
    st.markdown("### Display Options")
    display_col1, display_col2, display_col3 = st.columns(3)
    
    with display_col1:
        show_percentiles = st.checkbox("Show Percentile Bands", value=True, key='show_percentiles')
    
    with display_col2:
        show_members = st.checkbox("Show Individual Members", value=False, key='show_members')
    
    with display_col3:
        combine_plots = st.checkbox("Combine All Variables in One Plot", value=False, key='combine_plots',
                                   help="Overlay all selected variables on a single plot instead of separate plots per variable")
    
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
    
    if not selected_variables:
        st.info("Please select at least one weather variable to plot.")
        return
    
    if not selected_model_keys:
        st.info("Please select at least one ensemble model to plot.")
        return
    
    # Check for nearby observation station once
    has_nearby_station, station_info, distance = check_nearby_station(lat, lon, max_distance_km=obs_distance_km)
    if has_nearby_station:
        st.info(f"📍 Observation station '{station_info['name']}' found {distance:.2f} km away")
    
    # COMBINED MODE: Fetch all variables and combine into one plot
    if combine_plots:
        all_variable_data = {}  # {variable: (df_forecast, df_obs, selected_model_names, data_type)}
        
        with st.spinner(f"Fetching ensemble forecasts for {len(selected_variables)} variable(s)..."):
            for selected_variable in selected_variables:
                selected_data_type = all_variables_map[selected_variable]['type']
                
                # Get only the SELECTED models that provide this variable
                models_for_variable = []
                for model_key in selected_model_keys:
                    source_name, data_source, model, model_vars = model_variable_map[model_key]
                    if selected_variable in model_vars:
                        models_for_variable.append((source_name, data_source, model))
                
                if not models_for_variable:
                    st.warning(f"⚠️ None of the selected models provide '{selected_variable}'. Skipping.")
                    continue
                
                # Fetch data from each model/source combination for this variable
                all_forecast_dfs = []
                
                # Group models by source
                models_by_source = {}
                for source_name, data_source, model in models_for_variable:
                    if source_name not in models_by_source:
                        models_by_source[source_name] = {
                            'data_source': data_source,
                            'models': []
                        }
                    if model not in models_by_source[source_name]['models']:
                        models_by_source[source_name]['models'].append(model)
                
                # Fetch from each data source
                for source_name, source_info in models_by_source.items():
                    data_source = source_info['data_source']
                    models = source_info['models']
                    
                    try:
                        df = data_source.get_ensemble_data(
                            lat, lon, site, [selected_variable], selected_data_type, models
                        )
                        if not df.empty:
                            all_forecast_dfs.append(df)
                    except Exception as e:
                        st.warning(f"Failed to fetch ensemble data from {source_name} for '{selected_variable}': {str(e)}")
                
                # Combine all forecast dataframes for this variable
                if not all_forecast_dfs:
                    st.warning(f"No ensemble forecast data retrieved for '{selected_variable}'")
                    continue
                
                df_forecast = pd.concat(all_forecast_dfs, ignore_index=True)
                
                if df_forecast.empty:
                    st.warning(f"No ensemble forecast data retrieved for '{selected_variable}'")
                    continue
                
                # Fetch observation data
                df_obs = None
                if has_nearby_station and selected_data_type == 'hourly':
                    from data_sources.meteostat_obs import MeteostatObsDataSource
                    obs_source = MeteostatObsDataSource()
                    
                    @st.cache_data(ttl=3600)
                    def get_cached_obs_data(lat, lon, site, variables, data_type, previous_days, timezone):
                        return obs_source.get_deterministic_data(lat, lon, site, variables, data_type, [], previous_days, timezone)
                    
                    df_obs = get_cached_obs_data(
                        lat, lon, site, [selected_variable], selected_data_type, previous_days=2, timezone=timezone
                    )
                
                # Extract list of model names for this variable
                selected_model_names = list(OrderedDict.fromkeys([model for _, _, model in models_for_variable]))
                
                all_variable_data[selected_variable] = (df_forecast, df_obs, selected_model_names, selected_data_type)
        
        if not all_variable_data:
            st.warning("No data retrieved for any selected variable.")
            return
        
        # Create combined plot
        st.subheader(f'Combined Ensemble Forecast ({site})')
        st.caption(f"Showing {len(all_variable_data)} variable(s) with selected models")
        
        # Create a combined figure
        fig = go.Figure()
        
        # Track y-axes for multiple variables with different units
        yaxis_count = 0
        variable_colors = {}
        
        for idx, (variable, (df_forecast, df_obs, model_names, data_type)) in enumerate(all_variable_data.items()):
            yaxis_count += 1
            
            # Add traces for this variable
            for model in model_names:
                # Get ensemble members for this model and variable
                # Member columns are named: {variable}_{model}_member_XX
                member_cols = [col for col in df_forecast.columns 
                             if col.startswith(f'{variable}_{model}_member_')]
                
                if not member_cols:
                    continue
                
                if show_percentiles and len(member_cols) > 0:
                    # Calculate percentiles across member columns
                    member_values = df_forecast[member_cols].values
                    
                    p10 = pd.Series(member_values.min(axis=1), index=df_forecast.index)
                    p25 = pd.Series(pd.DataFrame(member_values).quantile(0.25, axis=1).values, index=df_forecast.index)
                    p50 = pd.Series(pd.DataFrame(member_values).quantile(0.50, axis=1).values, index=df_forecast.index)
                    p75 = pd.Series(pd.DataFrame(member_values).quantile(0.75, axis=1).values, index=df_forecast.index)
                    p90 = pd.Series(member_values.max(axis=1), index=df_forecast.index)
                    
                    datetime_col = df_forecast['datetime'] if 'datetime' in df_forecast.columns else df_forecast.index
                    
                    # Get color for this model
                    color = ENSEMBLE_MODEL_COLORS.get(model, f'hsl({idx * 60 % 360}, 70%, 50%)')
                    
                    # Add median line
                    fig.add_trace(go.Scatter(
                        x=datetime_col,
                        y=p50,
                        mode='lines',
                        name=f'{variable} - {model} (median)',
                        line=dict(color=color, width=2),
                        yaxis=f'y{yaxis_count}' if yaxis_count > 1 else 'y',
                        legendgroup=variable
                    ))
                    
                    # Add percentile bands
                    fig.add_trace(go.Scatter(
                        x=datetime_col,
                        y=p75,
                        mode='lines',
                        line=dict(width=0),
                        showlegend=False,
                        yaxis=f'y{yaxis_count}' if yaxis_count > 1 else 'y',
                        legendgroup=variable
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=datetime_col,
                        y=p25,
                        mode='lines',
                        fill='tonexty',
                        fillcolor=color.replace(')', ', 0.3)').replace('rgb', 'rgba') if 'rgb' in color else f'rgba(100, 100, 100, 0.3)',
                        line=dict(width=0),
                        name=f'{variable} - {model} (25-75%)',
                        yaxis=f'y{yaxis_count}' if yaxis_count > 1 else 'y',
                        legendgroup=variable
                    ))
            
            # Add observations if available
            if df_obs is not None and not df_obs.empty and variable in df_obs.columns:
                datetime_col = df_obs['datetime'] if 'datetime' in df_obs.columns else df_obs.index
                fig.add_trace(go.Scatter(
                    x=datetime_col,
                    y=df_obs[variable],
                    mode='markers+lines',
                    name=f'{variable} - Observations',
                    marker=dict(size=4, color='black'),
                    line=dict(color='black', width=1, dash='dot'),
                    yaxis=f'y{yaxis_count}' if yaxis_count > 1 else 'y',
                    legendgroup=variable
                ))
        
        # Update layout for multiple y-axes
        layout_updates = {
            'title': f'Combined Ensemble Forecast - {site}',
            'xaxis': {'title': 'Date/Time'},
            'hovermode': 'x unified',
            'height': 600
        }
        
        # Configure y-axes
        if yaxis_count == 1:
            layout_updates['yaxis'] = {'title': list(all_variable_data.keys())[0]}
        else:
            # Multiple y-axes - first on left, others on right
            for idx, variable in enumerate(all_variable_data.keys()):
                axis_num = idx + 1
                if axis_num == 1:
                    layout_updates['yaxis'] = {'title': variable, 'side': 'left'}
                else:
                    y_axis_key = f'yaxis{axis_num}'
                    layout_updates[y_axis_key] = {
                        'title': variable,
                        'overlaying': 'y',
                        'side': 'right' if idx % 2 == 1 else 'left',
                        'position': 1 - (idx - 1) * 0.05 if idx % 2 == 1 else (idx - 1) * 0.05
                    }
        
        fig.update_layout(**layout_updates)
        st.plotly_chart(fig, use_container_width=True)
        
        # Build caption
        all_sources = set()
        all_models = set()
        for variable, (df_forecast, df_obs, model_names, data_type) in all_variable_data.items():
            all_models.update(model_names)
        
        caption = f"Variables: **{', '.join(all_variable_data.keys())}** | Models: **{', '.join(all_models)}**"
        if has_nearby_station:
            caption += f" | Observations: **Meteostat ({station_info['name']})**"
        st.caption(caption)
    
    # SEPARATE MODE: Create individual plots for each variable
    else:
        for selected_variable in selected_variables:
            selected_data_type = all_variables_map[selected_variable]['type']
            
            # Get only the SELECTED models that provide this variable
            models_for_variable = []
            for model_key in selected_model_keys:
                source_name, data_source, model, model_vars = model_variable_map[model_key]
                if selected_variable in model_vars:
                    models_for_variable.append((source_name, data_source, model))
            
            if not models_for_variable:
                st.warning(f"⚠️ None of the selected models provide '{selected_variable}'. Skipping.")
                continue
            
            # Fetch data from each model/source combination for this variable
            all_forecast_dfs = []
            
            with st.spinner(f"Fetching ensemble forecasts for {selected_variable}..."):
                # Group models by source
                models_by_source = {}
                for source_name, data_source, model in models_for_variable:
                    if source_name not in models_by_source:
                        models_by_source[source_name] = {
                            'data_source': data_source,
                            'models': []
                        }
                    if model not in models_by_source[source_name]['models']:
                        models_by_source[source_name]['models'].append(model)
                
                # Fetch from each data source
                for source_name, source_info in models_by_source.items():
                    data_source = source_info['data_source']
                    models = source_info['models']
                    
                    try:
                        df = data_source.get_ensemble_data(
                            lat, lon, site, [selected_variable], selected_data_type, models
                        )
                        if not df.empty:
                            all_forecast_dfs.append(df)
                    except Exception as e:
                        st.warning(f"Failed to fetch ensemble data from {source_name} for '{selected_variable}': {str(e)}")
            
            # Combine all forecast dataframes for this variable
            if not all_forecast_dfs:
                st.warning(f"No ensemble forecast data retrieved for '{selected_variable}'")
                continue
            
            df_forecast = pd.concat(all_forecast_dfs, ignore_index=True)
            
            if df_forecast.empty:
                st.warning(f"No ensemble forecast data retrieved for '{selected_variable}'")
                continue
            
            # Fetch observation data
            df_obs = None
            if has_nearby_station and selected_data_type == 'hourly':
                from data_sources.meteostat_obs import MeteostatObsDataSource
                obs_source = MeteostatObsDataSource()
                
                @st.cache_data(ttl=3600)
                def get_cached_obs_data(lat, lon, site, variables, data_type, previous_days, timezone):
                    return obs_source.get_deterministic_data(lat, lon, site, variables, data_type, [], previous_days, timezone)
                
                with st.spinner("Fetching observation data..."):
                    df_obs = get_cached_obs_data(
                        lat, lon, site, [selected_variable], selected_data_type, previous_days=2, timezone=timezone
                    )
            
            # Extract list of model names for this variable
            selected_model_names = list(OrderedDict.fromkeys([model for _, _, model in models_for_variable]))
            
            # Create ensemble plot
            st.subheader(f'Ensemble Forecast: {selected_variable} ({site})')
            fig = create_ensemble_plot(
                df_forecast,
                selected_variable,
                selected_model_names,
                ENSEMBLE_MODEL_COLORS,
                show_percentiles=show_percentiles,
                show_members=show_members,
                df_obs=df_obs,
                timezone=timezone,
                thresholds=thresholds if enable_threshold else None
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Create exceedance probability plot if enabled
            if enable_threshold and thresholds:
                st.subheader(f'Exceedance Probability: {selected_variable}')
                
                # Calculate exceedance probabilities
                df_exceedance = pd.DataFrame()
                if 'datetime' in df_forecast.columns:
                    df_exceedance = pd.DataFrame({'datetime': df_forecast['datetime'].unique()})
                    df_exceedance = df_exceedance.set_index('datetime')
                
                for threshold in thresholds:
                    df_exceed = calculate_exceedance_probability(
                        df_forecast, selected_variable, threshold, selected_model_names
                    )
                    df_exceedance = pd.concat([df_exceedance, df_exceed], axis=1)
                
                fig_exceed = create_exceedance_plot(
                    df_exceedance,
                    selected_variable,
                    thresholds,
                    selected_model_names,
                    ENSEMBLE_MODEL_COLORS
                )
                st.plotly_chart(fig_exceed, use_container_width=True)
                
                st.caption(f"Showing probability (%) that {selected_variable} exceeds the specified thresholds")
            
            # Build caption showing all data sources used for this variable
            source_names = list(models_by_source.keys())
            caption = f"Data type: **{selected_data_type.capitalize()}** | Sources: **{', '.join(source_names)}** | Models: **{', '.join(selected_model_names)}**"
            if df_obs is not None and not df_obs.empty:
                caption += f" | Observations: **Meteostat ({station_info['name']})**"
            st.caption(caption)
            st.markdown("---")

