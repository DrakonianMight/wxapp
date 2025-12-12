#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for AWS API integration

This script tests the AWS API data source without running the full Streamlit app.
Usage: python test_aws_integration.py
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        import boto3
        print("  ✓ boto3")
    except ImportError:
        print("  ✗ boto3 - Run: pip install boto3")
        return False
    
    try:
        import xarray
        print("  ✓ xarray")
    except ImportError:
        print("  ✗ xarray - Run: pip install xarray")
        return False
    
    try:
        import netCDF4
        print("  ✓ netCDF4")
    except ImportError:
        print("  ✗ netCDF4 - Run: pip install netCDF4")
        return False
    
    try:
        from utils.cognito_auth import CognitoAuth
        print("  ✓ cognito_auth")
    except ImportError as e:
        print(f"  ✗ cognito_auth - {e}")
        return False
    
    try:
        from aws_api_extract import AWSAPIClient
        print("  ✓ aws_api_extract")
    except ImportError as e:
        print(f"  ✗ aws_api_extract - {e}")
        return False
    
    try:
        from data_sources.aws_api import AWSAPIDataSource
        print("  ✓ aws_api data source")
    except ImportError as e:
        print(f"  ✗ aws_api data source - {e}")
        return False
    
    print("All imports successful!\n")
    return True


def test_authentication():
    """Test authentication with AWS Cognito"""
    print("Testing authentication...")
    print("Enter your AWS Cognito credentials:")
    print("(Get these from your AWS Cognito console)")
    
    user_pool_id = input("User Pool ID (e.g., ap-southeast-2_XXXXXXXXX): ").strip()
    client_id = input("Client ID (e.g., xxxxxxxxxxxxxxxxxxxxx): ").strip()
    username = input("Username: ").strip()
    
    if not user_pool_id or not client_id:
        print("  ✗ User Pool ID and Client ID are required")
        return None, None
    
    import getpass
    password = getpass.getpass("Password: ")
    
    if not username or not password:
        print("  ✗ Username and password are required")
        return None, None
    
    try:
        from utils.cognito_auth import CognitoAuth
        auth = CognitoAuth(user_pool_id, client_id)
        
        print("  Authenticating...")
        success, id_token, error = auth.authenticate(username, password)
        
        if success:
            print(f"  ✓ Authentication successful!")
            print(f"  Token (first 50 chars): {id_token[:50]}...")
            return id_token, None
        else:
            print(f"  ✗ Authentication failed: {error}")
            return None, error
    except Exception as e:
        print(f"  ✗ Authentication error: {e}")
        return None, str(e)


def test_api_client(id_token):
    """Test API client functionality"""
    print("\nTesting API client...")
    
    try:
        from aws_api_extract import AWSAPIClient
        
        base_url = "https://fmeq0xvw60.execute-api.ap-southeast-2.amazonaws.com/prod"
        client = AWSAPIClient(base_url, id_token)
        
        # Test metadata for GSO
        print("  Testing metadata for GSO...")
        metadata = client.get_metadata("gso", domain="australia")
        print(f"  ✓ GSO metadata retrieved")
        
        # Test getting variables
        print("  Testing available variables for GSO...")
        variables = client.get_available_variables("gso", domain="australia")
        print(f"  ✓ Found {len(variables)} variables")
        print(f"  Sample variables: {variables[:5]}")
        
        # Test data extraction
        print("  Testing data extraction for GSO (Brisbane)...")
        ds = client.extract_point_data(
            model="gso",
            lon=153.0260,
            lat=-27.4705,
            variables=variables[:3],  # Just test with first 3 variables
            domain="australia"
        )
        print(f"  ✓ Data extracted successfully")
        print(f"  Dataset dimensions: {dict(ds.dims)}")
        
        return True
    except Exception as e:
        print(f"  ✗ API client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_source(id_token):
    """Test DataSource implementation"""
    print("\nTesting DataSource implementation...")
    
    try:
        from data_sources.aws_api import AWSAPIDataSource
        
        base_url = "https://fmeq0xvw60.execute-api.ap-southeast-2.amazonaws.com/prod"
        ds = AWSAPIDataSource(base_url, id_token, domain="brisbane")
        
        print(f"  Data source name: {ds.name}")
        
        # Test available models
        print("  Testing available models...")
        det_models = ds.get_available_models("deterministic")
        ens_models = ds.get_available_models("ensemble")
        print(f"  ✓ Deterministic models: {det_models}")
        print(f"  ✓ Ensemble models: {ens_models}")
        
        # Test available variables
        print("  Testing available variables...")
        variables = ds.get_available_variables("hourly")
        print(f"  ✓ Found {len(variables)} canonical variables")
        print(f"  Sample: {variables[:5]}")
        
        # Test getting deterministic data
        print("  Testing deterministic data retrieval (GSO, Brisbane)...")
        # Create a mock streamlit module to avoid import errors
        import types
        mock_st = types.ModuleType('streamlit')
        mock_st.warning = lambda x: print(f"    Warning: {x}")
        mock_st.session_state = {}
        sys.modules['streamlit'] = mock_st
        
        df = ds.get_deterministic_data(
            lat=-27.4705,
            lon=153.0260,
            site="Brisbane",
            variables=["temperature_2m", "wind_speed_10m"],
            data_type="hourly",
            models=["gso"]
        )
        
        if not df.empty:
            print(f"  ✓ Retrieved {len(df)} rows of data")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Date range: {df['datetime'].min()} to {df['datetime'].max()}")
        else:
            print(f"  ✗ No data retrieved")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ DataSource test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("AWS API Integration Test Suite")
    print("=" * 60)
    print()
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed. Please install missing dependencies.")
        return
    
    # Test authentication
    id_token, error = test_authentication()
    if not id_token:
        print("\n❌ Authentication failed. Cannot continue with API tests.")
        return
    
    # Test API client
    if not test_api_client(id_token):
        print("\n❌ API client tests failed.")
        return
    
    # Test DataSource
    if not test_data_source(id_token):
        print("\n❌ DataSource tests failed.")
        return
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\nYou can now run the app with: streamlit run app.py")


if __name__ == "__main__":
    main()
