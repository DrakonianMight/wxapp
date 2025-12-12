# AWS API Integration for wxapp

This document describes the integration of AWS API weather models (GSO, ACCESS-G, ACCESS-GE, ACCESS-CE) into the wxapp.

## Overview

The AWS API data source provides access to Australian weather models through an authenticated API endpoint. This requires AWS Cognito credentials.

## Architecture

### Components

1. **aws_api_extract.py** - Low-level API client for AWS weather API
   - `AWSAPIClient` - Handles authentication and API calls
   - Methods: `get_metadata()`, `get_available_variables()`, `extract_point_data()`

2. **data_sources/aws_api.py** - DataSource implementation
   - `AWSAPIDataSource` - Implements the DataSource abstract class
   - Handles variable name mapping between API and wxapp conventions
   - Supports both deterministic and ensemble forecasts

3. **utils/cognito_auth.py** - AWS Cognito authentication
   - `CognitoAuth` - Handles user authentication with AWS Cognito
   - Returns ID tokens for API authorization

4. **app.py** - Main application updates
   - Authentication UI in sidebar
   - Session state management for tokens
   - Dynamic data source registration

## Available Models

### Deterministic Models
- **gso** - Global Southern Ocean model
- **access-g** - ACCESS Global model

### Ensemble Models
- **access-ge** - ACCESS Global Ensemble
- **access-ce** - ACCESS City Ensemble (requires domain selection)

## Domain Support

The ACCESS-CE model requires a domain parameter. Available domains:
- adelaide
- brisbane
- sydney
- darwin
- canberra
- hobart
- melbourne
- perth
- nqld

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required new packages:
- boto3 (AWS SDK)
- xarray (netCDF handling)
- netCDF4 (netCDF support)

### 2. AWS Cognito Configuration

You need the following credentials:
- **User Pool ID** - AWS Cognito User Pool ID
- **Client ID** - AWS Cognito App Client ID
- **Username** - Your username
- **Password** - Your password

These can be entered in the wxapp sidebar under "AWS API Authentication".

### 3. Environment Variables (Optional)

For production deployment, consider using environment variables instead of hardcoding:

```python
import os
user_pool_id = os.getenv('AWS_USER_POOL_ID', 'default-value')
client_id = os.getenv('AWS_CLIENT_ID', 'default-value')
base_url = os.getenv('AWS_API_BASE_URL', 'https://...')
```

## Usage

### In the App

1. Launch the app: `streamlit run app.py`
2. In the sidebar, expand "AWS API Authentication"
3. Enter your AWS Cognito credentials
4. Click "Login"
5. Select "AWS API (GSO/ACCESS)" from the Data Source dropdown
6. Choose Deterministic or Ensemble forecast type
7. Select models and variables as usual

### Programmatic Usage

```python
from data_sources.aws_api import AWSAPIDataSource
from utils.cognito_auth import CognitoAuth

# Authenticate
auth = CognitoAuth(user_pool_id, client_id)
success, id_token, error = auth.authenticate(username, password)

if success:
    # Create data source
    ds = AWSAPIDataSource(
        base_url='https://fmeq0xvw60.execute-api.ap-southeast-2.amazonaws.com/prod',
        id_token=id_token,
        domain='brisbane'
    )
    
    # Get deterministic data
    df = ds.get_deterministic_data(
        lat=-27.4705,
        lon=153.0260,
        site='Brisbane',
        variables=['temperature_2m', 'wind_speed_10m'],
        data_type='hourly',
        models=['gso', 'access-g']
    )
    
    # Get ensemble data
    df_ens = ds.get_ensemble_data(
        lat=-27.4705,
        lon=153.0260,
        site='Brisbane',
        variables=['temperature_2m'],
        data_type='hourly',
        models=['access-ge', 'access-ce']
    )
```

## Variable Mapping

The data source automatically maps between wxapp canonical variable names and API variable names:

| wxapp Variable | API Variables |
|----------------|--------------|
| temperature_2m | t2, temperature_2m, temp_2m, air_temperature_2m |
| wind_speed_10m | ws10, wind_speed_10m, wind_speed |
| wind_direction_10m | wd10, wind_direction_10m, wind_direction |
| precipitation | tp, precipitation, total_precipitation, precip |
| relative_humidity_2m | rh2, relative_humidity_2m, rh_2m |
| pressure_msl | msl, mean_sea_level_pressure, pressure, mslp |
| cloud_cover | tcc, total_cloud_cover, cloud_cover |
| wind_gusts_10m | wg10, wind_gust_10m, wind_gusts |

## Error Handling

The integration includes comprehensive error handling:

1. **Authentication Errors** - Invalid credentials, expired tokens
2. **API Errors** - Network issues, invalid requests
3. **Data Errors** - Missing variables, invalid coordinates

Errors are displayed as warnings in the Streamlit UI and don't crash the app.

## Token Management

- ID tokens are stored in `st.session_state['aws_id_token']`
- Tokens may expire and require re-authentication
- The app will show a 401 error if the token expires
- Simply logout and login again to refresh the token

## Security Considerations

1. **Never commit credentials** - Use environment variables or Streamlit secrets
2. **Token storage** - Tokens are only stored in session state (memory)
3. **HTTPS** - The API uses HTTPS for secure communication
4. **Password field** - Passwords are masked in the UI

## Troubleshooting

### "Import boto3 could not be resolved"
- Install boto3: `pip install boto3`

### "Import xarray could not be resolved"
- Install xarray and netCDF4: `pip install xarray netCDF4`

### "Unauthorized: token expired or invalid"
- Your ID token has expired
- Click "Logout" and login again

### "Domain is required for ACCESS-CE"
- Select a domain in the authentication section
- Available domains: brisbane, sydney, melbourne, etc.

### No data returned
- Check that the selected variables are available for the model
- Try a different location (some models have limited coverage)
- Verify your credentials are still valid

## Future Enhancements

Possible improvements:
1. Automatic token refresh
2. Remember credentials (securely)
3. Model metadata caching
4. Variable availability checking before fetching
5. Multiple domain support in ensemble view
6. Bulk model fetching optimization

## API Endpoints

- **Metadata**: `GET /metadata/{model}?domain={domain}`
- **Extract**: `POST /extract/{model}` with JSON body:
  ```json
  {
    "x": [longitude],
    "y": [latitude],
    "variables": ["t2", "ws10"],
    "domain": "brisbane"  // For CE models
  }
  ```

## Contact

For AWS API access issues, contact the API administrator.
For wxapp integration issues, create an issue in the wxapp repository.
