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
        # Note: 'exclude' key is used in the new config, but keeping 'exclude_keywords' check for backward compat if needed
        # The user's new config uses 'exclude', so we map that.
        self.exclude_keywords = self.config.get('keywords', {}).get('exclude', [])
        self.high_priority_keywords = self.config.get('keywords', {}).get('high_priority', [])
        
    def extract_min_years_experience(self, text):
        """
        Extracts the minimum years of experience required from text.
        Returns the highest 'minimum' found, or 0 if none.
        Uses a restrictive regex to avoid false positives (e.g. years like 2026).
        """
        if not text:
            return 0
            
        # Restrictive pattern: matches 1-15 years/yrs followed by experience/work context
        pattern = r'\b([1-9]|1[0-5])\+?\s*(?:-\s*[1-9]\d*\s*)?(?:years?|yrs?)(?:\s+of\s+)?(?:experience|work)\b'
        
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        if not matches:
            return 0
            
        # Extract the numbers from matches
        valid_years = [int(m) for m in matches]
        
        return max(valid_years)

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
        title_blocklist = [k.lower() for k in self.config.get('title_blocklist', [])]
        penalty_skills = [k.lower() for k in self.config.get('penalty_skills', [])]
        
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
            
            # 2b. DEGREE & DOMAIN FILTER (Hard Negative)
            if not is_applied and any(blocked in title_lower for blocked in title_blocklist):
                logger.info(f"Excluding job: {job['title']} (Title Blocklist)")
                continue

            # 3. EXPERIENCE FILTER (Improved)
            if not is_applied and is_filter_enabled:
                # 3a. Title-Strict Bypass (Priority Acceptance)
                # Check title for keywords that imply entry-level, regardless of description text
                bypass_keywords = ['intern', 'new grad', 'entry level', 'university grad', 'junior']
                if any(kw in title_lower for kw in bypass_keywords):
                    logger.info(f"Priority Accepted: {job['title']} bypassed YOE check (Title match).")
                    required_exp = 0
                else:
                    # 3b. Structured data check (Future/Resilience)
                    # For now, we fall back to regex on description
                    required_exp = self.extract_min_years_experience(description_text)
                
                if required_exp > max_exp:
                    logger.info(f"Skipping {job['title']}: Requires {required_exp} years (Limit: {max_exp})")
                    continue

            # 4. SCORING LOGIC
            base_score = 0
            
            # Boost for "Intern/New Grad" (High Priority)
            if any(good_word in title_lower for good_word in high_priority):
                base_score += 20  # Huge boost for internships
            
            # Boost for standard Engineering terms
            if "software" in title_lower or "engineer" in title_lower or "developer" in title_lower:
                base_score += 5
                
            # Boost for Skill Matches & Domain Intersection
            tech_hits = 0
            domain_hits = 0
            domain_keywords = {
                "linesight", "erp", "plc", "mes", "manufacturing", "scada", 
                "industry 4.0", "iiot", "smart factory", "automation", 
                "digital twin", "supply chain"
            }
            
            for skill in preferred_skills:
                if skill in description_lower or skill in title_lower:
                    if skill in domain_keywords:
                        domain_hits += 1
                        base_score += 15
                    else:
                        tech_hits += 1
                        base_score += 10
            
            # Apply the Intersection Multiplier (The "Linesight" Boost)
            if tech_hits > 0 and domain_hits > 0:
                multiplier = 1.5 + (0.1 * min(tech_hits, domain_hits))
                score = int(base_score * multiplier)
            else:
                score = base_score
            
            # Penalty for wrong-stack skills (Soft Negative)
            for penalty in penalty_skills:
                if penalty in description_lower:
                    score -= 3
            
            # 5. EARLY BIRD FLAME 🔥
            est_date = self.normalize_date_est(job.get('date_posted'))
            # If no date_posted, default to current scrape time
            if not est_date:
                est_date = datetime.now(pytz.timezone('US/Eastern'))
            formatted_date = est_date.strftime('%Y-%m-%d %I:%M %p')
            
            is_fresh = False
            if est_date:
                now = datetime.now(pytz.timezone('US/Eastern'))
                # If future date (timezone quirk), clamp it? No, just check delta.
                if (now - est_date) < timedelta(hours=24) and (now - est_date) > timedelta(days=-1):
                    score += 50  # Push to very top
                    is_fresh = True

            # Format Title with Icon and Status
            # Scenario A: Job Found + Applied
            display_title = job['title']
            
            if is_applied:
                # Remove existing fire if present to avoid clutter, or keep it?
                # User pattern: "✅ " + title
                clean_title = display_title.replace("🔥 ", "")
                if "✅" not in clean_title:
                    display_title = "✅ " + clean_title
                
                score += 1000 # Boost to top
                # Ensure we track the status explicitly
                job['status'] = 'Applied' 
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
                "keywords_matched": [], 
                "raw_data": job.get('raw_data', {}),
                "is_applied": is_applied,
                "status": "Applied" if is_applied else "Active"
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
