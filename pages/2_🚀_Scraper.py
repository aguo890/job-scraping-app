import streamlit as st
import time
from utils.data_manager import JobDataService
from main import execute_scraping_run
from utils.ui_utils import inject_custom_css

# Page Config
st.set_page_config(page_title="Scraper Control", layout="wide")

# Global UI Inject (includes transparent toolbar)
inject_custom_css()

st.title("🚀 Scraper Operations")
st.markdown("---")

# Sync Data Service State
JobDataService._check_write_permissions()

# --- ACTION BAR ---
col_head, col_btn = st.columns([3, 1], vertical_alignment="bottom")

with col_head:
    st.subheader("🛠️ Scraper Controls")
    st.caption("Trigger a manual scraping run across all configured companies.")

with col_btn:
    is_running = JobDataService.is_scraper_running()
    
    if is_running:
        st.button("🚀 Scraper Busy...", type="primary", width="stretch", disabled=True, 
                  help="A scraping run is currently in progress (Global Lock active).")
    else:
        if st.button("🚀 Run Scraper Now", type="primary", width="stretch"):
            with st.status("Initializing Engine...", expanded=True) as status:
                st.write("Checking global lock...")
                
                # Execute the run
                result = execute_scraping_run()
                
                st.write("Updating history logs...")
                # Log the run via the DataService
                JobDataService.log_scrape_run(
                    jobs_found=result.get("processed", 0),
                    duration_seconds=result.get("duration_seconds", 0),
                    status=result.get("status", "Unknown")
                )
                
                if "Success" in result["status"]:
                    status.update(label="Scraping Complete!", state="complete", expanded=False)
                    st.success("✅ Scraping Complete!")
                    
                    # Display metrics
                    col_res1, col_res2 = st.columns(2)
                    col_res1.metric("Ingested (Raw)", result.get('ingested', 0))
                    col_res2.metric("Matches Your Filters", result.get('processed', 0))
                    
                    # Force Cache Clear for Data Freshness
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    status.update(label="Scraping Failed!", state="error", expanded=True)
                    st.error(f"❌ {result['status']}")

st.divider()

# --- HISTORY SECTION ---
st.subheader("📜 Scraping History")
with st.container(border=True):
    df_history = JobDataService.get_scrape_history_df()
    
    if not df_history.empty:
        st.dataframe(
            df_history, 
            width="stretch", 
            hide_index=True,
            column_config={
                "duration_seconds": st.column_config.NumberColumn("Duration (s)", format="%.2f"),
                "jobs_found": st.column_config.NumberColumn("Jobs Found"),
                "status": st.column_config.TextColumn("Status"),
                "timestamp": st.column_config.TextColumn("Run Date")
            }
        )
    else:
        st.info("No historical runs found. Trigger a scrape to see results here.")

st.divider()

# --- DISCOVERY PREVIEW ---
st.subheader("🛂 Latest High-Signal Discoveries")
st.caption("Immediate mobility preview of the most recently ingested roles.")

# Add parent directory to path to ensure config_utils and other modules are found
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from config_utils import load_config
config = load_config()
mobility_enabled = config.get('restrictions', {}).get('enabled', False)

payload = JobDataService.fetch_dashboard_payload()
df_recent = payload.get("data", None)

if df_recent is not None and not df_recent.empty:
    # 1. Inject Mobility Icons for Preview (Conditional)
    display_cols = ['company', 'title', 'location', 'score']
    
    if mobility_enabled and 'restriction_data' in df_recent.columns:
        def get_mobility_icon(res):
            if not isinstance(res, dict): return "🟡"
            status = res.get('mobility_status', 'NEUTRAL')
            if status == 'FRIENDLY': return "🟢"
            if status == 'RESTRICTED': return "🔴"
            return "🟡"
        
        df_recent['🛂'] = df_recent['restriction_data'].apply(get_mobility_icon)
        display_cols.insert(0, '🛂')
    
    # 2. Sort by date_posted (newest first)
    if 'date_posted' in df_recent.columns:
        df_recent = df_recent.sort_values(by="date_posted", ascending=False)
    
    # 3. Filter for Top 15
    df_preview = df_recent.head(15).copy()
    final_cols = [c for c in display_cols if c in df_preview.columns]
    
    st.dataframe(
        df_preview[final_cols],
        width="stretch",
        hide_index=True,
        column_config={
            "🛂": st.column_config.TextColumn("🛂", width="small", help="🟢 Friendly | 🟡 Neutral | 🔴 Restricted"),
            "score": st.column_config.NumberColumn("Score", format="%d")
        }
    )
    st.caption("💡 Full details and filtering controls are available on the main [Dashboard](Dashboard).")
else:
    st.info("Ingest some jobs to see the discovery preview.")

# --- NAVIGATION FOOTER ---
st.write("")
st.info("💡 Once finished, head back to the [Dashboard](Dashboard) to view your updated job feed.")
