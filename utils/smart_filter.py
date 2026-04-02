import yaml
import logging

class SmartFilter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SmartFilter, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        try:
            with open("config/filtering.yaml", "r") as f:
                self.config = yaml.safe_load(f)
            # Scalar configuration: Separate from arrays
            self.max_days_old = self.config.get('filtering', {}).get('max_days_old', 14)
        except Exception as e:
            logging.error(f"Failed to load filtering config: {e}")
            self.config = {}
            self.max_days_old = 14

    def is_recent(self, date_str: str) -> bool:
        """
        Determines if a job is within the max_days_old threshold.
        Fails open (returns True) if the date is missing or unparseable.
        """
        from datetime import datetime, timezone
        
        if not date_str:
            logging.warning("Missing date field from ATS API. Defaulting to current scrape time (Keep Job).")
            return True

        try:
            # Handle standard ISO 8601 with Z for UTC
            clean_date_str = date_str.replace("Z", "+00:00")
            job_date = datetime.fromisoformat(clean_date_str)
            
            # Ensure job_date is timezone aware for accurate comparison
            if job_date.tzinfo is None:
                 job_date = job_date.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            # age_days will be 0 if today, 1 if yesterday, etc.
            age_days = (now - job_date).days

            return age_days <= self.max_days_old

        except ValueError as e:
            logging.warning(f"Unparseable date '{date_str}': {e}. Failsafe triggered: keeping job.")
            return True

    def is_valid_location(self, location: str) -> bool:
        """Checks if location is allowed based on config."""
        if not location:
            return True # Default to keep if unknown
        
        loc_lower = location.lower()
        loc_rules = self.config.get("locations", {})

        # 1. Blocklist
        for term in loc_rules.get("exclude", []):
            if term.lower() in loc_lower:
                return False

        # 2. Allowlist
        for term in loc_rules.get("include", []):
            if term.lower() in loc_lower:
                return True

        # 3. Generic Remote
        if "remote" in loc_lower:
            return True

        return True

    def passes_hard_filters(self, job_data: dict) -> bool:
        """
        Gatekeeper: Determines if a job should be ingested at all.
        Strictly Boolean (True/False).
        Handles: Date, Location, and Banned Titles.
        """
        title = job_data.get('title', '')
        location = job_data.get('location', '')
        date_str = job_data.get('date_posted', '')

        if not title:
            return False

        # 1. Date Check
        if not self.is_recent(date_str):
            logging.debug(f"Dropped (Old): {title}")
            return False

        # 2. Location Check
        if not self.is_valid_location(location):
            logging.debug(f"Dropped (Location): {title} @ {location}")
            return False

        # 3. Title Check (Hard Exclusions)
        title_lower = title.lower()
        title_rules = self.config.get("titles", {})
        blocklist = self.config.get("title_blocklist", [])
        
        # Combined check for all hard-excluded keywords
        banned_keywords = title_rules.get("exclude", []) + blocklist
        
        for bad_word in banned_keywords:
            if bad_word.lower() in title_lower:
                logging.debug(f"Dropped (Banned Title): {title} due to '{bad_word}'")
                return False

        # 3b. Base Relevance (Safeguard)
        tech_indicators = ["engineer", "developer", "data", "scientist", "analyst", "intern", "researcher", "technical", "software", "machine learning"]
        if not any(tech in title_lower for tech in tech_indicators):
             logging.debug(f"Dropped (Not Tech): {title}")
             return False

        return True

# Singleton Export
job_filter = SmartFilter()
