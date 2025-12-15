# File: views/metadata_view.py
"""Metadata view showing available models and data sources"""

import streamlit as st
from typing import Dict


def show_metadata_view(data_sources: Dict):
    """
    Display metadata about available models and their parameters
    
    Args:
        data_sources: Dictionary of available data sources {name: DataSource}
    """
    st.title("📊 Models & Parameters")
    
    st.markdown("Overview of all available models and their supported parameters.")
    
    # Loop through each data source
    for source_name, data_source in data_sources.items():
        st.header(f"� {source_name}")
        
        # Deterministic Models
        st.subheader("Deterministic Models")
        try:
            det_models = data_source.get_available_models('deterministic')
            if det_models:
                for model in det_models:
                    with st.expander(f"📍 {model}"):
                        try:
                            model_vars = data_source.get_model_specific_variables(model, 'deterministic')
                            if model_vars:
                                st.markdown(f"**{len(model_vars)} parameters available:**")
                                # Display as bullet list in columns
                                cols_per_row = 3
                                var_chunks = [model_vars[i:i+cols_per_row] for i in range(0, len(model_vars), cols_per_row)]
                                
                                for chunk in var_chunks:
                                    cols = st.columns(cols_per_row)
                                    for idx, var in enumerate(chunk):
                                        cols[idx].markdown(f"• `{var}`")
                            else:
                                # Try to get general variables
                                general_vars = data_source.get_available_variables('hourly')
                                if general_vars:
                                    st.markdown(f"**{len(general_vars)} parameters available:**")
                                    cols_per_row = 3
                                    var_chunks = [general_vars[i:i+cols_per_row] for i in range(0, len(general_vars), cols_per_row)]
                                    
                                    for chunk in var_chunks:
                                        cols = st.columns(cols_per_row)
                                        for idx, var in enumerate(chunk):
                                            cols[idx].markdown(f"• `{var}`")
                                else:
                                    st.info("No parameters available")
                        except Exception as e:
                            st.info(f"Could not retrieve parameters: {str(e)}")
            else:
                st.info("No deterministic models available")
        except Exception as e:
            st.warning(f"Could not retrieve deterministic models: {str(e)}")
        
        # Ensemble Models
        if data_source.supports_ensemble:
            st.subheader("Ensemble Models")
            try:
                ens_models = data_source.get_available_models('ensemble')
                if ens_models:
                    for model in ens_models:
                        with st.expander(f"📍 {model}"):
                            try:
                                model_vars = data_source.get_model_specific_variables(model, 'ensemble')
                                if model_vars:
                                    st.markdown(f"**{len(model_vars)} parameters available:**")
                                    # Display as bullet list in columns
                                    cols_per_row = 3
                                    var_chunks = [model_vars[i:i+cols_per_row] for i in range(0, len(model_vars), cols_per_row)]
                                    
                                    for chunk in var_chunks:
                                        cols = st.columns(cols_per_row)
                                        for idx, var in enumerate(chunk):
                                            cols[idx].markdown(f"• `{var}`")
                                else:
                                    # Try to get general variables
                                    general_vars = data_source.get_available_variables('hourly')
                                    if general_vars:
                                        st.markdown(f"**{len(general_vars)} parameters available:**")
                                        cols_per_row = 3
                                        var_chunks = [general_vars[i:i+cols_per_row] for i in range(0, len(general_vars), cols_per_row)]
                                        
                                        for chunk in var_chunks:
                                            cols = st.columns(cols_per_row)
                                            for idx, var in enumerate(chunk):
                                                cols[idx].markdown(f"• `{var}`")
                                    else:
                                        st.info("No parameters available")
                            except Exception as e:
                                st.info(f"Could not retrieve parameters: {str(e)}")
                else:
                    st.info("No ensemble models available")
            except Exception as e:
                st.warning(f"Could not retrieve ensemble models: {str(e)}")
        
        st.markdown("---")
