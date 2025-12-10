import requests
import pandas as pd
from typing import List
import re

def getData(lat, lon, sites, variables=['temperature_2m','cloud_cover'], models=['ecmwf_ifs025','ecmwf_aifs025','bom_access_global','gfs_global', 'cma_grapes_global','ukmo_global_deterministic_10km']):
    """
    Retrieves hourly forecast data from the Open-Meteo API for one or more sites.

    Args:
        lat (list of str): List of latitudes.
        lon (list of str): List of longitudes.
        sites (list of str): List of site names (used for multi-site concatenation).
        variables (list, optional): Hourly variables to fetch. Defaults to ['temperature_2m','cloud_cover'].
        models (list, optional): Models to include in the forecast.

    Returns:
        pd.DataFrame: A DataFrame containing the hourly data.
    """
    if len(sites) > 1:
        lat_str = ','.join(lat)
        lon_str = ','.join(lon)
    else:
        lat_str = lat[0]
        lon_str = lon[0]
    variables_str = ','.join(variables)
    models_str = ','.join(models)

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&hourly={variables_str}&models={models_str}&timezone=GMT"

    response = requests.get(url)
    data = None
    if response.status_code == 200:
        data = response.json()
    else:
        print(f"Error retrieving hourly data from Open Meteo API. Status Code: {response.status_code}")
        # Return an empty DataFrame structure on failure
        return pd.DataFrame()

    def makeFrame(siteData):
        mdata = pd.DataFrame(siteData['hourly'])
        mdata.index = pd.to_datetime(mdata['time'])
        mdata = mdata.drop('time', axis=1)
        return mdata
    
    if len(sites) > 1:
        dlist = []
        # Note: Open-Meteo returns a list of data dictionaries when multiple lat/lon are queried
        # The zip assumes the response data corresponds to the input sites/lat/lon order
        for d, site in zip(data, sites):
            df = makeFrame(d)
            df['site'] = site
            dlist.append(df)
        return pd.concat(dlist)

    return makeFrame(data)


def getDailyData(lat, lon, sites, variables=['temperature_2m_max','temperature_2m_min'], models=['ecmwf_ifs','ecmwf_aifs025','bom_access_global','gfs_global', 'cma_grapes_global','ukmo_global_deterministic_10km']):
    """
    Retrieves daily forecast data from the Open-Meteo API for one or more sites.

    Args:
        lat (list of str): List of latitudes.
        lon (list of str): List of longitudes.
        sites (list of str): List of site names (used for multi-site concatenation).
        variables (list, optional): Daily variables to fetch. Defaults to ['temperature_2m_max','temperature_2m_min'].
        models (list, optional): Models to include in the forecast.

    Returns:
        pd.DataFrame: A DataFrame containing the daily data.
    """
    if len(sites) > 1:
        lat_str = ','.join(lat)
        lon_str = ','.join(lon)
    else:
        lat_str = lat[0]
        lon_str = lon[0]
    variables_str = ','.join(variables)
    models_str = ','.join(models)

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&daily={variables_str}&models={models_str}&timezone=GMT"

    response = requests.get(url)
    data = None
    if response.status_code == 200:
        data = response.json()
    else:
        print(f"Error retrieving daily data from Open Meteo API. Status Code: {response.status_code}")
        # Return an empty DataFrame structure on failure
        return pd.DataFrame()

    def makeFrame(siteData):
        mdata = pd.DataFrame(siteData['daily'])
        mdata.index = pd.to_datetime(mdata['time'])
        mdata = mdata.drop('time', axis=1)
        return mdata
    
    if len(sites) > 1:
        dlist = []
        for d, site in zip(data, sites):
            df = makeFrame(d)
            df['site'] = site
            dlist.append(df)
        return pd.concat(dlist)

    return makeFrame(data)


import pandas as pd
import requests
from typing import List, Dict

