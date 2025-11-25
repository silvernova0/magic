#!/usr/bin/env python3
"""
Quick performance test for optimized API
Tests single deck generation and measures time
"""

import requests
import json
import time

API_URL = "http://localhost:8000/api/deck/generate"

def test_generation_speed():
    """Test how fast the optimized model generates"""
    
    print("="*70)
    print("PERFORMANCE TEST - Optimized Model")
    print("="*70)
    
    test_params = {
        'commander': 'Niv-Mizzet, Parun',
        'theme': 'spellslinger',
        'colors': ['U', 'R'],
        'powerLevel': '3',
        'useCollectionOnly': False
    }
    
    print(f"\n📤 Sending request...")
    print(f"   Commander: {test_params['commander']}")
    print(f"   Theme: {test_params['theme']}")
    print(f"   Power Level: {test_params['powerLevel']}")
    
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, json=test_params, timeout=180)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        if response.status_code == 200:
            structure = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"   ⏱️  Generation time: {elapsed:.2f} seconds")
            print(f"   📊 Commander: {structure.get('commander', 'N/A')}")
            print(f"   📊 Strategy: {structure.get('strategy', 'N/A')}")
            print(f"   📊 Power Level: {structure.get('power_level', 'N/A')}")
            
            # Count card categories
            card_selection = structure.get('card_selection', {})
            total_cards = sum(cat.get('count', 0) for cat in card_selection.values() if isinstance(cat, dict))
            print(f"   📊 Total cards allocated: {total_cards}")
            
            if elapsed < 60:
                print(f"\n🎉 EXCELLENT! Under 1 minute")
            elif elapsed < 90:
                print(f"\n✅ GOOD! Under 1.5 minutes")
            else:
                print(f"\n⚠️  Still slow, may need more optimization")
                
            return True, elapsed
        else:
            print(f"\n❌ FAILED with status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False, elapsed
            
    except requests.exceptions.Timeout:
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"\n❌ TIMEOUT after {elapsed:.2f} seconds")
        return False, elapsed
    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"\n❌ ERROR: {e}")
        return False, elapsed

if __name__ == '__main__':
    success, time_taken = test_generation_speed()
    print(f"\n{'='*70}\n")
    
    if success:
        print(f"✅ Test passed in {time_taken:.2f}s")
        exit(0)
    else:
        print(f"❌ Test failed after {time_taken:.2f}s")
        exit(1)
