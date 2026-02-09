import asyncio
import logging
import time
import sys
from fetchers import JobFetcherManager

# Setup file logging
logging.basicConfig(
    filename='verification_log_final.txt',
    filemode='w',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)

# Targeted config for the broken companies (Updated)
TEST_CONFIG = [
    {"name": "Anduril", "ats": "greenhouse", "board_token": "andurilindustries"},
    {"name": "DoorDash", "ats": "greenhouse", "board_token": "doordashusa"},
    {"name": "Scale AI", "ats": "greenhouse", "board_token": "scaleai"}, 
    {"name": "Zoox", "ats": "lever", "board_token": "zoox"},
    {"name": "Bedrock Robotics", "ats": "ashby", "board_url": "https://jobs.ashbyhq.com/bedrock-robotics"},
    # Retool still fragile, testing to see if it works now or if we should warn user
    {"name": "Retool", "ats": "ashby", "board_url": "https://jobs.ashbyhq.com/retool"},
]

async def main():
    logger.info(f"Starting async fetch for {len(TEST_CONFIG)} companies...")
    print(f"Starting async fetch for {len(TEST_CONFIG)} companies...")
    
    manager = JobFetcherManager()
    try:
        jobs = await manager.fetch_all_jobs(TEST_CONFIG)
    except Exception as e:
        logger.error(f"Manager crashed: {e}", exc_info=True)
        jobs = []

    logger.info(f"Successfully fetched {len(jobs)} total jobs.")
    
    # Detailed Validation
    company_counts = {}
    for job in jobs:
        comp = job.get('company')
        company_counts[comp] = company_counts.get(comp, 0) + 1
        
    logger.info("Job Counts by Company:")
    print("\nJob Counts by Company:")
    for company in TEST_CONFIG:
        name = company['name']
        count = company_counts.get(name, 0)
        status = "✅" if count > 0 else "❌"
        msg = f"{status} {name}: {count} jobs"
        logger.info(msg)
        print(msg)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
