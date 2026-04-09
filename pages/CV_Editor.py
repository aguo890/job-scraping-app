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
import streamlit.components.v1 as components

def show_premium_toast(message="Render Complete", duration_ms=2000):
    # AI-CONTEXT: Custom toast implementation bypassing st.toast to avoid React state conflicts.
    # Uses a self-destructing HTML/JS payload for precise timing and CSS isolation.
    # We use window.parent.document to ensure the toast renders over the main Streamlit app.
    # Includes cleanup logic to prevent overlapping/bloated toasts in rapid rendering scenarios.
    
    toast_html = f"""
    <script>
        (function() {{
            const doc = window.parent.document;
            const toastId = 'custom-premium-toast';
            
            // Cleanup: Destroy the old toast instantly if it exists
            const existingToast = doc.getElementById(toastId);
            if (existingToast) {{
                existingToast.remove();
            }}
            
            // Create the new toast container
            const toast = doc.createElement('div');
            toast.id = toastId;
            toast.innerText = "{message}";
            
            // Apply Premium Glassmorphic CSS directly
            Object.assign(toast.style, {{
                position: 'fixed',
                bottom: '24px',
                right: '24px',
                background: 'rgba(46, 204, 113, 0.85)',
                backdropFilter: 'blur(8px)',
                WebkitBackdropFilter: 'blur(8px)',
                color: 'white',
                padding: '12px 24px',
                borderRadius: '8px',
                fontFamily: 'sans-serif',
                fontWeight: '500',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                zIndex: '999999',
                transition: 'opacity 0.4s ease, transform 0.4s ease',
                opacity: '0',
                transform: 'translateY(20px)'
            }});
            
            doc.body.appendChild(toast);
            
            // Trigger entry animation
            setTimeout(() => {{
                if (doc.getElementById(toastId) === toast) {{
                    toast.style.opacity = '1';
                    toast.style.transform = 'translateY(0)';
                }}
            }}, 50);
            
            // Trigger exit animation and complete DOM removal
            setTimeout(() => {{
                if (doc.getElementById(toastId) === toast) {{
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateY(20px)';
                    setTimeout(() => toast.remove(), 400); 
                }}
            }}, {duration_ms});
        }})();
    </script>
    """
    components.html(toast_html, height=0, width=0)

from utils.ui_utils import inject_custom_css

try:
    from cv_bridge import CVOrchestrator
except ImportError:
    CVOrchestrator = None

try:
    import ai_tailor
except ImportError:
    ai_tailor = None

# AI-CONTEXT: Native Streamlit Modal (Lightbox) for Full-Screen PDF viewing.
# Using width="large" ensures it takes up maximum screen real estate.
# This function is defined at the TOP of the file to ensure it's in memory 
# before any layout blocks (sidebar/main) try to call it.
@st.dialog(" ", width="large")
def show_fullscreen_preview(pdf_bytes):
    # AI-CONTEXT: Custom close button removed. Relying on native dialog 'X' header.
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # AI-CONTEXT: Iframe height bumped to 85vh to maximize space.
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="85vh" style="border-radius: 8px; border: none;" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)



st.set_page_config(page_title="CV Editor", layout="wide")

