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

# Custom CSS to reduce whitespace
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.2rem;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem;
    }
    h3 {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- Initialize Session State ---
if 'aws_authenticated' not in st.session_state:
    st.session_state['aws_authenticated'] = False
    st.session_state['aws_id_token'] = None
    st.session_state['aws_base_url'] = 'https://fmeq0xvw60.execute-api.ap-southeast-2.amazonaws.com/prod'
    st.session_state['aws_domain'] = 'brisbane'  # Default to Brisbane
    st.session_state['aws_domain_changed'] = False
    st.session_state['aws_just_authenticated'] = False
    st.session_state['show_login'] = True  # Show login screen on first load

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
@st.cache_resource
def load_site_data():
    """Load site list with caching for performance"""
    try:
        scatter_geo_df = pd.read_csv('./siteList.csv', skipinitialspace=True, usecols=['site', 'lat', 'lon'])
        scatter_geo_df = scatter_geo_df.rename(columns={'lat': 'latitude', 'lon': 'longitude'})
        return scatter_geo_df
    except FileNotFoundError:
        data = {
            'site': ['Brisbane', 'Sydney', 'Melbourne', 'Perth', 'Adelaide'],
            'latitude': [-27.4705, -33.8688, -37.8136, -31.9505, -34.9285],
            'longitude': [153.0260, 151.2093, 144.9631, 115.8605, 138.6007]
        }
        return pd.DataFrame(data)

# Load site data (cached)
scatter_geo_df = load_site_data()

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

# --- AWS Login Screen (if not authenticated) ---
if AWS_API_AVAILABLE and not st.session_state.get('aws_authenticated', False):
    st.title("🔐 wxapp Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("AWS API Authentication")
        st.info("🌏 Login to access GSO and ACCESS models")
        
        # AWS Cognito configuration
        user_pool_id = st.text_input(
            "User Pool ID",
            value="ap-southeast-2_T7xOIMSJh",
            key='aws_user_pool_id',
            type='password',
            help="Your AWS Cognito User Pool ID"
        )
        
        client_id = st.text_input(
            "Client ID",
            value="1quihqsjtc5iq0f745phcd19",
            key='aws_client_id',
            type='password',
            help="Your AWS Cognito Client ID"
        )
        
        username = st.text_input("Username", key='aws_username')
        password = st.text_input("Password", type='password', key='aws_password')
        
        # Domain selection for ACCESS-CE with Brisbane as default
        domain = st.selectbox(
            "ACCESS-CE Domain",
            options=['brisbane', 'adelaide', 'sydney', 'darwin', 'canberra', 
                     'hobart', 'melbourne', 'perth', 'nqld'],
            index=0,  # Brisbane is first and default
            key='aws_domain_select',
            help="Select your forecast domain (Brisbane is default)"
        )
        
        col_login1, col_login2 = st.columns(2)
        with col_login1:
            if st.button("🚀 Login", key='aws_login_btn', use_container_width=True):
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
                                st.session_state['show_login'] = False
                                st.success("✅ Authentication successful!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"❌ Authentication failed: {error}")
                        except Exception as e:
                            st.error(f"❌ Authentication error: {str(e)}")
        
        with col_login2:
            if st.button("Continue Without Login", key='skip_login_btn', use_container_width=True):
                st.session_state['show_login'] = False
                st.info("ℹ️ Continuing with Open-Meteo (free) data source only")
                st.rerun()
        
        st.caption("💡 Don't have AWS credentials? Click 'Continue Without Login' to use the free Open-Meteo data source")
    
    st.stop()  # Stop here until authenticated or skip login

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
    
    # Show AWS status and domain control if authenticated
    if AWS_API_AVAILABLE and st.session_state.get('aws_authenticated', False):
        st.success("✅ AWS API Connected")
        
        # Domain selector
        prev_domain = st.session_state.get('aws_domain', 'brisbane')
        domain_options = ['brisbane', 'adelaide', 'sydney', 'darwin', 'canberra', 
                         'hobart', 'melbourne', 'perth', 'nqld']
        
        domain = st.selectbox(
            "ACCESS-CE Domain",
            options=domain_options,
            index=domain_options.index(prev_domain),
            key='aws_domain_change',
            help="Domain for ACCESS-CE ensemble model forecasts"
        )
        
        if domain != prev_domain:
            st.session_state['aws_domain'] = domain
            st.info(f"Domain changed to {domain}. Reloading...")
            st.rerun()
        
        # Logout button
        if st.button("🚪 Logout", key='aws_logout_btn', use_container_width=True):
            st.session_state['aws_authenticated'] = False
            st.session_state['aws_id_token'] = None
            st.session_state['show_login'] = True
            st.rerun()
    elif AWS_API_AVAILABLE:
        st.info("ℹ️ Using free data sources only")
        if st.button("🔐 Login to AWS", key='show_login_btn', use_container_width=True):
            st.session_state['show_login'] = True
            st.rerun()
    
    # Get current data sources (dynamic based on authentication)
    DATA_SOURCES = get_data_sources()
    
    # Multi-source selector - automatically include AWS if authenticated
    source_options = list(DATA_SOURCES.keys())
    
    # Initialize with appropriate defaults
    if 'selected_data_sources' not in st.session_state:
        # If AWS is available, include it by default
        if 'AWS API (GSO/ACCESS)' in source_options:
            st.session_state['selected_data_sources'] = ['Open-Meteo', 'AWS API (GSO/ACCESS)']
        else:
            st.session_state['selected_data_sources'] = ['Open-Meteo']
    
    # When AWS becomes available after login, automatically add it
    if st.session_state.get('aws_authenticated', False) and 'AWS API (GSO/ACCESS)' in source_options:
        if 'AWS API (GSO/ACCESS)' not in st.session_state['selected_data_sources']:
            st.session_state['selected_data_sources'].append('AWS API (GSO/ACCESS)')
    
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
    
    # Combined Options menu
    with st.expander("⚙️ Options", expanded=False):
        st.markdown("### Display Settings")
        
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
        
        st.markdown("---")
        st.markdown("### Performance")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Cache", use_container_width=True, help="Clear all cached data to free memory"):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("Cache cleared!")
                st.rerun()
        
        with col2:
            show_metrics = st.checkbox(
                "Show Metrics", 
                value=False,
                help="Display render time and memory usage"
            )
            st.session_state['show_performance_metrics'] = show_metrics
    
    st.info('💡 Click any point on the map to get an instant forecast!')

# --- Site Selection Logic ---
current_df = st.session_state.get('site_data')
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

# --- Map Section (only for Deterministic and Ensemble views) ---
if forecast_type != 'Metadata':
    # Single row with map and controls
    map_col, controls_col = st.columns([2.5, 1])

    with map_col:
        # Named site selection (moved from sidebar to map area)
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

            st.selectbox(
                'Select Named Site',
                site_list,
                index=initial_selected_site_index,
                key='site_select_sidebar'
            )
        
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

        map_output = st_folium(m, width=None, height=350, returned_objects=['last_clicked'], 
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
        
        # Small current selection text under map
        st.caption(f"📍 **{selected_site}** • Lat: {lat:.2f} • Lon: {lon:.2f}")

    # Store the controls column for views to use
    st.session_state['controls_column_ref'] = controls_col

# --- Render Appropriate View ---
import time
start_time = time.time()

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
        custom_hourly_params=[],
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
        custom_hourly_params=[],
        base_hourly_params=BASE_HOURLY_PARAMS,
        daily_params=DAILY_PARAMS,
        obs_distance_km=st.session_state['obs_distance_km'],
        timezone=st.session_state['timezone']
    )

# Show performance metrics if enabled
if st.session_state.get('show_performance_metrics', False):
    elapsed = time.time() - start_time
    
    # Get memory usage
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        with st.sidebar:
            st.markdown("---")
            st.caption(f"⏱️ Render time: {elapsed:.2f}s")
            st.caption(f"💾 Memory: {memory_mb:.0f} MB")
    except ImportError:
        with st.sidebar:
            st.markdown("---")
            st.caption(f"⏱️ Render time: {elapsed:.2f}s")
            st.caption("💾 Install psutil for memory metrics")