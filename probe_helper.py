import asyncio
import aiohttp
import logging
from utils.network import SafeSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URLS_TO_TEST = [
    # Zoox
    "https://boards-api.greenhouse.io/v1/boards/zoox/jobs?content=true",
    "https://boards-api.greenhouse.io/v1/boards/zooxinc/jobs?content=true",
    "https://boards-api.greenhouse.io/v1/boards/zoox-inc/jobs?content=true",
    
    # Retool
    "https://boards-api.greenhouse.io/v1/boards/retool/jobs?content=true",
    "https://boards-api.greenhouse.io/v1/boards/retoolinc/jobs?content=true",
    "https://boards-api.greenhouse.io/v1/boards/retool-inc/jobs?content=true",
    
    # Scale AI
    "https://api.ashbyhq.com/posting-api/job-board/scale-ai",
    "https://api.ashbyhq.com/posting-api/job-board/scale",
    "https://api.ashbyhq.com/posting-api/job-board/scaleai",
]

async def probe():
    async with aiohttp.ClientSession() as session:
        client = SafeSession(session)
        for url in URLS_TO_TEST:
            print(f"Probing {url}...")
            try:
                # We use the raw session to see status codes even if not JSON
                async with session.get(url, headers=client.DEFAULT_HEADERS, timeout=10) as response:
                    print(f" -> Status: {response.status}")
                    if response.status == 200:
                        try:
                            data = await response.json()
                            count = 0
                            if isinstance(data, dict):
                                count = len(data.get('jobs', []))
                            elif isinstance(data, list):
                                count = len(data)
                            print(f" -> SUCCESS! Found {count} jobs.")
                        except:
                            print(" -> 200 OK but not JSON.")
                    elif response.status == 301 or response.status == 302:
                        print(f" -> Redirect to {response.headers.get('Location')}")
            except Exception as e:
                print(f" -> Error: {e}")

if __name__ == "__main__":
    # Windows fix
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(probe())
