import os
import yaml
import json
import streamlit as st

# Define base paths relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ensure config directory exists
CONFIG_DIR = os.path.join(BASE_DIR, "config")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR, exist_ok=True)

FILTERING_PATH = os.path.join(CONFIG_DIR, "filtering.yaml")
COMPANIES_PATH = os.path.join(CONFIG_DIR, "companies.yaml")

import shutil

@st.cache_data(ttl=3600)
def load_config_file(filepath):
    try:
        if not os.path.exists(filepath):
            example_filepath = filepath + ".example"
            if os.path.exists(example_filepath):
                try:
                    shutil.copy2(example_filepath, filepath)
                    # print(f"Initialized default configuration from {os.path.basename(example_filepath)}")
                except Exception as e:
                    st.error(f"Failed to initialize default config: {e}")
                    return {}
            else:
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

def load_user_prefs():
    """Load persistent user preferences from the data directory."""
    prefs_file = os.path.join(BASE_DIR, "data", "user_prefs.json")
    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_user_pref(key, value):
    """Save a single persistent user preference."""
    prefs_file = os.path.join(BASE_DIR, "data", "user_prefs.json")
    prefs = load_user_prefs()
    prefs[key] = value
    try:
        os.makedirs(os.path.dirname(prefs_file), exist_ok=True)
        with open(prefs_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Failed to save preference: {e}")
        return False
