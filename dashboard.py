import sys
import os

# Add the parent directory (root) to the Python path so we can find cv_bridge.py
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import streamlit as st
import pandas as pd
import json
import time

# Silence pandas downcasting warning
pd.set_option('future.no_silent_downcasting', True)

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

@st.cache_data(ttl=900)
def load_jobs_raw():
    if not os.path.exists(JOB_DATA_FILE):
        return None
    try:
        with open(JOB_DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def load_jobs_df(data):
    if not data:
        return pd.DataFrame()
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

# Load Raw Data (Cached with TTL)
raw_data = load_jobs_raw()

# Sideboard: Control & Observability
with st.sidebar:
    st.title("Job Hunter")
    st.markdown("---")
    
    # --- System Status ---
    st.markdown("### 🛰️ System Status")
    if raw_data:
        st.markdown("🟢 **Live Connection**")
        generated_at = raw_data.get("generated_at", "Unknown")
        # Format the ISO string for better readability if possible
        try:
            dt = datetime.fromisoformat(generated_at)
            display_time = dt.strftime("%b %d, %H:%M")
        except:
            display_time = generated_at
        st.caption(f"Last Scraped: {display_time}")
    else:
        st.markdown("🔴 **Offline / No Data**")
    st.markdown("---")

    st.header("⚙️ Controls")
    if st.button("🔄 Force Refresh Data", type="primary", use_container_width=True):
        load_jobs_raw.clear()
        st.cache_data.clear()
        st.rerun()
    
    if raw_data:
        total_count = raw_data.get("total_jobs", 0)
        st.caption(f"🗃️ Total Aggregated: {total_count}")
    st.divider()

if not raw_data:
    st.warning("⚠️ Waiting for the background scraper to complete its first run. Please check back in a few minutes.")
    st.info("💡 You can check the logs for progress.")
    st.stop()

# Create a copy to prevent mutating the cached object
df_jobs = load_jobs_df(raw_data).copy()
tracking_data = load_tracking()

if df_jobs.empty:
    st.warning("No jobs found in the aggregation file. Run the scraper!")
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
# --- Prettify Title (Vectorized) ---
# Initialize with original title
df_jobs['display_title'] = df_jobs['title']

# 1. Prepend star if saved
saved_mask = df_jobs['is_saved'] == True
df_jobs.loc[saved_mask, 'display_title'] = "⭐ " + df_jobs.loc[saved_mask, 'display_title']

# 2. Prepend Status Emojis
interview_mask = df_jobs['Status'] == 'Interviewing'
offer_mask = df_jobs['Status'] == 'Offer'

df_jobs.loc[interview_mask, 'display_title'] = "🎤 " + df_jobs.loc[interview_mask, 'display_title']
df_jobs.loc[offer_mask, 'display_title'] = "🎉 " + df_jobs.loc[offer_mask, 'display_title']

# Update the main title column
df_jobs['title'] = df_jobs['display_title']

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
        dates = pd.to_datetime(df_jobs['date_posted'], errors='coerce', format='ISO8601').dropna()
        if not dates.empty:
            st.caption(f"📅 {dates.min().strftime('%b %d')} – {dates.max().strftime('%b %d, %Y')}")

    st.divider()

    # --- Filters ---
    st.header("Filters")

    # --- Quick Filter Shortcuts ---
    st.subheader("Main View", divider="gray")
    
    view_options = {
        "Feed": "🆕 Feed",
        "Shortlist": "⭐ Shortlist",
        "Tracking": "📝 Tracking",
        "All": "🗂️ All"
    }
    
    # Helper for query params compatibility
    def get_query_param(key, default):
        if hasattr(st, "query_params"):
            return st.query_params.get(key, default)
        elif hasattr(st, "experimental_get_query_params"):
            params = st.experimental_get_query_params()
            return params.get(key, [default])[0]
        return default

    def set_query_param(key, value):
        if hasattr(st, "query_params"):
            st.query_params[key] = value
        elif hasattr(st, "experimental_set_query_params"):
            st.experimental_set_query_params(**{key: value})

    # --- Robust View Persistence Logic ---
    # PRECEDENCE: 1. URL (Deep Link) -> 2. Persisted State (History) -> 3. Default
    # NOTE: Widget-bound keys (main_view_filter) are cleared by Streamlit when
    # navigating away. We use _persisted_view (non-widget) to survive page switches.
    current_url_view = get_query_param("view", None)
    persisted_view = st.session_state.get("_persisted_view", "Feed")

    if current_url_view and current_url_view in view_options:
        # Scenario A: URL present & valid (refresh or deep link) → URL is source of truth
        st.session_state.main_view_filter = current_url_view
        st.session_state._persisted_view = current_url_view
    elif persisted_view != "Feed":
        # Scenario B: URL empty, persisted state saved (navigated "Back") → restore
        set_query_param("view", persisted_view)
        st.session_state.main_view_filter = persisted_view
        st.session_state._persisted_view = persisted_view
    else:
        # Scenario C: Fresh start → default to Feed
        st.session_state.main_view_filter = "Feed"
        st.session_state._persisted_view = "Feed"
        set_query_param("view", "Feed")

    # --- Session State Init ---
    if "table_version" not in st.session_state:
        st.session_state.table_version = 0


    def update_view_param():
        view = st.session_state.main_view_filter
        st.session_state._persisted_view = view  # Persist to non-widget key
        set_query_param("view", view)

    # Use segmented_control if available (Streamlit 1.39+)
    if hasattr(st, "segmented_control"):
        selected_view = st.segmented_control(
            "Main View",
            options=list(view_options.keys()),
            format_func=lambda x: view_options[x],
            label_visibility="collapsed",
            key="main_view_filter",
            on_change=update_view_param
        )
    else:
        # Fallback for older Streamlit
        # Map string value to index for radio fallback if needed, 
        # though st.radio with key handles strings internally usually.
        # But `index` argument is integer.
        # However, if `key` is present in session_state, `index` is ignored.
        selected_view = st.radio(
            "Main View",
            options=list(view_options.keys()),
            format_func=lambda x: view_options[x],
            horizontal=True,
            label_visibility="collapsed",
            key="main_view_filter",
            on_change=update_view_param
        )

    # Contextual filters based on view
    hide_rejected = True
    if selected_view == "All":
        hide_rejected = st.checkbox("🚫 Hide Rejected", value=True, key="filter_hide_rejected")

    # --- Standard Filters ---
    st.subheader("Refine", divider="gray")

    # Status multi-select
    all_statuses = sorted(df_jobs['Status'].unique().tolist())
    sel_statuses = st.multiselect("Status", all_statuses, default=[], key="filter_status",
                                   help="Leave empty to show all statuses")

    show_saved = False # implicitly handled by views, but keep valid for logic below if needed
    companies = ["All"] + sorted(df_jobs['company'].unique().tolist())
    sel_company = st.selectbox("Company", companies, key="filter_company")
    min_score = st.slider("Min Score", 0, int(df_jobs['score'].max()), 0, key="filter_min_score")

    # Title keyword search
    search_query = st.text_input("🔍 Search Title", key="filter_search",
                                  placeholder="e.g. intern, frontend, data...")

    # Date range filter
    date_range = None  # Initialize safely
    if 'date_posted' in df_jobs.columns:
        dates = pd.to_datetime(df_jobs['date_posted'], errors='coerce', format='ISO8601').dropna()
        if not dates.empty:
            min_date = dates.min().date()
            max_date = dates.max().date()
            date_range = st.date_input("📅 Date Range", value=(min_date, max_date),
                                        min_value=min_date, max_value=max_date,
                                        key="filter_date_range")

# --- Apply Filters ---
filtered_df = df_jobs.copy()

# 1. VIEW LOGIC (The Core "Inbox Zero" Flow)
if selected_view == "Feed":
    # Feed = New AND Not Saved AND Not Rejected
    # "Inbox Zero" - as soon as you save or apply, it leaves the feed.
    filtered_df = filtered_df[
        (filtered_df['Status'] == 'New') & 
        (filtered_df['is_saved'] == False) &
        (filtered_df['Status'] != 'Rejected')
    ]

elif selected_view == "Shortlist":
    # Shortlist = Saved AND Not Applied/Interviewing/Offer
    # We want to see what we saved but haven't acted on yet.
    # We generaly exclude 'Rejected' here unless explicitly desired, but standard flow implies Shortlist is for "To Apply"
    active_statuses = ['New', 'Saved'] 
    filtered_df = filtered_df[
        (filtered_df['is_saved'] == True) & 
        (filtered_df['Status'].isin(active_statuses))
    ]

elif selected_view == "Tracking":
    # Tracking = Applied, Interviewing, Offer
    tracking_statuses = ['Applied', 'Interviewing', 'Offer']
    filtered_df = filtered_df[filtered_df['Status'].isin(tracking_statuses)]

elif selected_view == "All":
    # All = Everything (optionally hide rejected)
    if hide_rejected:
        filtered_df = filtered_df[filtered_df['Status'] != 'Rejected']


# 2. Refine Filters (Company, Score, etc. apply on top of the View)

# Score filter
filtered_df = filtered_df[filtered_df['score'] >= min_score]

# Company filter
if sel_company != "All":
    filtered_df = filtered_df[filtered_df['company'] == sel_company]

# Status multi-select (allows further drilling down within a view)
if sel_statuses:
    filtered_df = filtered_df[filtered_df['Status'].isin(sel_statuses)]

# Title search
if search_query:
    filtered_df = filtered_df[filtered_df['title'].str.contains(search_query, case=False, na=False)]

# Date range filter
if 'date_posted' in df_jobs.columns and date_range is not None:
    dates_parsed = pd.to_datetime(filtered_df['date_posted'], errors='coerce', format='ISO8601')
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
    selection_mode=["multi-row", "single-cell"],
    key=f"job_dashboard_table_{st.session_state.table_version}",
    column_config={
        "Status": st.column_config.TextColumn("Status"),
        "url": st.column_config.LinkColumn("Link", display_text="Open"),
        "score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=50),
        "id": None
    },
    width="stretch",
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
    # [FIX] Filter out indices that are no longer valid for the current filtered dataframe
    valid_indices = [i for i in selected_indices if i < len(filtered_df)]
    
    if valid_indices:
        num_selected = len(valid_indices)
        selected_ids = filtered_df.iloc[valid_indices]['id'].tolist()
        # Update selected_indices to only valid ones for downstream use if needed, 
        # though downstream mostly uses selected_ids.
        selected_indices = valid_indices 
    else:
        num_selected = 0
        selected_ids = []

    # Visual Separator
    st.write("")

    # THE SLEEK TOOLBAR
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([1, 1.5, 2, 1.5], vertical_alignment="center")

        with col1:
            st.markdown(f"**{num_selected}** Selected")

        with col2:
            if st.button("⭐ Toggle Save", width="stretch"):
                for job_id in selected_ids:
                    if job_id not in tracking_data: tracking_data[job_id] = {}
                    current = tracking_data[job_id].get('saved', False)
                    tracking_data[job_id]['saved'] = not current
                save_tracking(tracking_data)
                
                save_tracking(tracking_data)
                
                # Clear selection after action
                st.session_state.table_version += 1
                st.rerun()

        with col3:
            new_status = st.selectbox(
                "Status",
                ["Applied", "Interviewing", "Offer", "Rejected", "New"],
                label_visibility="collapsed",
                key="status_selector"
            )

        with col4:
            if st.button("Update Status", type="primary", width="stretch"):
                for job_id in selected_ids:
                    if job_id not in tracking_data: tracking_data[job_id] = {}
                    tracking_data[job_id]['status'] = new_status
                    if new_status in ["Applied", "Interviewing", "Offer"]:
                        tracking_data[job_id]['saved'] = True
                save_tracking(tracking_data)
                
                save_tracking(tracking_data)
                
                # Clear selection after action
                st.session_state.table_version += 1
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
                if st.button(btn_label, type="primary", width="stretch"):
                    st.session_state["active_job"] = selected_job_row.to_dict()
                    st.switch_page("pages/CV_Editor.py")
    else:
        with st.container(border=True):
            col_cv1, col_cv2 = st.columns([3, 1], vertical_alignment="center")
            with col_cv1:
                st.markdown("<span style='color:#bbb'>⚠️ Select only **1** job to view or create a resume</span>", unsafe_allow_html=True)
            with col_cv2:
                st.button("📝 Create Resume", type="primary", width="stretch", disabled=True, key="multi_cv")

else:
    # Empty-state: ghost versions of both toolbar rows
    st.write("")
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([1, 1.5, 2, 1.5], vertical_alignment="center")
        with col1:
            st.markdown("<span style='color:#bbb'>**0** Selected</span>", unsafe_allow_html=True)
        with col2:
            st.button("⭐ Toggle Save", width="stretch", disabled=True, key="ghost_save")
        with col3:
            st.selectbox("Status", ["Applied", "Interviewing", "Offer", "Rejected", "New"],
                         label_visibility="collapsed", disabled=True, key="ghost_status")
        with col4:
            st.button("Update Status", type="primary", width="stretch", disabled=True, key="ghost_update")

    with st.container(border=True):
        col_cv1, col_cv2 = st.columns([3, 1], vertical_alignment="center")
        with col_cv1:
            st.markdown("<span style='color:#bbb'>📝 Select a job to view or create a resume</span>", unsafe_allow_html=True)
        with col_cv2:
            st.button("📝 Create Resume", type="primary", width="stretch", disabled=True, key="ghost_cv")
