import streamlit as st
import time
import subprocess
import sys
import os
import json
import ast
import tempfile
from utils.data_manager import JobDataService
from main import execute_scraping_run
from utils.ui_utils import inject_custom_css

# Page Config
st.set_page_config(page_title="Scraper Control", layout="wide")

# Global UI Inject (includes transparent toolbar)
inject_custom_css()

st.title("🛠️ Scraper Controls")
st.caption("Trigger a manual scraping run across all configured companies.")
st.markdown("---")

is_running = JobDataService.is_scraper_running()

if is_running:
    st.button("🚀 Scraper Busy...", type="primary", width="stretch", disabled=True, 
              help="A scraping run is currently in progress (Global Lock active).")
else:
    if st.button("🚀 Run Scraper Now", type="primary", width="stretch"):
        with st.status("Initializing Engine...", expanded=True) as status:
            st.write("Ensuring active connections and locks...")
            
            # Execute the run in a subprocess
            log_container = st.code("Starting...", language="bash")
            
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
                output_file = tmp.name
                
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cmd = [sys.executable, "-u", "main.py", "--output", output_file]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=parent_dir)
            st.session_state["scraper_process"] = process
            
            log_text = ""
            for line in iter(process.stdout.readline, ""):
                log_text += line
                log_container.code(log_text, language="bash")
                
            process.stdout.close()
            process.wait()
            
            if "scraper_process" in st.session_state:
                del st.session_state["scraper_process"]
                
            try:
                with open(output_file, "r") as f:
                    result = json.load(f)
            except Exception:
                result = {
                    "status": "Failed to parse CLI output", 
                    "jobs_found": 0, 
                    "duration_seconds": 0
                }
                
            if os.path.exists(output_file):
                os.remove(output_file)
            
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

def safe_extract_skills(tier_data):
    # If pandas loaded it as a string, evaluate it back into a dictionary
    if isinstance(tier_data, str):
        try:
            tier_data = ast.literal_eval(tier_data)
        except (ValueError, SyntaxError):
            return [] # Fail gracefully if the string is corrupt
            
    # Now that we are sure it's a dict, flatten it
    if isinstance(tier_data, dict):
        return [skill for tier in tier_data.values() for skill in tier]
        
    return []

payload = JobDataService.fetch_dashboard_payload()
df_recent = payload.get("data", None)

if df_recent is not None and not df_recent.empty:
    # 0. Safe Data Transformation for Matched Skills
    if 'matched_tiers' in df_recent.columns:
        df_recent['Matched_Skills'] = df_recent['matched_tiers'].apply(safe_extract_skills)
    else:
        df_recent['Matched_Skills'] = [[] for _ in range(len(df_recent))]

    # 1. Inject Mobility Icons for Preview (Conditional)
    display_cols = ['url', 'score', 'title', 'company', 'location', 'Matched_Skills']
    
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
            "url": st.column_config.LinkColumn("Link", display_text="Link"),
            "score": st.column_config.NumberColumn("Score", format="%d"),
            "Matched_Skills": st.column_config.ListColumn("Matched Skills", width="medium")
        }
    )
    st.caption("💡 Full details and filtering controls are available on the main [Dashboard](Dashboard).")
else:
    st.info("Ingest some jobs to see the discovery preview.")

# --- NAVIGATION FOOTER ---
st.write("")
st.info("💡 Once finished, head back to the [Dashboard](Dashboard) to view your updated job feed.")
