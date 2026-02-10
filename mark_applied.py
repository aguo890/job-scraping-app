#!/usr/bin/env python3
"""
Script to mark a job as applied.
Usage: python mark_applied.py <job_url_or_id>
"""

import sys
import json
import os
import argparse
from datetime import datetime

DATA_DIR = 'data'
JOBS_FILE = os.path.join(DATA_DIR, 'jobs_agg.json')
APPLIED_FILE = os.path.join(DATA_DIR, 'applied_jobs.json')

def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # handle both list and dict wrapper
            if isinstance(data, dict) and 'jobs' in data:
                return data['jobs']
            return data
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []

def save_json(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved to {filepath}")
    except Exception as e:
        print(f"Error saving {filepath}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Mark a job as applied.')
    parser.add_argument('identifier', help='Job URL or ID')
    args = parser.parse_args()

    identifier = args.identifier.strip()
    
    # 1. Load latest scrape
    latest_jobs = load_json(JOBS_FILE)
    if not latest_jobs:
        print("No job data found. Run the scraper first.")
        return

    # 2. Find the job
    target_job = None
    for job in latest_jobs:
        if str(job['id']) == identifier or job['url'] == identifier:
            target_job = job
            break
    
    if not target_job:
        print(f"Job not found in {JOBS_FILE} matching '{identifier}'")
        # Optional: Ask user if they want to enter details manually? 
        # For now, simplistic approach.
        return

    print(f"Found job: {target_job['title']} at {target_job['company']}")

    # 3. Load applied file
    applied_jobs = load_json(APPLIED_FILE)
    if isinstance(applied_jobs, dict): # Should be list, but just in case
        applied_jobs = []

    # 4. Check if already exists
    for job in applied_jobs:
        if job['id'] == target_job['id']:
            print("Job is already marked as applied.")
            return

    # 5. Add to applied list
    # Add metadata about when we applied
    target_job['applied_at'] = datetime.now().isoformat()
    target_job['applied'] = True
    
    applied_jobs.append(target_job)
    save_json(APPLIED_FILE, applied_jobs)
    print(f"Successfully marked job as applied!")

if __name__ == "__main__":
    main()
