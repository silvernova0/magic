"""
Generate synthetic Commander decks using Gemini AI
Uses the local card database and Gemini to create diverse, realistic decks
"""
import os
import sys
import json
import time
import random
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Load commanders from database using SQLite
print("Loading commanders from database...")
import sqlite3

db_path = 'prisma/dev.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all commanders
cursor.execute("SELECT name FROM Card WHERE isCommander = 1 ORDER BY RANDOM()")
commanders = [row[0] for row in cursor.fetchall()]
conn.close()

print(f"Found {len(commanders)} commanders in database")

# Define deck themes and strategies
THEMES = [
    "aggro", "control", "combo", "midrange", "voltron", "tokens", "aristocrats",
    "graveyard", "reanimator", "mill", "burn", "ramp", "group hug", "stax",
    "tribal", "spellslinger", "artifacts", "enchantments", "landfall", "+1/+1 counters",
    "sacrifice", "blink", "storm", "superfriends", "dragon tribal", "elf tribal",
    "goblin tribal", "zombie tribal", "vampire tribal", "merfolk tribal"
]

POWER_LEVELS = list(range(1, 11))  # 1-10

def generate_deck_prompt(commander, theme, power_level):
    """Generate a prompt for Gemini to create a Commander deck"""
    return f"""Create a Commander/EDH deck with exactly 99 cards total.

Commander: {commander}
Theme: {theme}
Power Level: {power_level}/10

CRITICAL RULES:
1. EXACTLY 99 cards total when you add up all quantities
2. The commander is in the deck (1x {commander})
3. Respect {commander}'s color identity strictly
4. Include 35-38 lands
5. Most cards are 1x (except basic lands)
6. Only real Magic: The Gathering cards
7. Stay on {theme} theme
8. Match power level {power_level}/10 (1=casual budget, 5=focused, 10=cEDH)

DECK COMPOSITION:
- 1x Commander: {commander}
- 35-38x Lands (including basics, duals, utility)
- 8-12x Ramp (Sol Ring, signets, land ramp, mana dorks)
- 8-12x Card Draw (engines that fit theme)
- 8-10x Removal (spot removal and board wipes)
- 30-40x Theme cards (creatures, spells for {theme} strategy)

Return ONLY this JSON (no markdown, no explanations):
{{
  "commander": "{commander}",
  "theme": "{theme}",
  "power_level": {power_level},
  "cards": [
    {{"name": "{commander}", "quantity": 1, "category": "Commander"}},
    {{"name": "Sol Ring", "quantity": 1, "category": "Artifact"}},
    {{"name": "Command Tower", "quantity": 1, "category": "Land"}},
    {{"name": "Forest", "quantity": 12, "category": "Land"}}
  ]
}}

COUNT YOUR CARDS: The quantities must sum to exactly 99."""

def parse_gemini_response(response_text):
    """Parse Gemini's response and extract the deck JSON"""
    try:
        # Remove markdown code blocks if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]
        
        # Parse JSON
        deck_data = json.loads(response_text.strip())
        
        # Validate structure
        if not all(key in deck_data for key in ['commander', 'cards']):
            return None
        
        # Validate card count
        total_cards = sum(card.get('quantity', 1) for card in deck_data['cards'])
        if total_cards < 95 or total_cards > 105:
            print(f"  ⚠️ Invalid card count: {total_cards}")
            return None
        
        return deck_data
    except Exception as e:
        print(f"  ❌ Parse error: {str(e)[:100]}")
        return None

def generate_deck(commander, theme, power_level, retries=3):
    """Generate a single deck with retry logic"""
    for attempt in range(retries):
        try:
            prompt = generate_deck_prompt(commander, theme, power_level)
            response = model.generate_content(prompt)
            
            deck_data = parse_gemini_response(response.text)
            if deck_data:
                return deck_data
            
            print(f"  Retry {attempt + 1}/{retries}...")
            time.sleep(2)
        
        except Exception as e:
            if '429' in str(e) or 'quota' in str(e).lower():
                wait_time = 60 * (attempt + 1)
                print(f"  ⏳ Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            elif '503' in str(e):
                print(f"  ⏳ Service unavailable, waiting 30s...")
                time.sleep(30)
            else:
                print(f"  ❌ Error: {str(e)[:100]}")
                time.sleep(5)
    
    return None

def save_progress(decks, output_file):
    """Save decks to file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for deck in decks:
            f.write(json.dumps(deck, ensure_ascii=False) + '\n')

def main():
    target_decks = 1900
    output_file = 'data/training/synthetic_decks.jsonl'
    
    # Create output directory
    os.makedirs('data/training', exist_ok=True)
    
    # Load existing progress if any
    existing_decks = []
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_decks = [json.loads(line) for line in f]
        print(f"📂 Found {len(existing_decks)} existing decks, resuming...")
    
    decks = existing_decks
    failed = 0
    
    print(f"\n{'='*60}")
    print(f"SYNTHETIC DECK GENERATOR")
    print(f"{'='*60}\n")
    print(f"Target: {target_decks} decks")
    print(f"Starting from: {len(decks)}")
    print(f"Commanders available: {len(commanders)}\n")
    
    try:
        while len(decks) < target_decks:
            # Select random commander, theme, and power level
            commander = random.choice(commanders)
            theme = random.choice(THEMES)
            power_level = random.choice(POWER_LEVELS)
            
            deck_num = len(decks) + 1
            print(f"[{deck_num}/{target_decks}] {commander} ({theme}, PL {power_level})")
            
            deck = generate_deck(commander, theme, power_level)
            
            if deck:
                decks.append(deck)
                print(f"  ✓ Generated ({len(deck['cards'])} cards)")
                
                # Save progress every 10 decks
                if len(decks) % 10 == 0:
                    save_progress(decks, output_file)
                    print(f"\n💾 Progress saved: {len(decks)} decks\n")
                
                # Rate limiting
                time.sleep(3)
            else:
                failed += 1
                print(f"  ✗ Failed")
                time.sleep(5)
    
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Interrupted by user")
    
    finally:
        # Final save
        save_progress(decks, output_file)
        
        print(f"\n{'='*60}")
        print(f"GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully generated: {len(decks)} decks")
        print(f"✗ Failed: {failed} decks")
        print(f"📁 Saved to: {output_file}")

if __name__ == '__main__':
    main()
