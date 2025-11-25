#!/usr/bin/env python3
"""
TopDeck.gg Decklist Scraper
Fetches full 100-card decklists from TopDeck.gg URLs collected by EDHTop16 scraper.
"""

import json
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

# Configuration
INPUT_FILE = Path(__file__).parent.parent / "data" / "training" / "edhtop16_tournaments.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "training" / "topdeck_decklists.json"
RATE_LIMIT_SECONDS = 1.0  # Be respectful to TopDeck.gg servers
REQUEST_TIMEOUT = 10
MAX_DECKLISTS = None  # Set to number for testing, None for all

def parse_decklist_page(html: str, url: str) -> dict:
    """Extract decklist from TopDeck.gg HTML page"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Check if deck exists
    error_message = soup.find('h3', string=lambda text: text and 'Unable to Display Deck' in text)
    if error_message:
        print(f"    ⚠️  Deck not available on TopDeck.gg")
        return None
    
    decklist_data = {
        'url': url,
        'scraped_at': datetime.now().isoformat(),
        'commander': [],
        'mainboard': {},  # Use dict to track quantities: {card_name: quantity}
        'total_cards': 0
    }
    
    # TopDeck.gg uses visible HTML with data attributes in text-list-item elements
    # Find the mainboard container
    mainboard_container = soup.find('div', {'data-section': 'Mainboard'})
    
    if not mainboard_container:
        print(f"    ⚠️  No mainboard section found")
        return None
    
    # Get all card list items in mainboard
    cards_found = 0
    for card_item in mainboard_container.find_all('li', class_='text-list-item'):
        card_link = card_item.find('a')
        if card_link:
            spans = card_link.find_all('span')
            if len(spans) >= 2:
                try:
                    quantity = int(spans[0].get_text().strip())
                    card_name = spans[1].get_text().strip()
                    decklist_data['mainboard'][card_name] = quantity
                    cards_found += 1
                except (ValueError, IndexError):
                    continue
    
    if cards_found == 0:
        print(f"    ⚠️  No cards extracted from HTML")
        return None
    
    # Extract commanders from JavaScript deckObj variable
    # TopDeck.gg embeds deck data in: const deckObj = {"Commanders":[...],"Mainboard":[...]}
    import re
    deck_obj_match = re.search(r'const deckObj = (\{.*?\});', html, re.DOTALL)
    if deck_obj_match:
        try:
            deck_obj_str = deck_obj_match.group(1)
            # Parse the JSON object
            deck_obj = json.loads(deck_obj_str)
            
            # Extract commanders
            if 'Commanders' in deck_obj:
                for card in deck_obj['Commanders']:
                    card_name = card.get('name', '')
                    quantity = card.get('count', 1)
                    for _ in range(quantity):
                        decklist_data['commander'].append(card_name)
                print(f"    ✓ Found {len(decklist_data['commander'])} commanders in JavaScript data")
        except json.JSONDecodeError as e:
            print(f"    ⚠️  Failed to parse deckObj JSON: {e}")
    else:
        print(f"    ⚠️  No deckObj found in JavaScript")
    
    # Convert mainboard dict to list format
    mainboard_list = []
    for card_name, quantity in decklist_data['mainboard'].items():
        mainboard_list.append({'name': card_name, 'quantity': quantity})
    
    decklist_data['mainboard'] = mainboard_list
    decklist_data['total_cards'] = (
        sum(c['quantity'] for c in mainboard_list) +
        len(decklist_data['commander'])
    )
    
    return decklist_data

def scrape_decklists():
    """Main scraper function"""
    print(f"🎯 TopDeck.gg Decklist Scraper")
    print(f"📂 Reading tournaments from: {INPUT_FILE}")
    
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        print(f"   Run scrape-edhtop16.py first to collect tournament data")
        return
    
    # Load tournament data
    with open(INPUT_FILE, 'r') as f:
        tournaments = json.load(f)
    
    # Extract all decklist URLs
    decklist_urls = []
    for tournament in tournaments:
        for entry in tournament.get('entries', []):
            url = entry.get('decklist_url')
            if url and url not in decklist_urls:
                decklist_urls.append({
                    'url': url,
                    'tournament': tournament['name'],
                    'player': entry.get('player'),
                    'commander': entry.get('commander'),
                    'position': entry.get('position'),
                    'record': f"{entry.get('wins', 0)}-{entry.get('losses', 0)}-{entry.get('draws', 0)}"
                })
    
    print(f"📊 Found {len(decklist_urls)} unique decklists to scrape")
    
    if MAX_DECKLISTS:
        decklist_urls = decklist_urls[:MAX_DECKLISTS]
        print(f"🔬 Testing with first {MAX_DECKLISTS} decklists")
    
    # Load existing data if available
    existing_decklists = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, 'r') as f:
            existing_data = json.load(f)
            existing_decklists = {d['url']: d for d in existing_data}
        print(f"📁 Loaded {len(existing_decklists)} previously scraped decklists")
    
    # Scrape each decklist
    results = []
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for i, deck_info in enumerate(decklist_urls, 1):
        url = deck_info['url']
        
        # Skip decks with Unknown Commander - means deck was never uploaded to TopDeck.gg
        if 'Unknown Commander' in deck_info.get('commander', ''):
            skip_count += 1
            if i % 50 == 0:
                print(f"⏩ Skipped {skip_count} decks (unknown commanders or already scraped)...")
            continue
        
        # Skip if already scraped
        if url in existing_decklists:
            results.append(existing_decklists[url])
            skip_count += 1
            if i % 50 == 0:
                print(f"⏩ Skipped {skip_count} decks (unknown commanders or already scraped)...")
            continue
        
        # Display commander info from EDHTop16 metadata
        commander_display = deck_info.get('commander', 'Unknown Commander')
        print(f"\n[{i}/{len(decklist_urls)}] 🎴 {deck_info['player']} - {commander_display}")
        print(f"    📍 {deck_info['tournament']} (#{deck_info['position']}, {deck_info['record']})")
        print(f"    🔗 {url}")
        
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            decklist = parse_decklist_page(response.text, url)
            
            if decklist and decklist['total_cards'] > 0:
                # Enrich with tournament metadata
                decklist['metadata'] = {
                    'tournament': deck_info['tournament'],
                    'player': deck_info['player'],
                    'commander': deck_info['commander'],  # From EDHTop16 (already filtered out Unknown Commander)
                    'position': deck_info['position'],
                    'record': deck_info['record']
                }
                results.append(decklist)
                success_count += 1
                
                # Show commanders and mainboard separately
                commander_names = ', '.join(decklist['commander']) if decklist['commander'] else 'None'
                mainboard_count = sum(c['quantity'] for c in decklist['mainboard'])
                commander_count = len(decklist['commander'])
                
                print(f"    ✅ {decklist['total_cards']} total cards")
                print(f"       Commander(s): {commander_names} ({commander_count} card{'s' if commander_count != 1 else ''})")
                print(f"       Mainboard: {mainboard_count} cards ({len(decklist['mainboard'])} unique)")
            else:
                fail_count += 1
                print(f"    ❌ Failed to parse decklist")
            
        except requests.RequestException as e:
            fail_count += 1
            print(f"    ❌ Request failed: {e}")
        
        # Rate limiting
        if i < len(decklist_urls):
            time.sleep(RATE_LIMIT_SECONDS)
    
    # Save results
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n" + "="*60)
    print(f"✅ Scraping complete!")
    print(f"📊 Results: {success_count} success, {skip_count} skipped, {fail_count} failed")
    print(f"💾 Saved {len(results)} decklists to: {OUTPUT_FILE}")
    print(f"="*60)

if __name__ == "__main__":
    scrape_decklists()
