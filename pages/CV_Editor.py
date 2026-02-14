import streamlit as st
import base64
import os
import sys
import time

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
        padding-top: 0px !important;
        padding-left: 40px !important;
        padding-right: 40px !important;
        padding-bottom: 40px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. Navigation Guard ---
if "active_job" not in st.session_state or not st.session_state["active_job"]:
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

# --- 2. Initialize Orchestrator ---
orchestrator = CVOrchestrator()

# --- 3. Load State ---
if "editor_yaml" not in st.session_state:
    st.session_state["editor_yaml"] = orchestrator.load_job_cv(job_id)

# --- SIDEBAR: Job Info, Navigation, AI Tools ---
with st.sidebar:
    st.header(f"📝 {company}")
    st.caption(f"**Role**: {title}")
    st.caption(f"**ID**: `{job_id}`")

    st.divider()

    if st.button("⬅️ Back to Dashboard", use_container_width=True):
        st.switch_page("dashboard.py")

    st.divider()

    # AI Tailoring Tools
    st.subheader("🤖 AI Tailoring")
    if ai_tailor:
        st.write("Auto-update CV using DeepSeek R1.")
        if st.button("Auto-Tailor with AI", type="primary", use_container_width=True):
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

# --- MAIN CONTENT: Editor | Preview ---
col_edit, col_prev = st.columns([1, 1])

with col_edit:
    yaml_input = st.text_area(
        "YAML Editor",
        value=st.session_state["editor_yaml"],
        height=700,
        key="yaml_editor"
    )

    # Autosave on change
    if yaml_input != st.session_state["editor_yaml"]:
        st.session_state["editor_yaml"] = yaml_input
        orchestrator.save_job_cv(job_id, yaml_input)
        st.toast("💾 Autosaved.", icon="💾")

with col_prev:
    if st.button("🔄 Render PDF", type="primary", use_container_width=True):
        with st.spinner("Rendering via RenderCV..."):
            pdf_path, status = orchestrator.render_from_content(job_id, yaml_input)
            if pdf_path:
                st.session_state["current_pdf"] = pdf_path
                st.success("✅ Render Complete!")
            else:
                st.error(f"❌ Render Failed: {status}")

    # Determine which PDF to display
    display_path = st.session_state.get("current_pdf")
    if not display_path:
        potential_path = os.path.join(orchestrator.output_dir, f"{job_id}.pdf")
        if os.path.exists(potential_path):
            display_path = potential_path

    # Display PDF
    if display_path and os.path.exists(display_path):
        with open(display_path, "rb") as f:
            pdf_bytes = f.read()
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

        pdf_iframe = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700" type="application/pdf"></iframe>'
        st.markdown(pdf_iframe, unsafe_allow_html=True)

        st.download_button(
            "⬇️ Download PDF",
            pdf_bytes,
            file_name=f"{job_id}_CV.pdf",
            mime="application/pdf",
            key=f"dl_{job_id}_{time.time()}"
        )
    else:
        st.info("No PDF rendered yet. Click **Render PDF** to generate.")
