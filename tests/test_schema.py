import pytest
import logging
from utils.schemas import JobListing

def test_job_listing_sanitization():
    """Test that HTML is stripped and whitespace is trimmed from all fields."""
    job = JobListing(
        id="gh_test_123",
        title="  Software Engineer  ",
        company="<b>Google</b>",
        url="https://jobs.google.com/123",
        location="  Remote (NYC)  ",
        description="<p>Help us build the future.</p>"
    )
    job.sanitize()
    
    assert job.title == "Software Engineer"
    assert job.company == "Google"
    assert job.location == "Remote (NYC)"
    assert job.description == "Help us build the future."

def test_job_listing_validation_success():
    """Test that a complete job record passes validation."""
    valid_data = {
        "id": "lever_456",
        "title": "Product Designer",
        "company": "Figma",
        "url": "https://figma.com/jobs/456"
    }
    job = JobListing(**valid_data)
    assert job.is_valid() is True

def test_job_listing_validation_failure(caplog):
    """Test that missing required fields trigger validation failure and explicit logging."""
    with caplog.at_level(logging.WARNING):
        # Missing company and url
        invalid_job = JobListing(
            id="ashby_789",
            title="Ghost Developer",
            company="",
            url=""
        )
        assert invalid_job.is_valid() is False
        
        # Check for explicit warning in logs
        assert "Validation Failed - Dropped Job Record" in caplog.text
        assert "Missing fields: ['company', 'url']" in caplog.text

def test_job_listing_from_dict_extra_fields():
    """Test that JobListing.from_dict ignores unexpected fields (resilience)."""
    data = {
        "id": "gh_1",
        "title": "Engineer",
        "company": "Test",
        "url": "http://test.com",
        "extra_garbage": "should be ignored",
        "keywords_matched": ["python"]
    }
    job = JobListing.from_dict(data)
    assert job.is_valid() is True
    assert job.title == "Engineer"
    # Check that extra fields are not present on the object
    assert not hasattr(job, "extra_garbage")
    assert not hasattr(job, "keywords_matched")

def test_job_listing_raw_data_memory_isolation():
    """Verify that distinct instances do not share the same raw_data dictionary in memory."""
    job1 = JobListing(id="1", title="A", company="B", url="C")
    job2 = JobListing(id="2", title="X", company="Y", url="Z")
    
    # Mutate job1's raw data
    job1.raw_data["test_key"] = "contaminated"
    
    # Assert job2 remains pristine (proves field(default_factory=dict) works)
    assert "test_key" not in job2.raw_data

def test_job_listing_to_dict():
    """Test correctly converting schema to dict for JSON serialization."""
    job_data = {
        "id": "test_id",
        "title": "Test Title",
        "company": "Test Company",
        "url": "http://test.com"
    }
    job = JobListing(**job_data)
    d = job.to_dict()
    assert d["id"] == "test_id"
    assert d["title"] == "Test Title"
    assert isinstance(d, dict)
