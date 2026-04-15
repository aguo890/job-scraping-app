import streamlit as st
import pandas as pd
import os
import sys
import yaml

# Ensure root directory is on the path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from utils.ui_utils import inject_custom_css
from config_utils import load_config, load_companies, save_yaml_safely, clean_df_list, FILTERING_PATH, COMPANIES_PATH

# Set page config
st.set_page_config(page_title="Job Hunter - Configuration", layout="wide")

# Global UI Inject (includes transparent toolbar)
inject_custom_css()

# Path to AI Config
AI_CONFIG_PATH = os.path.join(parent_dir, "config", "ai_config.yaml")

def load_ai_config():
    if os.path.exists(AI_CONFIG_PATH):
        try:
            with open(AI_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    return {}

config = load_config()
companies_config = load_companies()
ai_config = load_ai_config()

st.title("⚙️ Configuration")
st.markdown("Manage your job automation rules, AI prompts, and system preferences.")

tabs = st.tabs(["🕸️ Scraping Rules", "🧠 AI & Prompts", "🖥️ System Options", "🏢 Companies", "🛂 Restrictions", "🚨 Data Management"])

# --- TAB 1: SCRAPING RULES ---
with tabs[0]:
    with st.form("form_scraping_rules", border=False):
        st.subheader("🎯 Job Title & Keyword Filters")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🌟 High Priority")
            st.caption("Jobs matching these keywords will be prioritized and starred.")
            hp_titles = config.get('titles', {}).get('high_priority', [])
            df_hp = pd.DataFrame(hp_titles, columns=["Keyword"])
            ed_hp = st.data_editor(df_hp, num_rows="dynamic", width="stretch", hide_index=True, key="ed_hp_new")
        
        with col2:
            st.markdown("### 🚫 Skip Titles")
            st.caption("Jobs with these keywords in the title will be automatically excluded.")
            ex_titles = config.get('titles', {}).get('exclude', [])
            df_ex = pd.DataFrame(ex_titles, columns=["Keyword"])
            ed_ex = st.data_editor(df_ex, num_rows="dynamic", width="stretch", hide_index=True, key="ed_ex_new")
            
        with st.expander("🛠️ Advanced Skill & Content Filtering", expanded=True):
            # [AI CONTEXT: Tiered Skills Implementation]
            # Migration logic: If tiered_skills doesn't exist, use preferred_skills as Tier 1
            tiered = config.get('tiered_skills', {})
            t1_val = tiered.get('tier1', config.get('preferred_skills', []))
            t2_val = tiered.get('tier2', [])
            t3_val = tiered.get('tier3', [])

            st.markdown("### 💎 Tiered Skill Scoring")
            st.caption("Matched skills award jobs with specific points: Tier 1 (+10), Tier 2 (+20), Tier 3 (+50).")
            
            ts_c1, ts_c2, ts_c3 = st.columns(3)
            with ts_c1:
                st.markdown("##### 🧱 Tier 1 (Base)")
                ed_t1 = st.data_editor(pd.DataFrame(t1_val, columns=["Skill"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_t1")
            with ts_c2:
                st.markdown("##### 🚀 Tier 2 (Strong)")
                ed_t2 = st.data_editor(pd.DataFrame(t2_val, columns=["Skill"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_t2")
            with ts_c3:
                st.markdown("##### 🦄 Tier 3 (Niche)")
                ed_t3 = st.data_editor(pd.DataFrame(t3_val, columns=["Skill"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_t3")

            st.divider()
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.markdown("### ⚠️ Penalty Skills")
                pen_skills = config.get('penalty_skills', [])
                ed_sk_pen = st.data_editor(pd.DataFrame(pen_skills, columns=["Skill"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_sk_pen_new")
            with col_s2:
                st.markdown("### 🛑 Content Blocklist")
                st.caption("Exclude jobs containing these terms.")
                bl_titles = config.get('title_blocklist', [])
                ed_bl = st.data_editor(pd.DataFrame(bl_titles, columns=["Restricted Match"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_bl_new")





        st.subheader("📍 Location Preferences")
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            st.markdown("### ✅ Include")
            inc_locs = config.get('locations', {}).get('include', [])
            ed_loc_inc = st.data_editor(pd.DataFrame(inc_locs, columns=["Region"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_loc_inc_new")
        with col_l2:
            st.markdown("### 🚫 Exclude")
            ex_locs = config.get('locations', {}).get('exclude', [])
            ed_loc_ex = st.data_editor(pd.DataFrame(ex_locs, columns=["Region"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_loc_ex_new")

        if st.form_submit_button("💾 Save Scraping Rules", type="primary"):
            if 'titles' not in config: config['titles'] = {}
            config['titles']['high_priority'] = clean_df_list(ed_hp, "Keyword")
            config['titles']['exclude'] = clean_df_list(ed_ex, "Keyword")
            config['title_blocklist'] = clean_df_list(ed_bl, "Restricted Match")
            

            
            if 'locations' not in config: config['locations'] = {}
            config['locations']['include'] = clean_df_list(ed_loc_inc, "Region")
            config['locations']['exclude'] = clean_df_list(ed_loc_ex, "Region")
            
            config['tiered_skills'] = {
                'tier1': clean_df_list(ed_t1, "Skill"),
                'tier2': clean_df_list(ed_t2, "Skill"),
                'tier3': clean_df_list(ed_t3, "Skill")
            }
            if 'preferred_skills' in config:
                del config['preferred_skills']
            config['penalty_skills'] = clean_df_list(ed_sk_pen, "Skill")
            
            if save_yaml_safely(config, FILTERING_PATH):
                st.success("Scraping rules updated successfully!")
                st.rerun()



# --- TAB 2: AI & PROMPTS ---
with tabs[1]:
    with st.form("form_ai_settings", border=False):
        st.subheader("🔒 Authentication")
        st.info("API keys are stored in memory for this session and are never saved to disk.")
        
        # Load default from ENV, but allow user to override in session state
        default_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        current_key = st.session_state.get("session_api_key", default_key)
        
        new_api_key = st.text_input("API Key (DeepSeek or OpenAI)", value=current_key, type="password")
        
        st.subheader("🧠 Model & Prompts")
        ai_model = st.selectbox("Model", ["deepseek-reasoner", "deepseek-chat", "gpt-4o", "gpt-4o-mini"], 
                               index=0 if ai_config.get('model') == "deepseek-reasoner" else 2)
        
        base_prompt = st.text_area("Base Tailoring Prompt", 
                                  value=ai_config.get('base_prompt', "You are an expert resume writer..."),
                                  height=200)
        
        with st.expander("Advanced AI Parameters"):
            temp = st.slider("Temperature", 0.0, 1.0, float(ai_config.get('temperature', 0.7)), 0.1)
            max_tokens = st.number_input("Max Tokens", 100, 4000, int(ai_config.get('max_tokens', 2000)))

        if st.form_submit_button("💾 Save AI Settings", type="primary"):
            # 1. Securely store the API key in memory ONLY
            if new_api_key:
                st.session_state["session_api_key"] = new_api_key
            
            # 2. Safely write non-sensitive config to disk
            new_ai_config = {
                "model": ai_model,
                "base_prompt": base_prompt,
                "temperature": temp,
                "max_tokens": max_tokens
            }
            
            try:
                os.makedirs(os.path.dirname(AI_CONFIG_PATH), exist_ok=True)
                with open(AI_CONFIG_PATH, "w", encoding='utf-8') as file:
                    yaml.safe_dump(new_ai_config, file, default_flow_style=False)
                st.success("AI Session Key and Prompts updated successfully!")
            except Exception as e:
                st.error(f"Failed to save AI configuration: {e}")

    # --- Re-Import Resume (Outside Form — allows st.button) ---
    st.divider()
    st.subheader("📥 Re-Import Resume")
    st.caption(
        "Re-run the onboarding wizard to regenerate your Master CV and filtering "
        "config from a new resume using your own AI assistant."
    )
    if st.button("🔄 Launch Import Wizard", use_container_width=True):
        st.switch_page("pages/5_📥_Import_Resume.py")

# --- TAB 3: SYSTEM OPTIONS ---
with tabs[2]:
    with st.form("form_sys_settings", border=False):
        st.subheader("⚙️ System Performance")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            max_age = st.number_input("Max Job Age (Days)", 1, 90, int(config.get('filtering', {}).get('max_days_old', 14)))
            max_exp = st.number_input("Max Experience (Years)", 0, 20, int(config.get('filtering', {}).get('max_years_experience', 2)))
        with col_s2:
            concurrency = st.slider("Concurrency Limit", 1, 20, int(config.get('system', {}).get('concurrency_limit', 5)))
            timeout = st.slider("Request Timeout (Seconds)", 5, 60, int(config.get('system', {}).get('request_timeout', 15)))

        filter_enabled = st.toggle("Enable Filtering Logic", value=config.get('filtering', {}).get('is_enabled', True))
        
        with st.expander("🌐 Network & Browser"):
            env_ua = os.getenv("USER_AGENT")
            ua_value = env_ua or config.get('system', {}).get('user_agent', "")
            user_agent = st.text_input(
                "User Agent", 
                value=ua_value, 
                disabled=bool(env_ua),
                help="The identity string sent to job boards to mimic a real browser."
            )
            if env_ua:
                st.info("💡 **Environment Override Active:** The User Agent is locked because it's being set via your `.env` file.")
            else:
                st.caption("Change this only if you encounter frequent bot detection.")

        if st.form_submit_button("💾 Save System Settings", type="primary"):
            if 'filtering' not in config: config['filtering'] = {}
            config['filtering']['max_days_old'] = max_age
            config['filtering']['max_years_experience'] = max_exp
            config['filtering']['is_enabled'] = filter_enabled
            
            if 'system' not in config: config['system'] = {}
            config['system']['concurrency_limit'] = concurrency
            config['system']['request_timeout'] = timeout
            config['system']['user_agent'] = user_agent
            
            if save_yaml_safely(config, FILTERING_PATH):
                st.success("System options updated successfully!")
                st.rerun()

# --- TAB 4: COMPANIES ---
with tabs[3]:
    with st.form("form_companies", border=False):
        st.subheader("🏢 Company Management")
        st.caption("Manage titles and ATS targets for bulk scraping.")
        
        all_cos = companies_config.get('companies', [])
        df_cos = pd.DataFrame(all_cos)

        # Flatten enrichment status for easy indexing
        if 'enrichment' in df_cos.columns:
            df_cos['status_display'] = df_cos['enrichment'].apply(lambda x: x.get('status', 'pending') if isinstance(x, dict) else 'pending')
        else:
            df_cos['status_display'] = 'pending'

        # Filter UI (Replaces the split-brain logging)
        filter_status = st.radio(
            "Filter by Verification Status:", 
            ["All", "Verified", "Pending", "Error (Review Needed)"], 
            horizontal=True
        )

        display_df = df_cos
        if filter_status == "Verified":
            display_df = display_df[display_df['status_display'] == 'verified']
        elif filter_status == "Pending":
            display_df = display_df[display_df['status_display'] == 'pending']
        elif filter_status == "Error (Review Needed)":
            display_df = display_df[display_df['status_display'] == 'error']

        ed_cos = st.data_editor(
            display_df, 
            num_rows="dynamic", 
            width="stretch", 
            hide_index=True, 
            key="ed_companies_new",
            column_config={
                "ats": st.column_config.SelectboxColumn("ATS", options=["greenhouse", "lever", "ashby"], required=True),
                "board_token": st.column_config.TextColumn("Token", help="ATS Board Token"),
                "job_board_url": st.column_config.LinkColumn("UI Link", help="Human-readable job board link"),
                "careers_page": st.column_config.LinkColumn("Careers Page", help="Official company careers page"),
                "status_display": st.column_config.TextColumn("Status", disabled=True, help="Automation verification status")
            }
        )
        
        st.divider()
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("### 🎯 Target Filter")
            tar_cos = companies_config.get('target_companies', [])
            ed_tar = st.data_editor(pd.DataFrame(tar_cos, columns=["Company"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_tar_cos_new")
        with col_c2:
            st.markdown("### 🚫 Exclude Filter")
            exc_cos = companies_config.get('exclude_companies', [])
            ed_exc = st.data_editor(pd.DataFrame(exc_cos, columns=["Company"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_exc_cos_new")

        if st.form_submit_button("💾 Save Company Management", type="primary"):
            # Drop the calculated column before saving
            new_cos = ed_cos.dropna(subset=['name'])
            if 'status_display' in new_cos.columns:
                new_cos = new_cos.drop(columns=['status_display'])
            
            records = new_cos.to_dict('records')
            companies_config['companies'] = [c for c in records if str(c.get('name', '')).strip() != ""]
            companies_config['target_companies'] = clean_df_list(ed_tar, "Company")
            companies_config['exclude_companies'] = clean_df_list(ed_exc, "Company")
            
            if save_yaml_safely(companies_config, COMPANIES_PATH):
                st.success("Company configuration updated!")
                st.rerun()
                st.success("Company configuration updated!")
                st.rerun()

# --- TAB 5: RESTRICTIONS ---
with tabs[4]:
    with st.form("form_restrictions", border=False):
        st.subheader("🛂 Security & Visa Restrictions")
        st.caption("Identify jobs requiring specific citizenships or clearances.")
        
        re_cfg = config.get('restrictions', {})
        re_enabled = st.toggle("Enable Visa/Clearance Filtering", value=re_cfg.get('enabled', True))
        
        st.subheader("🛂 Quick Filters")
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            needs_sponsorship = st.toggle("Exclude jobs with NO Visa Sponsorship", 
                                          value=re_cfg.get('needs_sponsorship', False),
                                          help="Automatically excludes jobs containing phrases like 'no sponsorship' or 'h1-b not available'")
        with col_q2:
            no_clearance = st.toggle("Exclude jobs requiring Security Clearance", 
                                     value=re_cfg.get('no_clearance', False),
                                     help="Automatically excludes jobs requiring 'TS/SCI', 'Polygraph', or 'US Citizen'")

        with st.expander("🛠️ Advanced: Custom Keywords", expanded=True):
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                st.markdown("### 🔴 Red Flags (Restricted)")
                st.caption("Custom terms that trigger a restriction.")
                re_keywords = re_cfg.get('keywords', [])
                df_re = pd.DataFrame(re_keywords, columns=["Restricted Keyword"])
                ed_re_dedicated = st.data_editor(df_re, num_rows="dynamic", width="stretch", hide_index=True, key="ed_re_dedicated")
            
            with col_k2:
                st.markdown("### 🟢 Green Flags (Friendly)")
                st.caption("Custom terms that trigger a 'Friendly' status.")
                fr_keywords = re_cfg.get('mobility_friendly', [])
                df_fr = pd.DataFrame(fr_keywords, columns=["Friendly Keyword"])
                ed_fr_dedicated = st.data_editor(df_fr, num_rows="dynamic", width="stretch", hide_index=True, key="ed_fr_dedicated")

        if st.form_submit_button("💾 Save Restrictions", type="primary"):
            config['restrictions'] = {
                'enabled': re_enabled,
                'needs_sponsorship': needs_sponsorship,
                'no_clearance': no_clearance,
                'keywords': clean_df_list(ed_re_dedicated, "Restricted Keyword"),
                'mobility_friendly': clean_df_list(ed_fr_dedicated, "Friendly Keyword")
            }
            if save_yaml_safely(config, FILTERING_PATH):
                st.success("Restrictions updated successfully!")
                st.rerun()

    # --- Live Sandbox (Outside Form to allow st.button) ---
    st.divider()
    with st.expander("🧪 Test Restriction Logic (Sandbox)", expanded=False):
        st.caption("Paste a job description below to see if your *saved* configuration would flag it.")
        test_desc = st.text_area("Job Description to Test", height=150, key="re_test_sandbox_dedicated")
        if st.button("🔍 Run Analysis", width="stretch"):
            if test_desc:
                from utils.smart_filter import RestrictionEngine
                # Create engine with CURRENT session state values for immediate testing
                current_re_config = {
                    'enabled': re_enabled,
                    'needs_sponsorship': needs_sponsorship,
                    'no_clearance': no_clearance,
                    'keywords': clean_df_list(ed_re_dedicated, "Restricted Keyword"),
                    'mobility_friendly': clean_df_list(ed_fr_dedicated, "Friendly Keyword")
                }
                temp_engine = RestrictionEngine(current_re_config)
                res = temp_engine.analyze(test_desc)
                if res['mobility_status'] == 'RESTRICTED':
                    st.error(f"🚫 **Restricted:** {res['reason']}")
                elif res['mobility_status'] == 'FRIENDLY':
                    st.success(f"🟢 **Friendly:** {res['reason']}")
                else:
                    st.info("🟡 **Neutral:** No status markers found.")
            else:
                st.warning("Please paste a description to test.")

# --- TAB 6: DATA MANAGEMENT ---
with tabs[5]:
    st.subheader("🚨 Danger Zone")
    st.warning("These operations act on your raw data files. Proceed with caution.", icon="⚠️")
    
    with st.container(border=True):
        col_dm1, col_dm2 = st.columns([3, 1], vertical_alignment="center")
        with col_dm1:
            st.markdown("### Erase Stale Scraping History")
            st.caption("Clears all scraped jobs from `jobs_agg.json` so you can start a fresh search with new configuration parameters. Your `tracking.json` (applied/saved statuses) and generated resumes will REMAIN safe.")
        with col_dm2:
            import json
            if st.button("🗑️ Reset All Data", type="primary", use_container_width=True):
                submodule_file = os.path.join(parent_dir, "data", "jobs_agg.json")
                root_file = os.path.join(parent_dir, "..", "data", "jobs_agg.json")
                tracking_file = os.path.join(parent_dir, "..", "data", "tracking.json")
                if not os.path.exists(tracking_file):
                    tracking_file = os.path.join(parent_dir, "data", "tracking.json")
                
                try:
                    # 1. Load tracking data to know what to preserve
                    tracked_ids = set()
                    if os.path.exists(tracking_file):
                        with open(tracking_file, "r", encoding="utf-8") as f:
                            try:
                                tracking_data = json.load(f)
                                for jid, tdata in tracking_data.items():
                                    if tdata.get("saved", False) or tdata.get("status", "New") != "New":
                                        tracked_ids.add(jid)
                            except json.JSONDecodeError:
                                pass

                    # 2. Sweep jobs_agg.json files and preserve tracked jobs
                    cleared_any = False
                    for file_path in [submodule_file, root_file]:
                        if os.path.exists(file_path):
                            preserved_jobs = []
                            with open(file_path, "r", encoding="utf-8") as f:
                                try:
                                    current_data = json.load(f)
                                    all_jobs = current_data.get("jobs", [])
                                    preserved_jobs = [job for job in all_jobs if job.get("id") in tracked_ids]
                                except json.JSONDecodeError:
                                    pass
                                    
                            with open(file_path, "w", encoding="utf-8") as f:
                                json.dump({"jobs": preserved_jobs, "total_jobs": len(preserved_jobs), "generated_at": "Unknown"}, f)
                            cleared_any = True
                            
                    if cleared_any:
                        st.cache_data.clear()
                        st.success(f"Scraping history cleared successfully! {len(tracked_ids)} tracked/saved jobs were preserved.")
                    else:
                        st.info("No scraping history found to clear.")
                except Exception as e:
                    st.error(f"Failed to clear data: {e}")
