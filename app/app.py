# ========================================
# File: app.py
"""Main Streamlit application"""
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Import configuration
from config import (
    DEFAULT_LAT, DEFAULT_LON, BASE_HOURLY_PARAMS, DAILY_PARAMS
)

# Import data sources
from data_sources.open_meteo import OpenMeteoDataSource
from data_sources.meteostat_obs import MeteostatObsDataSource

# Import views
from views.deterministic_view import render_deterministic_view
from views.ensemble_view import render_ensemble_view

# --- Page Configuration ---
st.set_page_config(
    page_title="wxapp",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Initialize Data Sources ---
# You can add more data sources here
DATA_SOURCES = {
    'Open-Meteo': OpenMeteoDataSource(),
    # 'Another Source': AnotherDataSource(),  # Add more as needed
}

# Initialize observations source (always available for overlay)
OBS_SOURCE = MeteostatObsDataSource()

# --- Load Site Data ---
try:
    scatter_geo_df = pd.read_csv('./siteList.csv', skipinitialspace=True, usecols=['site', 'lat', 'lon'])
    scatter_geo_df = scatter_geo_df.rename(columns={'lat': 'latitude', 'lon': 'longitude'})
except FileNotFoundError:
    data = {
        'site': ['Brisbane', 'Sydney', 'Melbourne', 'Perth', 'Adelaide'],
        'latitude': [-27.4705, -33.8688, -37.8136, -31.9505, -34.9285],
        'longitude': [153.0260, 151.2093, 144.9631, 115.8605, 138.6007]
    }
    scatter_geo_df = pd.DataFrame(data)

# --- Initialize Session State ---
if 'site_data' not in st.session_state:
    st.session_state['site_data'] = scatter_geo_df.copy()

if 'ad_hoc_selection' not in st.session_state:
    st.session_state['ad_hoc_selection'] = {'site': "Brisbane", 'lat': DEFAULT_LAT, 'lon': DEFAULT_LON}

if 'last_named_site_selection' not in st.session_state:
    st.session_state['last_named_site_selection'] = st.session_state['ad_hoc_selection']['site']

if 'forecast_type' not in st.session_state:
    st.session_state['forecast_type'] = 'Deterministic'

if 'obs_distance_km' not in st.session_state:
    st.session_state['obs_distance_km'] = 2.0

if 'timezone' not in st.session_state:
    st.session_state['timezone'] = 'UTC'

# --- Header ---
st.title("wxapp")
st.caption("Interactive weather forecasting viewer with deterministic and probabilistic forecasts")

# --- Sidebar ---
with st.sidebar:
    st.header('Configuration')
    
    # Forecast type selector
    forecast_type = st.radio(
        "Forecast Type",
        options=['Deterministic', 'Probabilistic/Ensemble'],
        key='forecast_type_radio',
        help="Choose between single-value deterministic forecasts or ensemble/probabilistic forecasts"
    )
    st.session_state['forecast_type'] = forecast_type
    
    st.markdown("---")
    
    # Data source selector
    selected_source_name = st.selectbox(
        'Data Source',
        options=list(DATA_SOURCES.keys()),
        key='data_source_select'
    )
    data_source = DATA_SOURCES[selected_source_name]
    
    st.markdown("---")
    
    # Named site selection
    current_df = st.session_state.get('site_data')
    initial_selected_site_index = 0
    
    if current_df is not None and not current_df.empty:
        site_list = current_df['site'].tolist()
        
        try:
            current_display_site = st.session_state.get('ad_hoc_selection', {}).get('site', 'Brisbane')
            if current_display_site in site_list:
                initial_selected_site_index = site_list.index(current_display_site)
            elif st.session_state['last_named_site_selection'] in site_list:
                initial_selected_site_index = site_list.index(st.session_state['last_named_site_selection'])
        except Exception:
            pass

        initial_selected_site = st.selectbox(
            'Select Named Site',
            site_list,
            index=initial_selected_site_index,
            key='site_select_sidebar'
        )
    else:
        initial_selected_site = None
        st.warning("No named sites available.")
    
    st.markdown("---")
    
    # Custom parameters
    custom_hourly_input = st.text_input(
        'Add Custom Hourly Parameters',
        key='custom_hourly_input',
        placeholder='e.g., surface_pressure, precipitation',
        help="Enter additional variables separated by commas"
    ).strip()
    
    custom_hourly_params = []
    if custom_hourly_input:
        custom_hourly_params = [p.strip() for p in custom_hourly_input.split(',') if p.strip()]
    
    st.markdown("---")
    
    # Options expander
    with st.expander("⚙️ Display Options", expanded=False):
        st.subheader("Observations")
        obs_distance = st.number_input(
            'Max Distance for Observation Station (km)',
            min_value=0.1,
            max_value=50.0,
            value=2.0,
            step=0.5,
            key='obs_distance_input',
            help="Maximum distance to search for nearby observation stations"
        )
        st.session_state['obs_distance_km'] = obs_distance
        
        st.markdown("---")
        
        st.subheader("Timezone")
        timezone_options = [
            'UTC',
            'Australia/Brisbane',
            'Australia/Sydney',
            'Australia/Melbourne',
            'Australia/Perth',
            'Australia/Adelaide',
            'America/New_York',
            'America/Los_Angeles',
            'Europe/London',
            'Asia/Tokyo',
        ]
        timezone = st.selectbox(
            'Plot Timezone',
            options=timezone_options,
            index=0,
            key='timezone_select',
            help="Timezone for displaying dates and times on plots"
        )
        st.session_state['timezone'] = timezone
    
    st.info('💡 Click any point on the map to get an instant forecast!')

# --- Site Selection Logic ---
current_selection = st.session_state['ad_hoc_selection']
selected_site = current_selection['site']
lat = current_selection['lat']
lon = current_selection['lon']

sidebar_site_name = st.session_state.get('site_select_sidebar')

if current_df is not None and sidebar_site_name:
    if sidebar_site_name != st.session_state['last_named_site_selection']:
        site_info = current_df[current_df['site'] == sidebar_site_name]
        if not site_info.empty:
            new_lat = site_info['latitude'].values[0]
            new_lon = site_info['longitude'].values[0]
            
            st.session_state['ad_hoc_selection'] = {
                'site': sidebar_site_name, 
                'lat': new_lat, 
                'lon': new_lon
            }
            st.session_state['last_named_site_selection'] = sidebar_site_name
            
            lat = new_lat
            lon = new_lon
            selected_site = sidebar_site_name

# --- Map Section ---
map_col, info_col = st.columns([3, 1])

with map_col:
    m = folium.Map(location=[lat, lon], zoom_start=5, tiles="openstreetmap")
    
    if current_df is not None and not current_df.empty:
        for index, row in current_df.iterrows():
            color = 'blue' if row['site'] == selected_site else 'gray'
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                tooltip=row['site']
            ).add_to(m)

    folium.Marker(
        location=[lat, lon], 
        tooltip=f"Current: {selected_site} ({lat:.4f}, {lon:.4f})",
        icon=folium.Icon(color="red", icon="crosshairs", prefix='fa')
    ).add_to(m)

    map_output = st_folium(m, width=None, height=500, returned_objects=['last_clicked'], 
                           key="folium_map_main", use_container_width=True)

    clicked_data = map_output.get("last_clicked")
    if clicked_data:
        st.session_state['ad_hoc_selection'] = {
            'site': "Map Click Location", 
            'lat': clicked_data['lat'], 
            'lon': clicked_data['lng']
        }
        st.session_state['last_named_site_selection'] = st.session_state.get('site_select_sidebar', 'Brisbane')
        st.rerun()

with info_col:
    st.markdown("### Current Selection")
    st.metric("Location", selected_site)
    st.metric("Latitude", f"{lat:.4f}")
    st.metric("Longitude", f"{lon:.4f}")
    st.metric("Forecast Type", forecast_type)
    st.markdown("---")
    st.caption(f"Data Source: {data_source.name}")

st.divider()

# --- Render Appropriate View ---
if forecast_type == 'Deterministic':
    render_deterministic_view(
        data_source=data_source,
        lat=lat,
        lon=lon,
        site=selected_site,
        custom_hourly_params=custom_hourly_params,
        base_hourly_params=BASE_HOURLY_PARAMS,
        daily_params=DAILY_PARAMS,
        obs_distance_km=st.session_state['obs_distance_km'],
        timezone=st.session_state['timezone']
    )
    
elif forecast_type == 'Probabilistic/Ensemble':
    render_ensemble_view(
        data_source=data_source,
        lat=lat,
        lon=lon,
        site=selected_site,
        custom_hourly_params=custom_hourly_params,
        base_hourly_params=BASE_HOURLY_PARAMS,
        daily_params=DAILY_PARAMS,
        obs_distance_km=st.session_state['obs_distance_km'],
        timezone=st.session_state['timezone']
    )