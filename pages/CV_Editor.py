import sys
import os

# Add the parent directory (root) to the Python path so we can find cv_bridge.py
# CV_Editor is in pages/, so we need to go up TWO levels
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # job-scraping-app/
root_dir = os.path.dirname(parent_dir)     # Job-Automation-Suite/
sys.path.insert(0, root_dir)

import streamlit as st
import base64
import json
import time
import re
from datetime import datetime

from utils.ui_utils import inject_custom_css

try:
    from cv_bridge import CVOrchestrator
except ImportError:
    CVOrchestrator = None

try:
    import ai_tailor
except ImportError:
    ai_tailor = None

st.set_page_config(page_title="CV Editor", layout="wide")

# Global UI Inject (includes transparent toolbar)
inject_custom_css()

st.markdown("""
    <style>
    .stMainBlockContainer {
        padding-top: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-bottom: 0rem !important;
        max-width: 100% !important;
    }
    .stMain {
        min-height: 100vh !important;
    }
    /* Make YAML editor fill viewport like rendercv app */
    .stTextArea textarea {
        font-family: 'Source Code Pro', monospace;
        height: 85vh !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. Navigation Guard (with URL persistence) ---
SPECIAL_ROUTING_JOBS = {
    "master_cv": {
        "id": "master_cv",
        "company": "[SYSTEM] MASTER RECORD",
        "title": "Base CV",
        "is_master": True
    },
    "playground": {
        "id": "playground",
        "company": "[SYSTEM] PLAYGROUND",
        "title": "Scratch Pad",
        "is_playground": True
    }
}

def load_job_by_id(job_id):
    """Look up a job from jobs_agg.json by its id."""
    if job_id in SPECIAL_ROUTING_JOBS:
        return SPECIAL_ROUTING_JOBS[job_id]

    jobs_file = os.path.join(parent_dir, "data", "jobs_agg.json")
    if not os.path.exists(jobs_file):
        return None
    try:
        with open(jobs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for job in data.get("jobs", []):
            if job.get("id") == job_id:
                return job
    except Exception:
        pass
    return None

# --- Draft Management Persistence ---
def get_draft_path(job_id):
    """Returns path to the temporary draft file."""
    if job_id in SPECIAL_ROUTING_JOBS:
        return None
    return os.path.join(orchestrator.output_dir, f"{job_id}_Draft.yaml")

def save_draft_to_disk(job_id, content):
    """Explicitly persists the current buffer to disk."""
    path = get_draft_path(job_id)
    if path:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            st.error(f"Failed to save draft: {e}")
    return False

def load_cv_content(job_id):
    """
    Implements High-Reliability Recovery Pattern:
    1. Session State (Current Buffer)
    2. Disk Draft (_Draft.yaml)
    3. Tailored CV ({job_id}.yaml)
    4. Master CV
    """
    # 1. Session State (Memory Buffer)
    buffer_key = f"buffer_{job_id}"
    if buffer_key in st.session_state:
        return st.session_state[buffer_key]
    
    # 2. Disk Draft
    dp = get_draft_path(job_id)
    if dp and os.path.exists(dp):
        try:
            with open(dp, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            pass
            
    # 3 & 4. Orchestrator Logic (Tailored or Master)
    return orchestrator.load_job_cv(job_id)

# --- Robust Data Loading ---
# PRECEDENCE: 1. URL (Deep Link/Refresh) -> 2. Session State (Dashboard Nav) -> 3. Error
url_job_id = st.query_params.get("job_id")
state_job = st.session_state.get("active_job")

# SCENARIO A: URL present (deep link, refresh, or shared link)
if url_job_id:
    # If URL disagrees with state, URL wins — re-fetch from data
    if not state_job or str(state_job.get("id")) != str(url_job_id):
        recovered_job = load_job_by_id(url_job_id)
        if recovered_job:
            st.session_state["active_job"] = recovered_job
        else:
            st.warning(f"Job `{url_job_id}` not found in data. Return to Dashboard.")
            if st.button("⬅️ Back to Dashboard"):
                st.switch_page("dashboard.py")
            st.stop()
    # Ensure URL stays set for refresh consistency
    st.query_params["job_id"] = url_job_id

# SCENARIO B: No URL, but state exists (navigated from dashboard)
elif state_job:
    # Self-Healing: restore URL from state
    st.query_params["job_id"] = state_job.get("id", "")

# SCENARIO C: Nothing — no URL, no state
else:
    st.info("👋 No job selected. Choose a job from the Dashboard to tailor your CV.")
    st.markdown("---")

    col_master, col_playground = st.columns(2)
    with col_master:
        st.write("Edit the **Master CV Source** directly. Changes affect all future CV generations.")
        if st.button("🛠️ Edit Master CV Source", type="secondary", width="stretch"):
            st.session_state["active_job"] = SPECIAL_ROUTING_JOBS["master_cv"]
            st.rerun()
    with col_playground:
        st.write("Open a **Playground** to draft a CV from your template without affecting anything.")
        if st.button("🧪 Playground", type="secondary", width="stretch"):
            st.session_state["active_job"] = SPECIAL_ROUTING_JOBS["playground"]
            st.rerun()

    st.markdown("---")
    if st.button("⬅️ Back to Dashboard"):
        st.switch_page("dashboard.py")
    st.stop()

if not CVOrchestrator:
    st.error("CVOrchestrator could not be imported. Check cv_bridge.py.")
    st.stop()

job = st.session_state["active_job"]
job_id = job.get("id", "unknown_id")
company = job.get("company", "Unknown Company")
title = job.get("title", "N/A")
is_master = job.get("is_master", False)
is_playground = job.get("is_playground", False)

# --- 2. Restriction Warning ---
res_data = job.get("restriction_data", {})
if isinstance(res_data, dict) and res_data.get("restricted"):
    st.warning(f"⚠️ **Restriction Alert:** {res_data.get('reason')}. Please ensure you meet the eligibility requirements before tailoring.", icon="⚠️")

# --- 2. Initialize Orchestrator ---
# Uses default (Aaron_Guo_CV.yaml) which is mounted at root in Docker
orchestrator = CVOrchestrator()

# --- 3. Load State (with Job Switch Detection) ---
if "current_editing_job_id" not in st.session_state:
    st.session_state["current_editing_job_id"] = None

# If we switched jobs, force a reload and persist old draft
if st.session_state["current_editing_job_id"] != job_id:
    # --- Auto-Save Old Job Draft before switching ---
    old_id = st.session_state["current_editing_job_id"]
    if old_id and old_id in st.session_state.get("active_job", {}).get("id", ""): # Check if it's a real job
         # This is tricky because the old content is in the widget
         pass

    # --- Reset Playground if entering it ---
    if is_playground:
        orchestrator.reset_playground()
        
    # Clear old state and Load fresh recovery
    content = load_cv_content(job_id)
    st.session_state["editor_yaml"] = content
    st.session_state["yaml_editor"] = content
    st.session_state[f"buffer_{job_id}"] = content
    st.session_state["current_editing_job_id"] = job_id
    
    # Clear PDF state so we don't show wrong PDF
    st.session_state.pop("current_pdf", None)
    st.session_state.pop("render_status", None)
    st.session_state.pop("ai_strategy", None)

# Ensure editor_yaml is loaded if it's missing (e.g. first run)
if "editor_yaml" not in st.session_state:
    st.session_state["editor_yaml"] = orchestrator.load_job_cv(job_id)

if "is_rendering" not in st.session_state:
    st.session_state["is_rendering"] = False

if st.session_state.pop("render_success_toast", False):
    st.toast("✅ Render Complete! 📄")

# --- SIDEBAR: Job Info, Navigation, Render, Download, AI Tools ---
with st.sidebar:
    if is_master:
        st.header("🛠️ MASTER CV")
        st.warning("You are editing the Master CV source. Changes affect **all** future generations.", icon="⚠️")
    elif is_playground:
        st.header("🧪 PLAYGROUND")
        st.info("Temporary workspace. Your master CV is safe.", icon="🧪")
    else:
        st.header(f"📝 {company}")
        st.caption(f"**Role**: {title}")
    st.caption(f"**ID**: `{job_id}`")

    st.divider()

    if st.button("⬅️ Back to Dashboard", width="stretch"):
        if is_master or is_playground:
            # Clear special mode state on exit
            st.session_state.pop("active_job", None)
            st.session_state.pop("current_editing_job_id", None)
        st.switch_page("dashboard.py")

    st.divider()

    # Render button
    render_clicked = st.button("🔄 Render PDF", type="primary", width="stretch", disabled=st.session_state["is_rendering"])
    st.caption("*Or press Ctrl+Enter in the editor*")

    # Download button (if PDF exists)
    display_path = st.session_state.get("current_pdf")
    if not display_path:
        potential_path = os.path.join(orchestrator.output_dir, f"{job_id}.pdf")
        if os.path.exists(potential_path):
            display_path = potential_path

    if display_path and os.path.exists(display_path):
        # Sanitize for filename
        clean_company = re.sub(r'[^a-zA-Z0-9]', '_', company)
        clean_title = re.sub(r'[^a-zA-Z0-9]', '_', title)
        # Collapse multiple underscores
        clean_company = re.sub(r'_+', '_', clean_company).strip('_')
        clean_title = re.sub(r'_+', '_', clean_title).strip('_')
        
        nice_filename = f"Aaron_Guo_{clean_title}_{clean_company}.pdf"
        mtime = int(os.path.getmtime(display_path))
        
        with open(display_path, "rb") as f:
            pdf_data = f.read()
            st.download_button(
                "⏳ Rendering..." if st.session_state["is_rendering"] else "⬇️ Download PDF",
                data=pdf_data,
                file_name=nice_filename,
                mime="application/pdf",
                width="stretch",
                key=f"dl_{job_id}_{mtime}",
                disabled=st.session_state["is_rendering"]
            )

    # Reset Button
    if st.button("🔄 Reset to Base", help="Discard changes and revert to Master CV"):
        try:
            # 1. Remove tailored file if it exists (not for master mode)
            if not is_master:
                tailored_path = os.path.join(orchestrator.output_dir, f"{job_id}.yaml")
                if os.path.exists(tailored_path):
                    os.remove(tailored_path)
            
            # 2. Reload base CV
            if os.path.exists(orchestrator.base_cv_path):
                with open(orchestrator.base_cv_path, 'r', encoding='utf-8') as f:
                    base_content = f.read()
                st.session_state["editor_yaml"] = base_content
                st.session_state["yaml_editor"] = base_content # Force widget update
                st.session_state["current_editing_job_id"] = job_id  # Ensure synced
                st.toast("Reverted to Master CV! 🔄")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Master CV file not found!")
        except Exception as e:
            st.error(f"Error resetting: {e}")

    st.divider()

    # Application Workflow
    def mark_as_applied(target_id):
        """Mark job as applied in tracking.json"""
        tracking_file = os.path.join(parent_dir, "data", "tracking.json")
        if os.path.exists(tracking_file):
            try:
                with open(tracking_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}
            
        if target_id not in data:
            data[target_id] = {}
            
        data[target_id]["status"] = "Applied"
        data[target_id]["saved"] = True
        data[target_id]["date_applied"] = datetime.now().isoformat()
        
        with open(tracking_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        # [CLEANUP] Remove draft file after application
        dp = get_draft_path(target_id)
        if dp and os.path.exists(dp):
            try:
                os.remove(dp)
            except Exception:
                pass

    # Disable "Mark as Applied" in master/playground mode
    if st.button("🚀 Mark as Applied", type="primary", width="stretch",
                 help="Not available in this mode." if (is_master or is_playground) else "Mark as Applied and return to Dashboard",
                 disabled=(is_master or is_playground)):
        mark_as_applied(job_id)
        st.toast("Application Submitted! Returning to Dashboard...", icon="🚀")
        time.sleep(1.5)
        st.switch_page("dashboard.py")

    st.divider()

    # AI Tailoring Tools
    st.subheader("🤖 AI Tailoring")
    if is_master or is_playground:
        st.info("AI Tailoring is disabled in this mode (no job context).")
    elif ai_tailor:
        st.write("Auto-update CV using DeepSeek R1.")
        if st.button("Auto-Tailor with AI", type="primary", width="stretch"):
            with st.spinner("🧠 Rewriting CV... (30-60s)"):
                try:
                    strategy, new_yaml, gap, reasoning = ai_tailor.generate_tailored_resume(
                        base_yaml_content=st.session_state["editor_yaml"],
                        job_description=job.get("description", "No description provided"),
                        job_title=title,
                        company_name=company
                    )
                    st.session_state["editor_yaml"] = new_yaml
                    st.session_state["ai_strategy"] = strategy
                    st.session_state["ai_reasoning"] = reasoning
                    orchestrator.save_job_cv(job_id, new_yaml)
                    st.toast("AI updates applied! ✨")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")

        if "ai_strategy" in st.session_state and st.session_state["ai_strategy"]:
            with st.expander("📊 Strategy Report"):
                st.markdown(st.session_state["ai_strategy"])
    else:
        st.warning("AI module not available.")



# --- 3. Workspace Layout: 🏛️ CV TAILORING WORKSHOP ---
st.title("🏛️ CV Tailoring Workshop")

# --- Restriction Warning ---
res_data = job.get("restriction_data", {})
if isinstance(res_data, dict) and res_data.get("restricted"):
    st.error(f"🚫 **ITAR/Clearance Warning:** {res_data.get('reason')}. Ensure eligibility before tailoring.", icon="🚫")

st.divider()

# --- 4. Main Workflow Columns ---
col_strat, col_editor = st.columns([1, 2], gap="large")

with col_strat:
    st.subheader("🎯 Strategy & Context")
    
    # A. Job Context Card
    with st.container(border=True):
        st.markdown(f"### {company}")
        st.write(f"**Target Role:** {title}")
        st.caption(f"Job ID: `{job_id}`")
    
    st.divider()
    
    # B. AI Strategy & Gaps
    if "ai_strategy" in st.session_state and st.session_state["ai_strategy"]:
        with st.container(border=True):
            st.markdown("### 🧠 AI Strategy")
            st.info(st.session_state["ai_strategy"])
            
            if "gap_analysis" in st.session_state and st.session_state["gap_analysis"]:
                st.markdown("#### ⚠️ Gap Analysis")
                st.warning(st.session_state["gap_analysis"])
                
            if "ai_reasoning" in st.session_state and st.session_state["ai_reasoning"]:
                with st.expander("💭 Chain of Thought"):
                    st.caption(st.session_state["ai_reasoning"])
    else:
        st.info("Run **AI Tailor** to generate a strategy and gap analysis for this role.")

    st.divider()

    # C. AI Controls (Moved from Sidebar for context)
    if not (is_master or is_playground):
        if st.button("🤖 Auto-Tailor with AI", type="primary", width="stretch"):
            with st.spinner("🧠 Rewriting CV... (DeepSeek R1)"):
                try:
                    strategy, new_yaml, gap, reasoning = ai_tailor.generate_tailored_resume(
                        base_yaml_content=st.session_state["editor_yaml"],
                        job_description=job.get("description", "No description provided"),
                        job_title=title,
                        company_name=company
                    )
                    st.session_state["editor_yaml"] = new_yaml
                    st.session_state["yaml_editor"] = new_yaml # Sync buffer
                    st.session_state["ai_strategy"] = strategy
                    st.session_state["gap_analysis"] = gap
                    st.session_state["ai_reasoning"] = reasoning
                    orchestrator.save_job_cv(job_id, new_yaml)
                    st.toast("AI Strategy Applied! ✨")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Tailoring failed: {e}")

with col_editor:
    # --- Toolbar ---
    tool_l, tool_r = st.columns([3, 1])
    with tool_l:
        st.subheader("📝 CV Workshop")
    with tool_r:
        if st.button("🔄 Render PDF", type="primary", width="stretch", disabled=st.session_state["is_rendering"]):
            st.session_state["is_rendering"] = True
            st.rerun()

    # --- The Buffered Editor ---
    with st.container(border=True):
        # Initialize widget state if missing
        if "yaml_editor" not in st.session_state:
            st.session_state["yaml_editor"] = st.session_state["editor_yaml"]

        # The session state "yaml_editor" now acts as our persistent buffer
        edited_content = st.text_area(
            "Draft Buffer",
            value=st.session_state["yaml_editor"],
            height=None, # CSS controlled (85vh)
            key="yaml_editor_widget",
            label_visibility="collapsed",
            on_change=lambda: st.session_state.__setitem__("yaml_editor", st.session_state["yaml_editor_widget"])
        )
        # 1. Update In-Memory Buffers
        st.session_state["yaml_editor"] = edited_content
        st.session_state[f"buffer_{job_id}"] = edited_content

        # 2. Persistence Controls
        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            if st.button("💾 Save Draft", help="Persist changes to disk draft file", width="stretch"):
                if save_draft_to_disk(job_id, edited_content):
                    st.toast("Draft saved to disk! 📦")
        with c2:
            st.caption(f"Last Buffer Sync: {datetime.now().strftime('%H:%M:%S')}")

    # --- Render Logic (Inside Col) ---
    if st.session_state.get("is_rendering", False):
        with st.spinner("Compiling with RenderCV..."):
            content = st.session_state["yaml_editor"]
            # 1. Save current buffer to disk
            save_result = orchestrator.save_job_cv(job_id, content)
            if isinstance(save_result, dict) and not save_result.get("success", True):
                st.error(f"❌ Save Failed: {save_result.get('error', 'Unknown error')}")
            else:
                # 2. Render from content
                pdf_path, status = orchestrator.render_from_content(job_id, content)
                if pdf_path:
                    st.session_state["current_pdf"] = pdf_path
                    st.session_state["render_success_toast"] = True
                else:
                    st.error(f"❌ Render Failed: {status}")
            
            st.session_state["is_rendering"] = False
            st.rerun()

    # --- Download & Prev ---
    display_path = st.session_state.get("current_pdf")
    if not display_path:
        potential = os.path.join(orchestrator.output_dir, f"{job_id}.pdf")
        if os.path.exists(potential):
            display_path = potential

    if display_path and os.path.exists(display_path):
        with st.expander("📄 PDF Preview & Download", expanded=True):
            btn_col_l, btn_col_r = st.columns([3, 1])
            with btn_col_l:
                 st.info("PDF generated successfully. Review the preview below before downloading.")
            with btn_col_r:
                # Provide nice filename
                clean_t = re.sub(r'[^a-zA-Z0-9]', '_', title)
                clean_c = re.sub(r'[^a-zA-Z0-9]', '_', company)
                nice_name = f"Aaron_Guo_{clean_t}_{clean_c}.pdf"
                with open(display_path, "rb") as f:
                    st.download_button("⬇️ Download PDF", data=f.read(), file_name=nice_name, mime="application/pdf", width="stretch")

            # Inline PDF Preview
            with open(display_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            pdf_iframe = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" style="height: 60vh; border-radius: 8px;" type="application/pdf"></iframe>'
            st.markdown(pdf_iframe, unsafe_allow_html=True)
    else:
        st.info("Click **Render PDF** to generate the document.")

# Inject Keyboard Listener for Ctrl+Enter
import streamlit.components.v1 as components
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            if (doc.activeElement) { doc.activeElement.blur(); }
            setTimeout(() => {
                const buttons = Array.from(doc.querySelectorAll('button'));
                const renderBtn = buttons.find(b => b.innerText.includes('Render PDF'));
                if (renderBtn) { renderBtn.click(); }
            }, 100);
        }
    });
    </script>
    """,
    height=0,
    width=0,
)
