#!/usr/bin/env python3
"""
Main orchestration script for the job scraping application
"""
import os
import sys
import logging
import yaml
import asyncio
from datetime import datetime
from pathlib import Path

from fetchers import JobFetcherManager
from processor import JobProcessor
from reporter import JobReporter
from github_integration import GitHubIntegration
from ai_assistant import AIAssistant


def setup_logging():
    """Configure logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # File handler
    log_dir = Path('logs')
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
        logging.error(f"Configuration file not found: {config_file}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML configuration: {e}")
        raise


async def main():
    """Main execution flow"""
    logger = setup_logging()
    logger.info("=" * 80)
    logger.info("Starting Job Scraping Application")
    logger.info("=" * 80)
    
    try:
        # Load configurations
        logger.info("Loading configurations...")
        companies_config = load_config('config/companies.yaml')
        keywords_config = load_config('config/keywords.yaml')
        
        companies = companies_config.get('companies', [])
        logger.info(f"Loaded {len(companies)} companies")
        
        # Initialize components
        logger.info("Initializing components...")
        fetcher_manager = JobFetcherManager()
        processor = JobProcessor(keywords_config)
        reporter = JobReporter()
        github = GitHubIntegration()
        ai_assistant = AIAssistant()
        
        # Fetch jobs
        logger.info("Fetching jobs from all sources...")
        # Await the async fetcher
        raw_jobs = await fetcher_manager.fetch_all_jobs(companies)
        logger.info(f"Fetched {len(raw_jobs)} raw job postings")
        
        if not raw_jobs:
            logger.warning("No jobs found. Exiting.")
            return 0
        
        # Process jobs
        # NOTE: We keep this active to ensure jobs are Saved and Deduplicated.
        # This usually doesn't trigger costs unless it calls an LLM internally.
        logger.info("Processing jobs (normalize, deduplicate, rank)...")
        processed_jobs = processor.process_jobs(raw_jobs)
        
        logger.info(f"Processed to {len(processed_jobs)} unique jobs")
        
        if not processed_jobs:
            logger.warning("No jobs after processing. Exiting.")
            return 0
        
        # Generate reports (DISABLED)
        logger.info("Skipping Report Generation...")
        # report_files = reporter.generate_reports(processed_jobs) 
        report_files = {} 
        
        # AI Analysis (DISABLED)
        logger.info("Skipping AI analysis (disabled)...")
        ai_results = {'enabled': False}
        # ai_results = ai_assistant.analyze_top_jobs(processed_jobs, top_n=5)
        
        # GitHub Integration (DISABLED)
        # logger.info("Committing and pushing reports to GitHub...")
        # files_to_commit = []
        # if 'ai_insights' in report_files:
        #     files_to_commit.append(report_files['ai_insights'])
        # github.commit_and_push_reports(files_to_commit)
        
        # Create/Update GitHub Issue (DISABLED)
        # logger.info("Creating/updating Daily Roles Digest issue...")
        # github.create_daily_digest_issue(processed_jobs, report_files.get('markdown', ''))
        
        # Summary
        logger.info("=" * 80)
        logger.info("Job Scraping Complete!")
        logger.info(f"  - Total jobs fetched: {len(raw_jobs)}")
        logger.info(f"  - Jobs after processing: {len(processed_jobs)}")
        if processed_jobs:
            logger.info(f"  - Top job score: {processed_jobs[0].get('score', 0):.1f}")
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        pass