# Workshop-Specific CSS
workshop_css = """
.stMain {
    min-height: 100vh !important;
}

/* Workshop-specific container overrides */
.stMainBlockContainer {
    padding-bottom: 0rem !important;
    max-width: 100% !important;
}

/* AI-CONTEXT: Force Streamlit dialogs (modals) to act as true full-screen lightboxes. */
/* This MUST be applied globally to override React's pre-calculated boundaries on load. */
div[role="dialog"] {
    width: 95vw !important;
    max-width: 95vw !important;
    height: 95vh !important;
    max-height: 95vh !important;
}

/* AI-CONTEXT: The Ultimate Hammer. */
div[role="dialog"] iframe {
    height: 85vh !important;
    min-height: 85vh !important;
}

/* AI-CONTEXT: The stDialogHeader hiding rule was REMOVED here to restore 
   the native 'X' close button in the top right corner. */

/* AI-CONTEXT: Lock the internal dialog scroll to prevent ugly double-scrollbars */
div[role="dialog"] [data-testid="stDialogContent"] {
    overflow: hidden !important;
    padding-bottom: 0px !important;
}

/* Zero out inner padding to ensure 100% content occupancy */
div[role="dialog"] > div > div {
    padding: 0 !important;
}

/* AI-CONTEXT: Hide the specific title text (h2) while keeping the header visible 
   to preserve the native 'X' close button. */
div[role="dialog"] [data-testid="stDialogHeader"] h2 {
    display: none !important;
}

/* [AI CONTEXT: Fix Segmented Control text blocking click events. 
   Forces the mouse to ignore the text spans and pass the click to the background radio label.
   Scoped specifically via data-testid to prevent breaking text selection globally.] */
/* [AI CONFLICT RESOLUTION: Issue #15 Fix - Reliable Toggle Clickability] */
div[data-testid="stSegmentedControl"] [role="radiogroup"] {
    gap: 0 !important;
}

div[data-testid="stSegmentedControl"] label {
    cursor: pointer !important;
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 8px 16px !important;
    z-index: 10 !important;
}

div[data-testid="stSegmentedControl"] label p {
    pointer-events: none !important;
    width: 100% !important;
    text-align: center !important;
}

/* [AI CONTEXT: Fix Code Editor custom buttons text/icons blocking click events. 
   Ensures clicks on the "Save & Render" text or Play icon are captured by the button container.] */
.code_editor-buttons-container button * {
    pointer-events: none !important;
}
"""

# Global UI Inject (includes transparent toolbar + workshop styles)
inject_custom_css(workshop_css)

# --- User Preferences Persistence ---
def get_prefs_path():
    return os.path.join(parent_dir, "data", "user_prefs.json")

def load_user_prefs():
    prefs_file = get_prefs_path()
    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_user_pref(key, value):
    prefs_file = get_prefs_path()
    prefs = load_user_prefs()
    prefs[key] = value
    try:
        with open(prefs_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=4)
    except Exception as e:
        st.error(f"Failed to save preference: {e}")

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

# [AI CONTEXT: Dynamic Naming Fix #17]
def get_user_name_from_yaml(yaml_content):
    """Safely extracts name from RenderCV YAML for generic filename generation."""
    try:
        import yaml as pyyaml
        data = pyyaml.safe_load(yaml_content)
        name = data.get("cv", {}).get("name", "User")
        return name
    except Exception:
        return "User"

# Ensure editor_yaml is loaded if it's missing (e.g. first run)
if "editor_yaml" not in st.session_state:
    st.session_state["editor_yaml"] = orchestrator.load_job_cv(job_id)

if "is_rendering" not in st.session_state:
    st.session_state["is_rendering"] = False

