# File: views/metadata_view.py
"""Metadata view showing available models and data sources"""

import streamlit as st
import pandas as pd
from typing import Dict


def show_metadata_view(data_sources: Dict):
    """
    Display metadata about available models and data sources
    
    Args:
        data_sources: Dictionary of available data sources {name: DataSource}
    """
    st.title("📊 Data Sources & Models Metadata")
    
    st.markdown("""
    This page provides comprehensive information about all available data sources, 
    models, and their supported variables in the wxapp.
    """)
    
    # Overview section
    st.header("🌍 Data Sources Overview")
    
    overview_data = []
    for source_name, data_source in data_sources.items():
        overview_data.append({
            "Data Source": source_name,
            "Supports Deterministic": "✅" if hasattr(data_source, 'get_deterministic_data') else "❌",
            "Supports Ensemble": "✅" if data_source.supports_ensemble else "❌",
            "Authentication Required": "✅" if source_name == "AWS API (GSO/ACCESS)" else "❌"
        })
    
    overview_df = pd.DataFrame(overview_data)
    st.dataframe(overview_df, use_container_width=True, hide_index=True)
    
    # Detailed models section
    st.header("📋 Available Models by Data Source")
    
    for source_name, data_source in data_sources.items():
        with st.expander(f"🔍 {source_name}", expanded=True):
            
            # Deterministic models
            st.subheader("Deterministic Models")
            try:
                det_models = data_source.get_available_models('deterministic')
                if det_models:
                    det_data = []
                    for model in det_models:
                        # Get model-specific variables if available
                        try:
                            model_vars = data_source.get_model_specific_variables(model, 'deterministic')
                            var_count = len(model_vars) if model_vars else "N/A"
                        except Exception:
                            var_count = "N/A"
                        
                        det_data.append({
                            "Model": model,
                            "Type": "Deterministic",
                            "Variables Available": var_count
                        })
                    
                    det_df = pd.DataFrame(det_data)
                    st.dataframe(det_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No deterministic models available")
            except Exception as e:
                st.warning(f"Could not retrieve deterministic models: {str(e)}")
            
            # Ensemble models
            if data_source.supports_ensemble:
                st.subheader("Ensemble Models")
                try:
                    ens_models = data_source.get_available_models('ensemble')
                    if ens_models:
                        ens_data = []
                        for model in ens_models:
                            # Get model-specific variables if available
                            try:
                                model_vars = data_source.get_model_specific_variables(model, 'ensemble')
                                var_count = len(model_vars) if model_vars else "N/A"
                            except Exception:
                                var_count = "N/A"
                            
                            ens_data.append({
                                "Model": model,
                                "Type": "Ensemble",
                                "Variables Available": var_count
                            })
                        
                        ens_df = pd.DataFrame(ens_data)
                        st.dataframe(ens_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No ensemble models available")
                except Exception as e:
                    st.warning(f"Could not retrieve ensemble models: {str(e)}")
    
    # Variables section
    st.header("📊 Available Variables")
    
    st.markdown("""
    Variables availability varies by data source and model. Below is a summary of 
    common variables across different data sources.
    """)
    
    for source_name, data_source in data_sources.items():
        with st.expander(f"📌 Variables - {source_name}"):
            
            # Hourly variables
            st.subheader("Hourly Variables")
            try:
                hourly_vars = data_source.get_available_variables('hourly')
                if hourly_vars:
                    # Display as table with variable names
                    var_data = [{"Variable": var} for var in hourly_vars]
                    var_df = pd.DataFrame(var_data)
                    st.dataframe(var_df, use_container_width=True, hide_index=True)
                    st.caption(f"Total: {len(hourly_vars)} hourly variables")
                else:
                    st.info("No hourly variables available")
            except Exception as e:
                st.warning(f"Could not retrieve hourly variables: {str(e)}")
            
            # Daily variables
            st.subheader("Daily Variables")
            try:
                daily_vars = data_source.get_available_variables('daily')
                if daily_vars:
                    var_data = [{"Variable": var} for var in daily_vars]
                    var_df = pd.DataFrame(var_data)
                    st.dataframe(var_df, use_container_width=True, hide_index=True)
                    st.caption(f"Total: {len(daily_vars)} daily variables")
                else:
                    st.info("No daily variables available")
            except Exception as e:
                st.warning(f"Could not retrieve daily variables: {str(e)}")
    
    # Model-Specific Variables (detailed view)
    st.header("🎯 Model-Specific Variables")
    
    st.markdown("""
    Some models support only specific subsets of variables. Use this section to see 
    exactly which variables each model provides.
    """)
    
    for source_name, data_source in data_sources.items():
        with st.expander(f"🔎 Model Variables - {source_name}"):
            
            # Get all models (deterministic and ensemble)
            all_models = []
            try:
                det_models = data_source.get_available_models('deterministic')
                all_models.extend([(m, 'deterministic') for m in det_models])
            except Exception:
                pass
            
            if data_source.supports_ensemble:
                try:
                    ens_models = data_source.get_available_models('ensemble')
                    all_models.extend([(m, 'ensemble') for m in ens_models])
                except Exception:
                    pass
            
            if all_models:
                for model, model_type in all_models:
                    st.markdown(f"**{model}** ({model_type})")
                    
                    try:
                        model_vars = data_source.get_model_specific_variables(model, model_type)
                        if model_vars:
                            # Display in columns for compact view
                            cols_per_row = 3
                            var_chunks = [model_vars[i:i+cols_per_row] for i in range(0, len(model_vars), cols_per_row)]
                            
                            for chunk in var_chunks:
                                cols = st.columns(cols_per_row)
                                for idx, var in enumerate(chunk):
                                    cols[idx].markdown(f"• `{var}`")
                            
                            st.caption(f"Total: {len(model_vars)} variables")
                        else:
                            st.info("Variable list not available for this model")
                    except Exception as e:
                        st.info(f"Could not retrieve variables: {str(e)}")
                    
                    st.divider()
            else:
                st.info("No models available")
    
    # Compatibility matrix
    st.header("🔄 Data Source Compatibility")
    
    st.markdown("""
    Understanding how different data sources can be combined:
    """)
    
    compatibility_info = {
        "Feature": [
            "Multi-source selection",
            "Mixed variables per model",
            "Datetime standardization",
            "Timezone support",
            "Observation overlay",
            "Per-model variable selection"
        ],
        "Status": [
            "✅ Supported",
            "✅ Supported",
            "✅ Implemented",
            "✅ Supported",
            "✅ Available",
            "✅ Implemented"
        ],
        "Notes": [
            "Select multiple data sources simultaneously",
            "Different models can have different variables",
            "All sources use 'datetime' column",
            "Convert to local timezone for display",
            "Meteostat observations can be overlaid",
            "Configure variables per model in UI"
        ]
    }
    
    compat_df = pd.DataFrame(compatibility_info)
    st.dataframe(compat_df, use_container_width=True, hide_index=True)
    
    # Technical information
    st.header("⚙️ Technical Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Data Format")
        st.markdown("""
        **DataFrame Structure:**
        - `datetime`: Timestamp column (datetime64)
        - `site`: Location identifier
        - `model`: Model identifier
        - `{variable}_{model}`: Data columns
        
        **Ensemble Format:**
        - Additional `member` column or
        - Member columns: `{variable}_{model}_member_XX`
        """)
    
    with col2:
        st.subheader("Data Types")
        st.markdown("""
        **Hourly Data:**
        - Hourly timesteps
        - Forecast horizon: varies by model
        
        **Daily Data:**
        - Daily aggregates (min, max, mean)
        - Longer forecast horizons
        """)
    
    # Documentation links
    st.header("📚 Documentation")
    
    st.markdown("""
    For more detailed information, refer to the following documentation files:
    
    - `MULTI_SOURCE_USER_GUIDE.md` - Guide for using multiple data sources
    - `PER_MODEL_VARIABLE_SELECTION.md` - Per-model variable selection
    - `SMART_VARIABLE_ROUTING.md` - Automatic variable filtering
    - `DATETIME_STANDARDIZATION.md` - DateTime handling across sources
    - `DATETIME_XAXIS.md` - Plotting with datetime axes
    """)
    
    # Footer
    st.divider()
    st.caption("wxapp - Weather Forecast Viewer | Metadata Page v1.0")
