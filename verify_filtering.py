import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath('.'))

from processor.py import JobProcessor # wait, file is processor.py but it might be in root.
# Looking at list_dir: processor.py is in C:\Users\19803\Projects\job-scraping-app\

import re
from datetime import datetime
import pytz

# Mock Config
config = {
    'keywords': {
        'high_priority': ['Intern'],
        'exclude': []
    },
    'preferred_skills': [],
    'filtering': {
        'is_enabled': True,
        'max_years_experience': 3
    }
}

# Test cases
test_jobs = [
    {"id": "1", "title": "SE", "description": "Requires 5+ years of Java", "company": "A", "location": "Remote"},
    {"id": "2", "title": "Early Career SE", "description": "Requires 1-3 years of experience", "company": "B", "location": "Remote"},
    {"id": "3", "title": "Frontend", "description": "Experience with HTML5 and CSS3", "company": "C", "location": "Remote"},
    {"id": "4", "title": "Support", "description": "Must be available 24/7", "company": "D", "location": "Remote"},
    {"id": "5", "title": "Senior Engineer", "description": "7+ years experience", "company": "E", "location": "Remote"},
    {"id": "6", "title": "Intern", "description": "New Grad or 0-1 years experience", "company": "F", "location": "Remote"},
]

from processor import JobProcessor

proc = JobProcessor(config)

processed = proc.process_jobs(test_jobs)

print(f"\nFiltering results (Max Exp: {config['filtering']['max_years_experience']}):")
retained_titles = [j['title'] for j in processed]
for job in test_jobs:
    status = "RETAINED" if any(job['title'] in t for t in retained_titles) else "FILTERED"
    print(f"- {job['title']}: {status}")

# Verify specific cases
expected_filtered = ["SE", "Senior Engineer"]
for title in expected_filtered:
    if any(title in t for t in retained_titles):
        print(f"FAILED: {title} should have been filtered.")
    else:
        print(f"PASSED: {title} was filtered.")
