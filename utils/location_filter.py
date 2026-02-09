import yaml
import logging

# Singleton to load config only once
class LocationConfig:
    _config = None

    @classmethod
    def get(cls):
        if cls._config is None:
            try:
                with open("config/filtering.yaml", "r") as f:
                    data = yaml.safe_load(f)
                    cls._config = data.get("locations", {})
            except Exception as e:
                logging.error(f"Failed to load location config: {e}")
                cls._config = {"exclude": [], "include": []}
        return cls._config

def is_us_or_remote(location: str) -> bool:
    """
    Returns True if location matches US allowlist or generic Remote.
    Returns False if location matches International blocklist.
    """
    if not location:
        return True

    loc_lower = location.lower()
    config = LocationConfig.get()

    # 1. CHECK BLOCKLIST (Exclude)
    # Fast Fail: If it matches a banned region, drop it immediately.
    for term in config.get("exclude", []):
        if term.lower() in loc_lower:
            return False

    # 2. CHECK ALLOWLIST (Include)
    # Fast Pass: If it matches a known US hub, keep it immediately.
    for term in config.get("include", []):
        if term.lower() in loc_lower:
            return True

    # 3. GENERIC REMOTE CHECK
    # "Remote" is fine, but "Remote - UK" would have been caught by step 1.
    if "remote" in loc_lower:
        return True

    # 4. DEFAULT
    # If ambiguous (e.g. "Durham"), default to True (Keep).
    return True
