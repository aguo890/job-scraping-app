import streamlit as st
import pandas as pd
import json
import logging
import os
import time
from pathlib import Path
from datetime import datetime

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
                "company": "Acme [MOCK]", 
                "title": "Principal AI Orchestrator", 
                "location": "Remote", 
                "score": 48, 
                "date_posted": "2026-04-01", 
                "url": "https://example.com/mock1",
                "Status": "New"
            },
            {
                "id": "stub_2", 
                "company": "Globex [MOCK]", 
                "title": "Cloud Stability Engineer", 
                "location": "San Francisco", 
                "score": 42, 
                "date_posted": "2026-04-02", 
                "url": "https://example.com/mock2",
                "Status": "Interviewing"
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
        Uses explicit logging for cache monitoring.
        """
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
                "total_jobs": total_jobs
            }
        except Exception as e:
            logger.error(f"❌ Failed to parse {JOB_DATA_FILE.name}: {e}")
            return {
                "data": JobDataService._get_mock_df(), 
                "is_mock": True, 
                "last_updated": "ERR", 
                "total_jobs": 0
            }

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

