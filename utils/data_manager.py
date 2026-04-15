import streamlit as st
import pandas as pd
import json
import logging
import os
import time
from pathlib import Path
from datetime import datetime
import random
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base path relative to this file (job-scraping-app/utils/data_manager.py)
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

# SRE Logic: Check root directory first, then fallback to submodule data directory
ROOT_DATA_DIR = ROOT_DIR / "data"
DATA_DIR = ROOT_DATA_DIR if ROOT_DATA_DIR.exists() else (BASE_DIR / "data")

JOB_DATA_FILE = DATA_DIR / "jobs_agg.json"
TRACKING_FILE = DATA_DIR / "tracking.json"
HISTORY_FILE = DATA_DIR / "scrape_history.json"
LOCK_FILE = DATA_DIR / "scraper.lock"

class JobDataService:
    LOCK_TIMEOUT = 900  # 15 minutes in seconds

    @staticmethod
    def _check_write_permissions():
        """Guardrail: Ensure data/ is writable before proceeding with atomic writes."""
        if not DATA_DIR.exists():
            try:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"❌ Critical Error: Data directory {DATA_DIR} does not exist and cannot be created: {e}")
                return False
        
        if not os.access(DATA_DIR, os.W_OK):
            logger.error(f"❌ Critical Error: Data directory {DATA_DIR} is not writable.")
            return False
        return True

    @staticmethod
    def _get_mock_df():
        """Generates internal test stub data for UI verification during development/failures."""
        mock_jobs = [
            {
                "id": "stub_1", 
                "company": "Google [MOCK]", 
                "title": "Senior Cloud Architect", 
                "location": "Mountain View, CA", 
                "score": 48, 
                "date_posted": "2026-04-01", 
                "url": "https://example.com/mock1",
                "Status": "New",
                "restriction_data": {"restricted": False, "reason": "Green flag: 'sponsorship available'", "mobility_status": "FRIENDLY"}
            },
            {
                "id": "stub_2", 
                "company": "Anduril [MOCK]", 
                "title": "Defense Stability Engineer", 
                "location": "Costa Mesa, CA", 
                "score": 42, 
                "date_posted": "2026-04-02", 
                "url": "https://example.com/mock2",
                "Status": "Interviewing",
                "restriction_data": {"restricted": True, "reason": "Legal Code: 8 U.S.C. 1324b", "mobility_status": "RESTRICTED"}
            },
            {
                "id": "stub_3", 
                "company": "Standard Tech [MOCK]", 
                "title": "Full Stack Developer", 
                "location": "Remote", 
                "score": 35, 
                "date_posted": "2026-04-03", 
                "url": "https://example.com/mock3",
                "Status": "New",
                "restriction_data": {"restricted": False, "reason": None, "mobility_status": "NEUTRAL"}
            }
        ]
        return pd.DataFrame(mock_jobs)

    @staticmethod
    def is_scraper_running():
        """
        Global Scraping Status via Lock File monitoring.
        Implements 'Zombie Lock' protection with a 15-minute timeout.
        """
        if not LOCK_FILE.exists():
            return False
        
        # Check for Zombie Lock (Stale for > 15m)
        try:
            mtime = os.path.getmtime(LOCK_FILE)
            if (time.time() - mtime) > JobDataService.LOCK_TIMEOUT:
                logger.warning(f"⚠️ Zombie lock detected on {LOCK_FILE.name} (Stale for > 15m). Ignoring.")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to check lock status: {e}")
            return False

    @staticmethod
    @st.cache_data(ttl=3600)
    def fetch_dashboard_payload(file_mtime=None):
        """
        Returns a 'Data Envelope' containing the job dataframe 
        and metadata (mock status, last updated).
        
        [AI CONTEXT]: file_mtime is used as a cache key to force invalidation 
        when the underlying jobs_agg.json is updated on disk.
        """
        # OPTION: High-Frequency Remote Pull (SRE: Live Dashboard)
        if os.getenv("USE_GITHUB_DATA") == "true":
            raw_data = JobDataService._fetch_remote_jobs()
            if raw_data:
                jobs = raw_data.get("jobs", [])
                total_jobs = raw_data.get("total_jobs", 0)
                gen_at = raw_data.get("generated_at", "Unknown")
                df = pd.DataFrame(jobs)
                logger.info(f"🌐 LIVE: Fetched {len(df)} jobs from GitHub data-state branch.")
                return {
                    "data": df,
                    "is_mock": False,
                    "last_updated": gen_at,
                    "total_jobs": total_jobs,
                    "source": "GitHub (Live)"
                }

        logger.info(f"🔄 Request: Dashboard Payload (Disk check: {JOB_DATA_FILE.name})")
        
        # Permission Guardrail
        if not JobDataService._check_write_permissions():
            st.error("🚨 **System Error:** Data directory is not writable. Check Docker volume permissions.")
            st.stop()

        if not JOB_DATA_FILE.exists():
            logger.warning(f"⚠️ {JOB_DATA_FILE.name} missing. Returning [INTERNAL_TEST_STUB].")
            return {
                "data": JobDataService._get_mock_df(),
                "is_mock": True,
                "last_updated": "Unknown",
                "total_jobs": 0
            }
            
        try:
            with open(JOB_DATA_FILE, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                jobs = raw_data.get("jobs", [])
                total_jobs = raw_data.get("total_jobs", 0)
                gen_at = raw_data.get("generated_at", "Unknown")
            
            df = pd.DataFrame(jobs)
            
            # --- Season & Year Extraction (Performance: Pre-computed in cache) ---
            # [REGARDLESS OF SOURCE]: Standardize attributes for filtering
            if not df.empty and 'title' in df.columns:
                # Regex Expansion: Captures Internship Seasons, Quarters, Co-ops, and Grad placements
                season_regex = r'(Summer|Fall|Spring|Winter|Q[1-4]|Co-op|Grad Intern)\s+(\d{4})'
                extracted = df['title'].str.extract(season_regex, flags=re.IGNORECASE)
                df['Season'] = extracted[0].fillna('Other')
                df['Year'] = extracted[1].fillna('N/A')
                # Combine for UI display in filters: "Summer 2026"
                df['Season_Display'] = df.apply(
                    lambda x: f"{x['Season']} {x['Year']}" if x['Year'] != 'N/A' else x['Season'], 
                    axis=1
                )

            logger.info(f"✅ Cache Miss/Reload: Parsed {len(df)} jobs from disk.")
            
            return {
                "data": df,
                "is_mock": False,
                "last_updated": gen_at,
                "total_jobs": total_jobs,
                "source": "Local Disk"
            }
        except Exception as e:
            logger.error(f"❌ Failed to parse {JOB_DATA_FILE.name}: {e}")
            return {
                "total_jobs": 0
            }

    @staticmethod
    def get_backup_status():
        """Reads the last_backup.json file from the scraper to report DR status."""
        status_file = DATA_DIR / "last_backup.json"
        if not status_file.exists():
            return {"status": "No Backup Found", "timestamp": "N/A"}
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load backup status: {e}")
            return {"status": "Error", "timestamp": "N/A"}

    @staticmethod
    def _fetch_remote_jobs():
        """
        Pull the latest state directly from the data-state branch (GitHub Raw).
        Enabled via USE_GITHUB_DATA=true environment variable.
        """
        import requests
        repo = os.getenv("GITHUB_REPOSITORY")
        token = os.getenv("GITHUB_TOKEN")
        
        if not repo:
            return None
            
        url = f"https://raw.githubusercontent.com/{repo}/data-state/data/jobs_agg.json"
        headers = {"Authorization": f"token {token}"} if token else {}
        
        try:
            logger.info(f"🌐 Fetching remote state from {url}...")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch remote jobs: {e}")
            return None

    @staticmethod
    def load_tracking():
        """Loads user tracking data (saved/status) from tracking.json."""
        if not TRACKING_FILE.exists():
            return {}
        try:
            with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load tracking data: {e}")
            return {}

    @staticmethod
    def save_tracking_atomically(data):
        """
        Saves tracking data atomically to prevent corruption.
        Creates temp file in SAME directory to ensure cross-volume move safety.
        """
        temp_path = TRACKING_FILE.with_suffix(".tmp")
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Atomic OS-level replace
            temp_path.replace(TRACKING_FILE)
            logger.info(f"💾 {TRACKING_FILE.name} updated atomically.")
            return True
        except Exception as e:
            logger.error(f"❌ Atomic save failed for {TRACKING_FILE.name}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            return False

    @staticmethod
    def get_scrape_history_df():
        """Reads historical runs and returns a formatted DataFrame."""
        if not HISTORY_FILE.exists():
            return pd.DataFrame(columns=["timestamp", "jobs_found", "duration_seconds", "status"])
        
        try:
            with open(HISTORY_FILE, "r", encoding='utf-8') as f:
                history = json.load(f)
            
            df = pd.DataFrame(history)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values(by="timestamp", ascending=False).reset_index(drop=True)
                df['timestamp'] = df['timestamp'].dt.strftime("%Y-%m-%d %H:%M:%S")
            return df
        except Exception as e:
            logger.error(f"Failed to parse history log: {e}")
            return pd.DataFrame(columns=["timestamp", "jobs_found", "duration_seconds", "status"])

    @staticmethod
    def log_scrape_run(jobs_found, duration_seconds, status="Success"):
        """
        Appends a new scrape run record to the history log atomically.
        """
        # Ensure directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing data
        history = []
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                history = []
            
        # Append new run
        new_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "jobs_found": jobs_found,
            "duration_seconds": round(duration_seconds, 2),
            "status": status
        }
        history.append(new_entry)
        
        # Keep only the last 50 runs to prevent file bloat
        history = history[-50:]
        
        temp_path = HISTORY_FILE.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding='utf-8') as f:
                json.dump(history, f, indent=4)
            temp_path.replace(HISTORY_FILE)
            logger.info(f"📜 Updated history log atomically: {HISTORY_FILE.name}")
        except Exception as e:
            logger.error(f"❌ Failed to save history run: {e}")
            if temp_path.exists():
                temp_path.unlink()

    @staticmethod
    def cleanup_job_drafts(job_id):
        """Removes temporary draft files for a given job."""
        if not job_id: return
        # drafts are in Job-Automation-Suite/generated_cvs
        # BASE_DIR is job-scraping-app/
        root_dir = BASE_DIR.parent
        draft_file = root_dir / "generated_cvs" / f"{job_id}_Draft.yaml"
        if draft_file.exists():
            try:
                draft_file.unlink()
                logger.info(f"🧹 Cleaned up draft for job {job_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup draft {draft_file}: {e}")

    @staticmethod
    @st.cache_data(ttl=3600)
    def get_analytics_summary(file_mtime=None):
        """
        Aggregates tracking + job data into a single analytics payload
        for the Analytics page. Memoized to prevent recalculation on
        every Streamlit interaction.

        [AI CONTEXT]: file_mtime is a cache-busting key (same pattern
        as fetch_dashboard_payload). Pass os.path.getmtime() of both
        tracking.json and jobs_agg.json so the cache invalidates when
        either file changes on disk.
        """
        # 1. Load raw data
        tracking = {}
        if TRACKING_FILE.exists():
            try:
                with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                    tracking = json.load(f)
            except Exception as e:
                logger.error(f"Analytics: Failed to load tracking: {e}")

        jobs = []
        if JOB_DATA_FILE.exists():
            try:
                with open(JOB_DATA_FILE, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    jobs = content.get("jobs", [])
            except Exception as e:
                logger.error(f"Analytics: Failed to load jobs: {e}")

        # 2. Compute status counts
        total_scraped = len(jobs)
        status_counts = {"New": 0, "Saved": 0, "Applied": 0,
                         "Interviewing": 0, "Offer": 0, "Rejected": 0, "Hidden": 0}

        saved_ids = set()
        for job_id, meta in tracking.items():
            status = meta.get("status", "New")
            if status in status_counts:
                status_counts[status] += 1
            if meta.get("saved", False):
                saved_ids.add(job_id)

        num_saved = len(saved_ids)
        num_applied = status_counts["Applied"]
        num_interviewing = status_counts["Interviewing"]
        num_offer = status_counts["Offer"]
        num_rejected = status_counts["Rejected"]

        # 3. Sankey flow data (source → target → value)
        # Stages: Total → Saved → Applied → Interviewing → Offer
        #         with rejection branches at Applied and Interviewing
        sankey_nodes = [
            "Total Scraped",  # 0
            "Saved",          # 1
            "Applied",        # 2
            "Interviewing",   # 3
            "Offer",          # 4
            "Unsaved",        # 5
            "Not Applied",    # 6
            "Rejected",       # 7
            "No Response",    # 8
        ]

        # Calculate flow values
        unsaved = total_scraped - num_saved
        not_applied = max(num_saved - num_applied - num_interviewing - num_offer - num_rejected, 0)
        applied_forward = num_interviewing + num_offer
        applied_rejected = num_rejected
        applied_no_response = max(num_applied - applied_forward - applied_rejected, 0)
        interview_to_offer = num_offer
        interview_no_response = max(num_interviewing - num_offer, 0)

        sankey_sources = [0, 0, 1, 1, 2, 2, 2, 3, 3]
        sankey_targets = [1, 5, 2, 6, 3, 7, 8, 4, 8]
        sankey_values  = [
            num_saved,              # Total → Saved
            unsaved,                # Total → Unsaved
            num_applied + num_interviewing + num_offer + num_rejected,  # Saved → Applied (all who progressed)
            not_applied,            # Saved → Not Applied
            applied_forward,        # Applied → Interviewing
            applied_rejected,       # Applied → Rejected
            applied_no_response,    # Applied → No Response
            interview_to_offer,     # Interviewing → Offer
            interview_no_response,  # Interviewing → No Response
        ]

        # Filter out zero-value flows for clean rendering
        filtered = [(s, t, v) for s, t, v in zip(sankey_sources, sankey_targets, sankey_values) if v > 0]
        if filtered:
            sankey_sources, sankey_targets, sankey_values = zip(*filtered)
        else:
            sankey_sources, sankey_targets, sankey_values = [], [], []

        # 4. Company breakdown (top 15 by tracked jobs)
        company_status = {}
        job_lookup = {j["id"]: j for j in jobs}
        for job_id, meta in tracking.items():
            if meta.get("saved") or meta.get("status") not in (None, "New", "Hidden"):
                job = job_lookup.get(job_id, {})
                company = job.get("company", "Unknown")
                status = meta.get("status", "Saved")
                if company not in company_status:
                    company_status[company] = {}
                company_status[company][status] = company_status[company].get(status, 0) + 1

        # 5. Score distribution
        scores = [j.get("score", 0) for j in jobs if j.get("score") is not None]
        saved_scores = [job_lookup[jid].get("score", 0) for jid in saved_ids if jid in job_lookup]

        # 6. Timeline data (applications over time)
        timeline_data = []
        for job_id, meta in tracking.items():
            status = meta.get("status", "New")
            if status in ("Applied", "Interviewing", "Offer", "Rejected"):
                job = job_lookup.get(job_id, {})
                date = job.get("date_posted", "")
                if date:
                    timeline_data.append({"date": date, "status": status})

        return {
            "total_scraped": total_scraped,
            "num_saved": num_saved,
            "num_applied": num_applied,
            "num_interviewing": num_interviewing,
            "num_offer": num_offer,
            "num_rejected": num_rejected,
            "sankey_nodes": sankey_nodes,
            "sankey_sources": list(sankey_sources),
            "sankey_targets": list(sankey_targets),
            "sankey_values": list(sankey_values),
            "company_status": company_status,
            "scores": scores,
            "saved_scores": saved_scores,
            "timeline_data": timeline_data,
        }

