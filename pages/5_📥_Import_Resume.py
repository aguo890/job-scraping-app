import sys
import os

# Add the parent directory (root) to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import streamlit as st
from utils.onboarding_ui import render_wizard_ui

st.set_page_config(page_title="Resume Import — Setup Wizard", layout="wide")

# Call the shared UI logic in standalone mode
render_wizard_ui(is_standalone=True)
