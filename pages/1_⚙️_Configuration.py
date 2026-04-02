import streamlit as st
import pandas as pd
import os
import sys

# Ensure root directory is on the path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from config_utils import load_config, load_companies, save_yaml_safely, clean_df_list, FILTERING_PATH, COMPANIES_PATH

# Set page config
st.set_page_config(page_title="Job Hunter - Configuration", layout="wide")

config = load_config()
companies_config = load_companies()

if not config and not companies_config:
    st.warning("No configuration found. Please check your config files.")

tabs = st.tabs(["🎯 General", "📝 Titles", "📍 Locations", "🛠️ Skills", "🏢 Companies"])

with tabs[0]: # General
    st.header("General Settings")
    if config:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Filtering", "Enabled" if config.get('filtering', {}).get('is_enabled', True) else "Disabled")
        with col2:
            st.metric("Max Age", f"{config.get('filtering', {}).get('max_days_old', 14)} Days")
        with col3:
            st.metric("Max Exp", f"{config.get('filtering', {}).get('max_years_experience', 2)} Years")
        
        with st.expander("System Specs"):
            st.json(config.get('system', {}))
    else:
        st.info("General settings not found in filtering.yaml")

with tabs[1]: # Titles
    st.header("Job Title Rules")
    if config:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🌟 High Priority")
            hp_titles = config.get('titles', {}).get('high_priority', [])
            df_hp = pd.DataFrame(hp_titles, columns=["Keyword"])
            ed_hp = st.data_editor(df_hp, num_rows="dynamic", width="stretch", hide_index=True, key="ed_hp")
        with col2:
            st.markdown("### 🚫 Skip Titles")
            ex_titles = config.get('titles', {}).get('exclude', [])
            df_ex = pd.DataFrame(ex_titles, columns=["Keyword"])
            ed_ex = st.data_editor(df_ex, num_rows="dynamic", width="stretch", hide_index=True, key="ed_ex")
            
        st.divider()
        st.markdown("### 🛑 Degree & Domain Blocklist")
        bl_titles = config.get('title_blocklist', [])
        df_bl = pd.DataFrame(bl_titles, columns=["Restricted Match"])
        ed_bl = st.data_editor(df_bl, num_rows="dynamic", width="stretch", hide_index=True, key="ed_bl")

        if st.button("💾 Save Title Rules", type="primary", width="stretch", key="save_titles"):
            if 'titles' not in config: config['titles'] = {}
            config['titles']['high_priority'] = clean_df_list(ed_hp, "Keyword")
            config['titles']['exclude'] = clean_df_list(ed_ex, "Keyword")
            config['title_blocklist'] = clean_df_list(ed_bl, "Restricted Match")
            if save_yaml_safely(config, FILTERING_PATH):
                st.success("Title rules updated!")
                st.rerun()

with tabs[2]: # Locations
    st.header("Location Preferences")
    if config:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### ✅ Include")
            inc_locs = config.get('locations', {}).get('include', [])
            df_loc_inc = pd.DataFrame(inc_locs, columns=["Region"])
            ed_loc_inc = st.data_editor(df_loc_inc, num_rows="dynamic", width="stretch", hide_index=True, key="ed_loc_inc")
        with col2:
            st.markdown("### 🚫 Exclude")
            ex_locs = config.get('locations', {}).get('exclude', [])
            df_loc_ex = pd.DataFrame(ex_locs, columns=["Region"])
            ed_loc_ex = st.data_editor(df_loc_ex, num_rows="dynamic", width="stretch", hide_index=True, key="ed_loc_ex")

        if st.button("💾 Save Location Rules", type="primary", width="stretch", key="save_locs"):
            if 'locations' not in config: config['locations'] = {}
            config['locations']['include'] = clean_df_list(ed_loc_inc, "Region")
            config['locations']['exclude'] = clean_df_list(ed_loc_ex, "Region")
            if save_yaml_safely(config, FILTERING_PATH):
                st.success("Location rules updated!")
                st.rerun()

with tabs[3]: # Skills
    st.header("Skill Weighting")
    if config:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 💎 Preferred")
            pref_skills = config.get('preferred_skills', [])
            df_sk_pref = pd.DataFrame(pref_skills, columns=["Skill"])
            ed_sk_pref = st.data_editor(df_sk_pref, num_rows="dynamic", width="stretch", hide_index=True, key="ed_sk_pref")
        with col2:
            st.markdown("### ⚠️ Penalty")
            pen_skills = config.get('penalty_skills', [])
            df_sk_pen = pd.DataFrame(pen_skills, columns=["Skill"])
            ed_sk_pen = st.data_editor(df_sk_pen, num_rows="dynamic", width="stretch", hide_index=True, key="ed_sk_pen")

        if st.button("💾 Save Skill Rules", type="primary", width="stretch", key="save_skills"):
            config['preferred_skills'] = clean_df_list(ed_sk_pref, "Skill")
            config['penalty_skills'] = clean_df_list(ed_sk_pen, "Skill")
            if save_yaml_safely(config, FILTERING_PATH):
                st.success("Skill rules updated!")
                st.rerun()

with tabs[4]: # Companies
    st.header("Company Management")
    if companies_config:
        st.markdown("### 🏢 Source Companies (ATS Targets)")
        all_cos = companies_config.get('companies', [])
        df_cos = pd.DataFrame(all_cos)
        ed_cos = st.data_editor(
            df_cos, 
            num_rows="dynamic", 
            width="stretch", 
            hide_index=True, 
            key="ed_companies",
            column_config={
                "ats": st.column_config.SelectboxColumn("ATS", options=["greenhouse", "lever", "ashby"], required=True)
            }
        )
        
        st.divider()
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("### 🎯 Target Filter")
            tar_cos = companies_config.get('target_companies', [])
            ed_tar = st.data_editor(pd.DataFrame(tar_cos, columns=["Company"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_tar_cos")
        with col_c2:
            st.markdown("### 🚫 Exclude Filter")
            exc_cos = companies_config.get('exclude_companies', [])
            ed_exc = st.data_editor(pd.DataFrame(exc_cos, columns=["Company"]), num_rows="dynamic", width="stretch", hide_index=True, key="ed_exc_cos")

        if st.button("💾 Save Company Management", type="primary", width="stretch", key="save_cos"):
            new_cos = ed_cos.dropna(subset=['name']).to_dict('records')
            companies_config['companies'] = [c for c in new_cos if str(c.get('name', '')).strip() != ""]
            companies_config['target_companies'] = clean_df_list(ed_tar, "Company")
            companies_config['exclude_companies'] = clean_df_list(ed_exc, "Company")
            
            if save_yaml_safely(companies_config, COMPANIES_PATH):
                st.success("Company configuration updated!")
                st.rerun()
    else:
        st.warning("`companies.yaml` not found or empty.")
