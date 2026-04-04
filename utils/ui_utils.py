import streamlit as st

def render_status(status_string):
    """
    Returns a simple, clean markdown string for statuses 
    without relying on HTML injections.
    """
    status_map = {
        "Applied": "🟢 **Applied**",
        "Interviewing": "🎤 **Interviewing**",
        "Offer": "🎉 **Offer**",
        "Rejected": "🔴 **Rejected**",
        "New": "⚪ **New**",
        "Hidden": "👻 **Hidden**",
        "Saved": "⭐ **Saved**"
    }
    
    # Default to grey dot if status is unknown
    formatted_status = status_map.get(status_string, "⚪ **Unknown**")
    return formatted_status

def format_status_df(status):
    """Simple emoji mapper for dataframe cells"""
    status_emoji_map = {
        "Applied": "🟢 Applied",
        "Interviewing": "🎤 Interviewing",
        "Offer": "🎉 Offer",
        "Rejected": "🔴 Rejected",
        "New": "⚪ New",
        "Hidden": "👻 Hidden",
        "Saved": "⭐ Saved"
    }
    return status_emoji_map.get(status, "⚪ " + str(status))

def inject_custom_css():
    """
    Injects custom CSS to modernize the UI globally.
    Ensures a consistent look across all pages.
    """
    st.markdown("""
        <style>
        /* Make the top toolbar transparent */
        .stAppToolbar, [data-testid="stHeader"] {
            background-color: transparent !important;
            background: transparent !important;
            border-bottom: none !important;
        }
        
        /* Reduce main container padding for a sleeker look */
        .stMainBlockContainer {
            padding-top: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-bottom: 2rem !important;
        }

        /* Standardize button transitions */
        .stButton > button {
            transition: all 0.2s ease-in-out !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)
