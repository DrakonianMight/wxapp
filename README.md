# ========================================
# README.md
"""
# Modular Weather App

## Project Structure

```
wxapp/
├── app.py                          # Main Streamlit application
├── config.py                       # Configuration constants
├── om_extract.py                   # Your existing Open-Meteo extraction module
├── siteList.csv                    # Site locations (optional)
│
├── data_sources/                   # Data source implementations
│   ├── __init__.py
│   ├── base.py                    # Abstract base class for data sources
│   └── open_meteo.py              # Open-Meteo implementation
│
├── views/                          # View modules
│   ├── __init__.py
│   ├── deterministic_view.py      # Deterministic forecast view
│   └── ensemble_view.py           # Probabilistic/ensemble forecast view
│
└── utils/                          # Utility modules
    ├── __init__.py
    ├── plotting.py                # Plotting functions
    └── probability.py             # Probability calculations
```

## Key Features

### 1. Modular Data Sources
- Easy to add new data sources by inheriting from `DataSource` base class
- Each data source implements:
  - `get_deterministic_data()`: Fetch deterministic forecasts
  - `get_ensemble_data()`: Fetch ensemble forecasts
  - `get_available_models()`: List available models
  - `get_available_variables()`: List available variables

### 2. Two View Types

#### Deterministic View
- Single-value forecasts from multiple models
- Time series line plots
- Model comparison
- Support for custom variables

#### Probabilistic/Ensemble View
- Ensemble forecasts with uncertainty quantification
- Percentile bands (10-90%, 25-75%)
- Optional individual member display
- Threshold exceedance probability analysis
- Up to 3 customizable thresholds

### 3. Threshold Analysis
When enabled in the Probabilistic view:
- Define up to 3 threshold values
- Calculate percentage of ensemble members exceeding each threshold
- Visualize exceedance probability over time
- Useful for risk assessment and decision-making

## Adding a New Data Source

1. Create a new file in `data_sources/` (e.g., `my_source.py`)
2. Inherit from `DataSource` base class
3. Implement required methods:

```python
from data_sources.base import DataSource
import pandas as pd

class MyDataSource(DataSource):
    def __init__(self):
        super().__init__(name="My Source", supports_ensemble=True)
    
    def get_deterministic_data(self, lat, lon, site, variables, data_type, models):
        # Fetch and return DataFrame
        pass
    
    def get_ensemble_data(self, lat, lon, site, variables, data_type, models):
        # Fetch and return DataFrame with ensemble members
        pass
    
    def get_available_models(self, forecast_type='deterministic'):
        return ['model1', 'model2']
    
    def get_available_variables(self, data_type='hourly'):
        return ['temp', 'wind', 'pressure']
```

4. Register in `app.py`:

```python
from data_sources.my_source import MyDataSource

DATA_SOURCES = {
    'Open-Meteo': OpenMeteoDataSource(),
    'My Source': MyDataSource(),
}
```

## Expected Data Format

### Deterministic Data
DataFrame with:
- Index: Datetime
- Columns: `{variable}_{model}` (e.g., `temperature_2m_ecmwf_ifs`)

### Ensemble Data
DataFrame with:
- Index: Datetime
- Columns: `{variable}_{model}_member_{N}` (e.g., `temperature_2m_gfs_ensemble_member_01`)

## Installation

```bash
pip install streamlit pandas plotly folium streamlit-folium
```

## Running the App

```bash
streamlit run app.py
```

## Notes

- Data is cached for 1 hour to reduce API calls
- Map clicks allow ad-hoc location selection
- Custom variables can be added via text input
- Both hourly and daily forecast types supported
"""
else:
    render_ensemble_view(
        data_source=data_source,
        lat=lat,
        lon=lon,
        site=selected_site,
        custom_hourly_params=custom_hourly_params,
        base_hourly_params=BASE_HOURLY_PARAMS,
        daily_params=DAILY_PARAMS
    )
