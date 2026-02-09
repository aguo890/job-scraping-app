from utils.location_filter import is_us_or_remote

def test_locations():
    test_cases = {
        # Valid US/Remote
        "San Francisco, CA": True,
        "Remote - US": True,
        "New York City": True,
        "Austin, Texas": True,
        "Remote": True,
        "Foster City, CA": True,
        "Mountain View": True,
        "Durham, NC": True, # Should pass check 4 or 2 if added

        # Invalid International
        "London, UK": False,
        "Toronto, Canada": False,
        "Bengaluru, India": False,
        "Remote - Spain": False,
        "PL-Warsaw": False,
        "Rome, Italy": False,
        "Paris": False,
        "Berlin": False,
        "Sydney, Australia": False,
        
        # New Stricter Checks
        "Asia": False,
        "Taiwan, Taipei": False,
        "Kazakhstan, Almaty": False,
        "South East Asia": False,
        "Latin America": False,
        "Global": False,
        "Europe": False,
        "Seoul, Korea": False,
        "Tokyo": False,
        "Anywhere (Global)": False
    }

    print("--- Testing Stricter Location Filter ---")
    failed = False
    for loc, expected in test_cases.items():
        result = is_us_or_remote(loc)
        status = "✅" if result == expected else "❌"
        if result != expected:
            failed = True
        print(f"{status} '{loc}': Got {result}, Expected {expected}")

    if not failed:
        print("\nAll location tests passed!")
    else:
        print("\nSome tests failed. Adjust filter logic.")

if __name__ == "__main__":
    test_locations()
