import json
import os
from datetime import datetime, timedelta
import pytz
from dateutil import parser
import re
import logging

logger = logging.getLogger(__name__)
from utils.location_filter import is_us_or_remote

class JobProcessor:
    def __init__(self, config_input):
        # RESILIENT INIT: Handle dict (from main.py) or str path
        if isinstance(config_input, dict):
            self.config = config_input
        else:
            with open(config_input, 'r') as f:
                import yaml
                self.config = yaml.safe_load(f)
        
        # Helper lists for filtering/scoring
        # Unified config uses 'titles' section for keywords
        self.exclude_keywords = self.config.get('titles', {}).get('exclude', [])
        self.high_priority_keywords = self.config.get('titles', {}).get('high_priority', [])
        
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
            path = os.path.join('data', 'applied_jobs.json')
            if not os.path.exists(path):
                return []
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error loading applied jobs: {e}")
            return []

    def process_jobs(self, jobs):
        """
        Evaluator: Applies Soft Filters and Scoring.
        Note: Hard filters (Banned titles, old dates) already handled by Gatekeeper.
        """
        logger.info(f"Evaluating {len(jobs)} jobs...")
        processed = []
        seen_ids = set()
        
        # Load context
        applied_jobs = self.load_applied_jobs()
        applied_ids = {j['id'] for j in applied_jobs}
        applied_map = {j['id']: j for j in applied_jobs}

        # Scoring Weights from Config
        high_priority = [k.lower() for k in self.config.get('titles', {}).get('high_priority', [])]
        preferred_skills = [k.lower() for k in self.config.get('preferred_skills', [])]
        penalty_skills = [k.lower() for k in self.config.get('penalty_skills', [])]
        
        # Domain Intersection Targets
        domain_keywords = {
            "linesight", "erp", "plc", "mes", "manufacturing", "scada", 
            "industry 4.0", "iiot", "smart factory", "automation", 
            "digital twin", "supply chain"
        }
        
        # Experience Config
        filter_config = self.config.get('filtering', {})
        max_exp_limit = filter_config.get('max_years_experience', 5)

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
            # Architecture: Penalty = (extracted_min - limit) * -10
            # Skips for Applied or "Entry-level" Titles
            bypass_keywords = ['intern', 'new grad', 'entry level', 'university grad', 'junior']
            if not is_applied and not any(kw in title_lower for kw in bypass_keywords):
                min_yoe = self.extract_min_years_experience(description_text)
                if min_yoe > max_exp_limit:
                    penalty = (min_yoe - max_exp_limit) * -10
                    score += penalty
                    logger.debug(f"YOE Penalty for {job['title']}: {penalty} ({min_yoe} yrs > {max_exp_limit})")

            # 3. INTERSECTION MULTIPLIER (The "Holy Grail" Boost)
            tech_hits = 0
            domain_hits = 0
            for skill in preferred_skills:
                if skill in description_lower or skill in title_lower:
                    if skill in domain_keywords:
                        domain_hits += 1
                        score += 15
                    else:
                        tech_hits += 1
                        score += 10
            
            # Linesight Multiplier (1.5x)
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
                clean_title = display_title.replace("🔥 ", "").replace("✅ ", "")
                display_title = "✅ " + clean_title
            elif is_fresh:
                if "🔥" not in display_title:
                    display_title = "🔥 " + display_title
            
            processed_job = {
                "id": job['id'],
                "title": display_title,
                "company": job['company'],
                "location": job['location'],
                "url": job['url'],
                "score": score,
                "date_posted": est_date.strftime('%Y-%m-%d %I:%M %p'),
                "is_applied": is_applied,
                "status": "Applied" if is_applied else "Active",
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
                    title = "✅ " + title.replace("🔥 ", "")
                
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
