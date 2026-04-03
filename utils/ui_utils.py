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
