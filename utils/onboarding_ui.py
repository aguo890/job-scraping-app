"""
Shared UI logic for the Bring Your Own Agent (BYOA) Onboarding Wizard.

This module provides a reusable wizard component that can be rendered as:
1. A modal/dialog (on the Dashboard for new users).
2. A standalone page (manually triggered from the sidebar or settings).
"""
import streamlit as st
import os
from pathlib import Path
from onboarding_prompts import (
    CV_GENERATION_PROMPT, FILTERING_GENERATION_PROMPT,
    CV_PROMPT_INSTRUCTIONS, FILTERING_PROMPT_INSTRUCTIONS
)
from core.llm_sanitizer import (
    validate_cv_yaml, validate_filtering_yaml,
    merge_filtering_with_defaults, sanitize_llm_payload
)

from config_utils import save_yaml_safely, FILTERING_PATH, save_user_pref

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def render_wizard_ui(is_standalone=False):
    """
    Renders the BYOA Onboarding Wizard UI.
    
    Args:
        is_standalone (bool): If True, renders as a full page. If False, optimized for dialog.
    """
    if is_standalone:
        st.header("📥 Resume Import Wizard")
        st.markdown(
            "Regenerate your Master CV and filtering preferences using your own AI assistant. "
            "Follow the steps below to get set up."
        )
    else:
        st.markdown(
            "Set up your personalized job search in minutes. "
            "Use **your own AI** (ChatGPT, Claude, Gemini) to convert your resume — "
            "no API keys needed."
        )

    # --- Initialize session state for wizard ---
    if "onboarding_step" not in st.session_state:
        st.session_state.onboarding_step = 1

    step = st.session_state.onboarding_step

    # =====================================================
    # STEP 1: Prompt Hand-off (Copy to Clipboard)
    # =====================================================
    if step == 1:
        st.subheader("📋 Step 1: Copy Prompts to Your AI")

        prompt_tab_cv, prompt_tab_filter = st.tabs(["📄 Master CV Prompt", "⚙️ Filtering Config Prompt"])

        with prompt_tab_cv:
            st.markdown(CV_PROMPT_INSTRUCTIONS)
            st.code(CV_GENERATION_PROMPT, language="text")

        with prompt_tab_filter:
            st.markdown(FILTERING_PROMPT_INSTRUCTIONS)
            st.code(FILTERING_GENERATION_PROMPT, language="text")

        st.info("💡 **Tip:** Use the same AI chat session for both prompts — it will remember your resume context.", icon="💡")

        col_next, col_skip, col_dismiss = st.columns([2, 1, 1])
        with col_next:
            if st.button("✅ Generated Both → Next", type="primary", use_container_width=True):
                st.session_state.onboarding_step = 2
                st.rerun()
        with col_skip:
            if st.button("⏭️ Skip for Now", use_container_width=True, help="Hide for this session"):
                st.session_state.pop("force_onboarding", None)
                st.session_state.pop("onboarding_step", None)
                st.rerun() # Refresh to clear modal
        with col_dismiss:
            if st.button("🚫 Dismiss Forever", use_container_width=True, help="Never show this prompt again"):
                save_user_pref("show_onboarding", False)
                st.session_state["show_onboarding"] = False
                st.session_state.pop("force_onboarding", None)
                st.session_state.pop("onboarding_step", None)
                st.rerun() 

    # =====================================================
    # STEP 2: Paste Zone + Validate & Save
    # =====================================================
    elif step == 2:
        st.subheader("📥 Step 2: Paste & Save")

        cv_input = st.text_area(
            "Paste your **Master CV YAML** here",
            height=300,
            placeholder="Paste the YAML your AI generated for your resume...",
            key="onboarding_cv_input"
        )

        filtering_input = st.text_area(
            "Paste your **Filtering Config YAML** here",
            height=200,
            placeholder="Paste the YAML your AI generated for your job search config...",
            key="onboarding_filter_input"
        )

        col_save, col_back = st.columns([3, 1])

        with col_back:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.onboarding_step = 1
                st.rerun()

        with col_save:
            if st.button("💾 Validate & Save", type="primary", use_container_width=True):
                has_error = False

                # --- Validate CV YAML ---
                if not cv_input or not cv_input.strip():
                    st.error("❌ **Master CV** field is empty. Paste the YAML from your AI.")
                    has_error = True
                else:
                    cv_valid, cv_data, cv_err = validate_cv_yaml(cv_input)
                    if not cv_valid:
                        st.error(f"❌ **Master CV Error:** {cv_err}")
                        has_error = True

                # --- Validate Filtering YAML ---
                if not filtering_input or not filtering_input.strip():
                    st.error("❌ **Filtering Config** field is empty. Paste the YAML from your AI.")
                    has_error = True
                else:
                    filter_valid, filter_data, filter_err = validate_filtering_yaml(filtering_input)
                    if not filter_valid:
                        st.error(f"❌ **Filtering Config Error:** {filter_err}")
                        has_error = True

                if not has_error:
                    # --- Save CV YAML ---
                    try:
                        clean_cv = sanitize_llm_payload(cv_input)

                        # Always overwrite Master_CV.yaml — this replaces the
                        # default template with the user's actual resume.
                        cv_dir = Path(BASE_DIR).resolve().parent / "rendercv"
                        cv_dir.mkdir(parents=True, exist_ok=True)
                        cv_path = cv_dir / "Master_CV.yaml"

                        cv_path.write_text(clean_cv, encoding="utf-8")

                        st.success("✅ Master CV saved as `Master_CV.yaml`")
                    except Exception as e:
                        st.error(f"❌ Failed to save Master CV: {e}")
                        has_error = True

                    # --- Save Filtering Config ---
                    if not has_error:
                        try:
                            defaults_path = os.path.join(BASE_DIR, "config", "filtering.yaml.example")

                            merged_config = merge_filtering_with_defaults(filter_data, defaults_path)

                            if save_yaml_safely(merged_config, FILTERING_PATH):
                                st.success("✅ Filtering config saved and merged with defaults!")
                            else:
                                has_error = True
                        except Exception as e:
                            st.error(f"❌ Failed to save filtering config: {e}")
                            has_error = True

                    if not has_error:
                        st.balloons()
                        save_user_pref("show_onboarding", False)
                        # Ensure we also update session_state if it's referenced anywhere locally
                        st.session_state["show_onboarding"] = False
                        st.session_state.pop("force_onboarding", None)
                        st.session_state.pop("onboarding_step", None)
                        import time
                        time.sleep(1.5)
                        st.switch_page("pages/2_🚀_Scraper.py")
