import requests
import pandas as pd

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