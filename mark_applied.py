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
    parser.add_argument('--push', action='store_true', help='Automatically commit and push changes to GitHub')
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
    print(f"Successfully marked '{target_job['title']}' as applied!")

    # 6. Git Automation
    print("\nIMPORTANT: To persist this on the remote scraper, you must push this file.")
    try:
        import subprocess
        # Check if we should auto-push (could be an arg, but for now just ask or try)
        # Since this is a CLI tool, we can just try if the user passes a flag, 
        # but let's just do it if the user passed --push
        if getattr(args, 'push', False):
            print("Auto-pushing to GitHub...")
            subprocess.run(["git", "add", APPLIED_FILE], check=True)
            subprocess.run(["git", "commit", "-m", f"Mark applied: {target_job['title']}"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("Successfully pushed to GitHub!")
        else:
            print("Run the following to push manually:")
            print(f"  git add {APPLIED_FILE}")
            print(f"  git commit -m \"Mark applied: {target_job['title']}\"")
            print("  git push")
            print("\n(Tip: Run with --push next time to do this automatically)")

    except Exception as e:
        print(f"Git automation failed: {e}")

if __name__ == "__main__":
    main()
