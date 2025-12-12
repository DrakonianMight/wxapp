# Authentication and Data Source Lifecycle - Complete Flow

## Problem Statement
After authentication happens, the data sources need to update dynamically to include the AWS API option, and users need clear feedback that new options are available.

## Solution Overview
The app now properly handles the authentication lifecycle with these key features:
1. ✅ Data sources refresh after authentication
2. ✅ Clear success message highlights new availability
3. ✅ Data source selection persists correctly
4. ✅ Domain changes trigger proper reloads

## Complete Application Flow

### 📍 App Initialization (First Load)

```python
# Session State Initialization
st.session_state['aws_authenticated'] = False
st.session_state['aws_id_token'] = None
st.session_state['aws_domain'] = 'brisbane'
st.session_state['aws_just_authenticated'] = False

# Data Sources Available
get_data_sources() returns:
  - 'Open-Meteo': OpenMeteoDataSource()
  # No AWS API (not authenticated)
```

**UI Shows:**
```
Sidebar:
  🔐 AWS API Authentication [Collapsed]
  ───────────────────────
  Data Source: [Open-Meteo ▼]  ← Only option
```

---

### 📍 User Expands Authentication

```
🔐 AWS API Authentication [Expanded ▼]
  ℹ️ Enter your AWS credentials...
  
  User Pool ID: [filled]
  Client ID: [filled]
  Username: [user enters]
  Password: [user enters]
  Default Domain: [brisbane ▼]
  
  [Login] ← User clicks
```

---

### 📍 Login Process

**Step 1: Validate Input**
```python
if not username or not password:
    st.error("Please enter username and password")
    # STOP - don't proceed
```

**Step 2: Authenticate**
```python
with st.spinner("Authenticating..."):
    auth = CognitoAuth(user_pool_id, client_id)
    success, id_token, error = auth.authenticate(username, password)
```

**Step 3: Handle Success**
```python
if success:
    # Update session state
    st.session_state['aws_authenticated'] = True
    st.session_state['aws_id_token'] = id_token
    st.session_state['aws_domain'] = domain
    st.session_state['aws_just_authenticated'] = True  # ← New flag!
    
    # Show immediate feedback
    st.success("✅ Authentication successful!")
    st.info("💡 Select 'AWS API (GSO/ACCESS)' from dropdown")
    
    # Force app reload
    st.rerun()
```

**Step 4: Handle Failure**
```python
else:
    st.error(f"❌ Authentication failed: {error}")
    # Stay on same page, user can try again
```

---

### 📍 After Rerun (Post-Authentication)

**Sidebar Re-Execution Flow:**

1. **Authentication Section Runs**
   ```python
   # Now authenticated
   if st.session_state.get('aws_authenticated', False):
       # Show "Authenticated" state
   ```

2. **Data Sources Refresh**
   ```python
   DATA_SOURCES = get_data_sources()
   
   # Now returns:
   {
     'Open-Meteo': OpenMeteoDataSource(),
     'AWS API (GSO/ACCESS)': AWSAPIDataSource(
         id_token=st.session_state['aws_id_token'],
         domain=st.session_state['aws_domain']
     )
   }
   ```

3. **Success Message Displays**
   ```python
   if st.session_state.get('aws_just_authenticated', False):
       st.success("🎉 AWS API data source is now available!")
       st.session_state['aws_just_authenticated'] = False  # Clear flag
   ```

4. **Data Source Selector Updates**
   ```python
   # Options now include both:
   options = ['Open-Meteo', 'AWS API (GSO/ACCESS)']
   
   # Previous selection preserved (if still available)
   # Or defaults to first option
   ```

**UI Now Shows:**
```
Sidebar:
  🔐 AWS API Authentication [Can collapse]
    ✅ Authenticated with AWS API
    Current domain: brisbane
    [Change Domain] [Logout]
  
  ───────────────────────
  🎉 AWS API data source is now available! ← Success banner
  
  Data Source: [Open-Meteo ▼]  ← Can now select AWS API
               └─ Open-Meteo
                  AWS API (GSO/ACCESS) ← NEW!
```

---

### 📍 User Selects AWS API

