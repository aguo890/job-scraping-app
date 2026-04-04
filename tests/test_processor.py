import pytest
import logging
from processor import JobProcessor

@pytest.fixture
def processor(tmp_path):
    config = {
        'keywords': {
            'exclude': [],
            'high_priority': ['intern', 'new grad']
        },
        'filtering': {
            'is_enabled': True,
            'max_years_experience': 3
        }
    }
    
    # Create isolated mock state
    mock_file = tmp_path / "mock_applied_jobs.json"
    mock_file.write_text("[]")
    
    # Inject into config
    if isinstance(config, dict):
        config['applied_jobs_path'] = str(mock_file)
    else:
        config.applied_jobs_path = str(mock_file)
        
    return JobProcessor(config)

def test_extract_yoe_valid(processor):
    """Test standard experience extraction."""
    texts = [
        "3 years of experience",
        "At least 5 years of work",
        "Minimum 2+ years of experience required",
        "3-5 years of work experience"
    ]
    expected = [3, 5, 2, 3] # Note: current regex takes the first group (\d+) then max()
    for text, exp in zip(texts, expected):
        assert processor.extract_min_years_experience(text) == exp

def test_extract_yoe_false_positives(processor):
    """Test that unrelated numbers and large years are ignored."""
    texts = [
        "Summer 2026",
        "10 years of personal growth", # Missing 'experience' or 'work' context in regex
        "Windows 10",
        "HTML5",
        "Join our team of 20 engineers"
    ]
    for text in texts:
        assert processor.extract_min_years_experience(text) == 0

def test_process_jobs_bypass(processor):
    """Test that Intern/New Grad titles bypass the YOE check."""
    jobs = [{
        "id": "1",
        "title": "Software Engineering Intern",
        "company": "TestCorp",
        "location": "Remote",
        "url": "http://test.com",
        "description": "Requires 10 years of experience" # High YOE in description
    }]
    
    # max_exp in fixture is 3
    processed = processor.process_jobs(jobs)
    assert len(processed) == 1
    # Check that the core title is correct (it might have a 🔥 icon)
    assert "Software Engineering Intern" in processed[0]['title']

def test_process_jobs_no_bypass_for_description(processor):
    """Test that keywords in description do NOT bypass the YOE check (prevent Senior bypass)."""
    jobs = [{
        "id": "2",
        "title": "Senior Software Engineer",
        "company": "TestCorp",
        "location": "Remote",
        "url": "http://test.com",
        "date_posted": "2024-01-01",
        "description": "Requires 8 years of experience. We also hire interns." 
    }]
    
    processed = processor.process_jobs(jobs)
    # Should be penalized because it requires 8 years and title is NOT entry-level
    assert len(processed) == 1
    assert processed[0]['score'] < 0  # Verify soft penalty was applied

def test_process_jobs_disqualification(processor):
    """Test that non-entry roles are disqualified by high YOE."""
    jobs = [{
        "id": "3",
        "title": "Software Engineer",
        "company": "TestCorp",
        "location": "Remote",
        "url": "http://test.com",
        "date_posted": "2024-01-01",
        "description": "Requires 5 years of experience"
    }]
    
    processed = processor.process_jobs(jobs)
    # Should be penalized because it requires 5 years and title is NOT entry-level
    assert len(processed) == 1
    assert processed[0]['score'] < 0  # Verify soft penalty was applied
