import pytest
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Provide absolute resolution logic
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Import logic from main
from main import execute_scraping_run, LOCK_FILE

def test_scraper_lock_timeout_clears_stale_lock(monkeypatch):
    """
    Test that execute_scraping_run gracefully handles simulated lock offsets 
    that are older than 15 minutes.
    """
    # 1. Setup stale lock (older than 15 minutes)
    os.makedirs(LOCK_FILE.parent, exist_ok=True)
    stale_time = datetime.now() - timedelta(seconds=960)
    with open(LOCK_FILE, "w") as f:
        f.write(f"locked at {stale_time.isoformat()}")

    # 2. Prevent execute_scraping_run from actually scraping by mocking
    # asyncio.run, since we only want to test the lock clearing logic.
    monkeypatch.setattr('asyncio.run', lambda x: {"ingested_count": 0, "processed_count": 0})
    
    # Optional: Mock time.sleep to avoid jitter logic waiting in CI environments
    monkeypatch.setattr('time.sleep', lambda x: None)
    monkeypatch.setenv("GITHUB_ACTIONS", "false")

    try:
        # Run execution
        result = execute_scraping_run()

        # 3. Assertions
        # It shouldn't return the "Scraper failed: already running" message.
        # It should return "Success" (or whatever the mock completes with)
        assert "Success" in result["status"]
        assert not LOCK_FILE.exists() # The finally block or lock block will clear it
    finally:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()


def test_scraper_lock_fails_if_recent(monkeypatch):
    """
    Test that execute_scraping_run fails successfully returning an error if a lock is recent.
    """
    # 1. Setup fresh lock (younger than 15 minutes)
    os.makedirs(LOCK_FILE.parent, exist_ok=True)
    fresh_time = datetime.now() - timedelta(seconds=300) # 5 minutes ago
    with open(LOCK_FILE, "w") as f:
        f.write(f"locked at {fresh_time.isoformat()}")

    try:
        result = execute_scraping_run()
        
        # Should detect lock and fail
        assert "Failed: Scraper is already running in another process." in result["status"]
    finally:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
