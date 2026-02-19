import pytest
from fetchers import GreenhouseFetcher, LeverFetcher, AshbyFetcher
from utils.schemas import JobListing
from unittest.mock import MagicMock

# Clearly indicated mock data payloads
MOCK_GREENHOUSE_DATA = {
    "id": "gh_123",
    "title": "Software Engineer",
    "absolute_url": "https://boards.greenhouse.io/test/jobs/123",
    "location": {"name": "Remote"},
    "content": "Description info",
    "updated_at": "2024-02-19T10:00:00Z"
}

MOCK_LEVER_DATA = {
    "id": "lv_456",
    "text": "Data Scientist",
    "hostedUrl": "https://jobs.lever.co/test/456",
    "categories": {"location": "New York"},
    "description": "Lever description",
    "createdAt": 1708336800000
}

MOCK_ASHBY_DATA = {
    "id": "ash_789",
    "title": "Backend Engineer",
    "jobUrl": "https://jobs.ashbyhq.com/test/789",
    "location": "Global Remote",
    "description": "Ashby description",
    "publishedDate": "2024-02-19"
}

def test_greenhouse_mapping_resilience():
    # Mock the internal logic of fetcher
    # We test if the from_dict pattern in the fetcher's loop is resilient
    # We'll simulate the dict that the fetcher attempts to pass to JobListing.from_dict
    payload = {
        'id': f"gh_test_{MOCK_GREENHOUSE_DATA.get('id')}",
        'title': MOCK_GREENHOUSE_DATA.get('title'),
        'company': "GreenhouseCorp",
        'location': "Remote",
        'url': MOCK_GREENHOUSE_DATA.get('absolute_url'),
        'description': MOCK_GREENHOUSE_DATA.get('content'),
        'date_posted': MOCK_GREENHOUSE_DATA.get('updated_at'),
        'source': 'greenhouse',
        'score': 100,
        'match_reason': "Good match",
        'raw_data': MOCK_GREENHOUSE_DATA,
        'unexpected_extra': 'this should be ignored'
    }
    
    job = JobListing.from_dict(payload)
    assert job.id == "gh_test_gh_123"
    assert job.company == "GreenhouseCorp"
    assert job.raw_data["id"] == "gh_123"
    assert not hasattr(job, 'unexpected_extra')

def test_lever_mapping_resilience():
    payload = {
        'id': f"lever_test_{MOCK_LEVER_DATA.get('id')}",
        'title': MOCK_LEVER_DATA.get('text'),
        'company': "LeverCorp",
        'location': "New York",
        'url': MOCK_LEVER_DATA.get('hostedUrl'),
        'description': MOCK_LEVER_DATA.get('description'),
        'date_posted': "2024-02-19",
        'source': 'lever',
        'score': 80,
        'match_reason': "Match",
        'raw_data': MOCK_LEVER_DATA
    }
    job = JobListing.from_dict(payload)
    assert job.id == "lever_test_lv_456"
    assert job.company == "LeverCorp"

def test_ashby_mapping_resilience():
    payload = {
        'id': f"ashby_test_{MOCK_ASHBY_DATA.get('id')}",
        'title': MOCK_ASHBY_DATA.get('title'),
        'company': "AshbyCorp",
        'location': "Global Remote",
        'url': MOCK_ASHBY_DATA.get('jobUrl'),
        'description': MOCK_ASHBY_DATA.get('description'),
        'date_posted': MOCK_ASHBY_DATA.get('publishedDate'),
        'source': 'ashby',
        'score': 90,
        'match_reason': "Great Match",
        'raw_data': MOCK_ASHBY_DATA
    }
    job = JobListing.from_dict(payload)
    assert job.id == "ashby_test_ash_789"
    assert job.company == "AshbyCorp"
