from pathlib import Path
import json
from datetime import datetime, timedelta
import pytz
from dateutil import parser
import re
import logging
import os

logger = logging.getLogger(__name__)
# Base directory for absolute path resolution
BASE_DIR = Path(__file__).resolve().parent
from utils.location_filter import is_us_or_remote
from utils.smart_filter import RestrictionEngine

class JobProcessor:
    def __init__(self, config_input, config_override=None):
        # RESILIENT INIT: Handle dict (from main.py) or str path
        if isinstance(config_input, dict):
            self.config = config_input
        else:
            with open(config_input, 'r') as f:
                import yaml
                self.config = yaml.safe_load(f)
        
        # [AI CONTEXT]: Inject mock config parameters (for unit testing) 
        # specifically to allow deterministic testing of tiered weights.
        if config_override:
            if not isinstance(self.config, dict):
                self.config = {}
            for k, v in config_override.items():
                if isinstance(v, dict) and k in self.config and isinstance(self.config[k], dict):
                    self.config[k].update(v)
                else:
                    self.config[k] = v
        
        # Inject the applied jobs file path, defaulting to the production path if not provided
        # Support both dict and object configs for backward compatibility
        default_path = BASE_DIR / 'data' / 'applied_jobs.json'
        if isinstance(self.config, dict):
            self.applied_jobs_path = self.config.get('applied_jobs_path', default_path)
        else:
            self.applied_jobs_path = getattr(self.config, 'applied_jobs_path', default_path)
        
        # Helper lists for filtering/scoring
        # Unified config uses 'titles' section for keywords
        self.exclude_keywords = self.config.get('titles', {}).get('exclude', [])
        # Merge neutral keywords (e.g., II, III) which carry no weight but prevent exclusion
        self.neutral_keywords = self.config.get('titles', {}).get('neutral', [])
        self.high_priority_keywords = self.config.get('titles', {}).get('high_priority', [])
        
        # Initialize Restriction Engine (Visa/Clearance Filter)
        restriction_config = self.config.get('restrictions', {})
        self.restriction_engine = RestrictionEngine(restriction_config)
        
        # --- Tiered Scoring Logic (Backward Compatible) ---
        # [AI CONTEXT]: Weights prioritized by user feedback: Tier 1 (+10), Tier 2 (+20), Tier 3 (+50).
        tiered_cfg = self.config.get('tiered_skills', {})
        if tiered_cfg:
            self.tier1_skills = [k.lower() for k in tiered_cfg.get('tier1', [])]
            self.tier2_skills = [k.lower() for k in tiered_cfg.get('tier2', [])]
            self.tier3_skills = [k.lower() for k in tiered_cfg.get('tier3', [])]
        else:
            # Fallback for old schema: everything in preferred_skills goes to Tier 1
            logger.info("⚠️ Legacy 'preferred_skills' detected. Mapping everything to Tier 1.")
            self.tier1_skills = [k.lower() for k in self.config.get('preferred_skills', [])]
            self.tier2_skills = []
            self.tier3_skills = []
        
        # --- SRE Observability & Unified Config Sync ---
        # Architecture: YAML-first (Source of Truth), Environment Overrides (Testing)
        filter_config = self.config.get('filtering', {})
        
        # 1. Resolve MAX_YOE
        self.max_exp_limit = int(os.getenv("MAX_YOE", filter_config.get('max_years_experience', 2)))
        
        # 2. Resolve Multiplier with Safety Validation
        yaml_multiplier = filter_config.get('yoe_penalty_multiplier', -100)
        env_multiplier = os.getenv("YOE_PENALTY_MULTIPLIER")
        resolved_multiplier = int(env_multiplier) if env_multiplier else yaml_multiplier
        
        if resolved_multiplier > 0:
            logger.warning(f"⚠️ Positive YOE multiplier ({resolved_multiplier}) detected. Defaulting to -100 for safety.")
            resolved_multiplier = -100
        self.yoe_penalty_multiplier = resolved_multiplier
        
        # 3. Resolve Strict Mode
        yaml_strict = filter_config.get('strict_mode', False)
        env_strict = os.getenv("STRICT_MODE")
        self.strict_mode = env_strict.lower() == "true" if env_strict else yaml_strict
        
        logger.info("=" * 50)
        logger.info("🚀 JobProcessor (Unified Config Model) Active")
        logger.info(f"  - MAX_YOE Limit: {self.max_exp_limit} yrs")
        logger.info(f"  - STRICT_MODE: {'ENABLED' if self.strict_mode else 'DISABLED'}")
        logger.info(f"  - YOE Penalty: {self.yoe_penalty_multiplier}/yr")
        logger.info("=" * 50)
        
    def extract_min_years_experience(self, text):
        """
        Extracts the minimum years of experience required from text.
        Returns the MINIMUM found in a range (e.g., '3-5 years' -> 3).
        Capped at 15 to avoid false positives.
        """
        if not text:
            return 0
        
        # Pattern 1: "3-5 years of experience" or "5+ years"
        pattern1 = r'\b([1-9]|1[0-5])\+?\s*(?:-\s*([1-9]\d*)\s*)?(?:years?|yrs?)(?:\s+of\s+)?(?:\w+\s+){0,3}(?:experience|work)\b'
        
        # Pattern 2: "5 years' experience" (possessive form)
        pattern2 = r"\b([1-9]|1[0-5])\+?\s*(?:years?|yrs?)['']\s*(?:\w+\s+){0,2}(?:experience|work)\b"
        
        matches1 = re.findall(pattern1, text, re.IGNORECASE)
        matches2 = re.findall(pattern2, text, re.IGNORECASE)
        
        valid_years = []
        for m in matches1:
            # group 0 in pattern1 is the first number (min)
            valid_years.append(int(m[0]))
        for m in matches2:
            valid_years.append(int(m))
        
        if not valid_years:
            return 0
            
        # Return the MINIMUM found in the text (Architectural Direction)
        return min(valid_years)

    def normalize_location(self, location):
        """Standardize location string"""
        if not location:
            return "Remote"
        return str(location).strip()

    def is_us_location(self, location):
        """
        Check if location is US-based or Remote using centralized config.
        """
        return is_us_or_remote(location) 

    def normalize_date_est(self, date_str):
        """Parse date string to EST datetime"""
        if not date_str:
            return None
        
        try:
            # Handle various formats or use dateutil
            dt = parser.parse(date_str)
            
            # If naive, assume UTC (common in APIs) then convert to EST
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
                
            return dt.astimezone(pytz.timezone('US/Eastern'))
        except:
            return None

    def load_applied_jobs(self):
        """Load jobs that have been marked as applied"""
        try:
            # Use injected path (can be string or Path object)
            path = Path(self.applied_jobs_path)
            if not path.exists():
                return []
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error loading applied jobs: {e}")
            return []

    def process_jobs(self, jobs, existing_jobs=None):
        """
        Evaluator: Applies Soft Filters and Scoring.
        Now includes 'SRE-grade' state merging for GitHub Actions.
        """
        logger.info(f"Evaluating {len(jobs)} jobs...")
        
        # 1. EVALUATE & SCORE NEW JOBS
        newly_processed = self._evaluate_and_score(jobs)
        
        # 2. SYNC WITH EXISTING STATE (If provided)
        if existing_jobs:
            final_jobs = self.sync_job_state(existing_jobs, newly_processed)
        else:
            final_jobs = newly_processed
            
        return final_jobs

    def sync_job_state(self, existing_jobs, new_jobs, retention_days=60):
        """
        Merge & Purge: O(n) registry sync with 60-day retention policy.
        Preserves 'Golden Ticket' (Applied/Saved) jobs.
        """
        if not existing_jobs:
            return new_jobs
            
        logger.info(f"Syncing state: {len(existing_jobs)} existing vs {len(new_jobs)} new...")
        
        # Map existing jobs by ID for O(1) access
        registry = {job['id']: job for job in existing_jobs}
        now = datetime.now(pytz.utc)
        retention_cutoff = now - timedelta(days=retention_days)

        # 1. UPSERT: Update registry with new data, respecting Golden Ticket
        for job in new_jobs:
            jid = job['id']
            if jid in registry:
                # SRE RULE: Do not overwrite user-interacted status with raw scrape data
                if registry[jid].get('status') in ['Applied', 'Saved', 'Interviewing', 'Offer']:
                    continue
            registry[jid] = job

        # 2. RETENTION: Purge if (Old) AND (Not User-Interacted)
        hardened_list = []
        purged_count = 0
        
        for job in registry.values():
            try:
                # Parse fetch_date (ISO) or fallback to date_posted if missing
                f_date_str = job.get('fetch_date')
                if f_date_str:
                    f_date = datetime.fromisoformat(f_date_str)
                else:
                    # Legacy fallback
                    f_date = now # Default to now for missing dates
                
                # Keep Rule: (New enough) OR (Status is special)
                is_fresh = f_date > retention_cutoff
                is_gold = job.get('status') in ['Applied', 'Saved', 'Interviewing', 'Offer', 'Applied (Closed)']
                
                if is_fresh or is_gold:
                    hardened_list.append(job)
                else:
                    purged_count += 1
            except Exception as e:
                logger.warning(f"Retention check failed for {job.get('id')}: {e}. Keeping by default.")
                hardened_list.append(job)

        if purged_count > 0:
            logger.info(f"🧹 Retention: Purged {purged_count} stale jobs from registry.")
            
        # Re-sort by Score High->Low
        hardened_list.sort(key=lambda x: x.get('score', 0), reverse=True)
        return hardened_list

    def _evaluate_and_score(self, jobs):
        """
        Internal logic extracted from process_jobs.
        Strictly evaluates and scores a raw list of jobs.
        """
        processed = []
        seen_ids = set()
        
        # Load context
        applied_jobs = self.load_applied_jobs()
        applied_ids = {j['id'] for j in applied_jobs}
        applied_map = {j['id']: j for j in applied_jobs}

        # Scoring Weights from Config
        high_priority = [k.lower() for k in self.config.get('titles', {}).get('high_priority', [])]
        penalty_skills = [k.lower() for k in self.config.get('penalty_skills', [])]
        
        # [AI AGENT CONTEXT]: Experience limit and penalty now managed via __init__ 
        # using environment variables for parity across Docker services.
        max_exp_limit = self.max_exp_limit

        for job in jobs:
            job_id = job['id']
            if job_id in seen_ids: continue
            seen_ids.add(job_id)
            
            is_applied = job_id in applied_ids
            title_lower = job['title'].lower()
            description_text = str(job.get('description', ''))
            description_lower = description_text.lower()
            
            # 1. BASE SCORE
            score = 0
            
            # 1a. Applied Boost (Ultra Priority)
            if is_applied:
                score += 1000
            
            # 1b. Title Boosts (High Priority)
            if any(good_word in title_lower for good_word in high_priority):
                score += 50
            
            # 1c. Standard Engineering Boost
            if any(term in title_lower for term in ["software", "engineer", "developer", "data"]):
                score += 10

            # 2. SOFT FILTERS: YOE Penalty
            # Architecture: Penalty = (extracted_min - limit) * -100
            # Skips for Applied, "Entry-level" Titles, or Neutral Titles (II, III)
            bypass_keywords = ['intern', 'new grad', 'entry level', 'university grad', 'junior'] + self.neutral_keywords
            if not is_applied and not any(kw in title_lower for kw in bypass_keywords):
                min_yoe = self.extract_min_years_experience(description_text)
                if min_yoe > max_exp_limit:
                    # [AI AGENT CONTEXT]: Aggressive penalty to ensure drift is impossible.
                    penalty = (min_yoe - max_exp_limit) * self.yoe_penalty_multiplier
                    score += penalty
                    logger.debug(f"YOE Penalty for {job['title']}: {penalty} ({min_yoe} yrs > {max_exp_limit})")

            # 3. TIERED KEYWORD MATCHING (The "Precision Filter")
            # [AI AGENT CONTEXT]: Tier 1 (+10), Tier 2 (+20), Tier 3 (+50)
            tech_hits = 0
            domain_hits = 0
            
            # [AI AGENT CONTEXT]: Track specific hits for frontend transparency
            matched_tiers = {"tier1": [], "tier2": [], "tier3": []}

            # Tier 3 (Ultra-Niche: SCADA, PLC, etc.) -> +50
            for skill in self.tier3_skills:
                if skill in description_lower or skill in title_lower:
                    score += 50
                    domain_hits += 1
                    matched_tiers["tier3"].append(skill.upper())

            # Tier 2 (Strong Signal) -> +20
            for skill in self.tier2_skills:
                if skill in description_lower or skill in title_lower:
                    score += 20
                    tech_hits += 1
                    matched_tiers["tier2"].append(skill.upper())

            # Tier 1 (Foundational: Python, SQL) -> +10
            for skill in self.tier1_skills:
                if skill in description_lower or skill in title_lower:
                    score += 10
                    tech_hits += 1
                    matched_tiers["tier1"].append(skill.upper())
            
            # Intersection Multiplier (1.5x) - Retained for ultra-fit roles
            if tech_hits > 0 and domain_hits > 0:
                multiplier = 1.5 + (0.1 * min(tech_hits, domain_hits))
                score = int(score * multiplier)
            
            # 3a. Penalty for wrong-stack skills (Soft Negative)
            for penalty_skill in penalty_skills:
                if penalty_skill in description_lower:
                    score -= 5

            # 4. RECENCY BOOST (Early Bird Flame 🔥)
            est_date = self.normalize_date_est(job.get('date_posted'))
            if not est_date:
                est_date = datetime.now(pytz.timezone('US/Eastern'))
            
            now = datetime.now(pytz.timezone('US/Eastern'))
            is_fresh = (now - est_date) < timedelta(hours=24) and (now - est_date) > timedelta(days=-1)
            if is_fresh:
                score += 50

            # 5. DISPLAY FORMATTING
            display_title = job['title']
            if is_applied:
                clean_title = str(display_title).replace("🔥 ", "").replace("✅ ", "")
                display_title = "✅ " + clean_title
            elif is_fresh:
                if "🔥" not in display_title:
                    display_title = "🔥 " + display_title
            
            # 5b. Restriction Analysis (Defensive & Performance Optimized)
            restriction_data = {"restricted": False, "reason": None, "mobility_status": "NEUTRAL"}
            drop_enabled = self.config.get('restrictions', {}).get('drop_restricted', False)
            
            if self.config.get('restrictions', {}).get('enabled', False):
                restriction_data = self.restriction_engine.analyze(description_text)
            
            # --- HARD DROP: Silently discard restricted roles ---
            if drop_enabled and restriction_data.get('restricted') and not is_applied:
                logger.info(f"🗑️ Hard Drop (Restriction): Skipping '{job['title']}' at {job['company']}")
                continue

            # --- STRICT MODE DROP: Discard jobs with negative scores ---
            # SRE QUALITY CHECK: "Golden Ticket" pattern.
            # Never drop a job the user has already interacted with (is_applied).
            if self.strict_mode and score < 0 and not is_applied:
                logger.info(f"🗑️ Hard Drop (Strict Mode): Skipping role '{job['title']}' ({score} pts)")
                continue

            processed_job = {
                "id": job['id'],
                "title": display_title,
                "company": job['company'],
                "location": job['location'],
                "url": job['url'],
                "score": score,
                "matched_tiers": matched_tiers,
                "date_posted": est_date.strftime('%Y-%m-%d %I:%M %p'),
                "is_applied": is_applied,
                "status": "Applied" if is_applied else "Active",
                "restriction_data": restriction_data,
                "fetch_date": datetime.now(pytz.utc).isoformat(),
                "raw_data": job.get('raw_data', {})
            }
            if is_applied:
                processed_job['applied_at'] = applied_map[job_id].get('applied_at')
            
            processed.append(processed_job)

        # Restore missing applied jobs (Ghost Jobs)
        # Scenario B: Job Missing + Applied
        processed_ids = {j['id'] for j in processed}
        for applied_job in applied_jobs:
            if applied_job['id'] not in processed_ids:
                # The job is missing from the web, but we applied.
                # We must resurrect it.
                
                # Clone it to avoid mutating original cache if we were caching
                ghost_job = applied_job.copy()
                
                # Update Title/Status
                title = ghost_job['title']
                if "✅" not in title:
                    title = "✅ " + str(title).replace("🔥 ", "")
                
                # Explicitly set title to indicate closed? 
                # User asked for status: "✅ Applied (Closed)"
                # But status is usually a separate field in my json structure.
                # However, for the title display in markdown, we might want it visible.
                
                # If the title strictly needs to be the name, we handle status in the description or separate field.
                # But for the report, the title is what's seen.
                # Let's append (Closed) to the title for visibility in the MD list.
                if "(Closed)" not in title:
                    title += " (Closed)"
                
                ghost_job['title'] = title
                ghost_job['score'] = ghost_job.get('score', 0) + 1000 # Keep at top
                ghost_job['is_applied'] = True
                ghost_job['status'] = 'Applied (Closed)' # Explicit status
                ghost_job['is_ghost'] = True
                
                processed.append(ghost_job)

        # Re-sort by Score High->Low
        processed.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Processing complete: {len(processed)} jobs retained.")
        return processed