```python
selected_source_name = 'AWS API (GSO/ACCESS)'
data_source = DATA_SOURCES[selected_source_name]  # Fresh instance

# Domain selector appears
if 'AWS API' in selected_source_name:
    # Show domain dropdown
```

**UI Updates:**
```
Data Source: [AWS API (GSO/ACCESS) ▼]

**ACCESS-CE Domain**
Select Domain for ACCESS-CE: [brisbane ▼]
ℹ️ Domain used for ACCESS-CE ensemble model
```

---

### 📍 Domain Change Flow

**Option 1: Change in Main Sidebar**
```python
# User changes domain
new_domain = st.selectbox(..., key='aws_domain_main')

if new_domain != current_domain:
    st.session_state['aws_domain'] = new_domain
    st.info(f"Domain changed to {new_domain}...")
    st.rerun()  # ← Force reload
```

**Option 2: Change in Auth Expander**
```python
domain = st.selectbox(..., key='aws_domain_change')

if domain != prev_domain:
    st.session_state['aws_domain'] = domain
    st.info(f"Domain changed to {domain}. Reloading...")
    st.rerun()  # ← Force reload
```

**After Domain Change Rerun:**
```python
# Sidebar re-executes
DATA_SOURCES = get_data_sources()

# New AWSAPIDataSource instance created with new domain
AWSAPIDataSource(
    id_token=st.session_state['aws_id_token'],
    domain=st.session_state['aws_domain']  # ← Updated domain
)

# Fresh instance = empty _metadata_cache
# Next variable selection will fetch new metadata
```

---

### 📍 Variable Selection

**User opens variable dropdown:**
```python
# View calls data_source.get_available_variables()
variables = data_source.get_available_variables()

# First time after domain change:
for model in ['gso', 'access-g', 'access-ge', 'access-ce']:
    vars_list = self._get_model_variables(model, domain)
    # ↓ Cache miss → API call
    if cache_key not in self._metadata_cache:
        variables = self.client.get_available_variables(model, domain)
        self._metadata_cache[cache_key] = variables
    # ↓ Returns from cache on subsequent calls
```

**Variables appear in dropdown:**
- All variables from all models
- Updated for current domain (for access-ce)
- Fresh metadata from API

---

### 📍 Logout Flow

```python
if st.button("Logout"):
    st.session_state['aws_authenticated'] = False
    st.session_state['aws_id_token'] = None
    st.rerun()
```

**After Logout Rerun:**
```python
DATA_SOURCES = get_data_sources()
# Returns: {'Open-Meteo': OpenMeteoDataSource()}
# AWS API removed from options

# If AWS API was selected, selectbox falls back to Open-Meteo
```

---

## Key Mechanisms

### 1. Dynamic Data Source Creation
```python
def get_data_sources():
    """Called every time sidebar renders"""
    sources = {'Open-Meteo': OpenMeteoDataSource()}
    
    # Check current authentication state
    if AWS_API_AVAILABLE and st.session_state.get('aws_authenticated'):
        sources['AWS API (GSO/ACCESS)'] = AWSAPIDataSource(
            id_token=st.session_state['aws_id_token'],
            domain=st.session_state['aws_domain']
        )
    
    return sources
```

### 2. One-Time Success Message
```python
# Set flag on successful login
st.session_state['aws_just_authenticated'] = True

# Display and clear flag on next render
if st.session_state.get('aws_just_authenticated'):
    st.success("🎉 AWS API data source is now available!")
    st.session_state['aws_just_authenticated'] = False
```

### 3. Selection Persistence
```python
# Preserve user's previous selection if still available
if 'data_source_select' in st.session_state:
    prev_selection = st.session_state['data_source_select']
    if prev_selection in source_options:
        default_index = source_options.index(prev_selection)
```

### 4. Forced Reruns
```python
# After authentication
st.rerun()  # Entire app reruns, sidebar re-executes, data sources refresh

# After domain change
st.rerun()  # New data source instance created with new domain
```

---

## State Management

### Session State Variables

