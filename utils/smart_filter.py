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
            # Use absolute path for reliability across containers
            from pathlib import Path
            base_path = Path(__file__).resolve().parent.parent
            config_path = base_path / "config" / "filtering.yaml"
            with open(config_path, "r") as f:
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
        
        from dateutil import parser
        try:
            # 1. Pre-check for Unix Timestamps (Numeric strings or numbers)
            date_str_val = str(date_str).strip() if date_str is not None else ""
            if date_str_val.isdigit():
                ts = int(date_str_val)
                # Detect milliseconds (13+ digits) vs seconds (10 digits)
                if ts > 10000000000:
                    ts = ts / 1000.0
                job_date = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                # 2. Standard ISO/String Parsing (Robust via dateutil)
                job_date = parser.parse(date_str_val)
                if job_date.tzinfo is None:
                    job_date = job_date.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            # age_days will be 0 if today, 1 if yesterday, etc.
            age_days = (now - job_date).days

            return age_days <= self.max_days_old

        except (ValueError, OverflowError, TypeError, parser.ParserError) as e:
            # 3. Silent Failsafe for Production Logs (DEBUG level)
            logging.debug(f"Date Parsing: Format not recognized for '{date_str}': {e}. Defaulting to 'Keep'.")
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
