import streamlit as st
import time
from utils.data_manager import JobDataService
from main import execute_scraping_run

# Page Config
st.set_page_config(page_title="Scraper Control", layout="wide")

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

# --- NAVIGATION FOOTER ---
st.write("")
st.info("💡 Once finished, head back to the [Dashboard](Dashboard) to view your updated job feed.")
