import asyncio
import aiohttp
import sys

COMPANIES = {
    "Abridge": ["abridge", "abridge-ai", "abridgehq"],
    "Apex": ["apex", "apexspace", "apex-space"],
    "Granola": ["granola", "granola-ai", "granolahq"],
    "Harvey": ["harvey", "harveyai", "harvey-ai"],
    "Kalshi": ["kalshi", "kalshiex"],
    "Saronic": ["saronic", "saronictech", "saronic-tech"],
    "Science": ["science", "science-corp", "sciencecorp"],
    "Starcloud": ["starcloud", "star-cloud"],
    "Tennr": ["tennr", "tennrai", "tennr-ai"]
}

PROVIDERS = {
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{slug}"
}

async def probe():
    async with aiohttp.ClientSession() as session:
        for company, slugs in COMPANIES.items():
            for slug in slugs:
                for provider, url_template in PROVIDERS.items():
                    url = url_template.format(slug=slug)
                    try:
                        async with session.get(url, timeout=5) as response:
                            if response.status == 200:
                                data = await response.json()
                                count = 0
                                if isinstance(data, dict):
                                    if 'jobs' in data: count = len(data['jobs'])
                                    elif 'postings' in data: count = len(data['postings'])
                                    elif 'data' in data: count = len(data['data'])
                                elif isinstance(data, list):
                                    count = len(data)
                                
                                if count > 0:
                                    print(f"FOUND: {company} | {provider} | {slug} | {count} jobs | {url}")
                    except Exception as e:
                        pass

if __name__ == "__main__":
    asyncio.run(probe())
