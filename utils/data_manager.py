import streamlit as st
import pandas as pd
import json
import logging
import os
import time
from pathlib import Path
from datetime import datetime
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base path relative to this file (job-scraping-app/utils/data_manager.py)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
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
    @st.cache_data(ttl=60)
    def fetch_dashboard_payload():
        """
        Returns a 'Data Envelope' containing the job dataframe 
        and metadata (mock status, last updated).
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
            
        url = f"https://raw.githubusercontent.com/{repo}/data-state/job-scraping-app/data/jobs_agg.json"
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

