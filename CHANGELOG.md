# Changelog

## 2025-12-15 - AWS Login as Default

### Major Changes

#### 1. AWS Login Screen as Main Entry Point
- AWS authentication is now the primary login screen when the app starts
- Users see a clean, centered login form before accessing the main application
- Brisbane ACCESS-CE domain is set as the default selection (index 0)

#### 2. Streamlined User Flow
- **First Time Users**: 
  - See login screen with AWS credentials form
  - Brisbane domain pre-selected
  - Can click "Continue Without Login" to use free Open-Meteo data only
  
- **After Login**:
  - AWS API (GSO/ACCESS) data source is automatically added to selected sources
  - Sidebar shows "✅ AWS API Connected" status
  - Domain selector available in sidebar for easy switching
  - Logout button returns to login screen

#### 3. Automatic Data Source Selection
- When authenticated, AWS API is automatically included in selected data sources
- Users get both Open-Meteo and AWS API by default
- No need to manually select AWS API from dropdown

#### 4. Simplified Sidebar
- Removed the authentication expander from sidebar
- Clean status indicator: "✅ AWS API Connected" or "ℹ️ Using free data sources only"
- Domain selector directly in sidebar (no nested expander)
- Single logout button
- Option to show login screen again if user skipped it initially

### Technical Details

**Modified Files:**
- `app.py`: Complete restructure of authentication flow

**Key Changes:**
1. Added `show_login` session state flag
2. Login screen shown before main app (using `st.stop()`)
3. Brisbane domain default: `index=0` in domain selector
4. Automatic AWS API inclusion in `selected_data_sources`
5. Removed duplicate domain selectors
6. Streamlined sidebar authentication UI

### User Experience Improvements

**Before:**
1. User opens app → sees main interface
2. Must find and expand "AWS API Authentication" in sidebar
3. Login form hidden in expander
4. Must manually select domain
5. After login, must manually select "AWS API (GSO/ACCESS)" from dropdown
6. Confusing with multiple domain selectors

**After:**
1. User opens app → sees clean login screen
2. Brisbane domain pre-selected
3. Login or skip with clear buttons
4. After login, AWS API automatically available
5. Clean sidebar with status and controls
6. Single domain selector in logical location

### Migration Notes

**Session State Variables Added:**
- `show_login`: Controls whether to display login screen (default: True on first load)

**Default Values:**
- Domain: `'brisbane'` (unchanged)
- Data Sources: `['Open-Meteo', 'AWS API (GSO/ACCESS)']` when authenticated
- Data Sources: `['Open-Meteo']` when not authenticated

### Future Enhancements

Possible future improvements:
- Remember login state (with secure token storage)
- Add "Remember Me" option
- Support for multiple authentication providers
- User profile management
