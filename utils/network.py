import yaml
import aiohttp
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class SafeSession:
    _config_cache = None

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.config = self._get_config()

    @classmethod
    def _get_config(cls):
        # Load once and cache
        if cls._config_cache is None:
            try:
                with open("config/filtering.yaml", "r") as f:
                    data = yaml.safe_load(f)
                    cls._config_cache = data.get("system", {})
            except Exception as e:
                logger.error(f"Failed to load system config: {e}")
                cls._config_cache = {}
        return cls._config_cache

    @property
    def headers(self):
        # Dynamic load or fallback
        ua = self.config.get("user_agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)")
        return {
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def fetch_json(self, url: str, max_retries: int = 3) -> Optional[Any]:
        """Fetches JSON with async exponential backoff for 429/5xx errors."""
        timeout_val = self.config.get("request_timeout", 15)
        
        for attempt in range(max_retries):
            try:
                async with self.session.get(url, headers=self.headers, timeout=timeout_val) as response:
                    # 1. Success
                    if response.status == 200:
                        # Check content type loosely
                        ctype = response.headers.get("Content-Type", "").lower()
                        if "application/json" not in ctype and "text/json" not in ctype:
                             logger.debug(f"Warning: {url} returned {ctype} instead of JSON")
                        return await response.json()

                    # 2. Rate Limited or Server Error
                    elif response.status in (429, 500, 502, 503, 504):
                        wait_time = (2 ** attempt) # 1s, 2s, 4s
                        logger.warning(f"HTTP {response.status} on {url}. Retrying in {wait_time}s (Attempt {attempt+1}/{max_retries})")
                        import asyncio
                        await asyncio.sleep(wait_time)
                        continue

                    # 3. Permanent Client Error
                    else:
                        logger.error(f"HTTP {response.status} on {url}. Aborting.")
                        return None

            except Exception as e:
                logger.error(f"Network error for {url} (Attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
        
        logger.error(f"Failed to fetch {url} after {max_retries} attempts.")
        return None

    async def fetch_text(self, url: str) -> Optional[str]:
        timeout = self.config.get("request_timeout", 15)
        try:
            async with self.session.get(url, headers=self.headers, timeout=timeout) as response:
                if response.status != 200:
                    return None
                return await response.text()
        except Exception:
            return None
