#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatic variable categorization and grouping for multi-source comparison.

This module automatically categorizes weather variables by type and helps users
see which variables from different data sources can be compared together.
"""

from typing import Dict, List, Set, Tuple
from collections import defaultdict, OrderedDict
from utils.variable_mapper import VariableMapper


class VariableCategorizer:
    """Categorize and group variables for easy multi-source comparison"""
    
    # Category definitions with emoji icons
    CATEGORIES = OrderedDict([
        ('temperature', {
            'name': '🌡️ Temperature',
            'icon': '🌡️',
            'keywords': ['temperature', 'temp', 'dewpoint', 'dew', 'heat', 'cold']
        }),
        ('wind', {
            'name': '💨 Wind',
            'icon': '💨',
            'keywords': ['wind', 'gust', 'breeze']
        }),
        ('precipitation', {
            'name': '🌧️ Precipitation',
            'icon': '🌧️',
            'keywords': ['precip', 'rain', 'snow', 'rainfall', 'snowfall', 'prcp']
        }),
        ('humidity', {
            'name': '💧 Humidity & Moisture',
            'icon': '💧',
            'keywords': ['humidity', 'moisture', 'rhum', 'rh']
        }),
        ('solar', {
            'name': '☀️ Solar Radiation',
            'icon': '☀️',
            'keywords': ['solar', 'radiation', 'irradiance', 'shortwave', 'sw_', 'ghi', 'dni', 'dhi']
        }),
        ('cloud', {
            'name': '☁️ Cloud Cover',
            'icon': '☁️',
            'keywords': ['cloud', 'cld', 'tcc']
        }),
        ('pressure', {
            'name': '🌐 Pressure',
            'icon': '🌐',
            'keywords': ['pressure', 'pres', 'mslp', 'slp']
        }),
        ('other', {
            'name': '📊 Other Variables',
            'icon': '📊',
            'keywords': []
        })
    ])
    
    def __init__(self):
        """Initialize the categorizer with variable mapper"""
        self.mapper = VariableMapper()
    
    def categorize_variable(self, variable: str) -> str:
        """
        Categorize a single variable
        
        Args:
            variable: Variable name
        
        Returns:
            Category key (e.g., 'temperature', 'wind', etc.)
        """
        var_lower = variable.lower()
        
        # Check each category's keywords
        for category_key, category_info in self.CATEGORIES.items():
            if category_key == 'other':
                continue
            
            keywords = category_info['keywords']
            if any(keyword in var_lower for keyword in keywords):
                return category_key
        
        # Default to 'other' if no match
        return 'other'
    
    def group_variables_by_category(
        self, 
        variables: List[str]
    ) -> OrderedDict:
        """
        Group variables by category
        
        Args:
            variables: List of variable names
        
        Returns:
            OrderedDict of {category_key: [variables]}
        """
        grouped = OrderedDict()
        
        # Initialize all categories
        for category_key in self.CATEGORIES.keys():
            grouped[category_key] = []
        
        # Categorize each variable
        for var in variables:
            category = self.categorize_variable(var)
            grouped[category].append(var)
        
        # Remove empty categories
        grouped = OrderedDict((k, v) for k, v in grouped.items() if v)
        
        return grouped
    
    def find_equivalent_variables(
        self,
        source_variables: Dict[str, List[str]]
    ) -> OrderedDict:
        """
        Find equivalent variables across multiple data sources
        
        Args:
            source_variables: Dict of {source_name: [variable_names]}
        
        Returns:
            OrderedDict of {canonical_variable: {source_name: [source_variable_names]}}
        """
        # Map all variables to canonical form
        canonical_groups = defaultdict(lambda: defaultdict(list))
        
        for source_name, var_list in source_variables.items():
            for var in var_list:
                canonical = self.mapper.to_canonical(var)
                canonical_groups[canonical][source_name].append(var)
        
        # Sort by canonical name
        return OrderedDict(sorted(canonical_groups.items()))
    
    def create_variable_comparison_matrix(
        self,
        source_variables: Dict[str, List[str]]
    ) -> Tuple[OrderedDict, OrderedDict]:
        """
        Create a matrix showing which sources have which variables
        
        Args:
            source_variables: Dict of {source_name: [variable_names]}
        
        Returns:
            Tuple of:
            - OrderedDict of {canonical_var: {source: [actual_vars]}}
            - OrderedDict of {category: [canonical_vars_in_category]}
        """
        # Find equivalent variables
        equivalents = self.find_equivalent_variables(source_variables)
        
        # Categorize by canonical name
        categories = OrderedDict()
        for category_key in self.CATEGORIES.keys():
            categories[category_key] = []
        
        for canonical_var in equivalents.keys():
            category = self.categorize_variable(canonical_var)
            categories[category].append(canonical_var)
        
        # Remove empty categories
        categories = OrderedDict((k, v) for k, v in categories.items() if v)
        
        return equivalents, categories
    
    def format_variable_label(
        self,
        variable: str,
        source_availability: Dict[str, List[str]] = None,
        show_sources: bool = True
    ) -> str:
        """
        Format a variable label with source information
        
        Args:
            variable: Variable name (canonical or source-specific)
            source_availability: Dict of {source_name: [variables]} (optional)
            show_sources: Whether to show which sources provide this variable
        
        Returns:
            Formatted label string
        """
        canonical = self.mapper.to_canonical(variable)
        
        # Build label
        if canonical != variable:
            label = f"{canonical} ({variable})"
        else:
            label = canonical
        
        # Add source information if available
        if show_sources and source_availability:
            sources = []
            for source_name, vars_list in source_availability.items():
                if any(self.mapper.to_canonical(v) == canonical for v in vars_list):
                    sources.append(source_name)
            
            if sources:
                if len(sources) == 1:
                    label += f" [{sources[0]}]"
                else:
                    label += f" [{len(sources)} sources]"
        
        return label
    
    def get_common_variables(
        self,
        source_variables: Dict[str, List[str]],
        min_sources: int = 2
    ) -> List[str]:
        """
        Get variables that are available in at least min_sources sources
        
        Args:
            source_variables: Dict of {source_name: [variable_names]}
            min_sources: Minimum number of sources that must have the variable
        
        Returns:
            List of canonical variable names available in >= min_sources
        """
        equivalents = self.find_equivalent_variables(source_variables)
        
        common = []
        for canonical_var, sources_dict in equivalents.items():
            if len(sources_dict) >= min_sources:
                common.append(canonical_var)
        
        return common
    
    def create_category_selectbox_options(
        self,
        variables: List[str],
        include_all: bool = True
    ) -> Tuple[OrderedDict, List]:
        """
        Create categorized options for Streamlit selectbox
        
        Args:
            variables: List of variable names
            include_all: Whether to include an "All Categories" option
        
        Returns:
            Tuple of:
            - OrderedDict of {category_name: [variables]}
            - List of formatted options for selectbox
        """
        # Group by category
        grouped = self.group_variables_by_category(variables)
        
        # Create formatted categories
        category_options = OrderedDict()
        selectbox_options = []
        
        if include_all:
            selectbox_options.append("All Categories")
            category_options["All Categories"] = variables
        
        for category_key, vars_in_category in grouped.items():
            category_info = self.CATEGORIES[category_key]
            category_name = category_info['name']
            category_options[category_name] = vars_in_category
            selectbox_options.append(category_name)
        
        return category_options, selectbox_options


# Global instance
_categorizer = None

def get_categorizer() -> VariableCategorizer:
    """Get global VariableCategorizer instance (singleton)"""
    global _categorizer
    if _categorizer is None:
        _categorizer = VariableCategorizer()
    return _categorizer


# Convenience functions
def categorize_variable(variable: str) -> str:
    """Categorize a variable"""
    return get_categorizer().categorize_variable(variable)


def group_variables(variables: List[str]) -> OrderedDict:
    """Group variables by category"""
    return get_categorizer().group_variables_by_category(variables)


def find_common_variables(source_variables: Dict[str, List[str]], min_sources: int = 2) -> List[str]:
    """Find variables common to at least min_sources"""
    return get_categorizer().get_common_variables(source_variables, min_sources)


if __name__ == "__main__":
    # Example usage
    categorizer = VariableCategorizer()
    
    # Example: Multiple data sources
    sources = {
        'Open-Meteo': [
            'temperature_2m', 'wind_speed_10m', 'wind_direction_10m',
            'shortwave_radiation', 'precipitation', 'cloud_cover',
            'relative_humidity_2m'
        ],
        'AWS API': [
            't2m', 'ws10', 'wd10', 'sw_dn_avg', 'tp', 'tcc', 'rh'
        ],
        'Meteostat': [
            'temp', 'wspd', 'wdir', 'prcp', 'rhum'
        ]
    }
    
    print("=" * 70)
    print("Variable Categorization Example")
    print("=" * 70)
    
    # Create comparison matrix
    equivalents, categories = categorizer.create_variable_comparison_matrix(sources)
    
    # Print by category
    for category_key, vars_in_category in categories.items():
        category_info = categorizer.CATEGORIES[category_key]
        print(f"\n{category_info['name']}")
        print("-" * 70)
        
        for canonical_var in vars_in_category:
            source_vars = equivalents[canonical_var]
            print(f"\n  📌 {canonical_var}")
            for source_name, actual_vars in source_vars.items():
                print(f"     • {source_name:15s}: {', '.join(actual_vars)}")
    
    # Print common variables
    print("\n" + "=" * 70)
    print("Variables Available in Multiple Sources")
    print("=" * 70)
    common = categorizer.get_common_variables(sources, min_sources=2)
    for var in common:
        source_count = len(equivalents[var])
        print(f"  ✓ {var:30s} ({source_count} sources)")
