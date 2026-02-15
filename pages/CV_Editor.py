import streamlit as st
import base64
import json
import os
import sys
import time
import re
from datetime import datetime


# Add parent directory to path for imports (monorepo structure)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # job-scraping-app/
root_dir = os.path.dirname(parent_dir)     # Job-Automation-Suite/
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    from cv_bridge import CVOrchestrator
except ImportError:
    CVOrchestrator = None

try:
    import ai_tailor
except ImportError:
    ai_tailor = None

st.set_page_config(page_title="CV Editor", layout="wide")

st.markdown("""
    <style>
    .stMainBlockContainer {
        padding-top: 40px !important;
        padding-left: 40px !important;
        padding-right: 40px !important;
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
def load_job_by_id(job_id):
    """Look up a job from jobs_agg.json by its id."""
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

# Priority 1: session_state (navigated from dashboard)
# Priority 2: URL query param (page refresh)
if "active_job" not in st.session_state or not st.session_state["active_job"]:
    qp_job_id = st.query_params.get("job_id")
    if qp_job_id:
        recovered_job = load_job_by_id(qp_job_id)
        if recovered_job:
            st.session_state["active_job"] = recovered_job
        else:
            st.warning(f"Job `{qp_job_id}` not found in data. Return to Dashboard.")
            if st.button("⬅️ Back to Dashboard"):
                st.switch_page("dashboard.py")
            st.stop()
    else:
        st.warning("No job selected. Please return to the Dashboard.")
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

# Sync job_id to URL so refreshes work
st.query_params["job_id"] = job_id

# --- 2. Initialize Orchestrator ---
orchestrator = CVOrchestrator()

# --- 3. Load State ---
if "editor_yaml" not in st.session_state:
    st.session_state["editor_yaml"] = orchestrator.load_job_cv(job_id)

# --- SIDEBAR: Job Info, Navigation, Render, Download, AI Tools ---
with st.sidebar:
    st.header(f"📝 {company}")
    st.caption(f"**Role**: {title}")
    st.caption(f"**ID**: `{job_id}`")

    st.divider()

    if st.button("⬅️ Back to Dashboard", width="stretch"):
        st.switch_page("dashboard.py")

    st.divider()

    # Render button
    render_clicked = st.button("🔄 Render PDF", type="primary", width="stretch")
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
        
        with open(display_path, "rb") as f:
            st.download_button(
                "⬇️ Download PDF",
                f,
                file_name=nice_filename,
                mime="application/pdf",
                width="stretch",
                key=f"dl_{job_id}_{int(time.time())}"
            )

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

    if st.button("🚀 Mark as Applied", type="primary", width="stretch", help="Mark as Applied and return to Dashboard"):
        mark_as_applied(job_id)
        st.toast("Application Submitted! Returning to Dashboard...", icon="🚀")
        time.sleep(1.5)
        st.switch_page("dashboard.py")

    st.divider()

    # AI Tailoring Tools
    st.subheader("🤖 AI Tailoring")
    if ai_tailor:
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
                    st.success("AI updates applied!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")

        if "ai_strategy" in st.session_state and st.session_state["ai_strategy"]:
            with st.expander("📊 Strategy Report"):
                st.markdown(st.session_state["ai_strategy"])
    else:
        st.warning("AI module not available.")

# --- Render callback (triggered by Ctrl+Enter via on_change) ---
def trigger_render():
    content = st.session_state.get("yaml_editor", "")
    if content:
        st.session_state["editor_yaml"] = content
        orchestrator.save_job_cv(job_id, content)
        pdf_path, status = orchestrator.render_from_content(job_id, content)
        if pdf_path:
            st.session_state["current_pdf"] = pdf_path
            st.session_state["render_status"] = "success"
        else:
            st.session_state["render_status"] = f"fail:{status}"

# --- MAIN CONTENT: Editor | Preview ---
col_edit, col_prev = st.columns([1, 1])

with col_edit:
    st.text_area(
        "yaml_editor",
        value=st.session_state["editor_yaml"],
        height=None,  # Height controlled by CSS (85vh)
        key="yaml_editor",
        label_visibility="collapsed",
        on_change=trigger_render  # Fires on Ctrl+Enter
    )

with col_prev:
    # Handle render (from sidebar button)
    if render_clicked:
        with st.spinner("Rendering via RenderCV..."):
            content = st.session_state.get("yaml_editor", st.session_state["editor_yaml"])
            pdf_path, status = orchestrator.render_from_content(job_id, content)
            if pdf_path:
                st.session_state["current_pdf"] = pdf_path
                st.success("✅ Render Complete!")
            else:
                st.error(f"❌ Render Failed: {status}")

    # Show render status from Ctrl+Enter callback
    if st.session_state.get("render_status") == "success":
        st.toast("✅ Auto-rendered!", icon="✅")
        st.session_state.pop("render_status", None)
    elif st.session_state.get("render_status", "").startswith("fail:"):
        st.error(st.session_state["render_status"][5:])
        st.session_state.pop("render_status", None)

    # Determine which PDF to display
    pdf_display_path = st.session_state.get("current_pdf")
    if not pdf_display_path:
        potential = os.path.join(orchestrator.output_dir, f"{job_id}.pdf")
        if os.path.exists(potential):
            pdf_display_path = potential

    # Display PDF
    if pdf_display_path and os.path.exists(pdf_display_path):
        with open(pdf_display_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')

        pdf_iframe = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" style="height: 85vh;" type="application/pdf"></iframe>'
        st.markdown(pdf_iframe, unsafe_allow_html=True)
    else:
        st.info("No PDF yet. Click **Render PDF** in the sidebar or press **Ctrl+Enter**.")
