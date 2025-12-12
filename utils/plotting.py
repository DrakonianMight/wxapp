# File: utils/plotting.py
"""Plotting utilities for weather data"""

import plotly.graph_objs as go
from typing import Dict, List
import pandas as pd
from config import YAXIS_TITLES, DETERMINISTIC_MODEL_COLORS, ENSEMBLE_MODEL_COLORS

# Fallback color palette for models not in the config
FALLBACK_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5'
]


def get_yaxis_title(column: str) -> str:
    """Get Y-axis title for a variable"""
    return YAXIS_TITLES.get(column, column.replace('_', ' ').title())


def get_model_color(model_name: str, color_map: Dict, used_colors: set = None) -> str:
    """
    Get color for a model with fallback to palette if not in map
    
    Args:
        model_name: Name of the model
        color_map: Dictionary mapping model names to colors
        used_colors: Set of colors already used (to avoid duplicates)
    
    Returns:
        Color string (hex code)
    """
    if used_colors is None:
        used_colors = set()
    
    # First try exact match in color map
    if model_name in color_map:
        return color_map[model_name]
    
    # Try partial matches (in case of model name variations)
    for key in color_map:
        if key in model_name or model_name in key:
            return color_map[key]
    
    # Use fallback palette, cycling through unused colors first
    for color in FALLBACK_COLORS:
        if color not in used_colors:
            used_colors.add(color)
            return color
    
    # If all colors used, cycle through again
    idx = len(used_colors) % len(FALLBACK_COLORS)
    return FALLBACK_COLORS[idx]


