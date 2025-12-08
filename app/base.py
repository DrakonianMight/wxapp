# ========================================
# File: data_sources/base.py
"""Base class for data sources"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict, Any

class DataSource(ABC):
    """Abstract base class for weather data sources"""
    
    def __init__(self, name: str, supports_ensemble: bool = False):
        self.name = name
        self.supports_ensemble = supports_ensemble
    
    @abstractmethod
    def get_deterministic_data(
        self, 
        lat: float, 
        lon: float, 
        site: str, 
        variables: List[str], 
        data_type: str,
        models: List[str]
    ) -> pd.DataFrame:
        """Fetch deterministic forecast data"""
        pass
    
    @abstractmethod
    def get_ensemble_data(
        self, 
        lat: float, 
        lon: float, 
        site: str, 
        variables: List[str], 
        data_type: str,
        models: List[str]
    ) -> pd.DataFrame:
        """Fetch ensemble forecast data"""
        pass
    
    @abstractmethod
    def get_available_models(self, forecast_type: str = 'deterministic') -> List[str]:
        """Return list of available models for this data source"""
        pass
    
    @abstractmethod
    def get_available_variables(self, data_type: str = 'hourly') -> List[str]:
        """Return list of available variables for this data source"""
        pass