if st.session_state.pop("render_success_toast", False):
    show_premium_toast("✅ Render Complete! 📄", 2000)

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

    # --- Workspaces (Corrected Navigation) ---
    st.header("🛠️ Workspaces")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        if st.button("🛠️ Master CV", use_container_width=True, help="Edit Master Template", key="editor_nav_master"):
            st.query_params.update({"job_id": "master_cv"})
            st.session_state["active_job"] = SPECIAL_ROUTING_JOBS["master_cv"]
            st.rerun()
    with col_w2:
        if st.button("🧪 Playground", use_container_width=True, help="Scratch Pad", key="editor_nav_playground"):
            st.query_params.update({"job_id": "playground"})
            st.session_state["active_job"] = SPECIAL_ROUTING_JOBS["playground"]
            st.rerun()

    st.divider()

    # --- ⚙️ Workspace Layout Settings ---
    st.subheader("⚙️ Settings")
    
    # AI-CONTEXT: Callback to save preference to disk immediately on change.
    # This survives page navigation, hard reloads, and server restarts.
    def sync_layout_to_disk():
        save_user_pref("workspace_layout", st.session_state["workspace_layout"])

    # AI-CONTEXT: Initialize from the JSON file on first load.
    if "workspace_layout" not in st.session_state:
        prefs = load_user_prefs()
        default_layout = prefs.get("workspace_layout", "Tabbed")

        # [AI CONTEXT: Gracefully migrate legacy "Side-by-Side" preferences to prevent StreamlitAPIException 
        # when initializing the updated radio button options.]
        if default_layout == "Side-by-Side":
            default_layout = "Tabbed"

        st.session_state["workspace_layout"] = default_layout
    
    st.radio(
        "View Mode", 
        ["Stacked", "Tabbed"], 
        key="workspace_layout", 
        horizontal=True,
        on_change=sync_layout_to_disk
    )

    st.divider()

    # Render button
    st.info("💡 **To Render PDF**, please use the **Save & Render** button inside the editor window or press `Cmd/Ctrl + Enter`.")

    # --- 📄 Draft Management ---
    st.divider()
    save_cols = st.columns([1, 1])
    with save_cols[0]:
        if st.button("💾 Save Draft", help="Persist changes to disk draft file", width="stretch"):
            content_to_save = st.session_state.get("yaml_editor", "")
            if save_draft_to_disk(job_id, content_to_save):
                st.toast("Draft saved to disk! 📦")
    with save_cols[1]:
        st.caption(f"Last Sync: {datetime.now().strftime('%H:%M:%S')}")

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
        # [AI CONTEXT: Dynamic Naming Fix #17]
        user_name = get_user_name_from_yaml(st.session_state["editor_yaml"])
        clean_name = re.sub(r'[^a-zA-Z0-9]+', '_', user_name).strip('_')
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        nice_filename = f"{clean_name}_{clean_title}_{clean_company}_{today_str}.pdf"
        mtime = int(os.path.getmtime(display_path))
        
        with open(display_path, "rb") as f:
            pdf_data = f.read()

        # --- Sidebar PDF Toolbar ---
        pdf_cols = st.columns([1, 1])
        with pdf_cols[0]:
            st.download_button(
                "⏳ Rendering..." if st.session_state["is_rendering"] else "⬇️ Download",
                data=pdf_data,
                file_name=nice_filename,
                mime="application/pdf",
                use_container_width=True,
                key=f"dl_{job_id}_{mtime}",
                disabled=st.session_state["is_rendering"]
            )
        with pdf_cols[1]:
            if st.button("🔍 Full Screen", use_container_width=True, disabled=st.session_state["is_rendering"]):
                show_fullscreen_preview(pdf_data)

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
            with st.expander("📊 AI Strategy & Gaps"):
                st.markdown(st.session_state["ai_strategy"])
                
                if "gap_analysis" in st.session_state and st.session_state["gap_analysis"]:
                    st.divider()
                    st.markdown("### ⚠️ Gap Analysis")
                    st.warning(st.session_state["gap_analysis"])
                    
                if "ai_reasoning" in st.session_state and st.session_state["ai_reasoning"]:
                    st.divider()
                    st.markdown("### 💭 Reasoning")
                    st.caption(st.session_state["ai_reasoning"])
    else:
        st.warning("AI module not available.")# --- 4. Modular UI Components ---
