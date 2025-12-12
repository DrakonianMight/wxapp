#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract weather data from AWS API (GSO, ACCESS-G, ACCESS-GE, ACCESS-CE models)"""

import pandas as pd
import requests
import xarray as xr
import io
from typing import List, Optional, Dict
from datetime import datetime

# Model configurations
MODELS = ["gso", "access-g", "access-ge", "access-ce"]
CE_DOMAINS = ["adelaide", "brisbane", "sydney", "darwin", "canberra", "hobart", "melbourne", "perth", "nqld"]
DEFAULT_GSO_DOMAIN = "australia"
DEFAULT_CE_DOMAIN = "brisbane"


class AWSAPIClient:
    """Client for AWS weather API with authentication"""
    
    def __init__(self, base_url: str, id_token: str):
        """
        Initialize AWS API client
        
        Args:
            base_url: Base URL for the API (e.g., https://...amazonaws.com/prod)
            id_token: AWS Cognito ID token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.id_token = id_token
        self.headers = {
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json"
        }
    
    def get_metadata(self, model: str, domain: Optional[str] = None) -> Dict:
        """
        Get metadata for a model (available variables, latest run, etc.)
        
        Args:
            model: Model name (gso, access-g, access-ge, access-ce)
            domain: Domain name (required for access-ce, optional for gso)
        
        Returns:
            Dictionary with metadata
        """
        url = f"{self.base_url}/metadata/{model}"
        params = {}
        
        if model == "access-ce":
            if not domain:
                raise ValueError("Domain is required for ACCESS-CE metadata")
            params["domain"] = domain
        elif model == "gso" and domain:
            params["domain"] = domain or DEFAULT_GSO_DOMAIN
        
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        
        if response.status_code == 401:
            raise PermissionError("Unauthorized: token expired or invalid")
        if response.status_code != 200:
            raise RuntimeError(f"Metadata API error ({model}) {response.status_code}: {response.text[:300]}")
        
        return response.json()
    
    def get_available_variables(self, model: str, domain: Optional[str] = None) -> List[str]:
        """
        Get list of available variables for a model
        
        Args:
            model: Model name
            domain: Domain name (for access-ce or gso)
        
        Returns:
            List of variable names
        """
        data = self.get_metadata(model, domain)
        
        # Try different possible keys for variables
        vars_list = data.get("available_variables")
        if vars_list is None:
            vars_list = data.get("variables") or (data.get("data", {}).get("available_variables"))
        
        if not isinstance(vars_list, (list, tuple)) or len(vars_list) == 0:
            raise ValueError(f"No variables found in metadata response for {model}")
        
        return list(vars_list)
    
    def extract_point_data(
        self,
        model: str,
        lon: float,
        lat: float,
        variables: List[str],
        domain: Optional[str] = None
    ) -> xr.Dataset:
        """
        Extract data for a single point
        
        Args:
            model: Model name
            lon: Longitude
            lat: Latitude
            variables: List of variables to extract
            domain: Domain name (for access-ce or gso)
        
        Returns:
            xarray Dataset with extracted data
        """
        url = f"{self.base_url}/extract/{model}"
        
        payload = {"x": [lon], "y": [lat]}
        if variables:
            payload["variables"] = variables
        
        if model == "access-ce":
            if not domain:
                raise ValueError("Domain is required for ACCESS-CE")
            payload["domain"] = domain
        elif model == "gso":
            payload["domain"] = domain or DEFAULT_GSO_DOMAIN
        
        response = requests.post(url, json=payload, headers=self.headers, timeout=60)
        
        if response.status_code == 401:
            raise PermissionError("Unauthorized: token expired or invalid")
        if response.status_code != 200:
            raise RuntimeError(f"Extract API error ({model}) {response.status_code}: {response.text[:300]}")
        
        ds = xr.open_dataset(io.BytesIO(response.content), decode_timedelta=False)
        
        # Sort by time if present
        time_dims = ['time', 'valid_time', 'forecast_time']
        for time_dim in time_dims:
            if time_dim in ds.dims or time_dim in ds.coords:
                ds = ds.sortby(time_dim)
                break
        
        # Squeeze single-point dimensions (but not ensemble)
        for dim in ["point", "station", "location"]:
            if dim in ds.dims and ds.dims[dim] == 1:
                ds = ds.squeeze(dim)
        
        return ds


def get_data_for_point(
    base_url: str,
    id_token: str,
    model: str,
    lat: float,
    lon: float,
    variables: List[str],
    domain: Optional[str] = None
) -> pd.DataFrame:
    """
    Get data for a single point and convert to DataFrame
    
    Args:
        base_url: API base URL
        id_token: Authentication token
        model: Model name
        lat: Latitude
        lon: Longitude
        variables: List of variables
        domain: Domain (for access-ce or gso)
    
    Returns:
        DataFrame with time series data
    """
    client = AWSAPIClient(base_url, id_token)
    ds = client.extract_point_data(model, lon, lat, variables, domain)
    
    # Convert to DataFrame
    df = ds.to_dataframe().reset_index()
    
    # Add model column
    df['model'] = model
    
    return df
