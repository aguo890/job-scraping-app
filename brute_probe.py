import asyncio
import aiohttp
import logging
from utils.network import SafeSession

logging.basicConfig(filename='brute_results.txt', level=logging.INFO, format='%(message)s')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)

COMPANIES = {
    "Retool": ["retool", "retoolinc", "retool-inc", "retool-hiring", "retool-jobs", "retool-careers"],
}

PROVIDERS = {
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}"
}

async def probe():
    async with aiohttp.ClientSession() as session:
        client = SafeSession(session)
        
        for company, slugs in COMPANIES.items():
            logger.info(f"--- Probing {company} ---")
            for slug in slugs:
                # Try all providers for each slug just in case
                for provider, url_template in PROVIDERS.items():
                    url = url_template.format(slug=slug)
                    try:
                        # Use raw session to see all codes
                        async with session.get(url, headers=client.DEFAULT_HEADERS, timeout=5) as response:
                            if response.status == 200:
                                # Check if it actually has data
                                try:
                                    data = await response.json()
                                    count = 0
                                    if isinstance(data, dict):
                                        if 'jobs' in data: count = len(data['jobs'])
                                        elif 'postings' in data: count = len(data['postings']) # Lever sometimes
                                    elif isinstance(data, list):
                                        count = len(data)
                                    
                                    if count > 0:
                                        logger.info(f"✅ FOUND! {company} | {provider} | {slug} | {count} jobs | {url}")
                                    else:
                                        logger.info(f"⚠️  200 OK (Empty) | {company} | {provider} | {slug} | {url}")
                                except:
                                     logger.info(f"⚠️  200 OK (Not JSON) | {company} | {provider} | {slug}")
                            
                            elif response.status != 404:
                                logger.info(f"❌ {response.status} | {company} | {provider} | {slug}")
                                
                    except Exception as e:
                        pass

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(probe())