def getEnsembleData(lat_list: List[str], lon_list: List[str], site_list: List[str], 
                    variables: List[str], models: List[str]) -> pd.DataFrame:
    """
    Fetch ensemble forecast data from Open-Meteo Ensemble API, handling the flat member-per-column structure.
    
    Args:
        lat_list: List of latitude strings
        lon_list: List of longitude strings  
        site_list: List of site names
        variables: List of variable names to fetch (e.g., ['temperature_2m'])
        models: List of ensemble model names
    
    Returns:
        DataFrame with datetime index and columns following 'variable_model_member_XX' convention.
    """
    
    # Map model names to API parameters
    model_mapping: Dict[str, str] = {
        'ecmwf_ifs_ensemble': 'ecmwf_ifs025',
        'gfs_ensemble': 'gfs025',
    }
    
    all_site_model_data = []
    
    # We use the internal API model name for column construction
    # We assume only one model is requested per API call, matching the structure of your original code
    
    for lat, lon, site in zip(lat_list, lon_list, site_list):
        for model in models:
            api_model = model_mapping.get(model, model)
            
            # Build API URL
            base_url = "https://ensemble-api.open-meteo.com/v1/ensemble"
            
            params = {
                'latitude': lat,
                'longitude': lon,
                'hourly': ','.join(variables),
                'models': api_model,
                'timezone': 'GMT'
            }
            
            try:
                response = requests.get(base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if 'hourly' not in data:
                    print(f"No hourly data found for {site} with {model}")
                    continue
                
                # 1. Parse the datetime index
                times = pd.to_datetime(data['hourly']['time'])
                # Start a wide DataFrame for this site/model combination
                df_temp = pd.DataFrame({'time': times, 'site': site})
                
                # 2. Iterate through ALL keys returned in 'hourly' to find members
                for variable_key, var_values in data['hourly'].items():
                    if variable_key == 'time':
                        continue

                    # Check if the variable key is one of the variables we requested (e.g., 'temperature_2m')
                    base_variable = next((v for v in variables if variable_key.startswith(v)), None)
                    
                    if base_variable:
                        # Case A: Control member (e.g., 'temperature_2m')
                        if variable_key == base_variable:
                            col_name = f"{base_variable}_{model}" # Deterministic column name
                            df_temp[col_name] = var_values
                            
                        # Case B: Numbered member (e.g., 'temperature_2m_member01')
                        elif variable_key.startswith(f"{base_variable}_member"):
                            # Extract the member number (e.g., '01') and format it consistently
                            match = re.search(r'member(\d+)', variable_key)
                            if match:
                                member_idx = int(match.group(1)) # Convert to int
                                # Use f-string for consistent member naming like in the plotting function
                                col_name = f"{base_variable}_{model}_member_{member_idx:02d}"
                                df_temp[col_name] = var_values
                            
                # Append the resulting wide DataFrame for this site/model
                all_site_model_data.append(df_temp)
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching ensemble data for {site} with {model}: {e}")
                continue
            except Exception as e:
                print(f"Error parsing ensemble data for {site} with {model}: {e}")
                continue
    
    if not all_site_model_data:
        return pd.DataFrame()
    
    # Use functools.reduce for robustly merging all wide DataFrames on 'time' and 'site'
    from functools import reduce
    result_df = reduce(lambda left, right: pd.merge(left, right, on=['time', 'site'], how='outer'), 
                       all_site_model_data)

    # Final formatting: Set time as index and drop the site column
    result_df = result_df.set_index('time')
    result_df = result_df.drop(columns=['site'])
    return result_df

def getDailyEnsembleData(lat_list: List[str], lon_list: List[str], site_list: List[str],
                         variables: List[str], models: List[str]) -> pd.DataFrame:
    """
    Fetch daily ensemble forecast data from Open-Meteo Ensemble API
    
    Args:
        lat_list: List of latitude strings
        lon_list: List of longitude strings
        site_list: List of site names
        variables: List of daily variable names to fetch
        models: List of ensemble model names
    
    Returns:
        DataFrame with datetime index and columns for each variable_model_member combination
    """
    
    # Map model names to API parameters
    model_mapping = {
        'ecmwf_ifs_ensemble': 'ecmwf_ifs025',
        'gfs_ensemble': 'gfs025',
        'bom_access_global_ensemble': 'bom_access_global_ensemble'
    }
    
    all_data = []
    
    for lat, lon, site in zip(lat_list, lon_list, site_list):
        for model in models:
            api_model = model_mapping.get(model, model)
            
            # Build API URL
            base_url = "https://ensemble-api.open-meteo.com/v1/ensemble"
            
            params = {
                'latitude': lat,
                'longitude': lon,
                'daily': ','.join(variables),
                'models': api_model,
                'timezone': 'auto'
            }
            
            try:
                response = requests.get(base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if 'daily' not in data:
                    continue
                
                # Parse the datetime
                times = pd.to_datetime(data['daily']['time'])
                
                # Extract data for each variable and ensemble member
                for variable in variables:
                    if variable in data['daily']:
                        var_data = data['daily'][variable]
                        
                        # Check if it's ensemble data (list of lists) or single value (list)
                        if isinstance(var_data[0], list):
                            # Ensemble data - multiple members
                            num_members = len(var_data[0])
                            
                            for member_idx in range(num_members):
                                member_values = [timestep[member_idx] for timestep in var_data]
                                col_name = f"{variable}_{model}_member_{member_idx:02d}"
                                
                                df_temp = pd.DataFrame({
                                    'time': times,
                                    col_name: member_values,
                                    'site': site
                                })
                                all_data.append(df_temp)
                        else:
                            # Single deterministic value
                            col_name = f"{variable}_{model}"
                            df_temp = pd.DataFrame({
                                'time': times,
                                col_name: var_data,
                                'site': site
                            })
                            all_data.append(df_temp)
                            
            except requests.exceptions.RequestException as e:
                print(f"Error fetching daily ensemble data for {site} with {model}: {e}")
                continue
            except Exception as e:
                print(f"Error parsing daily ensemble data for {site} with {model}: {e}")
                continue
    
    if not all_data:
        return pd.DataFrame()
    
    # Merge all dataframes
    result_df = all_data[0]
    for df in all_data[1:]:
        result_df = pd.merge(result_df, df, on=['time', 'site'], how='outer')
    
    result_df = result_df.set_index('time')
    result_df = result_df.drop(columns=['site'])
    
    return result_df