def create_deterministic_plot(
    df: pd.DataFrame,
    selected_columns: List[str],
    all_variables_map: Dict,
    color_map: Dict,
    data_type: str,
    df_obs: pd.DataFrame = None,
    timezone: str = 'UTC'
) -> go.Figure:
    """
    Create time series plot for deterministic forecasts
    
    Args:
        df: DataFrame with forecast data
        selected_columns: List of variable names to plot
        all_variables_map: Dictionary mapping variables to metadata
        color_map: Dictionary mapping models to colors
        data_type: Type of data ('hourly' or 'daily')
        df_obs: Optional DataFrame with observation data to overlay
        timezone: Timezone for displaying dates (default: 'UTC')
    
    Returns:
        Plotly Figure object
    """
    import pytz
    from datetime import datetime
    
    fig = go.Figure()
    y_axis_label_set = False
    
    # Prepare dataframe with datetime handling
    df_plot = df.copy()
    
    # Ensure we have datetime data for x-axis
    if 'datetime' in df_plot.columns:
        x_data = df_plot['datetime']
        # Convert to specified timezone if needed
        try:
            tz = pytz.timezone(timezone)
            if pd.api.types.is_datetime64_any_dtype(x_data):
                if x_data.dt.tz is None:
                    x_data = x_data.dt.tz_localize('UTC').dt.tz_convert(tz)
                else:
                    x_data = x_data.dt.tz_convert(tz)
        except Exception as e:
            pass  # If conversion fails, use original timezone
    elif isinstance(df_plot.index, pd.DatetimeIndex):
        # Fallback to index if datetime column not present
        x_data = df_plot.index
        try:
            tz = pytz.timezone(timezone)
            if x_data.tz is None:
                x_data = x_data.tz_localize('UTC').tz_convert(tz)
            else:
                x_data = x_data.tz_convert(tz)
        except Exception as e:
            pass
    else:
        raise ValueError("DataFrame must have either 'datetime' column or DatetimeIndex")
    
    # Track used colors to ensure variety
    used_colors = set()
    
    for selected_column in selected_columns:
        cols_to_plot = [col for col in df_plot.columns if selected_column in col and col != 'datetime']
        
        if not y_axis_label_set:
            y_axis_label = get_yaxis_title(selected_column)
            y_axis_label_set = True

        for col in cols_to_plot:
            cleaned_col = col.replace(selected_column, '').strip('_')
            color = get_model_color(cleaned_col, color_map, used_colors)

            fig.add_trace(go.Scatter(
                x=x_data, 
                y=df_plot[col], 
                mode='lines', 
                name=f"{cleaned_col} ({all_variables_map[selected_column]['label']})", 
                line=dict(color=color)
            ))
    
    # Add observation data if available
    if df_obs is not None and not df_obs.empty:
        df_obs_plot = df_obs.copy()
        
        # Convert observation times to specified timezone
        if timezone != 'UTC':
            try:
                tz = pytz.timezone(timezone)
                if 'datetime' in df_obs_plot.columns:
                    if df_obs_plot['datetime'].dt.tz is None:
                        df_obs_plot['datetime'] = df_obs_plot['datetime'].dt.tz_localize('UTC').dt.tz_convert(tz)
                    else:
                        df_obs_plot['datetime'] = df_obs_plot['datetime'].dt.tz_convert(tz)
                elif hasattr(df_obs_plot.index, 'tz_localize'):
                    if df_obs_plot.index.tz is None:
                        df_obs_plot.index = df_obs_plot.index.tz_localize('UTC').tz_convert(tz)
                    else:
                        df_obs_plot.index = df_obs_plot.index.tz_convert(tz)
            except Exception:
                pass  # If conversion fails, use original timezone
        
        for selected_column in selected_columns:
            if selected_column in df_obs_plot.columns:
                # Use datetime column if available, otherwise use index
                if 'datetime' in df_obs_plot.columns:
                    x_data = df_obs_plot['datetime']
                else:
                    x_data = df_obs_plot.index
                
                fig.add_trace(go.Scatter(
                    x=x_data,
                    y=df_obs_plot[selected_column],
                    mode='markers',
                    name=f'Observations ({selected_column})',
                    marker=dict(color='black', size=4, symbol='circle'),
                    line=dict(color='black', width=2)
                ))

    fig.update_layout(
        title=f'{data_type.capitalize()} Forecast Data',
        yaxis_title=y_axis_label,
        legend=dict(
            title='Model & Variable',
            font=dict(size=10),
            orientation="h",
            yanchor="bottom",
            y=-0.3, 
            xanchor="left",
            x=0
        ),
        xaxis=dict(showgrid=True, title='Forecast Time'),
        yaxis=dict(showgrid=True),
        hovermode="x unified",
        margin=dict(l=30, r=30, t=30, b=30),
        template="simple_white"
    )
    
    # Add vertical line for current time
    try:
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        
        # Add vertical line using shape
        fig.add_shape(
            type="line",
            x0=current_time,
            x1=current_time,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(
                color="red",
                width=2,
                dash="dash"
            )
        )
        
        # Add annotation for the line
        fig.add_annotation(
            x=current_time,
            y=1.02,
            yref="paper",
            text="Now",
            showarrow=False,
            font=dict(color="red", size=12),
            xanchor="left"
        )
    except Exception as e:
        # Fallback to UTC if timezone fails
        try:
            current_time = datetime.now(pytz.UTC)
            fig.add_shape(
                type="line",
                x0=current_time,
                x1=current_time,
                y0=0,
                y1=1,
                yref="paper",
                line=dict(
                    color="red",
                    width=2,
                    dash="dash"
                )
            )
            fig.add_annotation(
                x=current_time,
                y=1.02,
                yref="paper",
                text="Now (UTC)",
                showarrow=False,
                font=dict(color="red", size=12),
                xanchor="left"
            )
        except Exception:
            pass  # If this also fails, skip the current time line
    
    return fig


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """
    Convert hex color to rgba string
    
    Args:
        hex_color: Hex color string (e.g., '#FF5733')
        alpha: Alpha/opacity value (0-1)
    
    Returns:
        RGBA color string
    """
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f'rgba({r}, {g}, {b}, {alpha})'


