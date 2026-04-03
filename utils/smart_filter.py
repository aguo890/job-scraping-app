import re
import yaml
import logging

# Centralized Constants for Restriction Filtering (Hardened 2026 Registry)
RESTRICTION_PRESETS = {
    "no_sponsorship": [
        "no sponsorship", "will not sponsor", "cannot sponsor", 
        "no visa", "h1-b sponsorship not available", "h1-b sponsorship is not available",
        "work authorization required", "legal right to work in the u.s. without sponsorship",
        "visa sponsorship", "sponsorship is not available", "e-verify", "i-9 compliance"
    ],
    "no_clearance": [
        # Citizens & Persons (Core Triggers)
        "u.s. citizen", "us citizen", "u.s. person", "us person",
        "dual citizen", "lawful permanent resident", "lpr", "u.s. national",
        # Standard Clearances (Reinforced)
        "clearance", "security clearance", "ts/sci", "secret clearance", 
        "polygraph", "top secret", "clearance required", "public trust", 
        "adjudication", "personnel vetting", "ts clearance", "secret level",
        # Federal Forms & Legal Codes (The 'Anduril' Fix)
        "sf-86", "sf-85", "sf-85p", "e-qip", "eqip", "eapp", "of-306",
        "8 u.s.c. 1324b", "1324b(a)(3)", "protected individual", "export control", "ear/itar",
        # Vetting Tiers
        "tier 1", "tier 2", "tier 3", "tier 4", "tier 5", "t1-t5", "t5 investigation",
        # Defense & Export Controls (ITAR/EAR)
        "itar", "ear", "export control", "22 cfr", "15 cfr", "ddtc",
        # Government Agencies (Global Exclude)
        "cia", "fbi", "nsa", "homeland security", "department of defense", "dod"
    ],
    "mobility_friendly": [
        "sponsorship available", "h1-b sponsorship", "h1b welcome", 
        "visa sponsorship", "will sponsor", "sponsorship provided",
        "global mobility", "relocation assistance", "transfers welcome"
    ]
}

# False Positive Guardrails: Ignore matches if near these terms
CONTEXT_EXCLUSIONS = ["sale", "event", "inventory", "warehouse", "retail", "store"]

def build_flexible_us_pattern(keywords):
    """
    Normalizes 'U.S.' and 'H1-B' variations within keywords into a flexible regex.
    Handles: US, U.S., U. S., u.s, us, H1B, H1-B, and varying spaces.
    """
    normalized = []
    for k in keywords:
        # 1. Handle U.S. prefix variations
        # Replace 'u.s.' or 'us' variations with a flexible prefix pattern
        k_flex = re.sub(r'u\.?\s?s\.?', r'u\\.?\\s?s\\.?', k, flags=re.IGNORECASE)
        
        # 2. Handle H1-B / H1B variations (make hyphen optional)
        k_flex = re.sub(r'h1-?b', r'h1-?b', k_flex, flags=re.IGNORECASE)

        # 3. Handle overall spacing flexibility (replace spaces with optional whitespace)
        k_flex = k_flex.replace(" ", r"\s+") # Changed from \s* to \s+ for better separation
        
        normalized.append(k_flex)
    return normalized


class RestrictionEngine:
    def __init__(self, config_or_keywords):
        """
        High-performance scanning engine. 
        Compiles regex pattern once for use across thousands of jobs.
        Supports both direct keyword lists (Legacy) and Config Objects (Presets).
        """
        if isinstance(config_or_keywords, list):
            # Legacy Support: Direct keyword list
            active_keywords = config_or_keywords
        elif isinstance(config_or_keywords, dict):
            # 2026 Enhanced Logic: Merge Presets + Custom Keywords
            config = config_or_keywords
            custom_keywords = config.get('keywords', [])
            active_keywords = list(custom_keywords)
            
            if config.get('needs_sponsorship'):
                active_keywords.extend(RESTRICTION_PRESETS["no_sponsorship"])
            if config.get('no_clearance'):
                active_keywords.extend(RESTRICTION_PRESETS["no_clearance"])
        else:
            active_keywords = []

        # 🟢 Positive Mobility Patterns (Merged Presets + Custom)
        friendly_keywords = list(RESTRICTION_PRESETS["mobility_friendly"])
        if isinstance(config_or_keywords, dict):
            friendly_keywords.extend(config_or_keywords.get('mobility_friendly', []))
        
        friendly_keywords = sorted(list(set([str(k).lower() for k in friendly_keywords if k])))
        friendly_flex = build_flexible_us_pattern(friendly_keywords)
        
        if friendly_flex:
            friendly_str = r'\b(?:' + '|'.join(friendly_flex) + r')\b'
            self.friendly_pattern = re.compile(friendly_str, re.IGNORECASE)
        else:
            self.friendly_pattern = None

        if not active_keywords:
            self.pattern = None
            return
            
        # Unique list and remove empty strings
        active_keywords = sorted(list(set([str(k).lower() for k in active_keywords if k])))
        
        # Apply Flexible U.S. Normalization
        flexible_keywords = build_flexible_us_pattern(active_keywords)
            
        # Pattern ensures word boundaries (\b) to avoid false positives 
        # Non-capturing group (?:...) for performance
        pattern_str = r'\b(?:' + '|'.join(flexible_keywords) + r')\b'
        self.pattern = re.compile(pattern_str, re.IGNORECASE)

    def analyze(self, text):
        """
        Returns stability metadata about mobility compatibility.
        Strict Hierarchy: 🔴 RESTRICTED > 🟢 FRIENDLY > 🟡 NEUTRAL
        """
        if not text:
            return {"restricted": False, "friendly": False, "reason": None, "mobility_status": "NEUTRAL"}
            
        # 1. PRIORITY 1: SCAN FOR RED FLAGS (🔴 RESTRICTED)
        if self.pattern:
            match = self.pattern.search(text)
            if match:
                # Contextual Ignore-Check (e.g., "clearance sale")
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                snippet = text[start:end].lower()
                
                if not any(word in snippet for word in CONTEXT_EXCLUSIONS):
                    return {
                        "restricted": True,
                        "friendly": False,
                        "reason": f"🔴 Red Flag: '{match.group(0)}'",
                        "mobility_status": "RESTRICTED"
                    }

        # 2. PRIORITY 2: SCAN FOR GREEN FLAGS (🟢 FRIENDLY)
        if hasattr(self, 'friendly_pattern') and self.friendly_pattern:
            f_match = self.friendly_pattern.search(text)
            if f_match:
                return {
                    "restricted": False,
                    "friendly": True,
                    "reason": f"🟢 Green Flag: '{f_match.group(0)}'",
                    "mobility_status": "FRIENDLY"
                }

        # 3. PRIORITY 3: FALLBACK (🟡 NEUTRAL)
        return {
            "restricted": False, 
            "friendly": False, 
            "reason": "🟡 Neutral: No mobility keywords detected", 
            "mobility_status": "NEUTRAL"
        }

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
