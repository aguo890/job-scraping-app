import schedule
import time
import logging
import sys
from datetime import datetime
import pytz
from main import run_scraper

# Configure logging to stdout so Docker captures it
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def job():
    logger.info("Starting scheduled job scraping...")
    try:
        run_scraper()
        
        # Touch a heartbeat file for Docker health checks
        import pathlib
        try:
            pathlib.Path('/tmp/scraper_heartbeat').touch()
        except Exception as heartbeat_err:
            logger.warning(f"Could not update heartbeat file: {heartbeat_err}")
            
        logger.info("Job scraping completed successfully.")
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)

def is_peak_hour(current_time):
    """Pure logic function for easy unit testing."""
    # Peak window: 8:00 AM to 12:59 PM (EST)
    return 8 <= current_time.hour < 13

def is_offpeak_hour(current_time):
    """Pure logic function for easy unit testing."""
    # Off-peak: Anytime outside 8:00 AM - 12:59 PM
    return current_time.hour < 8 or current_time.hour >= 13

def run_peak_job():
    tz = pytz.timezone('America/New_York')
    now = datetime.now(tz)
    if is_peak_hour(now):
        logger.info(f"[{now.strftime('%H:%M')}] Peak window active. Running 5-minute scrape...")
        job()

def run_offpeak_job():
    tz = pytz.timezone('America/New_York')
    now = datetime.now(tz)
    if is_offpeak_hour(now):
        logger.info(f"[{now.strftime('%H:%M')}] Off-peak window active. Running 30-minute scrape...")
        job()

# Run every 30 minutes
# schedule.every(30).minutes.do(job) # Replaced by dual schedule

# Dual-schedule registration
schedule.every(5).minutes.do(run_peak_job)
schedule.every(30).minutes.do(run_offpeak_job)

if __name__ == "__main__":
    # Run once immediately on startup
    logger.info("Scheduler started. Running initial job...")
    job()

    while True:
        schedule.run_pending()
        time.sleep(1)
