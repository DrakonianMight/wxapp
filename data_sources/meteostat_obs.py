# ========================================
# File: data_sources/meteostat_obs.py
"""Meteostat observations data source implementation"""
import pandas as pd
from typing import List
from base import DataSource
import ms_extract
import streamlit as st

class MeteostatObsDataSource(DataSource):
    """Meteostat historical observations data source"""
    
    def __init__(self):
        super().__init__(name="Meteostat-Obs", supports_ensemble=False)
        
        # Meteostat doesn't have models, but we'll use this to indicate it's observations
        self.observation_sources = ['meteostat_historical']
        
        # Mapping from meteostat column names to standard variable names
        self.variable_mapping = {
            'temp': 'temperature_2m',
            'dwpt': 'dewpoint_2m',
            'rhum': 'relative_humidity_2m',
            'wdir': 'wind_direction_10m',
            'wspd': 'wind_speed_10m',
            'wpgt': 'wind_gusts_10m',
            'pres': 'surface_pressure',
            'prcp': 'precipitation',
            # Note: meteostat doesn't have shortwave_radiation or cloud_cover percentage
            # 'coco' is a weather condition code, not cloud cover percentage
        }
        
        # Reverse mapping for translating requested variables to meteostat columns
        self.reverse_mapping = {v: k for k, v in self.variable_mapping.items()}
    
    def get_deterministic_data(
        self, 
        lat: float, 
        lon: float, 
        site: str, 
        variables: List[str], 
        data_type: str,
        models: List[str],
        previous_days: int = 1,
        timezone: str = 'UTC'
    ) -> pd.DataFrame:
        """
        Fetch historical observation data from Meteostat
        
        Args:
            lat: Latitude
            lon: Longitude
            site: Site name/identifier
            variables: List of requested variables (in standard format)
            data_type: 'hourly' or 'daily' (currently only hourly supported)
            models: Not used for observations, kept for interface consistency
            previous_days: Number of days of historical data to retrieve
            timezone: Target timezone for the datetime index (default: 'UTC')
        
        Returns:
            DataFrame with standardized column names and structure
        """
        if data_type != 'hourly':
            st.warning("Meteostat observations currently only supports hourly data")
            return pd.DataFrame()
        
        # Get meteostat data with timezone conversion
        locations = [(lat, lon)]
        raw_data = ms_extract.main(locations, previous_days=previous_days, timezone=timezone)
        
        if raw_data is None or raw_data.empty:
            return pd.DataFrame()
        
        # Transform to match the expected format
        df = self._transform_meteostat_data(raw_data, site, variables)
        
        return df
    
    def _transform_meteostat_data(
        self, 
        raw_data: pd.DataFrame, 
        site: str, 
        requested_variables: List[str]
    ) -> pd.DataFrame:
        """
        Transform meteostat data to match the standard format used by other data sources
        
        Args:
            raw_data: Raw DataFrame from meteostat
            site: Site name
            requested_variables: List of variables in standard format
        
        Returns:
            Transformed DataFrame with standard column names
        """
        df = raw_data.copy()
        
        # The raw_data from ms_extract has a timezone-aware DatetimeIndex
        # Reset it to create a 'datetime' column, preserving timezone info
        if isinstance(df.index, pd.DatetimeIndex):
            # Reset index - this creates a column (usually named 'time' by meteostat or index name)
            df = df.reset_index()
            # Find the datetime column (could be 'time', 'index', or unnamed)
            datetime_col = None
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    datetime_col = col
                    break
            
            if datetime_col and datetime_col != 'datetime':
                df = df.rename(columns={datetime_col: 'datetime'})
        elif 'time' in df.columns:
            df = df.rename(columns={'time': 'datetime'})
        
        # Add site column if not present
        if 'site' not in df.columns:
            df['site'] = site
        
        # Add model column to indicate this is observation data
        df['model'] = 'meteostat_obs'
        
        # Rename meteostat columns to standard variable names
        rename_dict = {}
        for meteostat_col, standard_var in self.variable_mapping.items():
            if meteostat_col in df.columns and standard_var in requested_variables:
                rename_dict[meteostat_col] = standard_var
        
        df = df.rename(columns=rename_dict)
        
        # Convert units if necessary
        df = self._convert_units(df)
        
        # Select only requested columns plus metadata
        metadata_cols = ['datetime', 'site', 'model']
        available_vars = [v for v in requested_variables if v in df.columns]
        
        # Add station metadata if available
        optional_cols = ['station_name', 'station_lat', 'station_lon', 'station_id']
        for col in optional_cols:
            if col in df.columns:
                metadata_cols.append(col)
        
        selected_cols = metadata_cols + available_vars
        selected_cols = [col for col in selected_cols if col in df.columns]
        
        df = df[selected_cols]
        
        # Sort by datetime
        if 'datetime' in df.columns:
            df = df.sort_values('datetime')
        
        # If no data variables are available, return empty DataFrame
        if not available_vars:
            return pd.DataFrame()
        
        return df
    
    def _convert_units(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert meteostat units to match Open-Meteo/standard data sources
        
        Meteostat units → Standard units:
        - temp, dwpt: °C → °C (no conversion needed)
        - rhum: % → % (no conversion needed)
        - wspd, wpgt: km/h → m/s (divide by 3.6)
        - wdir: degrees → degrees (no conversion needed)
        - pres: hPa → hPa (no conversion needed)
        - prcp: mm → mm (no conversion needed)
        
        Note: Meteostat does not provide:
        - shortwave_radiation
        - cloud_cover (percentage) - only condition code
        """
        df = df.copy()
        
        # Convert wind speed from km/h to m/s (1 km/h = 0.27778 m/s)
        wind_cols = ['wind_speed_10m', 'wind_gusts_10m']
        for col in wind_cols:
            if col in df.columns:
                # Convert km/h to m/s
                df[col] = df[col] / 3.6
        
        # Ensure pressure is in hPa (Meteostat provides hPa, Open-Meteo uses hPa)
        if 'surface_pressure' in df.columns:
            # No conversion needed - both use hPa
            pass
        
        # Ensure precipitation is in mm (Meteostat provides mm, Open-Meteo uses mm)
        if 'precipitation' in df.columns:
            # No conversion needed - both use mm
            pass
        
        return df
    
    def get_ensemble_data(
        self, 
        lat: float, 
        lon: float, 
        site: str, 
        variables: List[str], 
        data_type: str,
        models: List[str]
    ) -> pd.DataFrame:
        """Meteostat observations don't support ensemble data"""
        st.warning("Meteostat observations do not support ensemble data")
        return pd.DataFrame()
    
    def get_available_models(self, forecast_type: str = 'deterministic') -> List[str]:
        """Return list of available models (for observations, just the source)"""
        if forecast_type == 'deterministic':
            return self.observation_sources
        else:
            return []
    
    def get_available_variables(self, data_type: str = 'hourly') -> List[str]:
        """Return list of available variables from meteostat in standard format"""
        if data_type == 'hourly':
            # Return the standard variable names that we can map from meteostat
            return [
                'temperature_2m',
                'dewpoint_2m',
                'relative_humidity_2m',
                'wind_direction_10m',
                'wind_speed_10m',
                'wind_gusts_10m',
                'surface_pressure',
                'precipitation',
                # Note: Meteostat does not provide:
                # - 'shortwave_radiation'
                # - 'cloud_cover' (only condition code, not percentage)
            ]
        else:
            # Daily aggregations could be added in the future
            return []
