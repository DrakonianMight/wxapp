# File: utils/probability.py
"""Probability calculations for ensemble forecasts"""

import pandas as pd
import numpy as np
from typing import List, Dict


def calculate_exceedance_probability(
    df: pd.DataFrame, 
    variable: str, 
    threshold: float,
    models: List[str]
) -> pd.DataFrame:
    """
    Calculate probability of exceeding threshold across ensemble members
    
    For each time step, calculates what percentage of ensemble members 
    exceed the given threshold value.
    
    Args:
        df: DataFrame with ensemble data (columns like 'variable_model_member_00')
        variable: Variable name to analyze (e.g., 'temperature_2m')
        threshold: Threshold value to test against
        models: List of ensemble model names (e.g., ['gfs_ensemble', 'ecmwf_ifs_ensemble'])
    
    Returns:
        DataFrame with exceedance probabilities (0-100%) for each model
        Columns will be named: 'model_variable_exceed_threshold'
    
    Example:
        >>> df_exceed = calculate_exceedance_probability(
        ...     df, 
        ...     'temperature_2m', 
        ...     threshold=30.0, 
        ...     models=['gfs_ensemble']
        ... )
        >>> # Result will have column 'gfs_ensemble_temperature_2m_exceed_30.0'
        >>> # with values 0-100 indicating percentage of members exceeding 30°C
    """
    result_df = pd.DataFrame(index=df.index)
    
    for model in models:
        # Get all columns for this model and variable
        # Example: 'temperature_2m_gfs_ensemble_member_00', '_01', etc.
        model_cols = [col for col in df.columns 
                     if variable in col and model in col and '_member_' in col]
        
        if model_cols:
            # Extract ensemble data for all members
            ensemble_data = df[model_cols]
            
            # Count how many members exceed threshold at each time step
            # Then divide by total number of members and multiply by 100 for percentage
            exceedance = (ensemble_data > threshold).sum(axis=1) / len(model_cols) * 100
            
            # Store in result with descriptive column name
            result_df[f'{model}_{variable}_exceed_{threshold}'] = exceedance
    
    return result_df


def calculate_percentiles(
    df: pd.DataFrame,
    variable: str,
    model: str,
    percentiles: List[int] = [10, 25, 50, 75, 90]
) -> pd.DataFrame:
    """
    Calculate percentiles across ensemble members at each time step
    
    Args:
        df: DataFrame with ensemble data
        variable: Variable name to analyze
        model: Model name
        percentiles: List of percentiles to calculate (0-100)
    
    Returns:
        DataFrame with percentile values
        Columns will be named: 'model_variable_p10', 'model_variable_p25', etc.
    
    Example:
        >>> df_percentiles = calculate_percentiles(
        ...     df,
        ...     'temperature_2m',
        ...     'gfs_ensemble',
        ...     percentiles=[10, 50, 90]
        ... )
    """
    result_df = pd.DataFrame(index=df.index)
    
    # Get all columns for this model and variable
    model_cols = [col for col in df.columns 
                 if variable in col and model in col and '_member_' in col]
    
    if model_cols:
        ensemble_data = df[model_cols]
        
        for p in percentiles:
            # Calculate percentile at each time step
            result_df[f'{model}_{variable}_p{p}'] = ensemble_data.quantile(p/100, axis=1)
    
    return result_df


def calculate_ensemble_statistics(
    df: pd.DataFrame,
    variable: str,
    model: str
) -> pd.DataFrame:
    """
    Calculate comprehensive ensemble statistics
    
    Args:
        df: DataFrame with ensemble data
        variable: Variable name to analyze
        model: Model name
    
    Returns:
        DataFrame with mean, std, min, max, and quartiles
    
    Example:
        >>> stats = calculate_ensemble_statistics(df, 'temperature_2m', 'gfs_ensemble')
        >>> # Returns columns: mean, std, min, q25, median, q75, max
    """
    result_df = pd.DataFrame(index=df.index)
    
    # Get all ensemble member columns
    model_cols = [col for col in df.columns 
                 if variable in col and model in col and '_member_' in col]
    
    if not model_cols:
        return result_df
    
    ensemble_data = df[model_cols]
    
    # Calculate statistics
    result_df[f'{model}_{variable}_mean'] = ensemble_data.mean(axis=1)
    result_df[f'{model}_{variable}_std'] = ensemble_data.std(axis=1)
    result_df[f'{model}_{variable}_min'] = ensemble_data.min(axis=1)
    result_df[f'{model}_{variable}_q25'] = ensemble_data.quantile(0.25, axis=1)
    result_df[f'{model}_{variable}_median'] = ensemble_data.quantile(0.50, axis=1)
    result_df[f'{model}_{variable}_q75'] = ensemble_data.quantile(0.75, axis=1)
    result_df[f'{model}_{variable}_max'] = ensemble_data.max(axis=1)
    
    return result_df


