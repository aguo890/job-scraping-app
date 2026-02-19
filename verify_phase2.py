import asyncio
import logging
from utils.schemas import JobListing
from utils.network import SafeSession
import aiohttp

# Configure logging to see our validation warnings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_schema():
    print("\n--- Testing JobListing Schema ---")
    
    # 1. Valid Job
    valid_job = JobListing(
        id="gh_test_123",
        title="  Software Engineer  ",
        company="<b>Google</b>",
        url="https://jobs.google.com/123",
        description="<p>Help us build the future.</p>"
    )
    valid_job.sanitize()
    is_valid = valid_job.is_valid()
    print(f"Valid Job - Valid: {is_valid}, Title: '{valid_job.title}', Company: '{valid_job.company}', Desc: '{valid_job.description}'")

    # 2. Invalid Job (missing ID)
    invalid_job = JobListing(
        id="",
        title="Ghost Developer",
        company="Startup Inc",
        url="https://startup.com/ghost"
    )
    invalid_job.sanitize()
    is_valid = invalid_job.is_valid()
    print(f"Invalid Job (no ID) - Valid: {is_valid}")

    # 3. Invalid Job (missing URL)
    broken_job = JobListing(
        id="lever_456",
        title="Broken Lead",
        company="FixMe",
        url=""
    )
    broken_job.sanitize()
    is_valid = broken_job.is_valid()
    print(f"Broken Job (no URL) - Valid: {is_valid}")

async def test_network_structure():
    print("\n--- Testing Network Layer Structure ---")
    async with aiohttp.ClientSession() as session:
        safe_client = SafeSession(session)
        # We can't easily trigger a 429 without a target, 
        # but we can verify it doesn't crash on a simple 404
        print("Fetching non-existent URL (expecting failure log, no retry)...")
        res = await safe_client.fetch_json("https://google.com/404_not_found_random_12345")
        print(f"Fetch Result: {res}")

if __name__ == "__main__":
    asyncio.run(test_schema())
    asyncio.run(test_network_structure())
