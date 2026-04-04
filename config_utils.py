import os
import yaml
import streamlit as st

# Define base paths relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ensure config directory exists
CONFIG_DIR = os.path.join(BASE_DIR, "config")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR, exist_ok=True)

FILTERING_PATH = os.path.join(CONFIG_DIR, "filtering.yaml")
COMPANIES_PATH = os.path.join(CONFIG_DIR, "companies.yaml")

@st.cache_data(ttl=3600)
def load_config_file(filepath):
    try:
        if not os.path.exists(filepath):
            return {}
        with open(filepath, "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config if config is not None else {}
    except yaml.YAMLError as e:
        st.error(f"🚨 **Configuration Syntax Error:** Please check formatting in `{os.path.basename(filepath)}`. \n\nDetails: `{e}`")
        return {}
    except Exception as e:
        st.error(f"🚨 **Unexpected Error Loading Config:** {e}")
        return {}

def save_yaml_safely(config_data, filepath):
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding='utf-8') as f:
            # default_flow_style=False ensures human-readable vertical lists
            yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ **Failed to Save Changes:** {e}")
        return False

def clean_df_list(df, col_name):
    """Safely scrubs DataEditor output to remove NaNs and empty strings."""
    if df.empty:
        return []
    cleaned = df[col_name].dropna()
    return [str(x).strip() for x in cleaned if str(x).strip() != ""]

def load_config():
    return load_config_file(FILTERING_PATH)

def load_companies():
    return load_config_file(COMPANIES_PATH)