| Variable | Type | Purpose | Lifecycle |
|----------|------|---------|-----------|
| `aws_authenticated` | bool | Tracks auth status | Set on login, cleared on logout |
| `aws_id_token` | str | API auth token | Set on login, cleared on logout |
| `aws_domain` | str | Current CE domain | Set on login, updated on change |
| `aws_just_authenticated` | bool | Success message flag | Set on login, cleared after display |
| `aws_domain_changed` | bool | Domain change flag | Set on change, used for tracking |
| `data_source_select` | str | Selected data source | Managed by Streamlit widget |

---

## Execution Order (Critical!)

```
1. Session state initialization (if needed)
2. Sidebar starts rendering
3.   ├─ Authentication section
4.   │    ├─ Login button → updates state → st.rerun()
5.   │    └─ Domain change → updates state → st.rerun()
6.   ├─ Separator
7.   ├─ DATA_SOURCES = get_data_sources() ← Reads current state
8.   ├─ Success message (if aws_just_authenticated)
9.   ├─ Data source selector ← Uses fresh DATA_SOURCES
10.  └─ Domain selector (if AWS selected)
11. Main content area (uses selected data_source)
```

**Key Point:** `get_data_sources()` is called AFTER authentication changes, so it always reflects the current state.

---

## Testing Scenarios

### ✅ Scenario 1: Fresh Start → Login
1. App loads with only Open-Meteo
2. User logs in
3. App reruns
4. AWS API appears in dropdown
5. Success message displays once
6. User can select AWS API

### ✅ Scenario 2: Change Domain (Main Sidebar)
1. User selects AWS API
2. Domain selector appears
3. User changes domain
4. Info message shows
5. App reruns
6. New data source instance created
7. Variables update on next access

### ✅ Scenario 3: Change Domain (Auth Expander)
1. User opens auth expander
2. Changes domain dropdown
3. Info message shows
4. App reruns
5. New instance with new domain
6. Variables update

### ✅ Scenario 4: Logout
1. User clicks logout
2. App reruns
3. AWS API removed from dropdown
4. Falls back to Open-Meteo
5. Can login again

### ✅ Scenario 5: Selection Persistence
1. User selects AWS API
2. Changes some other setting (e.g., forecast type)
3. Sidebar reruns
4. AWS API still selected (preserved)

---

## Why This Works

1. **Reactive State**: `get_data_sources()` reads current session state
2. **Forced Reruns**: `st.rerun()` after state changes ensures UI updates
3. **One-Time Messages**: Flag pattern prevents message spam
4. **Fresh Instances**: New domain = new object = empty cache = fresh metadata
5. **Selection Preservation**: Widget keys maintain user choices across reruns

---

## Common Issues (Prevented)

### ❌ "AWS API not appearing after login"
**Prevented by:** 
- `st.rerun()` forces sidebar re-execution
- `get_data_sources()` called after auth state changes
- Success message confirms availability

### ❌ "Domain change doesn't update variables"
**Prevented by:**
- `st.rerun()` creates new data source instance
- Empty cache forces fresh metadata fetch
- Info message confirms reload

### ❌ "Success message shows every time"
**Prevented by:**
- `aws_just_authenticated` flag pattern
- Flag cleared after message displays
- Only set on successful login

### ❌ "Selection lost after domain change"
**Prevented by:**
- Selection preserved via `data_source_select` key
- Index-based default selection
- Fallback to first option if selection invalid

---

## Performance Considerations

### Efficient API Calls
- Metadata cached within each instance
- Only fetched on first variable access
- Only re-fetched on domain change

### Minimal Reruns
- Only rerun on authentication or domain changes
- Other changes don't trigger reruns
- Streamlit's differential rendering minimizes work

### Memory Management
- Old data source instances garbage collected
- Caches cleared automatically (new instance)
- Session state kept minimal

---

## Summary

The authentication and data source lifecycle is now properly managed:
1. ✅ **Login**: State updates → rerun → data sources refresh → success message → ready to use
2. ✅ **Domain Change**: State updates → rerun → new instance → fresh metadata → variables update
3. ✅ **Logout**: State clears → rerun → AWS removed → back to baseline
4. ✅ **Persistence**: Selections preserved across compatible state changes

The app is fully reactive and provides clear feedback at every step! 🎉
