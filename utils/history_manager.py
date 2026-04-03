import json
import os
import pandas as pd
from datetime import datetime

# Absolute path based on project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(BASE_DIR, "data", "scrape_history.json")

def log_scrape_run(jobs_found, duration_seconds, status="Success"):
    """
    Appends a new scrape run record to the history log.
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    
    # Load existing data
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding='utf-8') as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []
    else:
        history = []
        
    # Append new run
    new_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "jobs_found": jobs_found,
        "duration_seconds": round(duration_seconds, 2),
        "status": status
    }
    history.append(new_entry)
    
    # Keep only the last 50 runs to prevent file bloat
    history = history[-50:]
    
    with open(HISTORY_FILE, "w", encoding='utf-8') as f:
        json.dump(history, f, indent=4)

def get_scrape_history_df():
    """
    Reads the history log and returns a Pandas DataFrame for the UI.
    """
    if not os.path.exists(HISTORY_FILE):
        return pd.DataFrame(columns=["timestamp", "jobs_found", "duration_seconds", "status"])
    
    try:
        with open(HISTORY_FILE, "r", encoding='utf-8') as f:
            history = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return pd.DataFrame(columns=["timestamp", "jobs_found", "duration_seconds", "status"])
        
    df = pd.DataFrame(history)
    
    # Sort by timestamp descending (newest first)
    if not df.empty:
        # Ensure timestamp is comparable
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(by="timestamp", ascending=False).reset_index(drop=True)
        # Convert back to readable string for display
        df['timestamp'] = df['timestamp'].dt.strftime("%Y-%m-%d %H:%M:%S")
        
    return df
