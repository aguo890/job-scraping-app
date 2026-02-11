#!/usr/bin/env python3
"""
Test script to verify the precision of the scoring algorithm.
Tests hard negative filters (title_blocklist) and soft penalties (penalty_skills).
"""
import yaml
import logging
from processor import JobProcessor

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def make_job(title, description="Generic job description", company="TestCo"):
    """Helper to create a synthetic job dict."""
    return {
        "id": f"test_{title.lower().replace(' ', '_')[:30]}",
        "title": title,
        "company": company,
        "location": "San Francisco, CA",
        "url": "https://example.com",
        "description": description,
        "date_posted": "2026-02-10",
    }

def run_test():
    # Load the real config
    with open("config/keywords.yaml", "r") as f:
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

    # Run through the processor
    results = processor.process_jobs(test_jobs)

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
        print("✅ ALL HARD FILTERS PASSED")
    else:
        print("❌ SOME HARD FILTERS FAILED - Review above")
    print(f"📊 {len(results)} jobs accepted out of {len(test_jobs)} total")
    print(f"🚫 {len(test_jobs) - len(results)} jobs rejected by filters")
    print("=" * 70)

if __name__ == "__main__":
    run_test()
