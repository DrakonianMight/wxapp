# ========================================
# File: views/ensemble_view_new.py
"""Redesigned Ensemble/Probabilistic forecast view"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict
from collections import OrderedDict
from utils.variable_categorizer import VariableCategorizer
from config import ENSEMBLE_MODEL_COLORS
import numpy as np

def check_nearby_station(lat: float, lon: float, max_distance_km: float = 1.0):
    """Check if there's a meteostat station within max_distance_km"""
    try:
        from meteostat import Stations
        radius_meters = max_distance_km * 1000
        stations = Stations().nearby(lat, lon, radius=radius_meters).fetch(1)
        if not stations.empty:
            station = stations.iloc[0]
            distance = station.get('distance', 0) / 1000.0 if 'distance' in station else max_distance_km
            return True, station, distance
        return False, None, None
    except Exception as e:
        return False, None, None

def create_ensemble_members_plot(
    data_dict: Dict[str, pd.DataFrame],
    variable: str,
    models: List[str],
    timezone: str = 'UTC'
) -> go.Figure:
    """
    Create a plot showing all individual ensemble members for selected models
    
    Args:
        data_dict: {model_name: dataframe with ensemble members}
        variable: Variable to plot
        models: List of model names
        timezone: Timezone for display
    
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    for model in models:
        if model not in data_dict:
            continue
            
        df = data_dict[model]
        
        # Get color for this model
        color = ENSEMBLE_MODEL_COLORS.get(model, 'gray')
        
        # Find member columns for this variable
        member_cols = [col for col in df.columns if col.startswith(f'{variable}_{model}_member_')]
        
        if not member_cols:
            continue
        
        datetime_col = df['datetime'] if 'datetime' in df.columns else df.index
        
        # Plot each ensemble member
        for i, member_col in enumerate(member_cols):
            fig.add_trace(go.Scatter(
                x=datetime_col,
                y=df[member_col],
                mode='lines',
                name=f'{model} - Member {i+1}',
                line=dict(color=color, width=0.5, opacity=0.3),
                legendgroup=model,
                showlegend=(i == 0),  # Only show first member in legend
                hovertemplate=f'{model} Member {i+1}: %{{y:.2f}}<extra></extra>'
            ))
        
        # Calculate and plot ensemble mean
        member_values = df[member_cols].values
        ensemble_mean = member_values.mean(axis=1)
        
        fig.add_trace(go.Scatter(
            x=datetime_col,
            y=ensemble_mean,
            mode='lines',
            name=f'{model} - Mean',
            line=dict(color=color, width=2.5),
            legendgroup=model,
            hovertemplate=f'{model} Mean: %{{y:.2f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title=f'Ensemble Forecast: {variable}',
        xaxis_title='Date/Time',
        yaxis_title=variable,
        hovermode='x unified',
        height=500,
        showlegend=True
    )
    
    return fig

def calculate_exceedance_probability(
    data_dict: Dict[str, pd.DataFrame],
    variable: str,
    threshold: float,
    models: List[str]
) -> pd.DataFrame:
    """
    Calculate probability of exceedance (POE) for a threshold
    
    Args:
        data_dict: {model_name: dataframe with ensemble members}
        variable: Variable to analyze
        threshold: Threshold value
        models: List of model names
    
    Returns:
        DataFrame with POE for each model
    """
    poe_data = {}
    
    for model in models:
        if model not in data_dict:
            continue
            
        df = data_dict[model]
        member_cols = [col for col in df.columns if col.startswith(f'{variable}_{model}_member_')]
        
        if not member_cols:
            continue
        
        member_values = df[member_cols].values
        # Calculate percentage of members exceeding threshold
        poe = (member_values > threshold).sum(axis=1) / len(member_cols) * 100
        
        datetime_col = df['datetime'] if 'datetime' in df.columns else df.index
        poe_data[model] = pd.DataFrame({
            'datetime': datetime_col,
            f'POE_{threshold}': poe
        })
    
    return poe_data

def create_poe_plot(
    poe_data: Dict[str, Dict[float, pd.DataFrame]],
    variable: str,
    thresholds: List[float],
    models: List[str]
) -> go.Figure:
    """
    Create probability of exceedance plot
    
    Args:
        poe_data: {model: {threshold: dataframe}}
        variable: Variable name
        thresholds: List of thresholds
        models: List of model names
    
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    # Define line styles for different thresholds
    line_styles = ['solid', 'dash', 'dot']
    
    for model in models:
        if model not in poe_data:
            continue
        
        color = ENSEMBLE_MODEL_COLORS.get(model, 'gray')
        
        for idx, threshold in enumerate(thresholds):
            if threshold not in poe_data[model]:
                continue
            
            df = poe_data[model][threshold]
            
            fig.add_trace(go.Scatter(
                x=df['datetime'],
                y=df[f'POE_{threshold}'],
                mode='lines',
                name=f'{model} - POE > {threshold}',
                line=dict(
                    color=color,
                    width=2,
                    dash=line_styles[idx % len(line_styles)]
                ),
                hovertemplate=f'{model} POE > {threshold}: %{{y:.1f}}%<extra></extra>'
            ))
    
    fig.update_layout(
        title=f'Probability of Exceedance (POE): {variable}',
        xaxis_title='Date/Time',
        yaxis_title='Probability (%)',
        yaxis=dict(range=[0, 100]),
        hovermode='x unified',
        height=400,
        showlegend=True
    )
    
    return fig

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
    Render the redesigned ensemble/probabilistic forecast view
    
    Args:
        data_sources: Dictionary of {source_name: DataSource instance}
        lat, lon, site: Location information
        custom_hourly_params, base_hourly_params, daily_params: Variable lists
        obs_distance_km: Distance for observation search
        timezone: Timezone for display
    """
    
    # Removed large title - location info is shown under map
    
    # Check if any selected source supports ensemble
    ensemble_sources = {name: ds for name, ds in data_sources.items() if ds.supports_ensemble}
    
    if not ensemble_sources:
        st.warning("⚠️ None of the selected data sources support ensemble forecasts. Please select a data source with ensemble support (e.g., Open-Meteo or AWS API).")
        return
    
    # Collect available variables
    all_data_source_vars = []
    data_source_var_map = {}
    
    for source_name, data_source in ensemble_sources.items():
        try:
            source_vars = data_source.get_available_variables('hourly')
            all_data_source_vars.extend(source_vars)
            for var in source_vars:
                if var not in data_source_var_map:
                    data_source_var_map[var] = []
                data_source_var_map[var].append(source_name)
        except Exception:
            pass
    
    data_source_vars = list(OrderedDict.fromkeys(all_data_source_vars))
    all_params = base_hourly_params + custom_hourly_params + data_source_vars
    hourly_params = list(OrderedDict.fromkeys([p for p in all_params if p]))
    
    # Build variables map
    all_variables_map = OrderedDict()
    for var in hourly_params:
        if var in data_source_vars and var not in base_hourly_params and var not in custom_hourly_params:
            sources = data_source_var_map.get(var, [])
            if len(sources) == 1:
                label = f'{var} ({sources[0]})'
            else:
                label = f'{var} ({len(sources)} sources)'
        else:
            label = var
        all_variables_map[var] = {'label': label, 'type': 'hourly'}
    
    # Build model-to-variable mapping
    model_variable_map = OrderedDict()
    all_available_models = {}
    
    for source_name, data_source in ensemble_sources.items():
        models = data_source.get_available_models('ensemble')
        for model in models:
            model_key = f"{source_name}::{model}"
            all_available_models[model_key] = (source_name, data_source, model)
            
            try:
                model_vars = data_source.get_model_specific_variables(model, 'ensemble')
                model_variable_map[model_key] = (source_name, data_source, model, model_vars)
            except Exception:
                try:
                    general_vars = data_source.get_available_variables('hourly')
                    model_variable_map[model_key] = (source_name, data_source, model, general_vars)
                except Exception:
                    model_variable_map[model_key] = (source_name, data_source, model, [])
    
    # =========================================================================
    # SECTION 1: MODEL & PARAMETER SELECTION
    # =========================================================================
    
    # Use the controls column from app.py if available
    if 'controls_column_ref' in st.session_state:
        with st.session_state['controls_column_ref']:
            st.markdown("### 🎯 Models & Parameters")
            
            # Format model display
            def format_model_display(model_key):
                source_name, _, model, variables = model_variable_map[model_key]
                var_count = len(variables)
                return f"{model} - {var_count} vars"
            
            selected_model_keys = st.multiselect(
                'Models',
                options=list(all_available_models.keys()),
                default=[],
                format_func=format_model_display,
                key='ens_model_select',
                help="Select ensemble models",
                label_visibility="collapsed"
            )
            
            st.markdown("**Parameters**")
            
            # Initialize categorizer
            categorizer = VariableCategorizer()
            variable_options = [v for v in all_variables_map.keys()]
            categorized_vars = categorizer.group_variables_by_category(variable_options)
            
            # Category filter
            category_names = [categorizer.CATEGORIES[cat]['name'] for cat in categorized_vars.keys()]
            selected_category = st.selectbox(
                "Category",
                options=["All Categories"] + category_names,
                key='ens_category_filter',
                label_visibility="collapsed"
            )
            
            # Filter variables
            if selected_category == "All Categories":
                filtered_variables = variable_options
            else:
                for cat_key, cat_info in categorizer.CATEGORIES.items():
                    if cat_info['name'] == selected_category:
                        filtered_variables = categorized_vars.get(cat_key, [])
                        break
            
            # Variable selection
            selected_variables = st.multiselect(
                'Params',
                options=filtered_variables,
                default=[],
                format_func=lambda x: all_variables_map[x]['label'],
                key='ens_var_select',
                help="Select parameters",
                label_visibility="collapsed"
            )
    else:
        # Fallback to original two-column layout if controls column not available
        st.markdown("## 🎯 Select Models and Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Models")
            
            # Format model display
            def format_model_display(model_key):
                source_name, _, model, variables = model_variable_map[model_key]
                var_count = len(variables)
                return f"{model} ({source_name}) - {var_count} vars"
            
            selected_model_keys = st.multiselect(
                'Select Ensemble Models',
                options=list(all_available_models.keys()),
                default=[],
                format_func=format_model_display,
                key='ens_model_select',
                help="Select one or more ensemble models to visualize"
            )
        
        with col2:
            st.markdown("### Parameters")
            
            # Initialize categorizer
            categorizer = VariableCategorizer()
            variable_options = [v for v in all_variables_map.keys()]
            categorized_vars = categorizer.group_variables_by_category(variable_options)
            
            # Category filter
            category_names = [categorizer.CATEGORIES[cat]['name'] for cat in categorized_vars.keys()]
            selected_category = st.selectbox(
                "Filter by Category",
                options=["All Categories"] + category_names,
                key='ens_category_filter'
            )
            
            # Filter variables
            if selected_category == "All Categories":
                filtered_variables = variable_options
            else:
                for cat_key, cat_info in categorizer.CATEGORIES.items():
                    if cat_info['name'] == selected_category:
                        filtered_variables = categorized_vars.get(cat_key, [])
                        break
            
            # Variable selection
            selected_variables = st.multiselect(
                'Select Parameters',
                options=filtered_variables,
                default=[],
                format_func=lambda x: all_variables_map[x]['label'],
                key='ens_var_select',
                help="Select one or more parameters to plot (can mix different parameters on same plot)"
            )
    
    if not selected_model_keys:
        st.info("👆 Please select at least one ensemble model to continue.")
        return
    
    if not selected_variables:
        st.info("👆 Please select at least one parameter to continue.")
        return
    
    # =========================================================================
    # SECTION 2: FETCH DATA & CREATE MAIN PLOT
    # =========================================================================
    
    st.markdown("## 📈 Ensemble Members")
    st.caption("Showing all individual ensemble members for selected models")
    
    # Fetch data for all selected variables and models
    ensemble_data = {}  # {variable: {model: dataframe}}
    
    with st.spinner("Fetching ensemble data..."):
        for selected_variable in selected_variables:
            ensemble_data[selected_variable] = {}
            selected_data_type = all_variables_map[selected_variable]['type']
            
            # Get models that provide this variable
            models_for_variable = []
            for model_key in selected_model_keys:
                source_name, data_source, model, model_vars = model_variable_map[model_key]
                if selected_variable in model_vars:
                    models_for_variable.append((source_name, data_source, model))
            
            if not models_for_variable:
                st.warning(f"⚠️ None of the selected models provide '{selected_variable}'")
                continue
            
            # Fetch from each model
            for source_name, data_source, model in models_for_variable:
                try:
                    df = data_source.get_ensemble_data(
                        lat, lon, site, [selected_variable], selected_data_type, [model]
                    )
                    if not df.empty:
                        ensemble_data[selected_variable][model] = df
                except Exception as e:
                    st.warning(f"Failed to fetch data from {model}: {str(e)}")
    
    # Create single plot with ALL variables and models
    if ensemble_data:
        fig = go.Figure()
        
        # Track which models/variables we've added
        all_models_shown = set()
        
        # Create a color palette for models not in config
        default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                         '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        model_color_map = {}
        color_index = 0
        
        for variable in selected_variables:
            if variable not in ensemble_data or not ensemble_data[variable]:
                continue
            
            for model in ensemble_data[variable].keys():
                all_models_shown.add(model)
                df = ensemble_data[variable][model]
                
                # Get or assign color for this model
                if model in ENSEMBLE_MODEL_COLORS:
                    color = ENSEMBLE_MODEL_COLORS[model]
                elif model not in model_color_map:
                    # Assign a new color from the palette
                    model_color_map[model] = default_colors[color_index % len(default_colors)]
                    color = model_color_map[model]
                    color_index += 1
                else:
                    color = model_color_map[model]
                
                # Find member columns for this variable
                member_cols = [col for col in df.columns if col.startswith(f'{variable}_{model}_member_')]
                
                if not member_cols:
                    continue
                
                datetime_col = df['datetime'] if 'datetime' in df.columns else df.index
                
                # Plot each ensemble member
                for i, member_col in enumerate(member_cols):
                    fig.add_trace(go.Scatter(
                        x=datetime_col,
                        y=df[member_col],
                        mode='lines',
                        name=f'{model} - {variable} - Member {i+1}',
                        line=dict(color=color, width=0.5),
                        opacity=0.3,
                        legendgroup=f'{model}_{variable}',
                        showlegend=(i == 0),  # Only show first member in legend
                        hovertemplate=f'{model} - {variable} Member {i+1}: %{{y:.2f}}<extra></extra>'
                    ))
                
                # Calculate and plot ensemble mean
                member_values = df[member_cols].values
                ensemble_mean = member_values.mean(axis=1)
                
                fig.add_trace(go.Scatter(
                    x=datetime_col,
                    y=ensemble_mean,
                    mode='lines',
                    name=f'{model} - {variable} - Mean',
                    line=dict(color=color, width=2.5),
                    legendgroup=f'{model}_{variable}',
                    hovertemplate=f'{model} - {variable} Mean: %{{y:.2f}}<extra></extra>'
                ))
        
        # Simple layout with single y-axis
        fig.update_layout(
            title='Ensemble Forecast - All Selected Variables',
            xaxis_title='Date/Time',
            yaxis_title='Value',
            hovermode='x unified',
            height=500,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show info about the data
        models_list = sorted(list(all_models_shown))
        variables_list = [v for v in selected_variables if v in ensemble_data]
        st.caption(f"**Variables**: {', '.join(variables_list)} | **Models**: {', '.join(models_list)}")
    else:
        st.warning("No data available for selected variables and models.")
    
    # =========================================================================
    # SECTION 3: PROBABILITY OF EXCEEDANCE (POE) ANALYSIS
    # =========================================================================
    
    st.markdown("## 📊 Probability of Exceedance Analysis")
    
    enable_poe = st.checkbox(
        "Enable POE Analysis",
        value=False,
        key='enable_poe',
        help="Calculate probability that values will exceed specified thresholds"
    )
    
    if enable_poe:
        st.markdown("### Define Thresholds")
        st.caption("Add up to 3 threshold values for POE calculation")
        
        threshold_col1, threshold_col2, threshold_col3 = st.columns(3)
        
        thresholds = []
        
        with threshold_col1:
            use_t1 = st.checkbox("Threshold 1", value=True, key='use_threshold_1')
            if use_t1:
                t1 = st.number_input(
                    "Value",
                    value=20.0,
                    step=0.5,
                    key='threshold_1_value'
                )
                thresholds.append(t1)
        
        with threshold_col2:
            use_t2 = st.checkbox("Threshold 2", value=False, key='use_threshold_2')
            if use_t2:
                t2 = st.number_input(
                    "Value",
                    value=25.0,
                    step=0.5,
                    key='threshold_2_value'
                )
                thresholds.append(t2)
        
        with threshold_col3:
            use_t3 = st.checkbox("Threshold 3", value=False, key='use_threshold_3')
            if use_t3:
                t3 = st.number_input(
                    "Value",
                    value=30.0,
                    step=0.5,
                    key='threshold_3_value'
                )
                thresholds.append(t3)
        
        if thresholds:
            st.markdown("### POE Results")
            
            # Calculate POE for each variable
            for variable in selected_variables:
                if variable not in ensemble_data or not ensemble_data[variable]:
                    continue
                
                poe_data = {}  # {model: {threshold: dataframe}}
                
                with st.spinner(f"Calculating POE for {variable}..."):
                    for model in ensemble_data[variable].keys():
                        poe_data[model] = {}
                        for threshold in thresholds:
                            poe_results = calculate_exceedance_probability(
                                {model: ensemble_data[variable][model]},
                                variable,
                                threshold,
                                [model]
                            )
                            if model in poe_results:
                                poe_data[model][threshold] = poe_results[model]
                
                # Create POE plot
                fig_poe = create_poe_plot(
                    poe_data,
                    variable,
                    thresholds,
                    list(ensemble_data[variable].keys())
                )
                
                st.plotly_chart(fig_poe, use_container_width=True)
                
                # Show threshold info
                threshold_str = ', '.join([str(t) for t in thresholds])
                st.caption(f"**{variable}** - Thresholds: {threshold_str}")
        else:
            st.info("👆 Enable at least one threshold to see POE analysis")
