import json
import os
from datetime import datetime, timedelta
import pytz
from dateutil import parser
import re
import logging

logger = logging.getLogger(__name__)

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
        # Note: 'exclude' key is used in the new config, but keeping 'exclude_keywords' check for backward compat if needed
        # The user's new config uses 'exclude', so we map that.
        self.exclude_keywords = self.config.get('keywords', {}).get('exclude', [])
        self.high_priority_keywords = self.config.get('keywords', {}).get('high_priority', [])
        
    def extract_min_years_experience(self, text):
        """
        Extracts the minimum years of experience required from text.
        Returns the highest 'minimum' found, or 0 if none.
        """
        # Pattern explanation:
        # 1. Look for digits (\d+)
        # 2. Optional: Allow '3+' or '3-5' format
        # 3. Anchor to the word 'year' or 'yrs'
        # 4. robustly ignore 'HTML5' or 'Windows 10' by ensuring word boundaries
        
        # Matches: "5+ years", "3-5 years", "minimum of 4 years", "at least 2 years"
        pattern = r'(?i)(?:min|minimum|at least)?\s*(\d+)\s*(?:[-–]\s*\d+)?\+?\s*y(?:ea)?rs?'
        
        matches = re.findall(pattern, text)
        
        # Filter out likely false positives (e.g., years > 15 usually implies data noise)
        valid_years = [int(m) for m in matches if int(m) < 15]
        
        if not valid_years:
            return 0
            
        # If multiple requirements found, use the HIGHEST minimum
        return max(valid_years)

    def normalize_location(self, location):
        """Standardize location string"""
        if not location:
            return "Remote"
        return str(location).strip()

    def is_us_location(self, location):
        """
        Check if location is US-based or Remote.
        Adjust logic as needed for specific requirements.
        """
        if not location:
            return True # Default to include if unknown? Or False? Assuming True for safety.
        
        loc_lower = location.lower()
        
        # Allow Remote
        if "remote" in loc_lower:
            return True
            
        # Allow US locations
        us_identifiers = ["united states", "usa", "u.s.", "us", "ca", "ny", "tx", "wa", "ma", "nc", "dc", "va"]
        # Basic check: if any identifier is in the string. 
        # CAUTION: "us" matches "austin" or "industry". 
        # Better: check for ", us" or state codes.
        
        # Simple permissive check for now since we are scraping US-centric boards mostly
        # Real logic would be more complex.
        return True 

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
        logger.info(f"Processing {len(jobs)} jobs")
        processed = []
        seen_ids = set()
        
        # Load applied jobs configuration
        applied_jobs = self.load_applied_jobs()
        applied_ids = {j['id'] for j in applied_jobs}
        applied_map = {j['id']: j for j in applied_jobs}

        # Load filtering lists
        high_priority = [k.lower() for k in self.config['keywords'].get('high_priority', [])]
        exclude_words = [k.lower() for k in self.config['keywords'].get('exclude', [])]
        preferred_skills = [k.lower() for k in self.config.get('preferred_skills', [])]
        
        # Experience Filtering Config
        filter_config = self.config.get('filtering', {})
        is_filter_enabled = filter_config.get('is_enabled', False)
        max_exp = filter_config.get('max_years_experience', 5)

        for job in jobs:
            job_id = job['id']
            if job_id in seen_ids: continue
            seen_ids.add(job_id)
            
            is_applied = job_id in applied_ids
            
            # 1. Normalize & Filter Location (PRESERVED FEATURE)
            job['location'] = self.normalize_location(job.get('location'))
            # If applied, bypass location filter
            if not is_applied and not self.is_us_location(job['location']):
                logger.debug(f"Skipping non-US location: {job['location']}")
                continue

            title_lower = job['title'].lower()
            description_text = str(job.get('description', ''))
            description_lower = description_text.lower()
            
            # 2. THE TRASH FILTER
            # If applied, bypass keyword filter? Maybe.
            if not is_applied and any(bad_word in title_lower for bad_word in exclude_words):
                logger.debug(f"Excluding job: {job['title']} (Filtered Word)")
                continue
            
            # 3. EXPERIENCE FILTER (New Feature)
            if not is_applied and is_filter_enabled:
                full_text = f"{job['title']} {description_text}"
                required_exp = self.extract_min_years_experience(full_text)
                if required_exp > max_exp:
                    logger.info(f"Skipping {job['title']}: Requires {required_exp} years (Limit: {max_exp})")
                    continue

            # 4. SCORING LOGIC
            score = 0
            
            # Boost for "Intern/New Grad" (High Priority)
            if any(good_word in title_lower for good_word in high_priority):
                score += 20  # Huge boost for internships
            
            # Boost for standard Engineering terms
            if "software" in title_lower or "engineer" in title_lower or "developer" in title_lower:
                score += 5
                
            # Boost for Skill Matches (Keyword Matcher)
            matches = 0
            for skill in preferred_skills:
                if skill in description_lower or skill in title_lower:
                    matches += 1
                    score += 5
            
            # 5. EARLY BIRD FLAME 🔥
            est_date = self.normalize_date_est(job.get('date_posted'))
            formatted_date = est_date.strftime('%Y-%m-%d %I:%M %p') if est_date else ""
            
            is_fresh = False
            if est_date:
                now = datetime.now(pytz.timezone('US/Eastern'))
                # If future date (timezone quirk), clamp it? No, just check delta.
                if (now - est_date) < timedelta(hours=24) and (now - est_date) > timedelta(days=-1):
                    score += 50  # Push to very top
                    is_fresh = True

            # Format Title with Icon
            display_title = job['title']
            if is_applied:
                display_title = "✅ " + display_title.replace("🔥 ", "") # applied overrides fire? or keep both?
                score += 1000 # Keep at top top
            elif is_fresh:
                display_title = "🔥 " + display_title
            
            processed_job = {
                "id": job['id'],
                "title": display_title,
                "company": job['company'],
                "location": job['location'],
                "url": job['url'],
                "score": score,
                "date_posted": formatted_date,
                "keywords_matched": [], # could populate with matches if desired
                "raw_data": job.get('raw_data', {}),
                "is_applied": is_applied
            }
            if is_applied:
                # Merge any extra metadata from applied file if needed
                processed_job['applied_at'] = applied_map[job_id].get('applied_at')
            
            processed.append(processed_job)

        # Restore missing applied jobs (Ghost Jobs)
        processed_ids = {j['id'] for j in processed}
        for applied_job in applied_jobs:
            if applied_job['id'] not in processed_ids:
                # This job was applied to but is no longer in the scrape
                # We need to add it back
                # Ensure title has checkmark
                title = applied_job['title']
                if "✅" not in title:
                    title = "✅ " + title.replace("🔥 ", "")
                
                # Mark as ghost/closed?
                title += " (Post Closed?)"
                
                # Add to processed
                # Use stored score but maybe boost it to keep it visible?
                ghost_job = applied_job.copy()
                ghost_job['title'] = title
                ghost_job['score'] = ghost_job.get('score', 0) + 1000
                ghost_job['is_applied'] = True
                ghost_job['status'] = 'closed'
                
                processed.append(ghost_job)

        # Re-sort by Score High->Low
        processed.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Processing complete: {len(processed)} jobs retained.")
        return processed