def render_editor_workspace(job_id, company, title, is_master, is_playground):
    """
    AI-CONTEXT: Encapsulates the CV editor and toolbar. 
    Arguments passed explicitly to avoid scope isolation issues in modular layouts.
    """

    # --- The Buffered Editor ---
    with st.container(border=True):
        if "yaml_editor" not in st.session_state:
            st.session_state["yaml_editor"] = st.session_state["editor_yaml"]

        # [AI CONTEXT: Replaced native st.text_area with streamlit_code_editor for robust YAML editing. 
        # State is only updated when the explicit "Save" button is clicked (type == "submit") to prevent unnecessary re-renders.]
        from code_editor import code_editor

        # [AI CONTEXT: Added native Ace editor keybinds (Cmd+Enter/Ctrl+Enter) to trigger the submit action,
        # bypassing the need for fragile global JS listeners. Updated semantics to "Save & Render".]
        custom_btns = [{
            "name": "Save & Render", 
            "feather": "Play",
            "hasText": True,
            "alwaysOn": True,
            "commands": ["submit"],
            "style": {"bottom": "0.44rem", "right": "0.4rem"},
            "bindKey": {"win": "Ctrl-Enter", "mac": "Command-Enter"}
        }]

        # [AI CONTEXT: Added a permanent explicit key so we can intercept the editor's memory payload 
        # during view toggles before Streamlit garbage collects unmounted components.]
        editor_dict = code_editor(
            st.session_state["yaml_editor"], 
            lang="yaml", 
            height=[40, 50], 
            buttons=custom_btns,
            response_mode="blur",
            key=f"cv_code_editor_{job_id}"
        )

        # [AI CONTEXT: Decouple live text tracking from the submit hook so the dirty-state modal 
        # accurately detects unsaved changes when the user clicks the segmented control toggle.]
        
        # 1. ALWAYS capture the live text from the editor if it exists, regardless of submit state.
        # This ensures Python knows about unsaved keystrokes when the segmented control reruns the app.
        if editor_dict.get('text'):
            st.session_state["yaml_editor"] = editor_dict['text']
            st.session_state[f"buffer_{job_id}"] = editor_dict['text']

        # 2. ONLY lock the compile hash and trigger a hard rerun if they explicitly hit Save & Render
        if editor_dict.get('text') and editor_dict.get('type') == "submit":
            st.session_state[f"last_compiled_{job_id}"] = editor_dict['text']
            st.session_state["is_rendering"] = True
            st.rerun()




def render_pdf_preview(job_id, company, title):
    """
    AI-CONTEXT: Encapsulates the PDF visualization and download icon toolbar.
    Includes cache-busting logic and native lightbox integration.
    """
    display_path = st.session_state.get("current_pdf")
    if not display_path:
        potential = os.path.join(orchestrator.output_dir, f"{job_id}.pdf")
        if os.path.exists(potential):
            display_path = potential

    if display_path and os.path.exists(display_path):
        with st.container(border=True):
            # Inline PDF Preview (Match Editor Height: 85vh)
            # AI-CONTEXT: Pure Zen workspace. No buttons in the main content area.
            # Iframe restored to 85vh to perfectly match the editor column.
            update_time = st.session_state.get("pdf_update_time", 0)
            with open(display_path, "rb") as f:
                pdf_bytes = f.read()
                base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_iframe = f'<iframe id="pdf-preview-{update_time}" src="data:application/pdf;base64,{base64_pdf}" width="100%" style="height: 85vh; border-radius: 8px;" type="application/pdf"></iframe>'
            st.markdown(pdf_iframe, unsafe_allow_html=True)
    else:
        with st.container(border=True):
             st.info("Click **Render PDF** to generate the document.")

# --- Restriction Warning ---
res_data = job.get("restriction_data", {})
if isinstance(res_data, dict) and res_data.get("restricted"):
    st.error(f"🚫 **ITAR/Clearance Warning:** {res_data.get('reason')}. Ensure eligibility before tailoring.", icon="🚫")

if "render_error" in st.session_state and st.session_state["render_error"]:
    st.error(st.session_state["render_error"])

