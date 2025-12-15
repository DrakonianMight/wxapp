#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-discover and map variables from AWS API models.

This script queries the AWS API metadata endpoints to discover all available
variables across all models and domains, then automatically suggests mappings
to canonical variable names.
"""

import sys
import os
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aws_api_extract import AWSAPIClient, MODELS, CE_DOMAINS
from utils.variable_mapper import VariableMapper


class AWSVariableDiscovery:
    """Discover and analyze variables from AWS API"""
    
    def __init__(self, client: AWSAPIClient):
        """
        Initialize discovery tool
        
        Args:
            client: Authenticated AWSAPIClient instance
        """
        self.client = client
        self.mapper = VariableMapper()
        
        # Storage for discovered variables
        self.model_variables: Dict[str, List[str]] = {}  # model -> variables
        self.domain_variables: Dict[Tuple[str, str], List[str]] = {}  # (model, domain) -> variables
        self.all_variables: Set[str] = set()
        
    def discover_all_variables(self, verbose: bool = True) -> Dict:
        """
        Discover all available variables from all AWS models
        
        Args:
            verbose: Print progress information
        
        Returns:
            Dictionary with discovery results
        """
        results = {
            'models': {},
            'variables_by_model': {},
            'all_unique_variables': set(),
            'unmapped_variables': set(),
            'suggested_mappings': {}
        }
        
        if verbose:
            print("=" * 60)
            print("AWS API Variable Discovery")
            print("=" * 60)
        
        # Discover variables for each model
        for model in MODELS:
            if verbose:
                print(f"\n📦 Model: {model.upper()}")
            
            model_results = {
                'has_domains': model in ['access-ce', 'gso'],
                'variables': set(),
                'domains': {}
            }
            
            try:
                if model == 'access-ce':
                    # ACCESS-CE has different variables per domain
                    for domain in CE_DOMAINS:
                        if verbose:
                            print(f"   🌏 Domain: {domain}", end=" ... ")
                        
                        try:
                            vars_list = self.client.get_available_variables(model, domain)
                            model_results['domains'][domain] = vars_list
                            model_results['variables'].update(vars_list)
                            results['all_unique_variables'].update(vars_list)
                            
                            if verbose:
                                print(f"✓ {len(vars_list)} variables")
                        
                        except Exception as e:
                            if verbose:
                                print(f"✗ Error: {str(e)[:50]}")
                
                elif model == 'gso':
                    # GSO uses australia domain
                    if verbose:
                        print(f"   🌏 Domain: australia", end=" ... ")
                    
                    try:
                        vars_list = self.client.get_available_variables(model, 'australia')
                        model_results['domains']['australia'] = vars_list
                        model_results['variables'].update(vars_list)
                        results['all_unique_variables'].update(vars_list)
                        
                        if verbose:
                            print(f"✓ {len(vars_list)} variables")
                    
                    except Exception as e:
                        if verbose:
                            print(f"✗ Error: {str(e)[:50]}")
                
                else:
                    # access-g, access-ge don't use domains
                    if verbose:
                        print(f"   ", end="")
                    
                    try:
                        vars_list = self.client.get_available_variables(model, None)
                        model_results['variables'] = set(vars_list)
                        results['all_unique_variables'].update(vars_list)
                        
                        if verbose:
                            print(f"✓ {len(vars_list)} variables")
                    
                    except Exception as e:
                        if verbose:
                            print(f"✗ Error: {str(e)[:50]}")
                
                results['models'][model] = model_results
            
            except Exception as e:
                if verbose:
                    print(f"   ✗ Failed to query {model}: {str(e)[:100]}")
        
        # Analyze mappings
        if verbose:
            print(f"\n" + "=" * 60)
            print(f"📊 Discovery Summary")
            print(f"=" * 60)
            print(f"Total unique variables found: {len(results['all_unique_variables'])}")
        
        # Check which variables are already mapped
        for var in results['all_unique_variables']:
            canonical = self.mapper.to_canonical(var)
            if canonical == var:
                # Not mapped (or is itself canonical)
                if var not in self.mapper.canonical_to_alternatives:
                    results['unmapped_variables'].add(var)
        
        if verbose:
            print(f"Already mapped variables: {len(results['all_unique_variables']) - len(results['unmapped_variables'])}")
            print(f"Unmapped variables: {len(results['unmapped_variables'])}")
        
        # Suggest mappings based on naming patterns
        results['suggested_mappings'] = self._suggest_mappings(results['unmapped_variables'])
        
        return results
    
    def _suggest_mappings(self, unmapped_vars: Set[str]) -> Dict[str, str]:
        """
        Suggest canonical mappings for unmapped variables based on naming patterns
        
        Args:
            unmapped_vars: Set of unmapped variable names
        
        Returns:
            Dictionary of variable -> suggested_canonical mapping
        """
        suggestions = {}
        
        # Common AWS API naming patterns
        patterns = {
            # Temperature
            ('t2m', 't_2m', 'temp_2m', 'air_temp_2m'): 'temperature_2m',
            ('tmax', 't2m_max', 'temp_max'): 'temperature_2m_max',
            ('tmin', 't2m_min', 'temp_min'): 'temperature_2m_min',
            ('td', 'td2m', 'dew_point', 'dew_2m'): 'dewpoint_2m',
            
            # Wind
            ('u10', 'v10', 'ws_10m', 'wspd_10m'): 'wind_speed_10m',
            ('wdir_10m', 'wd_10m'): 'wind_direction_10m',
            ('gust', 'gust_10m', 'wg_10m'): 'wind_gusts_10m',
            
            # Precipitation
            ('precip', 'rain', 'rainfall', 'tp'): 'precipitation',
            
            # Humidity
            ('rh', 'rh_2m', 'rel_hum'): 'relative_humidity_2m',
            
            # Pressure
            ('mslp', 'pmsl', 'slp'): 'pressure_msl',
            ('ps', 'sfc_pres'): 'surface_pressure',
            
            # Clouds
            ('tcc', 'cld', 'cloudcover'): 'cloud_cover',
            
            # Radiation - IMPORTANT AWS-SPECIFIC MAPPINGS
            ('sw_dn_avg', 'sw_dn', 'ghi_avg', 'swdown'): 'shortwave_radiation',
            ('dni_avg', 'dni', 'sw_dir'): 'direct_radiation',
            ('dhi_avg', 'dhi', 'sw_diff'): 'diffuse_radiation',
            ('lw_dn', 'lw_down', 'lwdown'): 'longwave_radiation',
            
            # Solar-specific (GSO model)
            ('ghi', 'global_horizontal_irradiance'): 'shortwave_radiation',
            ('gti', 'global_tilted_irradiance'): 'tilted_radiation',
            ('poa', 'plane_of_array'): 'poa_radiation',
        }
        
        for var in unmapped_vars:
            var_lower = var.lower()
            
            # Check against patterns
            for pattern_vars, canonical in patterns.items():
                if var_lower in pattern_vars or any(p in var_lower for p in pattern_vars):
                    suggestions[var] = canonical
                    break
            
            # If no pattern match, use heuristics
            if var not in suggestions:
                if '2m' in var_lower and ('temp' in var_lower or 't' == var_lower[0]):
                    suggestions[var] = 'temperature_2m'
                elif '10m' in var_lower and 'wind' in var_lower:
                    suggestions[var] = 'wind_speed_10m'
                elif 'precip' in var_lower or 'rain' in var_lower:
                    suggestions[var] = 'precipitation'
                elif 'humid' in var_lower or 'rh' in var_lower:
                    suggestions[var] = 'relative_humidity_2m'
                elif 'pressure' in var_lower or 'pres' in var_lower:
                    suggestions[var] = 'surface_pressure'
                elif 'cloud' in var_lower:
                    suggestions[var] = 'cloud_cover'
                elif any(x in var_lower for x in ['sw', 'solar', 'irrad', 'ghi', 'rad']):
                    suggestions[var] = 'shortwave_radiation'
        
        return suggestions
    
    def print_detailed_report(self, results: Dict, show_all_vars: bool = False):
        """
        Print a detailed report of the discovery results
        
        Args:
            results: Results dictionary from discover_all_variables()
            show_all_vars: If True, print all variables for each model
        """
        print("\n" + "=" * 60)
        print("📋 Detailed Variable Report")
        print("=" * 60)
        
        # Print per-model breakdown
        for model, data in results['models'].items():
            print(f"\n{'─' * 60}")
            print(f"🔹 {model.upper()}")
            print(f"{'─' * 60}")
            
            if data['has_domains']:
                for domain, vars_list in data['domains'].items():
                    print(f"  Domain: {domain} ({len(vars_list)} variables)")
                    if show_all_vars:
                        for var in sorted(vars_list):
                            canonical = self.mapper.to_canonical(var)
                            mapped_status = "✓" if canonical != var else "○"
                            print(f"    {mapped_status} {var:30s} → {canonical}")
            else:
                print(f"  {len(data['variables'])} variables")
                if show_all_vars:
                    for var in sorted(data['variables']):
                        canonical = self.mapper.to_canonical(var)
                        mapped_status = "✓" if canonical != var else "○"
                        print(f"    {mapped_status} {var:30s} → {canonical}")
        
        # Print unmapped variables with suggestions
        if results['unmapped_variables']:
            print(f"\n{'=' * 60}")
            print(f"🔍 Unmapped Variables ({len(results['unmapped_variables'])})")
            print(f"{'=' * 60}")
            
            for var in sorted(results['unmapped_variables']):
                suggestion = results['suggested_mappings'].get(var, '❓ unknown')
                print(f"  {var:35s} → {suggestion}")
        
        # Print mapping statistics
        print(f"\n{'=' * 60}")
        print(f"📈 Mapping Statistics")
        print(f"{'=' * 60}")
        total = len(results['all_unique_variables'])
        mapped = total - len(results['unmapped_variables'])
        percentage = (mapped / total * 100) if total > 0 else 0
        
        print(f"  Total unique variables: {total}")
        print(f"  Already mapped: {mapped} ({percentage:.1f}%)")
        print(f"  Unmapped: {len(results['unmapped_variables'])}")
        print(f"  Suggested mappings: {len(results['suggested_mappings'])}")
    
    def generate_mapping_code(self, results: Dict) -> str:
        """
        Generate Python code to add to variable_mapper.py
        
        Args:
            results: Results from discover_all_variables()
        
        Returns:
            Python code string
        """
        code_lines = [
            "# AWS API specific variable mappings (auto-discovered)",
            "# Add these to the canonical_to_alternatives dictionary in VariableMapper:",
            ""
        ]
        
        # Group suggestions by canonical name
        by_canonical = defaultdict(set)
        for aws_var, canonical in results['suggested_mappings'].items():
            by_canonical[canonical].add(aws_var)
        
        for canonical in sorted(by_canonical.keys()):
            aws_vars = sorted(by_canonical[canonical])
            code_lines.append(f"# AWS API variables for {canonical}:")
            code_lines.append(f"'{canonical}': {{")
            code_lines.append(f"    '{canonical}',  # canonical name")
            for var in aws_vars:
                code_lines.append(f"    '{var}',  # AWS API")
            code_lines.append(f"}},")
            code_lines.append("")
        
        return "\n".join(code_lines)


def main():
    """Main entry point for variable discovery"""
    import getpass
    
    print("\n🔐 AWS API Variable Discovery Tool")
    print("=" * 60)
    print("This tool will discover all variables from AWS API models")
    print("and suggest mappings to canonical variable names.")
    print("=" * 60)
    
    # Get credentials
    print("\nPlease enter your AWS credentials:")
    user_pool_id = input("User Pool ID (e.g., ap-southeast-2_XXXXXXXXX): ").strip()
    client_id = input("Client ID (e.g., xxxxxxxxxxxxxxxxxxxxx): ").strip()
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    
    if not all([user_pool_id, client_id, username, password]):
        print("❌ All credentials are required")
        return 1
    
    # Authenticate
    print("\n🔑 Authenticating...")
    try:
        from utils.cognito_auth import CognitoAuth
        auth = CognitoAuth(user_pool_id, client_id)
        success, id_token, error = auth.authenticate(username, password)
        
        if not success:
            print(f"❌ Authentication failed: {error}")
            return 1
        
        print("✅ Authentication successful!")
    
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        return 1
    
    # Create client and discovery tool
    base_url = 'https://fmeq0xvw60.execute-api.ap-southeast-2.amazonaws.com/prod'
    client = AWSAPIClient(base_url, id_token)
    discovery = AWSVariableDiscovery(client)
    
    # Discover variables
    print("\n🔍 Discovering variables from AWS API...")
    results = discovery.discover_all_variables(verbose=True)
    
    # Print detailed report
    discovery.print_detailed_report(results, show_all_vars=True)
    
    # Generate mapping code
    print("\n" + "=" * 60)
    print("💾 Generated Mapping Code")
    print("=" * 60)
    code = discovery.generate_mapping_code(results)
    print(code)
    
    # Save to file
    output_file = 'aws_variable_mappings.txt'
    with open(output_file, 'w') as f:
        f.write("AWS API Variable Discovery Report\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total unique variables: {len(results['all_unique_variables'])}\n")
        f.write(f"Unmapped: {len(results['unmapped_variables'])}\n\n")
        f.write("Suggested Mappings:\n")
        f.write("-" * 60 + "\n")
        for var in sorted(results['unmapped_variables']):
            suggestion = results['suggested_mappings'].get(var, 'unknown')
            f.write(f"{var:35s} → {suggestion}\n")
        f.write("\n\n")
        f.write(code)
    
    print(f"\n✅ Report saved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
