import yaml
import logging
from fetchers import JobFetcherManager

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_samples():
    try:
        with open('config/companies.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Select one from each new category/ATS
        samples = [
            'Notion',      # Ashby
            'Stripe',      # Greenhouse
            'Palantir',    # Lever
            'Shield AI'    # Lever
        ]
        
        companies_to_test = [c for c in config['companies'] if c['name'] in samples]
        
        if not companies_to_test:
            logger.error("Sample companies not found in config!")
            return

        logger.info(f"Testing {len(companies_to_test)} sample companies...")
        
        manager = JobFetcherManager()
        
        success_count = 0
        for company in companies_to_test:
            logger.info(f"Testing fetch for {company['name']}...")
            try:
                jobs = manager.fetch_all_jobs([company])
                if jobs:
                    logger.info(f"SUCCESS: Fetched {len(jobs)} jobs for {company['name']}")
                    success_count += 1
                else:
                    logger.warning(f"WARNING: Fetched 0 jobs for {company['name']}")
            except Exception as e:
                logger.error(f"FAILURE: Error fetching {company['name']}: {e}")
        
        logger.info(f"Summary: {success_count}/{len(companies_to_test)} samples successful.")

    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    test_samples()
