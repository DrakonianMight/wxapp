#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Variable name mapper for standardizing variable names across different data sources.

This module provides a centralized mapping system to ensure that variables with
the same physical meaning (e.g., temperature, wind speed) are properly recognized
and compared across different model sources (Open-Meteo, AWS API, etc.).
"""

from typing import Dict, List, Optional, Set


class VariableMapper:
    """
    Centralized variable name mapping across different weather data sources.
    
    This class handles the conversion between different data source-specific
    variable names and canonical (standard) variable names used in wxapp.
    
    For example:
    - AWS API might call temperature: "t2", "temp_2m", "air_temperature_2m"
    - Open-Meteo calls it: "temperature_2m"
    - The canonical name we use is: "temperature_2m"
    """
    
    def __init__(self):
        """Initialize variable mapper with canonical mappings"""
        
        # Canonical variable name → List of alternative names across sources
        self.canonical_to_alternatives: Dict[str, Set[str]] = {
            # Temperature
            'temperature_2m': {
                'temperature_2m', 't2', 'temp_2m', 'air_temperature_2m',
                't2m', '2m_temperature', 'temp', 't', 'tas', 'air_temp'
            },
            'temperature_2m_max': {
                'temperature_2m_max', 't2_max', 'tmax', 'temp_max',
                '2m_temperature_max', 'temperature_max'
            },
            'temperature_2m_min': {
                'temperature_2m_min', 't2_min', 'tmin', 'temp_min',
                '2m_temperature_min', 'temperature_min'
            },
            'dewpoint_2m': {
                'dewpoint_2m', 'd2', 'dewpoint', 'dew_point_2m',
                'd2m', 'dwpt', 'dew_point'
            },
            
            # Wind
            'wind_speed_10m': {
                'wind_speed_10m', 'ws10', 'wind_speed', 'wspd',
                '10m_wind_speed', 'ws_10m', 'u10', 'v10', 'ws', 'wind'
            },
            'wind_direction_10m': {
                'wind_direction_10m', 'wd10', 'wind_direction', 'wdir',
                '10m_wind_direction', 'wd_10m', 'wd', 'wdir_10m'
            },
            'wind_gusts_10m': {
                'wind_gusts_10m', 'wg10', 'wind_gust_10m', 'wind_gusts',
                'wpgt', 'gust_10m', 'gusts', 'gust', 'wg'
            },
            
            # Precipitation
            'precipitation': {
                'precipitation', 'tp', 'total_precipitation', 'precip',
                'prcp', 'rain', 'rainfall', 'pr', 'accum_precip'
            },
            'snowfall': {
                'snowfall', 'snow', 'snow_depth', 'sf', 'snow_accum'
            },
            
            # Humidity
            'relative_humidity_2m': {
                'relative_humidity_2m', 'rh2', 'rh_2m', 'humidity',
                'rhum', 'rh', 'relative_humidity', 'hur', 'rel_hum'
            },
            
            # Pressure
            'pressure_msl': {
                'pressure_msl', 'msl', 'mean_sea_level_pressure', 'pressure',
                'mslp', 'pres', 'sea_level_pressure', 'slp', 'pmsl', 'psl'
            },
            'surface_pressure': {
                'surface_pressure', 'sp', 'sfc_pressure', 'ps', 'sfc_pres'
            },
            
            # Cloud and Radiation
            'cloud_cover': {
                'cloud_cover', 'tcc', 'total_cloud_cover', 'cloudcover',
                'cloud', 'clouds', 'cld', 'clt'
            },
            'cloud_cover_low': {
                'cloud_cover_low', 'lcc', 'low_cloud_cover', 'low_cloud'
            },
            'cloud_cover_mid': {
                'cloud_cover_mid', 'mcc', 'mid_cloud_cover', 'medium_cloud_cover', 'mid_cloud'
            },
            'cloud_cover_high': {
                'cloud_cover_high', 'hcc', 'high_cloud_cover', 'high_cloud'
            },
            'shortwave_radiation': {
                'shortwave_radiation', 'ssrd', 'solar_radiation', 'sr',
                'surface_solar_radiation', 'swr', 'ghi',
                'sw_dn_avg', 'sw_dn', 'surface_global_irradiance',
                'downwelling_shortwave', 'ghi_avg', 'swdown', 'rsds',
                'global_horizontal_irradiance', 'sw_radiation'
            },
            'direct_radiation': {
                'direct_radiation', 'direct_normal_irradiance', 'dni',
                'beam_radiation', 'dni_avg', 'sw_dir', 'direct_solar'
            },
            'diffuse_radiation': {
                'diffuse_radiation', 'diffuse_horizontal_irradiance', 'dhi',
                'diffuse_solar_radiation', 'dhi_avg', 'sw_diff', 'diffuse_solar'
            },
            'longwave_radiation': {
                'longwave_radiation', 'lw_dn', 'lw_down', 'lwdown',
                'longwave_down', 'downwelling_longwave', 'rlds'
            },
            
            # Wave parameters (if applicable)
            'wave_height': {
                'wave_height', 'hs', 'significant_wave_height', 'swh',
                'swell_wave_height'
            },
            'wave_period': {
                'wave_period', 'tp', 'peak_wave_period', 'wave_period_peak'
            },
            'wave_direction': {
                'wave_direction', 'wd', 'mean_wave_direction', 'mwd'
            },
            
            # Other meteorological variables
            'visibility': {
                'visibility', 'vis', 'horizontal_visibility'
            },
            'cape': {
                'cape', 'convective_available_potential_energy'
            },
            'lifted_index': {
                'lifted_index', 'li'
            },
            'soil_temperature_0_to_7cm': {
                'soil_temperature_0_to_7cm', 'st0_7', 'soil_temp_0_7'
            },
            'soil_moisture_0_to_7cm': {
                'soil_moisture_0_to_7cm', 'sm0_7', 'soil_moisture_0_7'
            },
        }
        
        # Build reverse mapping: alternative name → canonical name
        self.alternative_to_canonical: Dict[str, str] = {}
        for canonical, alternatives in self.canonical_to_alternatives.items():
            for alt in alternatives:
                self.alternative_to_canonical[alt.lower()] = canonical
    
    def to_canonical(self, variable_name: str) -> str:
        """
        Convert any variable name to its canonical form.
        
        Args:
            variable_name: Variable name from any data source
        
        Returns:
            Canonical variable name. If no mapping exists, returns original name.
        
        Examples:
            >>> mapper = VariableMapper()
            >>> mapper.to_canonical('t2')
            'temperature_2m'
            >>> mapper.to_canonical('ws10')
            'wind_speed_10m'
            >>> mapper.to_canonical('temperature_2m')
            'temperature_2m'
        """
        return self.alternative_to_canonical.get(variable_name.lower(), variable_name)
    
    def from_canonical(self, canonical_name: str, target_source: Optional[str] = None) -> str:
        """
        Convert canonical name to source-specific name.
        
        Args:
            canonical_name: Canonical variable name
            target_source: Target data source ('aws', 'open-meteo', 'meteostat', etc.)
                          If None, returns the canonical name.
        
        Returns:
            Source-specific variable name, or canonical if no mapping exists.
        
        Note:
            Currently returns canonical name as most sources accept it.
            Can be extended if specific sources require different names.
        """
        # Most sources now use canonical names, but this can be extended
        # if specific sources need different naming conventions
        
        if target_source == 'aws':
            # AWS API specific mappings (if they differ from canonical)
            aws_specific = {
                'temperature_2m': 't2',
                'wind_speed_10m': 'ws10',
                'wind_direction_10m': 'wd10',
                'precipitation': 'tp',
                # Add more if needed
            }
            return aws_specific.get(canonical_name, canonical_name)
        
        elif target_source == 'meteostat':
            # Meteostat specific mappings
            meteostat_specific = {
                'temperature_2m': 'temp',
                'dewpoint_2m': 'dwpt',
                'relative_humidity_2m': 'rhum',
                'wind_direction_10m': 'wdir',
                'wind_speed_10m': 'wspd',
                'wind_gusts_10m': 'wpgt',
                'surface_pressure': 'pres',
                'precipitation': 'prcp',
            }
            return meteostat_specific.get(canonical_name, canonical_name)
        
        # Default: return canonical name (Open-Meteo uses canonical names)
        return canonical_name
    
    def are_equivalent(self, var1: str, var2: str) -> bool:
        """
        Check if two variable names refer to the same physical parameter.
        
        Args:
            var1: First variable name
            var2: Second variable name
        
        Returns:
            True if variables are equivalent, False otherwise.
        
        Examples:
            >>> mapper = VariableMapper()
            >>> mapper.are_equivalent('temperature_2m', 't2')
            True
            >>> mapper.are_equivalent('temperature_2m', 'wind_speed_10m')
            False
        """
        canonical1 = self.to_canonical(var1)
        canonical2 = self.to_canonical(var2)
        return canonical1 == canonical2
    
    def get_all_canonical_names(self) -> List[str]:
        """
        Get list of all canonical variable names.
        
        Returns:
            Sorted list of canonical variable names
        """
        return sorted(list(self.canonical_to_alternatives.keys()))
    
    def get_alternatives(self, canonical_name: str) -> Set[str]:
        """
        Get all alternative names for a canonical variable.
        
        Args:
            canonical_name: Canonical variable name
        
        Returns:
            Set of alternative names (including canonical name)
        """
        return self.canonical_to_alternatives.get(canonical_name, {canonical_name})
    
    def standardize_variable_list(self, variables: List[str]) -> List[str]:
        """
        Convert a list of variables to canonical names.
        
        Args:
            variables: List of variable names (possibly from different sources)
        
        Returns:
            List of canonical variable names
        
        Examples:
            >>> mapper = VariableMapper()
            >>> mapper.standardize_variable_list(['t2', 'ws10', 'temperature_2m'])
            ['temperature_2m', 'wind_speed_10m', 'temperature_2m']
        """
        return [self.to_canonical(var) for var in variables]
    
    def find_common_variables(
        self, 
        source1_vars: List[str], 
        source2_vars: List[str]
    ) -> List[str]:
        """
        Find variables that are common between two data sources.
        
        Args:
            source1_vars: List of variables from first source
            source2_vars: List of variables from second source
        
        Returns:
            List of canonical variable names available in both sources
        
        Examples:
            >>> mapper = VariableMapper()
            >>> aws_vars = ['t2', 'ws10', 'tp']
            >>> om_vars = ['temperature_2m', 'wind_speed_10m', 'cloud_cover']
            >>> mapper.find_common_variables(aws_vars, om_vars)
            ['temperature_2m', 'wind_speed_10m']
        """
        canonical1 = set(self.standardize_variable_list(source1_vars))
        canonical2 = set(self.standardize_variable_list(source2_vars))
        return sorted(list(canonical1.intersection(canonical2)))


# Global instance for convenience
_mapper = None

def get_mapper() -> VariableMapper:
    """Get global VariableMapper instance (singleton)"""
    global _mapper
    if _mapper is None:
        _mapper = VariableMapper()
    return _mapper


# Convenience functions using global mapper
def to_canonical(variable_name: str) -> str:
    """Convert variable name to canonical form"""
    return get_mapper().to_canonical(variable_name)


def are_equivalent(var1: str, var2: str) -> bool:
    """Check if two variable names are equivalent"""
    return get_mapper().are_equivalent(var1, var2)


def standardize_variables(variables: List[str]) -> List[str]:
    """Standardize a list of variable names"""
    return get_mapper().standardize_variable_list(variables)


def find_common_variables(source1_vars: List[str], source2_vars: List[str]) -> List[str]:
    """Find common variables between two sources"""
    return get_mapper().find_common_variables(source1_vars, source2_vars)


if __name__ == "__main__":
    # Example usage and testing
    mapper = VariableMapper()
    
    print("Variable Mapping Examples:")
    print("-" * 50)
    
    # Test canonical conversion
    test_vars = ['t2', 'temperature_2m', 'ws10', 'wind_speed_10m', 'tp', 'precipitation']
    print("\nCanonical conversion:")
    for var in test_vars:
        print(f"  {var:20s} → {mapper.to_canonical(var)}")
    
    # Test equivalence
    print("\nEquivalence testing:")
    print(f"  't2' == 'temperature_2m': {mapper.are_equivalent('t2', 'temperature_2m')}")
    print(f"  'ws10' == 'wind_speed_10m': {mapper.are_equivalent('ws10', 'wind_speed_10m')}")
    print(f"  't2' == 'ws10': {mapper.are_equivalent('t2', 'ws10')}")
    
    # Test common variables
    print("\nFinding common variables:")
    aws_vars = ['t2', 'ws10', 'wd10', 'tp', 'rh2']
    om_vars = ['temperature_2m', 'wind_speed_10m', 'cloud_cover', 'precipitation']
    common = mapper.find_common_variables(aws_vars, om_vars)
    print(f"  AWS vars: {aws_vars}")
    print(f"  OpenMeteo vars: {om_vars}")
    print(f"  Common: {common}")
    
    # Show all canonical names
    print("\nAll canonical variable names:")
    for i, name in enumerate(mapper.get_all_canonical_names(), 1):
        print(f"  {i:2d}. {name}")
