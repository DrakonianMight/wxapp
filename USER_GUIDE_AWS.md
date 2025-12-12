# User Guide: Dynamic AWS API Integration

## What You'll See When Using AWS Models

### 1️⃣ Before Login
```
Sidebar:
  🔐 AWS API Authentication  [Collapsed ▶]
  ────────────────────────
  Data Source: [Open-Meteo ▼]  ← Only Open-Meteo available
```

### 2️⃣ Logging In
```
Expand Authentication Section:

🔐 AWS API Authentication  [Expanded ▼]
  ℹ️ Enter your AWS credentials to access GSO and ACCESS models
  
  User Pool ID: ••••••••••••••••••••
  Client ID: ••••••••••••••••••••
  Username: [your-username]
  Password: [••••••••]
  Default Domain (for ACCESS-CE): [brisbane ▼]
  
  [Sign In]  ← Click here
```

### 3️⃣ After Successful Login
```
🔐 AWS API Authentication  [Expanded ▼]
  ✅ Authentication successful! AWS models (GSO, ACCESS-G, 
     ACCESS-GE, ACCESS-CE) are now available.
  💡 Select 'AWS API (GSO/ACCESS)' from the Data Source dropdown 
     to use these models.

App reruns automatically...
```

### 4️⃣ Data Source Now Available
```
Sidebar:
  🔐 AWS API Authentication  [Can collapse now ▲]
    ✅ Authenticated with AWS API
    Current domain: brisbane
    
    Change Domain: [brisbane ▼]
    [Logout]
  
  ────────────────────────
  Data Source: [AWS API (GSO/ACCESS) ▼]  ← NEW OPTION!
                ↑ Select this
```

### 5️⃣ Domain Selector Appears
```
Data Source: [AWS API (GSO/ACCESS) ▼]

**ACCESS-CE Domain**
Select Domain for ACCESS-CE: [brisbane ▼]
ℹ️ Domain used for ACCESS-CE ensemble model
  
  ⚬ adelaide
  ⚬ brisbane  ← Currently selected
  ⚬ sydney
  ⚬ darwin
  ⚬ canberra
  ⚬ hobart
  ⚬ melbourne
  ⚬ perth
  ⚬ nqld
```

### 6️⃣ Changing Domain (Main Sidebar)
```
Select Domain: [sydney ▼]  ← Change from brisbane to sydney

💡 Domain changed to sydney. Variables will update for ACCESS-CE.

App reruns automatically...

Variables dropdown updates with sydney-specific options
```

### 7️⃣ Changing Domain (Auth Expander)
```
🔐 AWS API Authentication  [Expanded ▼]
  ✅ Authenticated with AWS API
  Current domain: brisbane
  
  Change Domain: [melbourne ▼]  ← Change here
  
💡 Domain changed to melbourne. Reloading...

App reruns automatically...
```

### 8️⃣ Using Deterministic View
```
Forecast Type: ⚪ Deterministic  [Selected]

Select Forecast Models: 
  [✓] gso
  [✓] access-g

Select Weather Variables:
  [✓] ghi (from GSO metadata)
  [✓] dni (from GSO metadata)
  [✓] t2 (from ACCESS-G metadata)
  [✓] ws10 (from ACCESS-G metadata)
  ... (all variables from both models shown)
```

### 9️⃣ Using Ensemble View
```
Forecast Type: ⚪ Probabilistic/Ensemble  [Selected]

Select Ensemble Models:
  [✓] gso
  [✓] access-ge
  [✓] access-ce

Select Weather Variable: [t2 ▼]
  ⚬ ghi (available in gso)
  ⚬ dni (available in gso)
  ⚬ t2 (available in all models)
  ⚬ rh2 (available in access-ge, access-ce)
  ⚬ ws10 (available in all models)
  ... (union of all variables from all models)
```

### 🔟 After Logout
```
🔐 AWS API Authentication  [Expanded ▼]
  Logging out...

App reruns automatically...

Data Source: [Open-Meteo ▼]  ← AWS API removed from dropdown
```

## Quick Actions

### ⚡ Quick Domain Change
1. Select AWS API data source
2. Change domain in dropdown below
3. App reruns automatically
4. New variables loaded

