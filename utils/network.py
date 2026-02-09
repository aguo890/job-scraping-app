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

    async def fetch_json(self, url: str) -> Optional[Any]:
        timeout = self.config.get("request_timeout", 15)
        try:
            async with self.session.get(url, headers=self.headers, timeout=timeout) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                
                # Check content type loosely
                ctype = response.headers.get("Content-Type", "").lower()
                if "application/json" not in ctype and "text/json" not in ctype:
                    logger.debug(f"Warning: {url} returned {ctype}")

                return await response.json()
        except Exception as e:
            logger.error(f"Network error for {url}: {e}")
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
