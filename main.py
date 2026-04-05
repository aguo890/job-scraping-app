#!/usr/bin/env python3
"""
Main orchestration script for the job scraping application
"""
import os
import sys
import logging
import yaml
import asyncio
import time
import json
from datetime import datetime
from pathlib import Path
import random

from fetchers import JobFetcherManager
from processor import JobProcessor
from reporter import JobReporter


# Base directory for absolute path resolution
BASE_DIR = Path(__file__).resolve().parent

def setup_logging():
    """Configure logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # File handler (Absolute path)
    log_dir = BASE_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"job_scraping_{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Root logger
    root_logger = logging.getLogger()
    # Reset handlers to avoid duplication
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return root_logger


def load_config(config_file: str):
    """Load YAML configuration file"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.getLogger().error(f"Configuration file not found: {config_file}")
        raise
    except yaml.YAMLError as e:
        logging.getLogger().error(f"Error parsing YAML configuration: {e}")
        raise


async def async_main(companies_filter: str = None):
    """Core async execution logic"""
    logger = logging.getLogger()
    
    try:
        # Load configurations using absolute paths
        logger.info(f"Loading configurations from {BASE_DIR}/config...")
        companies_config = load_config(str(BASE_DIR / 'config' / 'companies.yaml'))
        app_config = load_config(str(BASE_DIR / 'config' / 'filtering.yaml'))
        
        companies = companies_config.get('companies', [])
        
        # Filter if argument provided
        if companies_filter:
            target_names = [name.strip().lower() for name in companies_filter.split(",")]
            companies = [c for c in companies if c['name'].lower() in target_names]
            logger.info(f"🔧 Filter active: Scraping {len(companies)} companies matching: {companies_filter}")
        
        logger.info(f"Loaded {len(companies)} companies")
        
        if not companies:
            logger.warning("No companies to scrape. Exiting.")
            return {"ingested_count": 0, "processed_count": 0}
            
        # Initialize components
        logger.info("Initializing components...")
        fetcher_manager = JobFetcherManager()
        processor = JobProcessor(app_config)
        reporter = JobReporter()
        
        # Fetch jobs
        logger.info("Fetching jobs from all sources...")
        raw_jobs = await fetcher_manager.fetch_all_jobs(companies)
        logger.info(f"Qualified {len(raw_jobs)} job postings (passed Hard Filters)")
        
        # 3. LOAD EXISTING STATE (SRE: Source of Truth)
        # Check root data first, then submodule data as fallback
        root_data_path = Path(__file__).resolve().parent.parent / 'data' / 'jobs_agg.json'
        submodule_data_path = BASE_DIR / 'data' / 'jobs_agg.json'
        
        data_path = root_data_path if root_data_path.exists() else submodule_data_path
        
        existing_data = []
        if data_path.exists():
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    existing_data = content.get('jobs', [])
                logger.info(f"📂 Loaded {len(existing_data)} existing jobs from {data_path.name} for state-merge.")
            except Exception as e:
                logger.error(f"Failed to load existing state for merge: {e}")

        if not raw_jobs and not existing_data:
            logger.warning("No jobs found and no existing state. Exiting.")
            return {"ingested_count": 0, "processed_count": 0}
        
        # Process jobs
        logger.info("Processing jobs (normalize, deduplicate, rank)...")
        # [AI AGENT]: Pass existing_data to enable O(n) sync/retention logic
        processed_jobs = processor.process_jobs(raw_jobs, existing_jobs=existing_data)
        logger.info(f"Processed to {len(processed_jobs)} unique jobs")
        
        # 4. ATOMIC SAVE & REPORTING
        if processed_jobs:
            restricted_count = sum(1 for j in processed_jobs if j.get('restriction_data', {}).get('restricted'))
            logger.info(f"📊 Scrape Summary: {len(processed_jobs)} total, {restricted_count} restricted (Visa/Clearance).")
            
            # ATOMIC PERSISTENCE: Save to jobs_agg.json
            reporter.save_jobs_json(processed_jobs)
            # Optional: Daily markdown report
            reporter.generate_markdown_report(processed_jobs)
        else:
            logger.error("❌ No jobs were successfully processed. Aborting save.")

        # Return both counts for transparency
        return {
            "ingested_count": len(raw_jobs),
            "processed_count": len(processed_jobs)
        }
    
    except Exception as e:
        logger.error(f"Error in async_main: {e}", exc_info=True)
        raise


LOCK_FILE = BASE_DIR / "data" / "scraper.lock"

def execute_scraping_run(companies_filter: str = None):
    """
    Core logic meant to be imported by the Streamlit UI or other scripts.
    Returns a dictionary summary.
    """
    # 1. Check for existing lock
    if LOCK_FILE.exists():
        return {
            "status": "Failed: Scraper is already running in another process.", 
            "jobs_found": 0, 
            "duration_seconds": 0
        }

    setup_logging()
    logger = logging.getLogger()
    
    # [SRE: ANTI-BOT JITTER - Temporarily Disabled for Verification]
    # if os.getenv("GITHUB_ACTIONS") == "true":
    #     import random
    #     jitter = random.randint(60, 600)  # 1-10 minutes
    #     logger.info(f"⏳ CI Environment detected. Jitter: Sleeping for {jitter}s...")
    #     time.sleep(jitter)

    logger.info("=" * 80)
    logger.info("Starting Job Scraping Run")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    # Handle Windows event loop policy if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        # 2. Create the lock file
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCK_FILE, "w") as f:
            f.write(f"locked at {datetime.now().isoformat()}")

        # Use asyncio.run to execute the async logic synchronously
        # returns a dict with ingested_count and processed_count
        counts = asyncio.run(async_main(companies_filter))
        jobs_found = counts["processed_count"]
        ingested_count = counts["ingested_count"]
        duration = time.time() - start_time
        
        # [BUG FIX] Return separate counts for transparency (Ingested vs Processed)
        result = {
            "status": "Success",
            "ingested": ingested_count,
            "processed": jobs_found,
            "jobs_found": jobs_found, # Backwards compatibility
            "duration_seconds": round(duration, 2)
        }
        
        logger.info("=" * 80)
        logger.info(f"Run Complete: {result['status']}")
        logger.info(f"  - Ingested: {result['ingested']}")
        logger.info(f"  - Processed: {result['processed']}")
        logger.info(f"  - Duration: {result['duration_seconds']}s")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Scraping run failed: {e}")
        return {
            "status": f"Failed: {str(e)}",
            "jobs_found": 0,
            "duration_seconds": round(duration, 2)
        }
    finally:
        # 3. Always release the lock
        if LOCK_FILE.exists():
            try:
                os.remove(LOCK_FILE)
            except Exception as e:
                logger.error(f"Failed to remove lock file: {e}")

def main():
    """CLI Entry Point"""
    import argparse
    parser = argparse.ArgumentParser(description="Job Dashboard Scraper (CLI)")
    parser.add_argument("--companies", type=str, help="Comma-separated list of companies to scrape")
    args = parser.parse_args()
    
    print("🚀 Starting Job Scraper CLI...")
    result = execute_scraping_run(args.companies)
    
    if "Success" in result["status"]:
        print(f"✅ Success! Found {result['jobs_found']} jobs in {result['duration_seconds']}s.")
        return 0
    else:
        print(f"❌ Error: {result['status']}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