def calculate_probability_between_thresholds(
    df: pd.DataFrame,
    variable: str,
    lower_threshold: float,
    upper_threshold: float,
    models: List[str]
) -> pd.DataFrame:
    """
    Calculate probability of values falling between two thresholds
    
    Args:
        df: DataFrame with ensemble data
        variable: Variable name
        lower_threshold: Lower bound
        upper_threshold: Upper bound
        models: List of model names
    
    Returns:
        DataFrame with probabilities (0-100%)
    
    Example:
        >>> # Probability that temperature is between 20-30°C
        >>> df_prob = calculate_probability_between_thresholds(
        ...     df, 'temperature_2m', 20.0, 30.0, ['gfs_ensemble']
        ... )
    """
    result_df = pd.DataFrame(index=df.index)
    
    for model in models:
        model_cols = [col for col in df.columns 
                     if variable in col and model in col and '_member_' in col]
        
        if model_cols:
            ensemble_data = df[model_cols]
            
            # Check if values are within the range
            in_range = (ensemble_data >= lower_threshold) & (ensemble_data <= upper_threshold)
            probability = in_range.sum(axis=1) / len(model_cols) * 100
            
            result_df[f'{model}_{variable}_between_{lower_threshold}_{upper_threshold}'] = probability
    
    return result_df


def calculate_ensemble_spread(
    df: pd.DataFrame,
    variable: str,
    model: str
) -> pd.DataFrame:
    """
    Calculate ensemble spread (standard deviation and range)
    
    Larger spread indicates more uncertainty in the forecast.
    
    Args:
        df: DataFrame with ensemble data
        variable: Variable name
        model: Model name
    
    Returns:
        DataFrame with spread metrics
    """
    result_df = pd.DataFrame(index=df.index)
    
    model_cols = [col for col in df.columns 
                 if variable in col and model in col and '_member_' in col]
    
    if not model_cols:
        return result_df
    
    ensemble_data = df[model_cols]
    
    # Standard deviation (most common spread metric)
    result_df[f'{model}_{variable}_spread_std'] = ensemble_data.std(axis=1)
    
    # Range (max - min)
    result_df[f'{model}_{variable}_spread_range'] = (
        ensemble_data.max(axis=1) - ensemble_data.min(axis=1)
    )
    
    # Interquartile range (75th - 25th percentile)
    result_df[f'{model}_{variable}_spread_iqr'] = (
        ensemble_data.quantile(0.75, axis=1) - ensemble_data.quantile(0.25, axis=1)
    )
    
    return result_df


def calculate_risk_category_probabilities(
    df: pd.DataFrame,
    variable: str,
    thresholds: Dict[str, float],
    models: List[str]
) -> pd.DataFrame:
    """
    Calculate probabilities for predefined risk categories
    
    Args:
        df: DataFrame with ensemble data
        variable: Variable name
        thresholds: Dictionary of category names to threshold values
                   e.g., {'low': 20, 'medium': 30, 'high': 40}
        models: List of model names
    
    Returns:
        DataFrame with probability for each risk category
    
    Example:
        >>> thresholds = {
        ...     'comfortable': 25,  # < 25°C
        ...     'warm': 30,         # 25-30°C
        ...     'hot': 35,          # 30-35°C
        ...     'extreme': 40       # > 35°C
        ... }
        >>> df_risk = calculate_risk_category_probabilities(
        ...     df, 'temperature_2m', thresholds, ['gfs_ensemble']
        ... )
    """
    result_df = pd.DataFrame(index=df.index)
    
    # Sort thresholds
    sorted_categories = sorted(thresholds.items(), key=lambda x: x[1])
    
    for model in models:
        model_cols = [col for col in df.columns 
                     if variable in col and model in col and '_member_' in col]
        
        if not model_cols:
            continue
        
        ensemble_data = df[model_cols]
        
        # Calculate probability for each category
        for i, (category, threshold) in enumerate(sorted_categories):
            if i == 0:
                # First category: values below threshold
                prob = (ensemble_data < threshold).sum(axis=1) / len(model_cols) * 100
            elif i == len(sorted_categories) - 1:
                # Last category: values above this threshold
                prob = (ensemble_data >= threshold).sum(axis=1) / len(model_cols) * 100
            else:
                # Middle categories: between previous and current threshold
                prev_threshold = sorted_categories[i-1][1]
                prob = (
                    (ensemble_data >= prev_threshold) & (ensemble_data < threshold)
                ).sum(axis=1) / len(model_cols) * 100
            
            result_df[f'{model}_{variable}_{category}'] = prob
    
    return result_df