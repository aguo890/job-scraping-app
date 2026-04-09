import sys
import os
from pathlib import Path

# Add root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from processor import JobProcessor
import logging

logging.basicConfig(level=logging.ERROR)

def test_tiered_weights():
    # [AI CONTEXT]: Inject deterministic mock config for fully decoupled testing
    mock_config = {
        "filtering": {"max_years_experience": 5, "strict_mode": False},
        "titles": {"high_priority": [], "neutral": [], "exclude": []},
        "tiered_skills": {
            "tier1": ["Python"],
            "tier2": ["Docker"],
            "tier3": ["SCADA"]
        },
        "restrictions": {"enabled": False}
    }
    
    # Initialize processor with override
    # Pass empty dict for config_input so it doesn't try to load a file
    processor = JobProcessor(config_input={}, config_override=mock_config)
    
    # Define test jobs with specific keywords
    test_jobs = [
        {"id": "tier1_hit", "title": "Dev", "company": "C1", "location": "R1", "url": "u1", "description": "Needs Python expertise"},
        {"id": "tier2_hit", "title": "Dev", "company": "C2", "location": "R2", "url": "u2", "description": "Needs Docker expertise"},
        {"id": "tier3_hit", "title": "Dev", "company": "C3", "location": "R3", "url": "u3", "description": "Needs SCADA expertise"},
        {"id": "multi_hit", "title": "Dev", "company": "C4", "location": "R4", "url": "u4", "description": "Needs Python and SCADA"}
    ]
    
    # Process
    results = processor._evaluate_and_score(test_jobs)
    results_map = {j['id']: j for j in results}
    
    # Verification
    # Note: 50 point freshness boost is active if date_posted is missing
    # We strip the boost for purity in this test comparison
    
    def get_base_score(job_id):
        # Subtract 50 if it was applied automatically for freshness
        score = results_map[job_id]['score']
        return score - 50 if score >= 50 else score

    print(f"Tier 1 (+10) Result: {get_base_score('tier1_hit')}")
    print(f"Tier 2 (+20) Result: {get_base_score('tier2_hit')}")
    print(f"Tier 3 (+50) Result: {get_base_score('tier3_hit')}")
    print(f"Multi Hit (+10 + 50 * 1.6) Result: {get_base_score('multi_hit')}")

    assert get_base_score('tier1_hit') == 10
    assert get_base_score('tier2_hit') == 20
    assert get_base_score('tier3_hit') == 50
    
    # Multi-hit logic: (10 + 50) * 1.6 = 96
    assert get_base_score('multi_hit') == 96 
    
    # Verify matched_tiers payload
    assert "PYTHON" in results_map['tier1_hit']['matched_tiers']['tier1']
    assert "DOCKER" in results_map['tier2_hit']['matched_tiers']['tier2']
    assert "SCADA" in results_map['tier3_hit']['matched_tiers']['tier3']
    
    print("\n✅ Tiered Scoring Test PASSED!")

if __name__ == "__main__":
    try:
        test_tiered_weights()
    except AssertionError:
        print("❌ Test FAILED: Assertion Error")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        sys.exit(1)
