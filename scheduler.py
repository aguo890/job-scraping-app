import schedule
import time
import logging
import sys
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

# Run every 30 minutes
schedule.every(30).minutes.do(job)

# Run once immediately on startup
logger.info("Scheduler started. Running initial job...")
job()

while True:
    schedule.run_pending()
    time.sleep(1)
