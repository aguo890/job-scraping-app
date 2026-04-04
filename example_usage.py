#!/usr/bin/env python3
"""
Example usage script - demonstrates how to use the job scraping components
"""
from fetchers import GreenhouseFetcher
from processor import JobProcessor
from reporter import JobReporter

# Example: Fetch jobs from a single company
def example_greenhouse_fetch():
    """Example: Fetch jobs from Greenhouse"""
    print("Example: Fetching jobs from Greenhouse API")
    fetcher = GreenhouseFetcher()
    
    # Fetch jobs from a company (e.g., OpenAI)
    jobs = fetcher.fetch_jobs("openai", "OpenAI")
    print(f"Fetched {len(jobs)} jobs from OpenAI")
    
    if jobs:
        print(f"\nFirst job: {jobs[0]['title']} at {jobs[0]['company']}")
    
    return jobs


def example_job_processing():
    """Example: Process and rank jobs"""
    print("\nExample: Processing and ranking jobs")
    
    # Sample job data
    sample_jobs = [
        {
            'id': 'test_1',
            'title': 'Senior Software Engineer',
            'company': 'Tech Corp',
            'location': 'San Francisco, CA',
            'description': 'Looking for a Senior Software Engineer with Python and React experience',
            'url': 'https://example.com/job1',
            'source': 'greenhouse'
        },
        {
            'id': 'test_2',
            'title': 'Junior Developer',
            'company': 'Startup Inc',
            'location': 'Remote',
            'description': 'Entry-level position for a developer',
            'url': 'https://example.com/job2',
            'source': 'lever'
        }
    ]
    
    # Load keywords config
    import yaml
    with open('config/keywords.yaml', 'r') as f:
        keywords_config = yaml.safe_load(f)
    
    # Process jobs
    processor = JobProcessor(keywords_config)
    processed = processor.process_jobs(sample_jobs)
    
    print(f"Processed {len(processed)} jobs")
    for job in processed:
        print(f"  - {job['title']} (Score: {job['score']:.1f})")
    
    return processed


def example_report_generation():
    """Example: Generate reports"""
    print("\nExample: Generating reports")
    
    # Sample processed jobs
    sample_jobs = [
        {
            'id': 'test_1',
            'title': 'Senior Software Engineer',
            'company': 'Tech Corp',
            'location': 'San Francisco, CA',
            'description': 'Great opportunity for an experienced engineer',
            'url': 'https://example.com/job1',
            'source': 'greenhouse',
            'score': 25.0,
            'processed_at': '2024-01-15T10:00:00'
        }
    ]
    
    # Generate reports
    reporter = JobReporter()
    reports = reporter.generate_reports(sample_jobs)
    
    print("Generated reports:")
    for report_type, path in reports.items():
        print(f"  - {report_type}: {path}")
    
    return reports


if __name__ == "__main__":
    print("=" * 60)
    print("Job Scraping Application - Usage Examples")
    print("=" * 60)
    
    # Note: These examples may fail if network access is restricted
    # or if API endpoints are unavailable
    
    try:
        # Example 1: Processing jobs
        processed_jobs = example_job_processing()
        
        # Example 2: Generate reports (with sample data)
        if processed_jobs:
            reporter = JobReporter()
            reports = reporter.generate_reports(processed_jobs)
            print("\nReports generated successfully!")
            print(f"Check: {reports['json']}")
            print(f"Check: {reports['markdown']}")
    
    except Exception as e:
        print(f"\nError in examples: {e}")
        print("This is expected if network access is restricted.")
    
    print("\n" + "=" * 60)
    print("For full functionality, run: python main.py")
    print("=" * 60)
