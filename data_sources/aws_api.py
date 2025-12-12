#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AWS API data source (GSO, ACCESS-G, ACCESS-GE, ACCESS-CE models)"""

import pandas as pd
import streamlit as st
from typing import List, Optional
from datetime import datetime
import xarray as xr
import sys
import os

# Add parent directory to path to import aws_api_extract
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base import DataSource
from aws_api_extract import AWSAPIClient, get_data_for_point, MODELS, CE_DOMAINS, DEFAULT_CE_DOMAIN


class AWSAPIDataSource(DataSource):
    """Data source for AWS API weather models (GSO, ACCESS-G, ACCESS-GE, ACCESS-CE)"""
    
    def __init__(self, base_url: str, id_token: str, domain: Optional[str] = None):
        """
        Initialize AWS API data source
        
        Args:
            base_url: API base URL
            id_token: AWS Cognito ID token
            domain: Default domain for CE models
        """
        super().__init__(name="AWS API (GSO/ACCESS)", supports_ensemble=True)
        self.base_url = base_url
        self.id_token = id_token
        self.default_domain = domain or DEFAULT_CE_DOMAIN
        self.client = AWSAPIClient(base_url, id_token)
        
        # Cache for metadata by model and domain
        self._metadata_cache = {}
    
    def _get_model_variables(self, model: str, domain: Optional[str] = None) -> List[str]:
        """
        Fetch available variables for a model from metadata endpoint
        
        Args:
            model: Model name
            domain: Domain (for access-ce or gso)
        
        Returns:
            List of available variable names
        """
        cache_key = f"{model}_{domain or 'default'}"
        
        if cache_key not in self._metadata_cache:
            try:
                variables = self.client.get_available_variables(model, domain)
                self._metadata_cache[cache_key] = variables
            except Exception as e:
                st.warning(f"Failed to fetch metadata for {model}: {str(e)}")
                return []
        
        return self._metadata_cache[cache_key]
    
    def _dataset_to_dataframe(self, ds: xr.Dataset, model: str, is_ensemble: bool = False) -> pd.DataFrame:
        """
        Convert xarray Dataset to DataFrame suitable for plotting
        
        Args:
            ds: xarray Dataset
            model: Model name (to add as column)
            is_ensemble: If True, pivot ensemble members to wide format for plotting
        
        Returns:
            DataFrame with datetime, variable columns, and optional member column
        """
        # Check for ensemble dimension
        has_ensemble = 'member' in ds.dims or 'ensemble' in ds.dims or 'number' in ds.dims
        
        if has_ensemble:
            # Find the ensemble dimension name
            ens_dim = None
            for dim_name in ['member', 'ensemble', 'number']:
                if dim_name in ds.dims:
                    ens_dim = dim_name
                    break
            
            # Convert to dataframe with multi-index
            df = ds.to_dataframe().reset_index()
            
            # Rename ensemble dimension to 'member'
            if ens_dim and ens_dim != 'member':
                df = df.rename(columns={ens_dim: 'member'})
            
            # Find time column
            time_col = None
            for col in ['time', 'valid_time', 'forecast_time', 'datetime']:
                if col in df.columns:
                    time_col = col
                    break
            
            if time_col and time_col != 'datetime':
                df = df.rename(columns={time_col: 'datetime'})
            
            # Ensure datetime is datetime64
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            
            # For ensemble plotting, pivot to wide format
            # Expected format: variable_model_member_XX columns
            if is_ensemble and 'member' in df.columns:
                # Get variable columns (excluding datetime, member, model)
                var_cols = [col for col in df.columns if col not in ['datetime', 'member', 'model', 'lat', 'lon', 'latitude', 'longitude']]
                
                if var_cols and 'datetime' in df.columns:
                    # Pivot each variable
                    result_df = df[['datetime']].drop_duplicates().reset_index(drop=True)
                    
                    for var in var_cols:
                        # Create pivot with datetime as index and member as columns
                        pivot_df = df.pivot_table(
                            index='datetime',
                            columns='member',
                            values=var,
                            aggfunc='first'
                        )
                        
                        # Rename columns to match expected format: variable_model_member_XX
                        pivot_df.columns = [f'{var}_{model}_member_{str(col).zfill(2)}' for col in pivot_df.columns]
                        
                        # Merge with result
                        result_df = result_df.merge(pivot_df.reset_index(), on='datetime', how='outer')
                    
                    # Add model column
                    result_df['model'] = model
                    
                    return result_df
            
            # Add model column for non-pivoted data
            df['model'] = model
            return df
        else:
            df = ds.to_dataframe().reset_index()
            
            # Find time column
            time_col = None
            for col in ['time', 'valid_time', 'forecast_time', 'datetime']:
                if col in df.columns:
                    time_col = col
                    break
            
            if time_col and time_col != 'datetime':
                df = df.rename(columns={time_col: 'datetime'})
            
            # Ensure datetime is datetime64
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            
            # Add model column
            df['model'] = model
            
            return df
    
    def get_deterministic_data(
        self,
        lat: float,
        lon: float,
        site: str,
        variables: List[str],
        data_type: str,
        models: List[str]
    ) -> pd.DataFrame:
        """Get deterministic forecast data"""
        
        # Filter to deterministic models only (gso is also available as deterministic)
        det_models = [m for m in models if m in ['gso', 'access-g']]
        
        if not det_models:
            return pd.DataFrame()
        
        all_dfs = []
        
        for model in det_models:
            try:
                # Determine domain
                domain = None
                if model == 'gso':
                    domain = 'australia'
                
                # Get available variables from metadata
                available_vars = self._get_model_variables(model, domain)
                
                if not available_vars:
                    st.warning(f"No variables available for {model}")
                    continue
                
                # Use requested variables that are available, or all if none specified
                if variables:
                    api_variables = [v for v in variables if v in available_vars]
                else:
                    api_variables = available_vars
                
                if not api_variables:
                    st.warning(f"None of the requested variables are available for {model}")
                    continue
                
                # Get data
                ds = self.client.extract_point_data(
                    model=model,
                    lon=lon,
                    lat=lat,
                    variables=api_variables,
                    domain=domain
                )
                
                # Convert to DataFrame (deterministic format)
                df = self._dataset_to_dataframe(ds, model, is_ensemble=False)
                all_dfs.append(df)
                
            except Exception as e:
                st.warning(f"Failed to fetch {model}: {str(e)}")
                continue
        
        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True)
        return pd.DataFrame()
    
    def get_ensemble_data(
        self,
        lat: float,
        lon: float,
        site: str,
        variables: List[str],
        data_type: str,
        models: List[str]
    ) -> pd.DataFrame:
        """Get ensemble forecast data"""
        
        # Filter to ensemble models only (gso can also be used as ensemble)
        ens_models = [m for m in models if m in ['gso', 'access-ge', 'access-ce']]
        
        if not ens_models:
            return pd.DataFrame()
        
        all_dfs = []
        
        for model in ens_models:
            try:
                # Determine domain (CE requires domain)
                domain = None
                if model == 'access-ce':
                    # Check session state for domain selection
                    domain = st.session_state.get('aws_domain', self.default_domain)
                elif model == 'gso':
                    domain = 'australia'
                
                # Get available variables from metadata
                available_vars = self._get_model_variables(model, domain)
                
                if not available_vars:
                    st.warning(f"No variables available for {model}")
                    continue
                
                # Use requested variables that are available, or all if none specified
                if variables:
                    api_variables = [v for v in variables if v in available_vars]
                else:
                    api_variables = available_vars
                
                if not api_variables:
                    st.warning(f"None of the requested variables are available for {model}")
                    continue
                
                # Get data
                ds = self.client.extract_point_data(
                    model=model,
                    lon=lon,
                    lat=lat,
                    variables=api_variables,
                    domain=domain
                )
                
                # Convert to DataFrame (ensemble format - pivot members to columns)
                df = self._dataset_to_dataframe(ds, model, is_ensemble=True)
                all_dfs.append(df)
                
            except Exception as e:
                st.warning(f"Failed to fetch {model}: {str(e)}")
                continue
        
        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True)
        return pd.DataFrame()
    
    def get_available_models(self, forecast_type: str = "deterministic") -> List[str]:
        """Get list of available models"""
        if forecast_type == "deterministic":
            return ["gso", "access-g"]
        elif forecast_type == "ensemble":
            return ["gso", "access-ge", "access-ce"]
        else:
            return MODELS
    
    def get_available_variables(self, data_type: str = "hourly") -> List[str]:
        """
        Get list of available variables by querying metadata for all models
        
        Returns union of all variables from all models
        """
        all_vars = set()
        
        # Get variables from all models
        for model in MODELS:
            try:
                domain = None
                if model == 'access-ce':
                    domain = st.session_state.get('aws_domain', self.default_domain)
                elif model == 'gso':
                    domain = 'australia'
                
                vars_list = self._get_model_variables(model, domain)
                all_vars.update(vars_list)
            except Exception:
                continue
        
        return sorted(list(all_vars))
    
    def get_model_specific_variables(self, model: str, forecast_type: str = 'deterministic', domain: str = None) -> List[str]:
        """
        Get list of variables available for a specific model
        
        Args:
            model: Model name (gso, access-g, access-ge, access-ce)
            forecast_type: 'deterministic' or 'ensemble' (not used for AWS API)
            domain: Domain for CE models or GSO
        
        Returns:
            List of variable names available for this model
        """
        # Use appropriate domain
        if model == 'gso':
            domain = 'australia'
        elif model == 'access-ce' and not domain:
            domain = st.session_state.get('aws_domain', self.default_domain)
        
        try:
            return self._get_model_variables(model, domain)
        except Exception as e:
            st.warning(f"Failed to get variables for {model}: {str(e)}")
            return []
