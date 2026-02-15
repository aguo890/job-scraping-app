
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.location_filter import is_us_or_remote

DATA_FILE = os.path.join('data', 'jobs_agg.json')

def clean_jobs():
    if not os.path.exists(DATA_FILE):
        print("No data file found.")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    jobs = data.get('jobs', [])
    initial_count = len(jobs)
    
    cleaned_jobs = []
    removed_count = 0
    
    print(f"Checking {initial_count} jobs against location filters...")
    
    for job in jobs:
        loc = job.get('location', '')
        if is_us_or_remote(loc):
            cleaned_jobs.append(job)
        else:
            print(f"  [REMOVED] {job.get('company')} - {job.get('title')} ({loc})")
            removed_count += 1
            
    data['jobs'] = cleaned_jobs
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"\nDone! Removed {removed_count} jobs. Remaining: {len(cleaned_jobs)}")

if __name__ == "__main__":
    clean_jobs()