### ⚡ Check Current Domain
Look at Authentication expander:
```
✅ Authenticated with AWS API
Current domain: brisbane  ← Shows current domain
```

### ⚡ Switch Between Views
- **Deterministic**: gso, access-g available
- **Ensemble**: gso, access-ge, access-ce available
- GSO works in BOTH views!

## Visual Feedback Messages

### ✅ Success Messages
- `✅ Authentication successful! AWS models are now available.`
- `✅ Authenticated with AWS API`

### 💡 Info Messages
- `💡 Select 'AWS API (GSO/ACCESS)' from Data Source dropdown`
- `💡 Domain changed to {domain}. Variables will update.`
- `💡 Domain changed to {domain}. Reloading...`

### ⚠️ Warning Messages
- `⚠️ Failed to fetch metadata for {model}: {error}`
- `⚠️ None of the requested variables are available for {model}`
- `⚠️ Failed to fetch {model}: {error}`

### ❌ Error Messages
- `❌ Authentication failed: {reason}`
- `❌ Authentication error: {details}`

## Model Availability Reference

| Model | Deterministic | Ensemble | Domain | Description |
|-------|--------------|----------|---------|-------------|
| **gso** | ✅ | ✅ | australia (fixed) | Solar irradiance nowcast |
| **access-g** | ✅ | ❌ | none | ACCESS Global deterministic |
| **access-ge** | ❌ | ✅ | none | ACCESS Global Ensemble |
| **access-ce** | ❌ | ✅ | **required** | ACCESS City Ensemble |

## Tips for Best Experience

1. **Select domain BEFORE choosing variables** (for access-ce)
2. **Variables auto-update** when domain changes (no manual refresh)
3. **Check "Current domain"** in auth expander to verify which domain is active
4. **GSO for solar** - available in both deterministic and ensemble views
5. **Multiple domains** - change domain anytime to access different ACCESS-CE data

## Keyboard Shortcuts

- **Enter** to submit login form
- **Tab** to navigate between fields
- **Space** to toggle checkboxes (model selection)
- **Arrow keys** to navigate dropdowns

## Common Workflows

### Solar Nowcast (GSO)
```
Login → Select AWS API → Deterministic View → 
Select GSO → Select ghi/dni/dhi → Click map location
```

### City Weather Ensemble
```
Login → Select AWS API → Change domain to sydney → 
Ensemble View → Select access-ce → Select t2 → Click map
```

### Compare All Models
```
Login → Select AWS API → Ensemble View → 
Select all three models → Select common variable → 
View ensemble spread comparison
```

## What Happens Behind the Scenes

### On Login
1. ✓ Authenticate with AWS Cognito
2. ✓ Store ID token in session
3. ✓ Store selected domain
4. ✓ App reruns
5. ✓ `get_data_sources()` creates AWS instance
6. ✓ AWS API appears in dropdown

### On Domain Change
1. ✓ Detect domain change
2. ✓ Update session state
3. ✓ Show info message
4. ✓ App reruns
5. ✓ New AWS instance created
6. ✓ Fresh metadata cache
7. ✓ Variables update in dropdowns

### On Variable Selection
1. ✓ Call `get_available_variables()`
2. ✓ Check cache (empty for new instance)
3. ✓ Fetch from API metadata endpoint
4. ✓ Cache results
5. ✓ Display in dropdown

## Troubleshooting

### Domain change doesn't seem to work?
- Look for the info message (should appear)
- Check if app reran (URL might flash)
- Verify domain in auth expander matches what you selected

### Variables don't include new domain's variables?
- Make sure you changed domain BEFORE opening variable dropdown
- Try closing and re-opening the variable dropdown
- If still stuck, logout and login again

### AWS API not in dropdown after login?
- Check for error messages in auth expander
- Verify credentials are correct
- Make sure you clicked "Sign In" button
- Try refreshing the page (Ctrl+R or Cmd+R)

## Support

If you encounter issues:
1. Check the authentication expander for error messages
2. Look at the Streamlit logs in terminal
3. Verify your credentials are correct
4. Try logout → login again
5. Check `DYNAMIC_UPDATES.md` for technical details
