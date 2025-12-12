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

# Import AWS API data source components
try:
    from data_sources.aws_api import AWSAPIDataSource
    from utils.cognito_auth import CognitoAuth
    AWS_API_AVAILABLE = True
except ImportError:
    AWS_API_AVAILABLE = False

# Import views
from views.deterministic_view import render_deterministic_view
from views.ensemble_view import render_ensemble_view
from views.metadata_view import show_metadata_view

# --- Page Configuration ---
st.set_page_config(
    page_title="wxapp",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Initialize Session State ---
if 'aws_authenticated' not in st.session_state:
    st.session_state['aws_authenticated'] = False
    st.session_state['aws_id_token'] = None
    st.session_state['aws_base_url'] = 'https://fmeq0xvw60.execute-api.ap-southeast-2.amazonaws.com/prod'
    st.session_state['aws_domain'] = 'brisbane'
    st.session_state['aws_domain_changed'] = False
    st.session_state['aws_just_authenticated'] = False

# Function to get current data sources (dynamically includes AWS if authenticated)
def get_data_sources():
    """Return dictionary of available data sources based on authentication state"""
    sources = {
        'Open-Meteo': OpenMeteoDataSource(),
        # Add more static sources here
    }
    
    # Add AWS API data source if authenticated
    if AWS_API_AVAILABLE and st.session_state.get('aws_authenticated', False):
        try:
            aws_ds = AWSAPIDataSource(
                base_url=st.session_state['aws_base_url'],
                id_token=st.session_state['aws_id_token'],
                domain=st.session_state.get('aws_domain', 'brisbane')
            )
            sources['AWS API (GSO/ACCESS)'] = aws_ds
        except Exception as e:
            st.warning(f"Failed to initialize AWS API data source: {str(e)}")
    
    return sources

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
        "View Mode",
        options=['Deterministic', 'Probabilistic/Ensemble', 'Metadata'],
        key='forecast_type_radio',
        help="Choose between forecasts or view metadata about models and data sources"
    )
    st.session_state['forecast_type'] = forecast_type
    
    st.markdown("---")
    
    # AWS API Authentication Section
    if AWS_API_AVAILABLE:
        with st.expander("🔐 AWS API Authentication", expanded=not st.session_state.get('aws_authenticated', False)):
            if not st.session_state.get('aws_authenticated', False):
                st.info("Enter your AWS credentials to access GSO and ACCESS models")
                
                # AWS Cognito configuration (you can move these to environment variables)
                user_pool_id = st.text_input(
                    "User Pool ID",
                    value="ap-southeast-2_T7xOIMSJh",
                    key='aws_user_pool_id',
                    type='password'
                )
                
                client_id = st.text_input(
                    "Client ID",
                    value="1quihqsjtc5iq0f745phcd19",
                    key='aws_client_id',
                    type='password'
                )
                
                username = st.text_input("Username", key='aws_username')
                password = st.text_input("Password", type='password', key='aws_password')
                
                # Domain selection for ACCESS-CE
                domain = st.selectbox(
                    "Domain (for ACCESS-CE)",
                    options=['brisbane', 'adelaide', 'sydney', 'darwin', 'canberra', 
                             'hobart', 'melbourne', 'perth', 'nqld'],
                    index=None,
                    placeholder="Select a domain...",
                    key='aws_domain_select'
                )
                
                if st.button("Login", key='aws_login_btn'):
                    if not username or not password:
                        st.error("Please enter username and password")
                    else:
                        with st.spinner("Authenticating..."):
                            try:
                                auth = CognitoAuth(user_pool_id, client_id)
                                success, id_token, error = auth.authenticate(username, password)
                                
                                if success:
                                    st.session_state['aws_authenticated'] = True
                                    st.session_state['aws_id_token'] = id_token
                                    st.session_state['aws_domain'] = domain
                                    st.session_state['aws_just_authenticated'] = True  # Flag for success message
                                    st.success("✅ Authentication successful! AWS models (GSO, ACCESS-G, ACCESS-GE, ACCESS-CE) are now available.")
                                    st.info("💡 Select 'AWS API (GSO/ACCESS)' from the Data Source dropdown to use these models.")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Authentication failed: {error}")
                            except Exception as e:
                                st.error(f"❌ Authentication error: {str(e)}")
            else:
                st.success("✅ Authenticated with AWS API")
                st.caption(f"Current domain: {st.session_state.get('aws_domain', 'brisbane')}")
                
                # Allow changing domain
                prev_domain = st.session_state.get('aws_domain', 'brisbane')
                domain = st.selectbox(
                    "Change Domain (for ACCESS-CE)",
                    options=['brisbane', 'adelaide', 'sydney', 'darwin', 'canberra', 
                             'hobart', 'melbourne', 'perth', 'nqld'],
                    index=['brisbane', 'adelaide', 'sydney', 'darwin', 'canberra', 
                           'hobart', 'melbourne', 'perth', 'nqld'].index(prev_domain),
                    key='aws_domain_change',
                    help="Changing domain will reload metadata for ACCESS-CE model"
                )
                
                if domain != prev_domain:
                    st.session_state['aws_domain'] = domain
                    st.info(f"Domain changed to {domain}. Reloading...")
                    st.rerun()
                
                if st.button("Logout", key='aws_logout_btn'):
                    st.session_state['aws_authenticated'] = False
                    st.session_state['aws_id_token'] = None
                    st.rerun()
    
    st.markdown("---")
    
    # Get current data sources (dynamic based on authentication)
    DATA_SOURCES = get_data_sources()
    
    # Show success message if AWS just became available
    if 'aws_just_authenticated' in st.session_state and st.session_state['aws_just_authenticated']:
        st.success("🎉 AWS API data source is now available! Select it from the multi-select below.")
        st.session_state['aws_just_authenticated'] = False  # Clear flag
    
    # Multi-source selector - allow selecting multiple data sources
    source_options = list(DATA_SOURCES.keys())
    
    # Initialize previous selections
    if 'selected_data_sources' not in st.session_state:
        st.session_state['selected_data_sources'] = [source_options[0]] if source_options else []
    
    # Preserve previous selections that are still available
    default_sources = [s for s in st.session_state.get('selected_data_sources', []) if s in source_options]
    if not default_sources and source_options:
        default_sources = [source_options[0]]
    
    selected_source_names = st.multiselect(
        'Data Sources',
        options=source_options,
        default=default_sources,
        key='data_source_multiselect',
        help="Select one or more data sources to compare their models in the same plot"
    )
    
    # Update session state
    st.session_state['selected_data_sources'] = selected_source_names
    
    # Create dictionary of selected data sources
    selected_data_sources = {name: DATA_SOURCES[name] for name in selected_source_names}
    
    # Show domain selector for AWS API data source if it's selected
    if any('AWS API' in name for name in selected_source_names) and st.session_state.get('aws_authenticated', False):
        st.markdown("**ACCESS-CE Domain**")
        current_domain = st.session_state.get('aws_domain', 'brisbane')
        domain_options = ['brisbane', 'adelaide', 'sydney', 'darwin', 'canberra', 
                         'hobart', 'melbourne', 'perth', 'nqld']
        
        new_domain = st.selectbox(
            'Select Domain for ACCESS-CE',
            options=domain_options,
            index=domain_options.index(current_domain) if current_domain in domain_options else 0,
            key='aws_domain_main',
            help='Domain used for ACCESS-CE ensemble model'
        )
        
        if new_domain != current_domain:
            st.session_state['aws_domain'] = new_domain
            st.session_state['aws_domain_changed'] = True
            # Force re-initialization of data source with new domain
            st.info(f"Domain changed to {new_domain}. Variables will update for ACCESS-CE.")
            st.rerun()
    
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
    # Show all selected data sources
    if selected_data_sources:
        st.caption(f"Data Sources: {', '.join(selected_data_sources.keys())}")
    else:
        st.warning("⚠️ No data sources selected. Please select at least one data source.")

st.divider()

# --- Render Appropriate View ---
if forecast_type == 'Metadata':
    # Show metadata view regardless of data source selection
    show_metadata_view(selected_data_sources or get_data_sources())
elif not selected_data_sources:
    st.error("❌ Please select at least one data source from the sidebar to continue.")
elif forecast_type == 'Deterministic':
    render_deterministic_view(
        data_sources=selected_data_sources,
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
        data_sources=selected_data_sources,
        lat=lat,
        lon=lon,
        site=selected_site,
        custom_hourly_params=custom_hourly_params,
        base_hourly_params=BASE_HOURLY_PARAMS,
        daily_params=DAILY_PARAMS,
        obs_distance_km=st.session_state['obs_distance_km'],
        timezone=st.session_state['timezone']
    )