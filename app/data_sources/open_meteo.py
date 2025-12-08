# ========================================
# File: data_sources/open_meteo.py
"""Open-Meteo data source implementation"""
import pandas as pd
from typing import List
from base import DataSource
import om_extract
import streamlit as st

class OpenMeteoDataSource(DataSource):
    """Open-Meteo forecast data source"""
    
    def __init__(self):
        super().__init__(name="Open-Meteo", supports_ensemble=True)
        
        self.deterministic_models = [
            'ecmwf_ifs', 
            'ecmwf_aifs025', 
            'bom_access_global', 
            'gfs_global', 
            'cma_grapes_global', 
            'ukmo_global_deterministic_10km'
        ]
        
        self.ensemble_models = [
            'ecmwf_ifs_ensemble',
            'gfs_ensemble',
        ]
    
    def get_deterministic_data(
        self, 
        lat: float, 
        lon: float, 
        site: str, 
        variables: List[str], 
        data_type: str,
        models: List[str]
    ) -> pd.DataFrame:
        """Fetch deterministic forecast data from Open-Meteo"""
        lat_list = [str(lat)]
        lon_list = [str(lon)]
        site_list = [site]
        
        if data_type == 'hourly':
            df = om_extract.getData(lat_list, lon_list, site_list, variables=variables, models=models)
        else:  # daily
            df = om_extract.getDailyData(lat_list, lon_list, site_list, variables=variables, models=models)
        
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
        """Fetch ensemble forecast data from Open-Meteo"""

        lat_list = [str(lat)]
        lon_list = [str(lon)]
        site_list = [site]
        
        if data_type == 'hourly':
            # You may need to create getEnsembleData in om_extract module
            if hasattr(om_extract, 'getEnsembleData'):
                df = om_extract.getEnsembleData(lat_list, lon_list, site_list, variables=variables, models=models)
            else:
                # Fallback to regular getData
                df = om_extract.getData(lat_list, lon_list, site_list, variables=variables, models=models)
        else:  # daily
            if hasattr(om_extract, 'getDailyEnsembleData'):
                df = om_extract.getDailyEnsembleData(lat_list, lon_list, site_list, variables=variables, models=models)
            else:
                df = om_extract.getDailyData(lat_list, lon_list, site_list, variables=variables, models=models)
        
        return df
    
    def get_available_models(self, forecast_type: str = 'deterministic') -> List[str]:
        """Return list of available models"""
        if forecast_type == 'deterministic':
            return self.deterministic_models
        else:
            return self.ensemble_models
    
    def get_available_variables(self, data_type: str = 'hourly') -> List[str]:
        """Return list of available variables"""
        from config import BASE_HOURLY_PARAMS, DAILY_PARAMS
        if data_type == 'hourly':
            return BASE_HOURLY_PARAMS
        else:
            return DAILY_PARAMS
