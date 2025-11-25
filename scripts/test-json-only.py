#!/usr/bin/env python3
"""
Test to verify model outputs ONLY JSON (no conversational text)
"""

import requests
import json

API_URL = "http://localhost:8000/api/deck/generate"

def test_json_only_output():
    """Test that model outputs only JSON, no conversational text"""
    
    print("="*70)
    print("JSON-ONLY OUTPUT TEST")
    print("="*70)
    
    test_params = {
        'commander': 'Niv-Mizzet, Parun',
        'theme': 'spellslinger',
        'colors': ['U', 'R'],
        'powerLevel': '3',
        'useCollectionOnly': False
    }
    
    print(f"\n📤 Sending request...")
    
    try:
        response = requests.post(API_URL, json=test_params, timeout=120)
        
        if response.status_code == 200:
            # Get the raw response text
            raw_text = response.text
            
            print(f"\n✅ API responded successfully")
            print(f"\n📝 Raw response (first 500 chars):")
            print("-" * 70)
            print(raw_text[:500])
            print("-" * 70)
            
            # Try to parse as JSON
            try:
                structure = json.loads(raw_text)
                print(f"\n✅ Response is valid JSON")
                
                # Check if response starts with JSON (no conversational prefix)
                stripped = raw_text.strip()
                if stripped.startswith('{'):
                    print(f"✅ Response starts with JSON (no conversational text)")
                else:
                    print(f"⚠️  Response has text before JSON:")
                    # Find where JSON starts
                    json_start = stripped.find('{')
                    if json_start > 0:
                        prefix = stripped[:json_start]
                        print(f"   Prefix: '{prefix}'")
                
                # Check if response ends with JSON (no conversational suffix)
                if stripped.endswith('}'):
                    print(f"✅ Response ends with JSON (no conversational text after)")
                else:
                    print(f"⚠️  Response has text after JSON:")
                    json_end = stripped.rfind('}')
                    if json_end > 0 and json_end < len(stripped) - 1:
                        suffix = stripped[json_end+1:]
                        print(f"   Suffix: '{suffix}'")
                
                # Print summary
                print(f"\n📊 Response Summary:")
                print(f"   Commander: {structure.get('commander', 'N/A')}")
                print(f"   Strategy: {structure.get('strategy', 'N/A')}")
                print(f"   Total length: {len(raw_text)} characters")
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"\n❌ Response is NOT valid JSON")
                print(f"   Error: {e}")
                print(f"\n📝 Full response:")
                print(raw_text)
                return False
        else:
            print(f"\n❌ API returned status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == '__main__':
    success = test_json_only_output()
    print(f"\n{'='*70}\n")
    
    if success:
        print(f"✅ Test passed - Model outputs JSON only")
        exit(0)
    else:
        print(f"❌ Test failed - Model outputs extra text")
        exit(1)
