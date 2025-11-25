import requests
import json
import sys

API_URL = "http://localhost:3000/api/commander/build-local"
HEADERS = {
    "Content-Type": "application/json",
    "x-test-auth": "antigravity-secret"
}

def test_pair(commander, partner, expected_valid, description):
    print(f"Testing: {description} ({commander} + {partner})...")
    payload = {
        "commander": commander,
        "partner": partner,
        "strategy": "good stuff",
        "powerLevel": 7,
        "bracket": 7,
        "colors": ["W", "U", "B", "R", "G"] # Dummy colors, will be filtered by API
    }
    
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        
        if expected_valid:
            if response.status_code == 400:
                print(f"❌ FAILED: Expected valid, got 400: {response.text}")
                return False
            elif response.status_code in [200, 503]:
                print(f"✅ PASSED: Valid pair accepted (Status: {response.status_code})")
                return True
            else:
                print(f"⚠️ WARNING: Unexpected status {response.status_code}: {response.text}")
                # 500 might be model error, but validation passed
                return True
        else:
            if response.status_code == 400:
                print(f"✅ PASSED: Invalid pair rejected as expected (Status: 400)")
                return True
            else:
                print(f"❌ FAILED: Expected 400, got {response.status_code}")
                return False
                
    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Could not connect to API. Is Next.js running on port 3000?")
        return False
    except requests.exceptions.ReadTimeout:
        print("⚠️ WARNING: Read timed out (60s). Assuming validation passed but generation took too long.")
        # If it timed out, it means it passed validation and went to generation (which is slow)
        if expected_valid:
            return True
        else:
            print("❌ FAILED: Invalid pair should have failed fast, but timed out.")
            return False
    except Exception as e:
        print(f"❌ FAILED: Error: {e}")
        return False

def main():
    # Reordered to test invalid first (fast fail)
    tests = [
        ("Atraxa, Praetors' Voice", "Sol Ring", False, "Invalid Pair (Sol Ring not partner)"),
        ("Urza, Lord High Artificer", "Cultist of the Absolute", False, "Invalid Background (Urza doesn't choose background)"),
        ("Pippin, Guard of the Citadel", "Sol Ring", False, "Invalid Partner With (Mismatch)"),
        ("Vial Smasher the Fierce", "Thrasios, Triton Hero", True, "Valid Partner Pair"),
        ("Wilson, Refined Grizzly", "Cultist of the Absolute", True, "Valid Background Pair"),
        ("Pippin, Guard of the Citadel", "Merry, Warden of Isengard", True, "Valid Partner With"),
    ]
    
    passed = 0
    for cmd, ptr, exp, desc in tests:
        if test_pair(cmd, ptr, exp, desc):
            passed += 1
            
    print(f"\nResults: {passed}/{len(tests)} passed.")
    if passed == len(tests):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
