import sys
import os
import yaml

# Ensure project root is in path
sys.path.insert(0, os.path.join(os.getcwd(), 'job-scraping-app'))
from utils.smart_filter import RestrictionEngine

def run_test_scenario(name, config, test_cases):
    print(f"\n--- 🛡️ Scenario: {name} ---")
    engine = RestrictionEngine(config)
    
    print("-" * 100)
    print(f"{'Text':<50} | {'Exp Res':<7} | {'Act Res':<7} | {'Act Status':<10} | {'Rating'}")
    print("-" * 100)
    
    all_passed = True
    for text, expected_res, expected_status in test_cases:
        result = engine.analyze(text)
        actual_res = result['restricted']
        actual_status = result['mobility_status']
        
        passed = (actual_res == expected_res) and (actual_status == expected_status)
        if not passed: all_passed = False
        
        status_icon = "✅" if passed else "❌"
        print(f"{text[:50]:<50} | {str(expected_res):<7} | {str(actual_res):<7} | {actual_status:<10} | {status_icon}")
    
    return all_passed

def main():
    # 1. Test ONLY Sponsorship Toggle (Red Flags)
    sponsorship_cfg = {'needs_sponsorship': True, 'no_clearance': False, 'keywords': []}
    sponsorship_cases = [
        ("No visa sponsorship provided", True, "RESTRICTED"),
        ("H1-B sponsorship is not available", True, "RESTRICTED"),
        ("Work authorization required", True, "RESTRICTED"),
        ("Senior Backend Engineer", False, "NEUTRAL")
    ]
    
    # 2. Test ONLY Clearance Toggle (Federal & Defense Hardening)
    clearance_cfg = {'needs_sponsorship': False, 'no_clearance': True, 'keywords': []}
    clearance_cases = [
        ("Requires a Tier 5 background investigation", True, "RESTRICTED"),
        ("Must complete the SF-86 and e-QIP", True, "RESTRICTED"),
        ("Compliance with 22 CFR (ITAR) is mandatory", True, "RESTRICTED"),
        ("Must be a U. S. Person as defined by 8 U.S.C. 1324b(a)(3)", True, "RESTRICTED"), # Legal Hard Kill
        ("Software Developer", False, "NEUTRAL")
    ]
    
    # 3. Test Positive Green Flags (Sponsorship Friendly)
    friendly_cfg = {'needs_sponsorship': False, 'no_clearance': False, 'keywords': []}
    friendly_cases = [
        ("H1-B sponsorship is available for this role", False, "FRIENDLY"),
        ("Visa sponsorship provided for qualifying candidates", False, "FRIENDLY"),
        ("We participate in E-Verify", False, "NEUTRAL"), # E-Verify Trap Fix
        ("Frontend Developer", False, "NEUTRAL")
    ]
    
    # 4. Test False Positive Guardrails
    fp_cfg = {'needs_sponsorship': False, 'no_clearance': True, 'keywords': []}
    fp_cases = [
        ("Visit our store for a massive clearance sale!", False, "NEUTRAL"),
        ("Inventory clearance event at the warehouse", False, "NEUTRAL"),
        ("Requires a Top Secret clearance", True, "RESTRICTED")
    ]

    # 5. Priority Hierarchy (Hard Kill Overrides Friendly)
    priority_cfg = {'needs_sponsorship': True, 'no_clearance': True, 'keywords': []}
    priority_cases = [
        ("We will sponsor your H1-B, but you must be a U.S. Person (ITAR)", True, "RESTRICTED"),
        ("Sponsorship available for those with a Top Secret clearance", True, "RESTRICTED"),
        ("Engineering Intern - H1-B Welcome", False, "FRIENDLY")
    ]

    s1 = run_test_scenario("Sponsorship Preset (Negative)", sponsorship_cfg, sponsorship_cases)
    s2 = run_test_scenario("Clearance Preset (Hardened)", clearance_cfg, clearance_cases)
    s3 = run_test_scenario("Mobility Friendly (Positive)", friendly_cfg, friendly_cases)
    s4 = run_test_scenario("False Positive Guardrails", fp_cfg, fp_cases)
    s5 = run_test_scenario("Priority Hierarchy (Red > Green)", priority_cfg, priority_cases)

    if all([s1, s2, s3, s4, s5]):
        print("\n✨ ALL INTERNATIONAL MOBILITY SCENARIOS PASSED! ✨\n")
    else:
        print("\n⚠️ SCENARIO FAILURES DETECTED! ⚠️\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
