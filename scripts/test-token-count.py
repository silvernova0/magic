#!/usr/bin/env python3
"""
Test to measure actual token count of model output
"""

import requests
import json
from transformers import AutoTokenizer

API_URL = "http://localhost:8000/api/deck/generate"
BASE_MODEL = "models/qwen2.5-3b"

def test_token_count():
    """Measure actual token count of model output"""
    
    print("="*70)
    print("TOKEN COUNT ANALYSIS")
    print("="*70)
    
    # Load tokenizer
    print("\n📦 Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    
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
            raw_text = response.text
            
            # Tokenize the output
            tokens = tokenizer.encode(raw_text)
            token_count = len(tokens)
            
            print(f"\n✅ API responded successfully")
            print(f"\n📊 Token Analysis:")
            print(f"   Characters: {len(raw_text)}")
            print(f"   Tokens: {token_count}")
            print(f"   Chars/Token ratio: {len(raw_text)/token_count:.2f}")
            
            # Parse JSON to count cards
            structure = json.loads(raw_text)
            card_selection = structure.get('card_selection', {})
            total_cards = sum(cat.get('count', 0) for cat in card_selection.values() if isinstance(cat, dict))
            priority_cards = len(structure.get('priority_cards', []))
            
            print(f"\n📊 Deck Analysis:")
            print(f"   Total cards allocated: {total_cards}")
            print(f"   Priority cards: {priority_cards}")
            print(f"   Commander: {structure.get('commander', 'N/A')}")
            
            # Estimate tokens per card
            if total_cards > 0:
                tokens_per_card = token_count / total_cards
                print(f"   Tokens per card (avg): {tokens_per_card:.1f}")
            
            # Show if we're close to limits
            print(f"\n⚠️  Token Limits:")
            print(f"   Current max_new_tokens: 1200")
            print(f"   Actual tokens used: {token_count}")
            print(f"   Buffer remaining: {1200 - token_count} tokens")
            
            if token_count > 1000:
                print(f"   ❌ Would have been truncated at 1000 tokens!")
            else:
                print(f"   ✅ Would fit in 1000 tokens")
                
            return True, token_count
            
        else:
            print(f"\n❌ API returned status {response.status_code}")
            return False, 0
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

if __name__ == '__main__':
    success, tokens = test_token_count()
    print(f"\n{'='*70}\n")
    
    if success:
        print(f"✅ Test complete - Output is {tokens} tokens")
        exit(0)
    else:
        print(f"❌ Test failed")
        exit(1)