# --- 4.5. Render Compilation Logic ---
if st.session_state.get("is_rendering", False):
    with st.spinner("Compiling with RenderCV..."):
        content = st.session_state["yaml_editor"]
        # 1. Save current buffer to disk
        save_result = orchestrator.save_job_cv(job_id, content)
        if isinstance(save_result, dict) and not save_result.get("success", True):
            st.session_state["render_error"] = f"❌ Save Failed: {save_result.get('error', 'Unknown error')}"
        else:
            # 2. Render from content
            pdf_path, status = orchestrator.render_from_content(job_id, content)
            if pdf_path:
                st.session_state["current_pdf"] = pdf_path
                st.session_state["render_success_toast"] = True
                # AI-CONTEXT: Cache-buster update to force UI refresh of the PDF iframe.
                st.session_state["pdf_update_time"] = time.time()
                
                # Clear previous render error
                if "render_error" in st.session_state:
                    del st.session_state["render_error"]
                    
                # Auto-switch to preview mode
                if st.session_state.get("workspace_layout") != "Stacked":
                    st.session_state["workspace_view_mode"] = "👁️ Rendered Preview"
            else:
                st.session_state["render_error"] = f"❌ Render Failed: {status}"
        
        st.session_state["is_rendering"] = False
        st.rerun()

# --- 5. Workspace Execution ---
layout = st.session_state.get("workspace_layout", "Stacked")

# Pass arguments explicitly for scope safety
if layout == "Stacked":
    render_editor_workspace(job_id, company, title, is_master, is_playground)
    st.divider()
    with st.expander("📄 PDF Preview & Download", expanded=True):
        render_pdf_preview(job_id, company, title)
else:
    # [AI CONTEXT: Fake Tabs (State-Controlled Layout)]
    # We use st.segmented_control to impersonate tabs. Clicking this natively triggers a Python rerun.
    
    current_view = st.session_state.get("workspace_view_mode", "📝 Code Editor")
    
    view_mode = st.segmented_control(
        "Workspace View Toggle",
        ["📝 Code Editor", "👁️ Rendered Preview"],
        default=current_view,
        label_visibility="collapsed"
    )
    
    # Sync widget state with session
    if view_mode:
        st.session_state["workspace_view_mode"] = view_mode
    else:
        view_mode = current_view

    if view_mode == "📝 Code Editor":
        # Always reset the ignore flag when they go back to the editor
        st.session_state[f"ignore_dirty_{job_id}"] = False
        render_editor_workspace(job_id, company, title, is_master, is_playground)
        
    elif view_mode == "👁️ Rendered Preview":
        
        # [AI CONTEXT: GARBAGE COLLECTION RESCUE]
        # Because the code_editor component isn't rendered in this block, Streamlit will wipe its data
        # at the end of this run. We must securely extract the unsaved text from memory first so our
        # dirty-state modal can accurately evaluate the delta.
        editor_memory_key = f"cv_code_editor_{job_id}"
        if editor_memory_key in st.session_state:
            ghost_payload = st.session_state[editor_memory_key]
            if isinstance(ghost_payload, dict) and ghost_payload.get("text"):
                # Rescue the unsaved keystrokes into our permanent buffers
                st.session_state["yaml_editor"] = ghost_payload["text"]
                st.session_state[f"buffer_{job_id}"] = ghost_payload["text"]

        current_yaml = st.session_state.get(f"buffer_{job_id}", "")
        
        # 2. INITIALIZE TRACKER ON FIRST LOAD
        if f"last_compiled_{job_id}" not in st.session_state:
            st.session_state[f"last_compiled_{job_id}"] = current_yaml
            
        last_compiled = st.session_state[f"last_compiled_{job_id}"]

        # 3. ROBUST TEXT NORMALIZATION (Ignores hidden line-ending differences)
        def clean_text(text):
            return text.strip().replace('\r\n', '\n') if isinstance(text, str) else ""

        is_dirty = clean_text(current_yaml) != clean_text(last_compiled)

        # 4. Auto-Compile on Tab Switch (Fix for Issue #8)
        if is_dirty:
            st.session_state[f"last_compiled_{job_id}"] = current_yaml
            st.session_state["is_rendering"] = True
            st.rerun()
            
        else:
            # State is clean
            render_pdf_preview(job_id, company, title)