def create_ensemble_plot(
    df: pd.DataFrame,
    variable: str,
    models: List[str],
    color_map: Dict,
    show_percentiles: bool = True,
    show_members: bool = False,
    df_obs: pd.DataFrame = None,
    timezone: str = 'UTC',
    thresholds: List[float] = None
) -> go.Figure:
    """
    Create ensemble forecast plot with percentiles and/or individual members
    
    Args:
        df: DataFrame with ensemble data (columns like 'var_model_member_00')
        variable: Variable name to plot
        models: List of ensemble model names
        color_map: Dictionary mapping models to colors
        show_percentiles: Whether to show percentile bands
        show_members: Whether to show individual ensemble members
        df_obs: Optional DataFrame with observation data to overlay
        timezone: Timezone for displaying dates (default: 'UTC')
        thresholds: Optional list of threshold values to display as horizontal lines
        show_percentiles: Whether to show percentile bands
        show_members: Whether to show individual ensemble members
        df_obs: Optional DataFrame with observation data to overlay
        timezone: Timezone for displaying dates (default: 'UTC')
    
    Returns:
        Plotly Figure object
    """
    import pytz
    from datetime import datetime
    
    fig = go.Figure()
    
    # Prepare dataframe with datetime handling
    df_plot = df.copy()
    
    # Ensure we have datetime data for x-axis
    if 'datetime' in df_plot.columns:
        x_data = df_plot['datetime']
        # Convert to specified timezone if needed
        try:
            tz = pytz.timezone(timezone)
            if pd.api.types.is_datetime64_any_dtype(x_data):
                if x_data.dt.tz is None:
                    x_data = x_data.dt.tz_localize('UTC').dt.tz_convert(tz)
                else:
                    x_data = x_data.dt.tz_convert(tz)
        except Exception as e:
            print(f"Warning: Could not convert forecast timezone: {e}")
            pass  # If conversion fails, use original timezone
    elif isinstance(df_plot.index, pd.DatetimeIndex):
        # Fallback to index if datetime column not present
        x_data = df_plot.index
        try:
            tz = pytz.timezone(timezone)
            if x_data.tz is None:
                x_data = x_data.tz_localize('UTC').tz_convert(tz)
            else:
                x_data = x_data.tz_convert(tz)
        except Exception as e:
            print(f"Warning: Could not convert forecast timezone: {e}")
            pass
    else:
        raise ValueError("DataFrame must have either 'datetime' column or DatetimeIndex")
    
    # Track used colors to ensure variety
    used_colors = set()
    
    for model in models:
        # Find all columns for this model and variable
        model_cols = [col for col in df_plot.columns 
                     if variable in col and model in col and '_member_' in col]
        
        if not model_cols:
            continue
            
        color = get_model_color(model, color_map, used_colors)
        ensemble_data = df_plot[model_cols]
        
        if show_percentiles:
            # Calculate percentiles
            p10 = ensemble_data.quantile(0.10, axis=1)
            p25 = ensemble_data.quantile(0.25, axis=1)
            p50 = ensemble_data.quantile(0.50, axis=1)
            p75 = ensemble_data.quantile(0.75, axis=1)
            p90 = ensemble_data.quantile(0.90, axis=1)
            
            # Add 10-90% band
            fig.add_trace(go.Scatter(
                x=x_data, 
                y=p90,
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip',
                name=f'{model}_p90'
            ))
            
            fig.add_trace(go.Scatter(
                x=x_data, 
                y=p10,
                mode='lines',
                line=dict(width=0),
                fillcolor=hex_to_rgba(color, 0.1),
                fill='tonexty',
                name=f'{model} 10-90%',
                hoverinfo='skip'
            ))
            
            # Add 25-75% band
            fig.add_trace(go.Scatter(
                x=x_data, 
                y=p75,
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip',
                name=f'{model}_p75'
            ))
            
            fig.add_trace(go.Scatter(
                x=x_data, 
                y=p25,
                mode='lines',
                line=dict(width=0),
                fillcolor=hex_to_rgba(color, 0.2),
                fill='tonexty',
                name=f'{model} 25-75%',
                hoverinfo='skip'
            ))
            
            # Median line
            fig.add_trace(go.Scatter(
                x=x_data, 
                y=p50,
                mode='lines',
                name=f'{model} Median',
                line=dict(color=color, width=2)
            ))
        
        if show_members:
            # Show individual ensemble members as thin lines
            for i, col in enumerate(model_cols):
                fig.add_trace(go.Scatter(
                    x=x_data, 
                    y=df_plot[col],
                    mode='lines',
                    name=f'{model} Member {i+1}',
                    line=dict(color=color, width=0.5),
                    opacity=0.3,
                    showlegend=(i == 0)  # Only show first member in legend
                ))
    
    # Add observation data if available
    if df_obs is not None and not df_obs.empty:
        df_obs_plot = df_obs.copy()
        
        # Convert observation times to specified timezone
        try:
            tz = pytz.timezone(timezone)
            if 'datetime' in df_obs_plot.columns:
                if pd.api.types.is_datetime64_any_dtype(df_obs_plot['datetime']):
                    # Check if already timezone-aware
                    if df_obs_plot['datetime'].dt.tz is None:
                        # Localize to UTC first, then convert
                        df_obs_plot['datetime'] = df_obs_plot['datetime'].dt.tz_localize('UTC').dt.tz_convert(tz)
                    else:
                        # Already timezone-aware, just convert
                        df_obs_plot['datetime'] = df_obs_plot['datetime'].dt.tz_convert(tz)
            elif isinstance(df_obs_plot.index, pd.DatetimeIndex):
                if df_obs_plot.index.tz is None:
                    df_obs_plot.index = df_obs_plot.index.tz_localize('UTC').tz_convert(tz)
                else:
                    # Already timezone-aware, just convert
                    df_obs_plot.index = df_obs_plot.index.tz_convert(tz)
        except Exception as e:
            print(f"Warning: Could not convert observation timezone: {e}")
            pass  # If conversion fails, use original timezone
        
        if variable in df_obs_plot.columns:
            # Use datetime column if available, otherwise use index
            if 'datetime' in df_obs_plot.columns:
                x_data = df_obs_plot['datetime']
            else:
                x_data = df_obs_plot.index
            
            fig.add_trace(go.Scatter(
                x=x_data,
                y=df_obs_plot[variable],
                mode='markers',
                name='Observations',
                marker=dict(color='black', size=5, symbol='circle'),
                line=dict(color='black', width=2)
            ))
    
    fig.update_layout(
        title=f'Ensemble Forecast - {get_yaxis_title(variable)}',
        yaxis_title=get_yaxis_title(variable),
        xaxis=dict(showgrid=True, title='Forecast Time'),
        yaxis=dict(showgrid=True),
        hovermode="x unified",
        margin=dict(l=30, r=30, t=30, b=30),
        template="simple_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="left",
            x=0
        )
    )
    
    # Add vertical line for current time
    try:
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        
        # Add vertical line using shape
        fig.add_shape(
            type="line",
            x0=current_time,
            x1=current_time,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(
                color="red",
                width=2,
                dash="dash"
            )
        )
        
        # Add annotation for the line
        fig.add_annotation(
            x=current_time,
            y=1.02,
            yref="paper",
            text="Now",
            showarrow=False,
            font=dict(color="red", size=12),
            xanchor="left"
        )
    except Exception as e:
        # Fallback to UTC if timezone fails
        try:
            current_time = datetime.now(pytz.UTC)
            fig.add_shape(
                type="line",
                x0=current_time,
                x1=current_time,
                y0=0,
                y1=1,
                yref="paper",
                line=dict(
                    color="red",
                    width=2,
                    dash="dash"
                )
            )
            fig.add_annotation(
                x=current_time,
                y=1.02,
                yref="paper",
                text="Now (UTC)",
                showarrow=False,
                font=dict(color="red", size=12),
                xanchor="left"
            )
        except Exception:
            pass  # If this also fails, skip the current time line
    
    # Add horizontal threshold lines if provided
    if thresholds:
        threshold_colors = ['orange', 'purple', 'brown']  # Different colors for different thresholds
        for i, threshold in enumerate(thresholds):
            color = threshold_colors[i % len(threshold_colors)]
            
            # Add horizontal line
            fig.add_shape(
                type="line",
                x0=0,
                x1=1,
                xref="paper",
                y0=threshold,
                y1=threshold,
                line=dict(
                    color=color,
                    width=2,
                    dash="dot"
                )
            )
            
            # Add annotation for the threshold
            fig.add_annotation(
                x=1.01,
                xref="paper",
                y=threshold,
                text=f"Threshold: {threshold}",
                showarrow=False,
                font=dict(color=color, size=10),
                xanchor="left",
                yanchor="middle"
            )
    
    return fig


