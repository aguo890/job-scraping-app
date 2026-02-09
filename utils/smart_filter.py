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
        except Exception as e:
            logging.error(f"Failed to load filtering config: {e}")
            self.config = {}

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

    def check_eligibility(self, title: str) -> tuple[bool, int, str]:
        """Analyzes Job Title. Returns (is_eligible, score, reason)."""
        if not title:
            return False, 0, "No Title"

        title_lower = title.lower()
        title_rules = self.config.get("titles", {})
        skills = self.config.get("preferred_skills", [])

        # 1. Exclude
        for bad_word in title_rules.get("exclude", []):
            if bad_word.lower() in title_lower:
                return False, 0, f"Banned: {bad_word}"

        # 2. Base Relevance (Safeguard)
        tech_indicators = ["engineer", "developer", "data", "scientist", "analyst", "intern", "researcher", "technical", "software", "machine learning"]
        if not any(tech in title_lower for tech in tech_indicators):
             return False, 0, "Not a tech role"

        # 3. Scoring
        score = 0
        reasons = []

        # Priority Keywords
        for word in title_rules.get("high_priority", []):
            if word.lower() in title_lower:
                score += 10
                reasons.append(f"Priority: {word}")

        # Skills
        for skill in skills:
            if skill.lower() in title_lower:
                score += 5
                reasons.append(f"Skill: {skill}")

        return True, score, ", ".join(reasons)

# Singleton Export
job_filter = SmartFilter()
