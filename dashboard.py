import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- Configuration ---
TRACKING_FILE = "data/tracking.json"
JOB_DATA_FILE = "data/jobs_agg.json"

st.set_page_config(page_title="Job Hunter", layout="wide")

st.markdown("""
    <style>
    /* Make the bottom toolbar sticky */
    div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stVerticalBlockBorderWrapper"]) {
        position: sticky;
        bottom: 20px;
        z-index: 100;
        background-color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- Data Loading & Saving ---
def load_tracking():
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_tracking(data):
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@st.cache_data
def load_jobs():
    if not os.path.exists(JOB_DATA_FILE):
        return pd.DataFrame()
    with open(JOB_DATA_FILE, "r") as f:
        data = json.load(f)
    jobs = data.get("jobs", [])
    if not jobs:
        return pd.DataFrame()
    
    df = pd.DataFrame(jobs)
    
    # Cleanup
    object_cols = ['raw_data', 'keywords_matched']
    for col in object_cols:
        if col in df.columns:
            df[col] = df[col].astype(str)
            
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce').fillna(0)
        
    return df

# --- Main App ---
st.title("🚀 Job Hunter")

df_jobs = load_jobs()
tracking_data = load_tracking()

if df_jobs.empty:
    st.warning("No jobs found yet. Run the scraper!")
    st.stop()

# --- Merge Data ---
saved_map = {k: v.get('saved', False) for k, v in tracking_data.items()}
status_map = {k: v.get('status', 'New') for k, v in tracking_data.items()}

df_jobs['Status'] = df_jobs['id'].map(status_map).fillna('New')
df_jobs['is_saved'] = df_jobs['id'].map(saved_map).fillna(False)

# --- Prettify Title ---
def prettify_title(row):
    title = row['title']
    if row['is_saved']:
        title = "⭐ " + title
    # Add status emoji if it's special
    if row['Status'] == "Interviewing":
        title = "🎤 " + title
    elif row['Status'] == "Offer":
        title = "🎉 " + title
    return title

df_jobs['title'] = df_jobs.apply(prettify_title, axis=1)

# --- Filters ---
with st.sidebar:
    st.header("Filters")
    if st.button("🔄 Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()
        
    show_saved = st.checkbox("⭐ Show Saved Only")
    companies = ["All"] + sorted(df_jobs['company'].unique().tolist())
    sel_company = st.selectbox("Company", companies)
    min_score = st.slider("Min Score", 0, int(df_jobs['score'].max()), 0)

# Apply Filters
filtered_df = df_jobs[df_jobs['score'] >= min_score]
if sel_company != "All":
    filtered_df = filtered_df[filtered_df['company'] == sel_company]
if show_saved:
    filtered_df = filtered_df[filtered_df['is_saved'] == True]

# Sort: Saved/Special Status first, then Date, then Score
# We create a simple priority map for sorting
status_priority = {"Offer": 5, "Interviewing": 4, "Applied": 3, "New": 1, "Rejected": 0}
filtered_df['status_prio'] = filtered_df['Status'].map(status_priority).fillna(1)
filtered_df = filtered_df.sort_values(by=["status_prio", "is_saved", "date_posted", "score"], ascending=[False, False, False, False])

# --- TABLE ---
display_cols = ['Status', 'score', 'date_posted', 'company', 'title', 'location', 'url', 'id']
final_cols = [c for c in display_cols if c in filtered_df.columns]

st.caption("💡 **Tip:** Select rows on the left to perform actions.")

event = st.dataframe(
    filtered_df[final_cols],
    on_select="rerun",
    selection_mode="multi-row",
    column_config={
        "Status": st.column_config.TextColumn("Status"),
        "url": st.column_config.LinkColumn("Link", display_text="Open"),
        "score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=50),
        "id": None
    },
    use_container_width=True,
    hide_index=True,
    height=600
)

# --- ACTION TOOLBAR ---
selected_indices = event.selection.rows

if selected_indices:
    num_selected = len(selected_indices)
    selected_ids = filtered_df.iloc[selected_indices]['id'].tolist()
    
    # Visual Separator
    st.write("") 

    # THE SLEEK TOOLBAR
    # We use a bordered container to group everything
    with st.container(border=True):
        
        # vertical_alignment="center" aligns text/inputs/buttons on the same line
        col1, col2, col3, col4 = st.columns([1, 1.5, 2, 1.5], vertical_alignment="center")
        
        # 1. Selection Count
        with col1:
            st.markdown(f"**{num_selected}** Selected")
            
        # 2. Toggle Save Button
        with col2:
            if st.button("⭐ Toggle Save", use_container_width=True):
                for job_id in selected_ids:
                    if job_id not in tracking_data: tracking_data[job_id] = {}
                    current = tracking_data[job_id].get('saved', False)
                    tracking_data[job_id]['saved'] = not current
                save_tracking(tracking_data)
                st.rerun()

        # 3. Status Dropdown (No Label, clean look)
        with col3:
            new_status = st.selectbox(
                "Status", 
                ["Applied", "Interviewing", "Offer", "Rejected", "New"],
                label_visibility="collapsed",
                key="status_selector"
            )

        # 4. Update Button (Primary Color)
        with col4:
            if st.button("Update Status", type="primary", use_container_width=True):
                for job_id in selected_ids:
                    if job_id not in tracking_data: tracking_data[job_id] = {}
                    tracking_data[job_id]['status'] = new_status
                    # Logic: If you mark it Applied/Interviewing, auto-save the job
                    if new_status in ["Applied", "Interviewing", "Offer"]:
                        tracking_data[job_id]['saved'] = True
                save_tracking(tracking_data)
                st.rerun()