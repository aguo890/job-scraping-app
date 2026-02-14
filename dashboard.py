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
    /* Reduce main container padding */
    .stMainBlockContainer {
        padding-top: 0px !important;
        padding-left: 40px !important;
        padding-right: 40px !important;
        padding-bottom: 40px !important;
    }
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
cv_status_map = {k: v.get('cv_status', 'Generic') for k, v in tracking_data.items()}
resume_map = {k: os.path.basename(v['cv_pdf_path']) if v.get('cv_pdf_path') else '' for k, v in tracking_data.items()}

df_jobs['Status'] = df_jobs['id'].map(status_map).fillna('New')
df_jobs['is_saved'] = df_jobs['id'].map(saved_map).fillna(False)
df_jobs['cv_status'] = df_jobs['id'].map(cv_status_map).fillna('Generic')
df_jobs['resume'] = df_jobs['id'].map(resume_map).fillna('')

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
filtered_df = filtered_df.sort_values(by=["status_prio", "is_saved", "date_posted", "score"], ascending=[False, False, False, False]).reset_index(drop=True)

# --- TABLE ---
st.caption(f"Showing **{len(filtered_df)}** of {len(df_jobs)} jobs")

display_cols = ['Status', 'score', 'date_posted', 'company', 'title', 'location', 'url', 'id']
final_cols = [c for c in display_cols if c in filtered_df.columns]

event = st.dataframe(
    filtered_df[final_cols],
    on_select="rerun",
    selection_mode=["single-row", "single-cell"],
    key="job_dashboard_table",
    column_config={
        "Status": st.column_config.TextColumn("Status"),
        "url": st.column_config.LinkColumn("Link", display_text="Open"),
        "score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=50),
        "id": None
    },
    use_container_width=True,
    hide_index=True,
    height=530
)

# --- ACTION TOOLBAR ---
# Extract selected row from either row selection OR cell click
selected_indices = []
if event.selection:
    if event.selection.rows:
        selected_indices = event.selection.rows
    elif event.selection.cells:
        # Cell click — extract the row index from the cell tuple (row, col)
        selected_indices = list(set(cell[0] for cell in event.selection.cells))

if selected_indices:
    num_selected = len(selected_indices)
    selected_ids = filtered_df.iloc[selected_indices]['id'].tolist()

    # Visual Separator
    st.write("")

    # THE SLEEK TOOLBAR
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([1, 1.5, 2, 1.5], vertical_alignment="center")

        with col1:
            st.markdown(f"**{num_selected}** Selected")

        with col2:
            if st.button("⭐ Toggle Save", use_container_width=True):
                for job_id in selected_ids:
                    if job_id not in tracking_data: tracking_data[job_id] = {}
                    current = tracking_data[job_id].get('saved', False)
                    tracking_data[job_id]['saved'] = not current
                save_tracking(tracking_data)
                st.rerun()

        with col3:
            new_status = st.selectbox(
                "Status",
                ["Applied", "Interviewing", "Offer", "Rejected", "New"],
                label_visibility="collapsed",
                key="status_selector"
            )

        with col4:
            if st.button("Update Status", type="primary", use_container_width=True):
                for job_id in selected_ids:
                    if job_id not in tracking_data: tracking_data[job_id] = {}
                    tracking_data[job_id]['status'] = new_status
                    if new_status in ["Applied", "Interviewing", "Offer"]:
                        tracking_data[job_id]['saved'] = True
                save_tracking(tracking_data)
                st.rerun()

    # --- CV Editor / Resume Navigation ---
    if num_selected == 1:
        selected_job_row = filtered_df.iloc[selected_indices[0]]
        resume_file = selected_job_row.get('resume', '')
        has_resume = bool(resume_file)

        with st.container(border=True):
            col_cv1, col_cv2 = st.columns([3, 1], vertical_alignment="center")
            with col_cv1:
                company = selected_job_row.get('company', 'Unknown')
                title = selected_job_row.get('title', 'Unknown')
                if has_resume:
                    st.markdown(f"📄 **Resume**: `{resume_file}`  |  {company} — {title}")
                else:
                    st.markdown(f"📝 **No Resume Yet** |  {company} — {title}")
            with col_cv2:
                btn_label = "📄 View Resume" if has_resume else "📝 Create Resume"
                if st.button(btn_label, type="primary", use_container_width=True):
                    st.session_state["active_job"] = selected_job_row.to_dict()
                    st.switch_page("pages/CV_Editor.py")

else:
    # Empty-state: ghost versions of both toolbar rows
    st.write("")
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([1, 1.5, 2, 1.5], vertical_alignment="center")
        with col1:
            st.markdown("<span style='color:#bbb'>**0** Selected</span>", unsafe_allow_html=True)
        with col2:
            st.button("⭐ Toggle Save", use_container_width=True, disabled=True, key="ghost_save")
        with col3:
            st.selectbox("Status", ["Applied", "Interviewing", "Offer", "Rejected", "New"],
                         label_visibility="collapsed", disabled=True, key="ghost_status")
        with col4:
            st.button("Update Status", type="primary", use_container_width=True, disabled=True, key="ghost_update")

    with st.container(border=True):
        col_cv1, col_cv2 = st.columns([3, 1], vertical_alignment="center")
        with col_cv1:
            st.markdown("<span style='color:#bbb'>📝 Select a job to view or create a resume</span>", unsafe_allow_html=True)
        with col_cv2:
            st.button("📝 Create Resume", type="primary", use_container_width=True, disabled=True, key="ghost_cv")