def create_exceedance_plot(
    df: pd.DataFrame,
    variable: str,
    thresholds: List[float],
    models: List[str],
    color_map: Dict
) -> go.Figure:
    """
    Create exceedance probability plot showing probability of exceeding thresholds
    
    Args:
        df: DataFrame with exceedance probability data (from calculate_exceedance_probability)
        variable: Variable name
        thresholds: List of threshold values
        models: List of ensemble model names
        color_map: Dictionary mapping models to colors
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Define line styles for different thresholds
    line_styles = ['solid', 'dash', 'dot', 'dashdot']
    
    # Ensure we have datetime data for x-axis
    if 'datetime' in df.columns:
        x_data = df['datetime']
    elif isinstance(df.index, pd.DatetimeIndex):
        x_data = df.index
    else:
        # Fallback to integer index if no datetime found
        x_data = df.index
    
    for threshold_idx, threshold in enumerate(thresholds):
        line_style = line_styles[threshold_idx % len(line_styles)]
        
        for model in models:
            col_name = f'{model}_{variable}_exceed_{threshold}'
            
            if col_name in df.columns:
                color = color_map.get(model, 'gray')
                
                fig.add_trace(go.Scatter(
                    x=x_data,
                    y=df[col_name],
                    mode='lines',
                    name=f'{model} > {threshold}',
                    line=dict(color=color, dash=line_style, width=2),
                    hovertemplate=f'{model}<br>Threshold: {threshold}<br>Probability: %{{y:.1f}}%<extra></extra>'
                ))
    
    fig.update_layout(
        title=f'Exceedance Probability - {get_yaxis_title(variable)}',
        yaxis_title='Probability of Exceedance (%)',
        xaxis=dict(showgrid=True, title='Forecast Time'),
        yaxis=dict(showgrid=True, range=[0, 100]),
        hovermode="x unified",
        margin=dict(l=30, r=30, t=30, b=30),
        template="simple_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="left",
            x=0,
            font=dict(size=10)
        )
    )
    
    # Add horizontal reference lines at 10%, 50%, 90%
    for prob in [10, 50, 90]:
        fig.add_hline(
            y=prob, 
            line_dash="dot", 
            line_color="gray", 
            opacity=0.3,
            annotation_text=f"{prob}%",
            annotation_position="right"
        )
    
    return fig


def create_ensemble_spaghetti_plot(
    df: pd.DataFrame,
    variable: str,
    model: str,
    color: str
) -> go.Figure:
    """
    Create a 'spaghetti plot' showing all ensemble members as individual lines
    
    Args:
        df: DataFrame with ensemble data
        variable: Variable name to plot
        model: Model name
        color: Color for the lines
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Find all member columns
    member_cols = [col for col in df.columns 
                  if variable in col and model in col and '_member_' in col]
    
    if not member_cols:
        return fig
    
    # Ensure we have datetime data for x-axis
    if 'datetime' in df.columns:
        x_data = df['datetime']
    elif isinstance(df.index, pd.DatetimeIndex):
        x_data = df.index
    else:
        # Fallback to integer index if no datetime found
        x_data = df.index
    
    # Add each member as a thin line
    for i, col in enumerate(member_cols):
        fig.add_trace(go.Scatter(
            x=x_data,
            y=df[col],
            mode='lines',
            name=f'Member {i+1}',
            line=dict(color=color, width=1),
            opacity=0.4,
            showlegend=(i < 5)  # Only show first 5 in legend to avoid clutter
        ))
    
    # Add ensemble mean as thick line
    ensemble_data = df[member_cols]
    ensemble_mean = ensemble_data.mean(axis=1)
    
    fig.add_trace(go.Scatter(
        x=x_data,
        y=ensemble_mean,
        mode='lines',
        name='Ensemble Mean',
        line=dict(color=color, width=3),
        opacity=1.0
    ))
    
    fig.update_layout(
        title=f'Ensemble Members - {model} - {get_yaxis_title(variable)}',
        yaxis_title=get_yaxis_title(variable),
        xaxis=dict(showgrid=True, title='Forecast Time'),
        yaxis=dict(showgrid=True),
        hovermode="x unified",
        margin=dict(l=30, r=30, t=30, b=30),
        template="simple_white"
    )
    
    return fig