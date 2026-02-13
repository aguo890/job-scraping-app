import streamlit as st
import pandas as pd
import json
import sys
import os
import time

# Add parent directory to path to import cv_bridge (for Monorepo structure)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from cv_bridge import CVOrchestrator
except ImportError:
    # Fallback if cv_bridge is in the same directory (during transition)
    try:
         from cv_bridge import CVOrchestrator
    except ImportError:
         CVOrchestrator = None

from datetime import datetime

# --- Configuration ---
# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKING_FILE = os.path.join(BASE_DIR, "data", "tracking.json")
JOB_DATA_FILE = os.path.join(BASE_DIR, "data", "jobs_agg.json")

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
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_tracking(data):
    with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

@st.cache_data
def load_jobs():
    if not os.path.exists(JOB_DATA_FILE):
        return pd.DataFrame()
    with open(JOB_DATA_FILE, "r", encoding='utf-8') as f:
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

# --- Sidebar ---
with st.sidebar:
    # --- Quick Stats ---
    st.header("📊 Overview")

    total_jobs = len(df_jobs)
    num_companies = df_jobs['company'].nunique()
    num_saved = int(df_jobs['is_saved'].sum())
    num_applied = len([v for v in tracking_data.values() if v.get('status') == 'Applied'])
    num_interviewing = len([v for v in tracking_data.values() if v.get('status') == 'Interviewing'])
    num_offers = len([v for v in tracking_data.values() if v.get('status') == 'Offer'])
    num_rejected = len([v for v in tracking_data.values() if v.get('status') == 'Rejected'])
    num_saved_unapplied = int((df_jobs['is_saved'] & (df_jobs['Status'] != 'Applied')).sum())
    avg_score = df_jobs['score'].mean()

    col_a, col_b = st.columns(2)
    col_a.metric("Total Jobs", total_jobs)
    col_b.metric("Companies", num_companies)

    col_c, col_d = st.columns(2)
    col_c.metric("⭐ Saved", num_saved)
    col_d.metric("📝 Applied", num_applied)

    col_e, col_f = st.columns(2)
    col_e.metric("🎤 Interviewing", num_interviewing)
    col_f.metric("🎉 Offers", num_offers)

    col_g, col_h = st.columns(2)
    col_g.metric("📋 TODO", num_saved_unapplied, help="Saved but not yet applied")
    col_h.metric("❌ Rejected", num_rejected)

    st.metric("Avg Score", f"{avg_score:.1f}")

    if 'date_posted' in df_jobs.columns:
        dates = pd.to_datetime(df_jobs['date_posted'], errors='coerce').dropna()
        if not dates.empty:
            st.caption(f"📅 {dates.min().strftime('%b %d')} – {dates.max().strftime('%b %d, %Y')}")

    st.divider()

    # --- Filters ---
    st.header("Filters")
    if st.button("🔄 Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()

    # --- Quick Filter Shortcuts ---
    st.subheader("Quick Filters", divider="gray")
    show_saved_unapplied = st.checkbox("⭐ Saved & Unapplied", key="filter_saved_unapplied",
                                        help="Show saved jobs you haven't applied to yet")
    show_applied = st.checkbox("📝 Applied Only", key="filter_applied",
                                help="Show only jobs you've applied to")
    hide_rejected = st.checkbox("🚫 Hide Rejected", value=True, key="filter_hide_rejected",
                                 help="Exclude jobs marked as Rejected")
    hide_applied = st.checkbox("🚫 Hide Applied", value=False, key="filter_hide_applied",
                                help="Exclude jobs you've already applied to")

    # --- Standard Filters ---
    st.subheader("Refine", divider="gray")

    # Status multi-select
    all_statuses = sorted(df_jobs['Status'].unique().tolist())
    sel_statuses = st.multiselect("Status", all_statuses, default=[], key="filter_status",
                                   help="Leave empty to show all statuses")

    show_saved = st.checkbox("⭐ Show Saved Only", key="filter_saved")
    companies = ["All"] + sorted(df_jobs['company'].unique().tolist())
    sel_company = st.selectbox("Company", companies, key="filter_company")
    min_score = st.slider("Min Score", 0, int(df_jobs['score'].max()), 0, key="filter_min_score")

    # Title keyword search
    search_query = st.text_input("🔍 Search Title", key="filter_search",
                                  placeholder="e.g. intern, frontend, data...")

    # Date range filter
    if 'date_posted' in df_jobs.columns:
        dates = pd.to_datetime(df_jobs['date_posted'], errors='coerce').dropna()
        if not dates.empty:
            min_date = dates.min().date()
            max_date = dates.max().date()
            date_range = st.date_input("📅 Date Range", value=(min_date, max_date),
                                        min_value=min_date, max_value=max_date,
                                        key="filter_date_range")

# --- Apply Filters ---
filtered_df = df_jobs.copy()

# Score filter
filtered_df = filtered_df[filtered_df['score'] >= min_score]

# Company filter
if sel_company != "All":
    filtered_df = filtered_df[filtered_df['company'] == sel_company]

# Saved only
if show_saved:
    filtered_df = filtered_df[filtered_df['is_saved'] == True]

# Quick filter: Saved & Unapplied
if show_saved_unapplied:
    filtered_df = filtered_df[(filtered_df['is_saved'] == True) & (filtered_df['Status'] != 'Applied')]

# Quick filter: Applied Only
if show_applied:
    filtered_df = filtered_df[filtered_df['Status'] == 'Applied']

# Hide Rejected
if hide_rejected:
    filtered_df = filtered_df[filtered_df['Status'] != 'Rejected']

# Hide Applied
if hide_applied:
    filtered_df = filtered_df[filtered_df['Status'] != 'Applied']

# Status multi-select
if sel_statuses:
    filtered_df = filtered_df[filtered_df['Status'].isin(sel_statuses)]

# Title search
if search_query:
    filtered_df = filtered_df[filtered_df['title'].str.contains(search_query, case=False, na=False)]

# Date range filter
if 'date_posted' in df_jobs.columns and 'date_range' in dir():
    dates_parsed = pd.to_datetime(filtered_df['date_posted'], errors='coerce')
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        mask = (dates_parsed.dt.date >= start_date) & (dates_parsed.dt.date <= end_date)
        filtered_df = filtered_df[mask | dates_parsed.isna()]

# Sort: Saved/Special Status first, then Date, then Score
# We create a simple priority map for sorting
status_priority = {"Offer": 5, "Interviewing": 4, "Applied": 3, "New": 1, "Rejected": 0}
filtered_df['status_prio'] = filtered_df['Status'].map(status_priority).fillna(1)
filtered_df = filtered_df.sort_values(by=["status_prio", "is_saved", "date_posted", "score"], ascending=[False, False, False, False])

# --- TABLE ---
st.caption(f"Showing **{len(filtered_df)}** of {len(df_jobs)} jobs")
display_cols = ['Status', 'score', 'date_posted', 'company', 'title', 'location', 'url', 'id']
final_cols = [c for c in display_cols if c in filtered_df.columns]



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

# --- CV GENERATION ACTION (Sidebar) ---
# We place this here to ensure 'event' and selection are defined
if selected_indices and CVOrchestrator:
    with st.sidebar:
        st.divider()
        st.header("📄 CV Generation")
        
        if st.button("Generate CV for Selected", type="primary", use_container_width=True):
             # Initialize Orchestrator
             # We assume the script is running from job-scraping-app, so base cv is in ../rendercv
             # But we need to handle the relative path carefully.
             # CVOrchestrator defaults to "rendercv/Aaron_Guo_CV.yaml" relative to ITS root.
             # If cv_bridge is in root, it finds it in rendercv/.
             
             try:
                orchestrator = CVOrchestrator() # Uses default path
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Get the actual job objects from the selection
                jobs_to_process = filtered_df.iloc[selected_indices].to_dict('records')
                
                success_files = []
                
                for idx, job in enumerate(jobs_to_process):
                    company_name = job.get('company', 'Unknown')
                    status_text.text(f"Generating CV for {company_name}...")
                    
                    try:
                        # Call the bridge
                        pdf_path = orchestrator.generate_tailored_cv(job)
                        
                        # Store success
                        success_files.append((company_name, pdf_path))
                        
                    except Exception as e:
                        st.error(f"Failed for {company_name}: {e}")
                        
                    progress_bar.progress((idx + 1) / len(jobs_to_process))
                
                status_text.empty()
                progress_bar.empty()
                
                if success_files:
                    st.success(f"✅ Generated {len(success_files)} CVs!")
                    for company, path in success_files:
                        st.write(f"**{company}**: `{os.path.basename(path)}`")
                        # Try to offer download if file exists
                        if os.path.exists(path):
                             with open(path, "rb") as f:
                                  st.download_button(
                                      f"⬇️ Download {company} CV",
                                      f,
                                      file_name=os.path.basename(path),
                                      mime="application/pdf",
                                      key=f"dl_{company}_{time.time()}"
                                  )
             except Exception as e:
                 st.error(f"Initialization Error: {e}")
