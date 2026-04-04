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
import yaml
from utils.ui_utils import render_status, format_status_df, inject_custom_css
from utils.data_manager import JobDataService


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

# Global UI Inject (includes transparent toolbar)
inject_custom_css()

st.markdown("""
    <style>
    /* Make ONLY the bottom action toolbar sticky, not every container */
    [data-testid="stVerticalBlockBorderWrapper"]:has(button[key="status_selector"]),
    [data-testid="stVerticalBlockBorderWrapper"]:has(button[key="ghost_status"]) {
        position: sticky;
        bottom: 20px;
        z-index: 100;
        background-color: white;
        box-shadow: 0 -5px 15px rgba(0,0,0,0.05);
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

from config_utils import load_config, load_companies, clean_df_list, save_yaml_safely, FILTERING_PATH, COMPANIES_PATH

def load_tracking():
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_tracking(data):
    with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# --- Main App ---

# Fetch Data Envelope via Centralized Service
payload = JobDataService.fetch_dashboard_payload()
raw_data_obj = payload.get("data", pd.DataFrame())
is_mock = payload.get("is_mock", False)
df_jobs_raw = raw_data_obj.copy()

# Sideboard: Status & Stats
with st.sidebar:
    # --- Controls ---

    if st.button("🔄 Force Refresh Data", type="primary", width="stretch"):
        st.cache_data.clear()
        st.rerun()

if df_jobs_raw.empty and not is_mock:
    st.warning("⚠️ No data found. Head to the Scraper page to start.")
    if st.button("🚀 Go to Scraper", width="stretch"):
        st.switch_page("pages/2_🚀_Scraper.py")
    st.stop()

# Initialize Tracking
tracking_data = JobDataService.load_tracking()
df_jobs = df_jobs_raw.copy()


# --- Merge Data ---
saved_map = {k: v.get('saved', False) for k, v in tracking_data.items()}
status_map = {k: v.get('status', 'New') for k, v in tracking_data.items()}
cv_status_map = {k: v.get('cv_status', 'Generic') for k, v in tracking_data.items()}
resume_map = {k: os.path.basename(v['cv_pdf_path']) if v.get('cv_pdf_path') else '' for k, v in tracking_data.items()}

df_jobs['Status'] = df_jobs['id'].map(status_map).fillna('New')
df_jobs['Status_Display'] = df_jobs['Status'].apply(format_status_df)
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
    st.subheader("📊 Quick Insights")
    
    # Calculate stats
    total_jobs = len(df_jobs)
    num_companies = df_jobs['company'].nunique()
    num_saved = int(df_jobs['is_saved'].sum())
    num_applied = len([v for v in tracking_data.values() if v.get('status') == 'Applied'])
    num_interviewing = len([v for v in tracking_data.values() if v.get('status') == 'Interviewing'])
    num_offers = len([v for v in tracking_data.values() if v.get('status') == 'Offer'])
    num_rejected = len([v for v in tracking_data.values() if v.get('status') == 'Rejected'])
    num_saved_unapplied = int((df_jobs['is_saved'] & (df_jobs['Status'] != 'Applied')).sum())
    avg_score = df_jobs['score'].mean()
    
    with st.container(border=True):
        if is_mock:
            st.caption("⚠️ Mock Data")
        col_a, col_b = st.columns(2)
        col_a.metric("Total Jobs", total_jobs)
        col_b.metric("Companies", num_companies)

    with st.container(border=True):
        if is_mock:
            st.caption("⚠️ Mock Data")
        col_c, col_d = st.columns(2)
        col_c.metric("⭐ Saved", num_saved)
        col_d.metric("📝 Applied", num_applied)

    with st.container(border=True):
        if is_mock:
            st.caption("⚠️ Mock Data")
        col_e, col_f = st.columns(2)
        col_e.metric("🎤 Interviewing", num_interviewing)
        col_f.metric("🎉 Offers", num_offers)

    with st.container(border=True):
        if is_mock:
            st.caption("⚠️ Mock Data")
        col_g, col_h = st.columns(2)
        col_g.metric("📋 TODO", num_saved_unapplied, help="Saved but not yet applied")
        col_h.metric("❌ Rejected", num_rejected)

    with st.container(border=True):
        if is_mock:
            st.caption("⚠️ Mock Data")
        st.metric("Avg Score", f"{avg_score:.1f}")


    if 'date_posted' in df_jobs.columns:
        dates = pd.to_datetime(df_jobs['date_posted'], errors='coerce', format='ISO8601').dropna()
        if not dates.empty:
            st.caption(f"📅 {dates.min().strftime('%b %d')} – {dates.max().strftime('%b %d, %Y')}")

    # --- System Status (Hard Drop Indicator) ---
    st.sidebar.subheader("⚙️ System Status")
    app_config = load_config()
    drop_enabled = app_config.get('restrictions', {}).get('drop_restricted', False)
    if drop_enabled:
        st.sidebar.info("🗑️ **Hard Drop Active:** Restricted jobs are permanently dropped during ingestion. Your database only contains viable leads.")
    else:
        st.sidebar.caption("🗄️ **Full Retention:** All jobs are saved. Use the Mobility Filter above to hide restricted leads.")

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
    hide_hidden = True
    if selected_view == "All":
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            hide_rejected = st.checkbox("🚫 Hide Rejected", value=True, key="filter_hide_rejected")
        with col_f2:
            hide_hidden = st.checkbox("👻 Hide Hidden", value=True, key="filter_hide_hidden")

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

    # --- Mobility Filtering (Granular Control) ---
    config = load_config()
    mobility_enabled = config.get('restrictions', {}).get('enabled', False)
    
    selected_mobility = [] # Initialize fallback
    if mobility_enabled:
        st.subheader("🛂 Mobility Filter", divider="gray")
        mobility_options = {
            "🟢 Friendly": "FRIENDLY",
            "🟡 Neutral": "NEUTRAL", 
            "🔴 Restricted": "RESTRICTED"
        }
        selected_labels = st.multiselect(
            "Include Statuses:",
            options=list(mobility_options.keys()),
            default=["🟢 Friendly", "🟡 Neutral"],
            help="🟢 Friendly: Mentioned sponsorship | 🟡 Neutral: No mention | 🔴 Restricted: ITAR/Clearance required",
            key="filter_mobility_multiselect"
        )
        selected_mobility = [mobility_options[label] for label in selected_labels]

# --- Main Dashboard Area ---
# PURPOSELY HIDDEN (Architectural Decision) - Moving Scraper to a separate page. 
# DO NOT RE-ENABLE WITHOUT EXPLICIT USER CONSENT.
# st.title("🎯 Job Hunter Dashboard")

if is_mock:
    st.warning("⚠️ **[INTERNAL_TEST_STUB]** — Currently using generated mock data for UI testing. Scrape history unavailable.")
else:
    # Check for Active Scraper
    if JobDataService.is_scraper_running():
        st.info("🚀 **Scraper In Progress:** The background engine is currently searching for new listings. Refresh in a few minutes.")

# st.info("💡 **Manual Controls Moved:** You can now trigger manual updates or view logs on the [🚀 Scraper Page](Scraper).")


st.divider()


# --- Apply Filters ---
filtered_df = df_jobs.copy()

# 0. Mobility Column Injection (Defensive & Conditional)
if mobility_enabled and 'restriction_data' in filtered_df.columns:
    def get_mobility_display(x):
        if not isinstance(x, dict):
            return "🟡 Neutral"
        if x.get('restricted', False):
            return "🔴 Restricted"
        if x.get('friendly', False):
            return "🟢 Friendly"
        return "🟡 Neutral"
    
    filtered_df['Mobility'] = filtered_df['restriction_data'].apply(get_mobility_display)
    
    # Apply Filtering Logic (Stable Mapping)
    if selected_mobility:
        # Check against the raw enum in restriction_data for stability
        filtered_df = filtered_df[filtered_df['restriction_data'].apply(
            lambda x: x.get('mobility_status', 'NEUTRAL') if isinstance(x, dict) else 'NEUTRAL'
        ).isin(selected_mobility)]
elif 'Mobility' in filtered_df.columns:
    filtered_df = filtered_df.drop(columns=['Mobility'])

# 1. VIEW LOGIC (The Core "Inbox Zero" Flow)
if selected_view == "Feed":
    # Feed = New AND Not Saved AND Not Rejected AND Not Hidden
    # "Inbox Zero" - as soon as you save or apply, it leaves the feed.
    filtered_df = filtered_df[
        (filtered_df['Status'] == 'New') & 
        (filtered_df['is_saved'] == False) &
        (filtered_df['Status'] != 'Rejected') &
        (filtered_df['Status'] != 'Hidden')
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
    filtered_df = filtered_df[filtered_df['Status'].isin(tracking_statuses) & (filtered_df['Status'] != 'Hidden')]

elif selected_view == "All":
    # All = Everything (optionally hide rejected/hidden)
    if hide_rejected:
        filtered_df = filtered_df[filtered_df['Status'] != 'Rejected']
    if hide_hidden:
        filtered_df = filtered_df[filtered_df['Status'] != 'Hidden']


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
status_priority = {"Offer": 5, "Interviewing": 4, "Applied": 3, "New": 1, "Rejected": 0, "Hidden": -1}
filtered_df['status_prio'] = filtered_df['Status'].map(status_priority).fillna(1)
filtered_df = filtered_df.sort_values(by=["status_prio", "is_saved", "date_posted", "score"], ascending=[False, False, False, False]).reset_index(drop=True)


# --- TABLE ---
st.caption(f"Showing **{len(filtered_df)}** of {len(df_jobs)} jobs")

display_cols = ['Mobility', 'score', 'date_posted', 'company', 'title', 'location', 'url', 'id']
final_cols = [c for c in display_cols if c in filtered_df.columns]

event = st.dataframe(
    filtered_df[final_cols],
    on_select="rerun",
    selection_mode=["multi-row", "single-cell"],
    key=f"job_dashboard_table_{st.session_state.table_version}",
    column_config={
        "Mobility": st.column_config.TextColumn("🛂 Status", width="small", help="🟢 Friendly | 🟡 Neutral | 🔴 Restricted"),
        "url": st.column_config.LinkColumn("Link", display_text="Open"),
        "score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=50),
        "id": None
    },
    width="stretch",
    hide_index=True,
    height=530
)

# --- FOOTER ---
st.write("")
# PURPOSELY HIDDEN (Architectural Decision) - Moving Scraper to a separate page. 
# DO NOT RE-ENABLE WITHOUT EXPLICIT USER CONSENT.
# st.caption("Job Tracker v2026.4.3 | Architecture by [DEEPMIND_ANTIGRAVITY]")




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
        col1, col_save, col_hide, col3, col4 = st.columns([1, 1.2, 1.2, 1.5, 1.2], vertical_alignment="center")

        with col1:
            st.markdown(f"**{num_selected}** Selected")

        with col_save:
            if st.button("⭐ Save", width="stretch", help="Toggle Save"):
                for job_id in selected_ids:
                    if job_id not in tracking_data: tracking_data[job_id] = {}
                    current = tracking_data[job_id].get('saved', False)
                    tracking_data[job_id]['saved'] = not current
                JobDataService.save_tracking_atomically(tracking_data)
                st.session_state.table_version += 1
                st.rerun()


        with col_hide:
            if st.button("🚫 Hide", width="stretch", help="Hide from Feed"):
                for job_id in selected_ids:
                    if job_id not in tracking_data: tracking_data[job_id] = {}
                    tracking_data[job_id]['status'] = 'Hidden'
                    tracking_data[job_id]['saved'] = False # Usually if hiding, we don't want it saved
                JobDataService.save_tracking_atomically(tracking_data)
                st.session_state.table_version += 1
                st.rerun()


        with col3:
            new_status = st.selectbox(
                "Status",
                ["Applied", "Interviewing", "Offer", "Rejected", "New", "Hidden"],
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
                    
                    # [CLEANUP] If job is moved to terminal state, remove drafts
                    if new_status in ["Applied", "Rejected", "Hidden"]:
                        JobDataService.cleanup_job_drafts(job_id)
                
                JobDataService.save_tracking_atomically(tracking_data)
                
                # Clear selection after action
                st.session_state.table_version += 1
                st.rerun()


    # --- CV Editor / Resume Navigation & Restriction Audit ---
    if num_selected == 1:
        selected_job_row = filtered_df.iloc[selected_indices[0]]
        
        # Restriction Audit Trail
        res_data = selected_job_row.get('restriction_data', {})
        if isinstance(res_data, dict) and res_data.get('restricted'):
            st.error(f"🚫 **Restricted Role:** {res_data.get('reason')}", icon="🚫")
        resume_file = selected_job_row.get('resume', '')
        has_resume = bool(resume_file)

        with st.container(border=True):
            col_cv1, col_cv2 = st.columns([3, 1], vertical_alignment="center")
            with col_cv1:
                company_name = selected_job_row.get('company', 'Unknown')
                job_title = selected_job_row.get('title', 'Unknown')
                
                # Metadata-Driven Link Rendering (Quality Check: Verification Ledger)
                enrichment = selected_job_row.get('enrichment') or {}
                status = enrichment.get('status', 'pending')
                
                # Verified marketing pages are the primary target
                if status == 'verified':
                    display_url = selected_job_row.get('careers_page')
                else:
                    # Fallback for pending/unverified entries: use normalized UI link or legacy
                    display_url = selected_job_row.get('job_board_url') or selected_job_row.get('url', '#')
                
                if has_resume:
                    st.markdown(f"📄 **Resume**: `{resume_file}`  |  [{company_name} — {job_title}]({display_url})")
                else:
                    st.markdown(f"📝 **No Resume Yet** |  [{company_name} — {job_title}]({display_url})")
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
        col1, col_save, col_hide, col3, col4 = st.columns([1, 1.2, 1.2, 1.5, 1.2], vertical_alignment="center")
        with col1:
            st.markdown("<span style='color:#bbb'>**0** Selected</span>", unsafe_allow_html=True)
        with col_save:
            st.button("⭐ Save", width="stretch", disabled=True, key="ghost_save")
        with col_hide:
            st.button("🚫 Hide", width="stretch", disabled=True, key="ghost_hide")
        with col3:
            st.selectbox("Status", ["Applied", "Interviewing", "Offer", "Rejected", "New", "Hidden"],
                         label_visibility="collapsed", disabled=True, key="ghost_status")
        with col4:
            st.button("Update Status", type="primary", width="stretch", disabled=True, key="ghost_update")

    with st.container(border=True):
        col_cv1, col_cv2 = st.columns([3, 1], vertical_alignment="center")
        with col_cv1:
            st.markdown("<span style='color:#bbb'>📝 Select a job to view or create a resume</span>", unsafe_allow_html=True)
        with col_cv2:
            st.button("📝 Create Resume", type="primary", width="stretch", disabled=True, key="ghost_cv")
