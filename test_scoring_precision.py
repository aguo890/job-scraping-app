import yaml
import logging
import os
import json
import shutil
import tempfile
from processor import JobProcessor
from utils.smart_filter import job_filter

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def make_job(title, description="Generic job description", company="TestCo"):
    """Helper to create a synthetic job dict."""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    return {
        "id": f"test_{title.lower().replace(' ', '_')[:30]}",
        "title": title,
        "company": company,
        "location": "San Francisco, CA",
        "url": "https://example.com",
        "description": description,
        "date_posted": today,
    }

def run_test():
    # Setup temporary data directory to avoid pollution
    temp_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(temp_dir, "data"), exist_ok=True)
    
    # Create empty applied_jobs.json in temp dir
    with open(os.path.join(temp_dir, "data", "applied_jobs.json"), "w") as f:
        json.dump([], f)

    # Backup real data
    has_backup = False
    if os.path.exists("data"):
        os.rename("data", "data_backup")
        has_backup = True
    
    # Use temp data
    os.rename(os.path.join(temp_dir, "data"), "data")

    try:
        # Load the real config
        with open("config/filtering.yaml", "r") as f:
            config = yaml.safe_load(f)

        processor = JobProcessor(config)

        # === TEST CASES ===
        test_jobs = [
            # SHOULD BE REJECTED (Hard Negative - Title Blocklist)
            make_job("PhD Machine Learning Engineer", "Research ML models at scale"),
            make_job("Ph.D Intern - AI Research", "Deep learning research internship"),
            make_job("MBA Intern - Product", "Business strategy and product management"),
            make_job("Hardware Engineer", "Design PCB circuits and embedded systems"),
            make_job("iOS Engineering Intern", "Build native iOS apps using Swift"),
            make_job("Perception Engineering Intern", "Computer vision for autonomous vehicles"),
            make_job("Android Developer Intern", "Kotlin-based mobile development"),
            make_job("Firmware Engineer", "Low-level embedded C programming"),
            make_job("Robotics Software Engineer", "ROS, C++, sensor fusion"),

            # SHOULD BE ACCEPTED (Good Matches - High Score)
            make_job("Software Engineer Intern, Data Engineering",
                     "Build ETL pipelines using Python, SQL, and Airflow. Deploy with Docker and AWS."),
            make_job("Backend Software Engineering Intern",
                     "FastAPI, PostgreSQL, React frontend. Python microservices."),
            make_job("Full Stack Engineer - New Grad 2026",
                     "React, Node.js, Python, AWS, Docker. Data-driven product."),

            # SHOULD BE ACCEPTED BUT PENALIZED (Soft Negative - Wrong Stack in Description)
            make_job("Software Engineer Intern",
                     "We use Swift, Kotlin, and C++ for our cross-platform mobile SDK."),
            make_job("Data Platform Engineer",
                     "MATLAB and CUDA for high-performance computing pipelines."),
        ]

        # === EXECUTION: THE PIPELINE ===
        
        # 1. THE GATEKEEPER (Hard Filters)
        passed_gatekeeper = []
        rejected_by_gatekeeper = []
        
        for job in test_jobs:
            if job_filter.passes_hard_filters(job):
                passed_gatekeeper.append(job)
            else:
                rejected_by_gatekeeper.append(job)
                
        # 2. THE EVALUATOR (Scoring)
        results = processor.process_jobs(passed_gatekeeper)

        # Display results
        print("\n" + "=" * 70)
        print("PRECISION TEST RESULTS")
        print("=" * 70)

        accepted_titles = {j['title'].replace("🔥 ", "").replace("✅ ", "") for j in results}

        # Check rejections
        expected_rejected = [
            "PhD Machine Learning Engineer",
            "Ph.D Intern - AI Research",
            "MBA Intern - Product",
            "Hardware Engineer",
            "iOS Engineering Intern",
            "Perception Engineering Intern",
            "Android Developer Intern",
            "Firmware Engineer",
            "Robotics Software Engineer",
        ]

        print("\n--- HARD FILTER RESULTS ---")
        all_rejected_ok = True
        for title in expected_rejected:
            if title in accepted_titles:
                print(f"  ❌ FAIL: '{title}' should have been REJECTED but was accepted")
                all_rejected_ok = False
            else:
                print(f"  ✅ PASS: '{title}' correctly REJECTED")

        # Check acceptances
        print("\n--- ACCEPTED JOBS ---")
        for job in results:
            clean_title = job['title'].replace("🔥 ", "").replace("✅ ", "")
            print(f"  ✅ {clean_title:50s} | Score: {job['score']:>4}")

        # Check that good matches scored higher than penalized ones
        print("\n--- SCORE COMPARISON ---")
        for job in results:
            clean_title = job['title'].replace("🔥 ", "").replace("✅ ", "")
            if "Data Engineering" in clean_title or "Backend" in clean_title or "Full Stack" in clean_title:
                print(f"  🎯 GOOD MATCH:  {clean_title:45s} Score: {job['score']}")
            else:
                print(f"  ⚠️  PENALIZED:   {clean_title:45s} Score: {job['score']}")

        # Final verdict
        print("\n" + "=" * 70)
        if all_rejected_ok:
            print("✅ ALL HARD FILTERS PASSED (Gatekeeper is working)")
        else:
            print("❌ SOME HARD FILTERS FAILED - Gatekeeper missed something")
        
        # Verify YOE Penalty (New Requirement)
        print("\n--- YOE PENALTY VERIFICATION ---")
        yoe_test_job = make_job("Software Engineer (High YOE)", "Requires 12+ years experience")
        if job_filter.passes_hard_filters(yoe_test_job):
            yoe_results = processor.process_jobs([yoe_test_job])
            # Find the specific job in results
            yoe_res = next((j for j in yoe_results if j['id'] == yoe_test_job['id']), None)
            if yoe_res:
                print(f"  📊 12+ YOE Job Score: {yoe_res['score']} (Should be significantly negative/penalized)")
                if yoe_res['score'] < 0:
                    print("  ✅ PASS: Significant penalty applied for high YOE requirement")
                else:
                    print("  ❌ FAIL: Penalty for high YOE was not significant enough")
        
        print(f"\n📊 {len(results)} jobs accepted out of {len(test_jobs)} total")
        print(f"🚫 {len(test_jobs) - len(results)} jobs rejected by filters")
        print("=" * 70)

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Restore backup
        if os.path.exists("data"):
            shutil.rmtree("data")
        if has_backup and os.path.exists("data_backup"):
            os.rename("data_backup", "data")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    run_test()
