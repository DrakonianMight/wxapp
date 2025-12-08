import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from collections import OrderedDict
# --- Imports for map and utilities ---
import folium
from streamlit_folium import st_folium
# ---------------------------------
# Import the actual forecast data extraction module
import om_extract 

# --- Configuration and Setup ---
st.set_page_config(
    page_title="wxapp",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Constants
DEFAULT_LAT = -27.4705  # Brisbane
DEFAULT_LON = 153.0260

# Static BASE parameters for Open-Meteo Forecast
# These are the default variables visible on load
BASE_HOURLY_PARAMS = [
    'shortwave_radiation', 
    'temperature_2m', 
    'cloud_cover',
    # Added new variables below:
    'wind_speed_10m', 
    'wind_direction_10m', 
    'wind_gusts_10m',
    'relative_humidity_2m',
    'dewpoint_2m'
]
DAILY_PARAMS = ['temperature_2m_max', 'temperature_2m_min']

# Define a color mapping for each possible forecast model
color_map = {
    'ecmwf_ifs': '#FF5733', 
    'ecmwf_aifs025': '#C70039', 
    'bom_access_global': '#33FF57', 
    'gfs_global': '#AAAAAA', 
    'cma_grapes_global': '#8A2BE2', 
    'ukmo_global_deterministic_10km': '#00FFFF'
}

# --- Restore Mock Site Data ---
try:
    # Attempt to load the real file
    scatter_geo_df = pd.read_csv('./siteList.csv', skipinitialspace=True, usecols=['site', 'lat', 'lon'])
    scatter_geo_df = scatter_geo_df.rename(columns={'lat': 'latitude', 'lon': 'longitude'})
except FileNotFoundError:
    # st.warning("`siteList.csv` not found. Using mock site data.") # Optional: Hide warning for cleaner look
    data = {
        'site': ['Brisbane', 'Sydney', 'Melbourne', 'Perth', 'Adelaide'],
        'latitude': [-27.4705, -33.8688, -37.8136, -31.9505, -34.9285],
        'longitude': [153.0260, 151.2093, 144.9631, 115.8605, 138.6007]
    }
    scatter_geo_df = pd.DataFrame(data)

# Ensure the DataFrame is in session state
if 'site_data' not in st.session_state:
    st.session_state['site_data'] = scatter_geo_df.copy()

# Initialize session state for ad-hoc map clicks
if 'ad_hoc_selection' not in st.session_state:
    # Set initial selection to Brisbane
    st.session_state['ad_hoc_selection'] = {'site': "Brisbane", 'lat': DEFAULT_LAT, 'lon': DEFAULT_LON}

# Initialize a tracker for the last named site chosen, used to prevent map click overwrites
if 'last_named_site_selection' not in st.session_state:
    st.session_state['last_named_site_selection'] = st.session_state['ad_hoc_selection']['site']
# ---------------------------------


# --- Utility Functions ---

def get_yaxis_title(column):
    """Generates the Y-axis title based on the selected column name."""
    title_dict = {
        'shortwave_radiation': 'Shortwave Radiation (W/m²)',
        'wind_speed_10m': 'Wind Speed at 10m (m/s)',
        'wind_direction_10m': 'Wind Direction at 10m (°)', # Added for the new variable
        'wind_gusts_10m': 'Wind Gusts at 10m (m/s)',
        'temperature_2m': 'Temperature at 2m (°C)',
        'cloud_cover': 'Cloud Cover (%)',
        'relative_humidity_2m': 'Relative Humidity at 2m (%)', # Added for the new variable
        'dewpoint_2m': 'Dewpoint Temperature at 2m (°C)', # Added for the new variable
        'temperature_2m_max': 'Max Temperature at 2m (°C)',
        'temperature_2m_min': 'Min Temperature at 2m (°C)',
    }
    # Use the column name if no specific title is found
    return title_dict.get(column, column.replace('_', ' ').title())

@st.cache_data(ttl=3600)
def get_and_cache_forecast_data(lat, lon, site, variables, data_type, models):
    """ Fetches and caches Open-Meteo forecast data. """
    st.info(f"Fetching **{data_type}** forecast for **{site}** ({lat:.4f}, {lon:.4f}) using models: {', '.join(models)}...", icon="📡")
    
    lat_list = [str(lat)]
    lon_list = [str(lon)]
    site_list = [site]
    
    # Note: No timeout applied here as om_extract is assumed to handle API errors or be fast,
    # and caching provides stability.
    if data_type == 'hourly':
        df = om_extract.getData(lat_list, lon_list, site_list, variables=variables, models=models)
    else: # daily
        df = om_extract.getDailyData(lat_list, lon_list, site_list, variables=variables, models=models)
        
    if df.empty:
        st.error("Could not retrieve data from Open Meteo API. Check connection/parameters.")

    return df


# --- Streamlit Layout ---

# Header Section (Simplified)
st.title("wxapp")
st.caption("Interactive weather forecasting viewer. Click the map or select a site.")

# --- Sidebar Menu ---
with st.sidebar:
    st.header('Forecast Selection Menu')
    
    # --- NAMED SITE SELECTION ---
    current_df = st.session_state.get('site_data')
    initial_selected_site_index = 0
    if current_df is not None and not current_df.empty:
        site_list = current_df['site'].tolist()
        
        # Determine the index for the initial selection (either the last named site or default)
        try:
            current_display_site = st.session_state.get('ad_hoc_selection', {}).get('site', 'Brisbane')
            if current_display_site in site_list:
                initial_selected_site_index = site_list.index(current_display_site)
            elif st.session_state['last_named_site_selection'] in site_list:
                 initial_selected_site_index = site_list.index(st.session_state['last_named_site_selection'])
        except Exception:
            pass

        # Ensure the selected value of this widget is stored in st.session_state['site_select_sidebar']
        initial_selected_site = st.selectbox(
            'Select Named Site',
            site_list,
            index=initial_selected_site_index,
            key='site_select_sidebar'
        )
    else:
        initial_selected_site = None
        st.warning("No named sites available in the data.")
    # ----------------------------
    
    # --- NEW: Custom Parameter Input ---
    st.markdown("---")
    custom_hourly_input = st.text_input(
        'Add Custom Hourly Parameters',
        key='custom_hourly_input',
        placeholder='e.g., dewpoint_2m, surface_pressure',
        help="Enter Open-Meteo hourly variables separated by commas. These are treated as Hourly data."
    ).strip()
    
    custom_hourly_params = []
    if custom_hourly_input:
        # Split by comma and clean up spaces
        custom_hourly_params = [p.strip() for p in custom_hourly_input.split(',') if p.strip()]

    # 1. Combine base and custom parameters
    # Filter out custom params that are already in the base list to avoid duplication
    hourly_params = BASE_HOURLY_PARAMS + [p for p in custom_hourly_params if p not in BASE_HOURLY_PARAMS]
    
    # 2. DYNAMIC VARIABLE MAP GENERATION
    # Redefine all_variables_map dynamically based on current inputs
    all_variables_map = OrderedDict()
    
    # Process Hourly Parameters (Base and Custom)
    for var in hourly_params:
        is_obs_available = False 
        label = f'Hourly: {var}'
        if var in custom_hourly_params:
            label += ' (Custom)'
        
        all_variables_map[var] = {'label': label, 'type': 'hourly', 'is_obs_available': is_obs_available}

    # Process Daily Parameters (Static)
    for var in DAILY_PARAMS:
        all_variables_map[var] = {'label': 'Daily: ' + var, 'type': 'daily', 'is_obs_available': False}

    # Column Dropdown (Uses the dynamically generated all_variables_map, defaulted to empty list)
    variable_options = list(all_variables_map.keys())
    selected_columns = st.multiselect(
        'Select Weather Variables',
        options=variable_options,
        format_func=lambda x: all_variables_map[x]['label'],
        default=[], 
        key='column_select'
    )
    
    # Model Selection Multiselect (DEFAULTED TO EMPTY LIST)
    all_models = list(color_map.keys())
    selected_models = st.multiselect(
        'Select Forecast Models to Display',
        options=all_models,
        default=[], 
        key='model_select'
    )
    
    st.info('Click any point on the map to get an instant forecast for that location!')


# --- Site Selection Logic ---

# Split the top section into Map (3/4) and Info (1/4)
map_col, info_col = st.columns([3, 1])

# --- Determine Current Location (from session state/map click/sidebar) ---
current_selection = st.session_state['ad_hoc_selection']
selected_site = current_selection['site']
lat = current_selection['lat']
lon = current_selection['lon']

# Get the value from the sidebar selectbox
sidebar_site_name = st.session_state.get('site_select_sidebar')

# --- Only override the map click location if the user actively changes the sidebar selection ---
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


# --- Map Column: Folium Implementation ---
with map_col:
    # Initialize Map
    m = folium.Map(location=[lat, lon], zoom_start=5, tiles="openstreetmap")
    
    # Add markers for all named sites
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

    # Add a prominent marker for the current selected location
    folium.Marker(
        location=[lat, lon], 
        tooltip=f"Current: {selected_site} ({lat:.4f}, {lon:.4f})",
        icon=folium.Icon(color="red", icon="crosshairs", prefix='fa')
    ).add_to(m)

    # Display the Folium map
    map_output = st_folium(m, width=None, height=500, returned_objects=['last_clicked'], key="folium_map_main", use_container_width=True)

    # --- PROCESS MAP CLICK OUTPUT ---
    clicked_data = map_output.get("last_clicked")

    if clicked_data:
        # Map click updates the session state
        st.session_state['ad_hoc_selection'] = {
            'site': "Map Click Location", 
            'lat': clicked_data['lat'], 
            'lon': clicked_data['lng']
        }
        # Reset the named site tracker so the sidebar doesn't override next time
        st.session_state['last_named_site_selection'] = st.session_state.get('site_select_sidebar', 'Brisbane')
        
        st.rerun() 
    
# --- Info Column (Displays current coordinates) ---
with info_col:
    st.markdown("### Current Selection")
    st.metric("Location Name", selected_site)
    st.metric("Latitude", f"{lat:.4f}")
    st.metric("Longitude", f"{lon:.4f}")
    st.markdown("---")
    st.caption("Forecast data courtesy of Open-Meteo.")


# --- Main Content Section: Plots ---
st.divider()

if not selected_columns:
    st.info("Please select at least one variable in the sidebar menu to plot the data.")
    st.stop() 

# Get the first selected variable to determine the data type and the variable for observation plot
first_selected_var = selected_columns[0]
selected_data_type = all_variables_map[first_selected_var]['type']
variables_to_fetch = [
    var for var in selected_columns 
    if all_variables_map[var]['type'] == selected_data_type
]
obs_param = first_selected_var


# --- 2. Forecast Plot (Time Series) ---
st.subheader(f'Time Series Forecast for {selected_site}')


if not selected_models:
    st.warning("Please select at least one model in the sidebar menu to plot the forecast.")
else:
    # Call the cached data function which internally calls om_extract
    df_forecast = get_and_cache_forecast_data(
        lat=lat, 
        lon=lon, 
        site=selected_site, 
        variables=variables_to_fetch, 
        data_type=selected_data_type,
        models=selected_models
    )

    if df_forecast.empty:
        st.warning("No forecast data retrieved for the selected site and variables.")
    else:
        
        # Create the plot figure
        fig_ts = go.Figure()
        y_axis_label_set = False
        
        for selected_column in selected_columns:
            # Filter the dataframe for the selected column
            cols_to_plot = [col for col in df_forecast.columns if selected_column in col]
            
            if not y_axis_label_set:
                y_axis_label = get_yaxis_title(selected_column)
                y_axis_label_set = True

            # Add traces for each model
            for col in cols_to_plot:
                # Extract the model name
                cleaned_col = col.replace(selected_column, '').strip('_')

                # Get color
                color = color_map.get(cleaned_col, 'black')

                fig_ts.add_trace(go.Scatter(
                    x=df_forecast.index, 
                    y=df_forecast[col], 
                    mode='lines', 
                    name=f"{cleaned_col} ({all_variables_map[selected_column]['label']})", 
                    line=dict(color=color)
                ))

        # Update layout of the plot
        fig_ts.update_layout(
            title=f'{selected_data_type.capitalize()} Forecast Data',
            yaxis_title=y_axis_label,
            legend=dict(
                title='Model & Variable',
                font=dict(size=10),
                orientation="h",
                yanchor="bottom",
                y=-0.3, 
                xanchor="left",
                x=0
            ),
            xaxis=dict(showgrid=True, title='Forecast Time'),
            yaxis=dict(showgrid=True),
            hovermode="x unified",
            margin=dict(l=30, r=30, t=30, b=30),
            template="simple_white"
        )
        
        st.plotly_chart(fig_ts, use_container_width=True)
        
    st.caption(f"Forecast data type currently selected: **{selected_data_type.capitalize()}**")