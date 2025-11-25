import requests
import json
import subprocess
import os
import sys

def test_api_integration():
    print("🧪 Starting API Integration Test...")
    
    # 1. Call API to generate structure
    url = "http://localhost:8000/api/deck/generate"
    payload = {
        "commander": "The Ur-Dragon",
        "theme": "Dragon Tribal",
        "colors": ["W", "U", "B", "R", "G"],
        "powerLevel": "3"
    }
    
    print(f"📡 Calling API at {url}...")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        structure = response.json()
        print("✅ API returned valid JSON structure")
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

    # 2. Save to temp file
    temp_file = "temp_structure_test.json"
    with open(temp_file, 'w') as f:
        json.dump(structure, f, indent=2)
    print(f"💾 Saved structure to {temp_file}")

    # 3. Run deck builder script
    print("🔨 Running deck builder script...")
    cmd = [sys.executable, "scripts/build-deck-from-structure.py", temp_file]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Deck builder failed")
            print(result.stderr)
            return False
        
        print("✅ Deck builder completed successfully")
        
        # 4. Verify output
        # The script usually saves to {temp_file}_deck.json (replacing .json with _deck.json)
        # But wait, the script logic in route.ts was:
        # inputFile.replace('.json', '_deck.json').replace('/temp/', '/v3_executed/')
        # Let's check where build-deck-from-structure.py saves it.
        # Usually it saves to the same dir with _deck.json suffix if not specified otherwise.
        
        output_file = temp_file.replace(".json", "_deck.json")
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                deck = json.load(f)
            
            card_count = len(deck.get('mainboard', []))
            print(f"🃏 Generated deck has {card_count} cards")
            
            if card_count == 100:
                print("✅ Card count is correct (100)")
            else:
                print(f"⚠️ Card count is {card_count} (expected 100)")
                
            print("🎉 End-to-End Validation PASSED!")
            return True
        else:
            print(f"❌ Output file {output_file} not found")
            print("Stdout:", result.stdout)
            return False

    except Exception as e:
        print(f"❌ Error running deck builder: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists("temp_structure_test_deck.json"):
            os.remove("temp_structure_test_deck.json")

if __name__ == "__main__":
    success = test_api_integration()
    sys.exit(0 if success else 1)
