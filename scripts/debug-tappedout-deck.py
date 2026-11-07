"""
Debug TappedOut deck parsing - examine actual HTML structure
"""
import requests
from bs4 import BeautifulSoup
import json

# First, get a deck URL from search results
print("="*60)
print("STEP 1: Get deck URL from search results")
print("="*60)

search_url = 'https://tappedout.net/mtg-decks/search/'
params = {
    'q': '',
    'format': 'edh',
    'is_top': 'on',
    'o': '-Views',
    'page': 1,
    'submit': 'Filter+results'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(search_url, params=params, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Get first deck link
import re
deck_links = soup.find_all('a', href=re.compile(r'/mtg-decks/[^/]+/$'))
deck_url = None

for link in deck_links:
    href = link.get('href')
    if href and '/search/' not in href and href.count('/') >= 3:
        deck_url = 'https://tappedout.net' + href
        break

if not deck_url:
    print("❌ Could not find deck URL")
    exit()

print(f"✅ Found deck URL: {deck_url}")

# Fetch the deck page
print(f"\n{'='*60}")
print("STEP 2: Fetch deck page and analyze structure")
print("="*60)

response = requests.get(deck_url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Content length: {len(response.text)} bytes")

if response.status_code != 200:
    print("❌ Failed to fetch deck")
    exit()

soup = BeautifulSoup(response.text, 'html.parser')

# Analyze deck structure
print(f"\n{'='*60}")
print("DECK STRUCTURE ANALYSIS")
print("="*60)

# 1. Find deck name/title
print("\n1. DECK NAME:")
title_options = [
    soup.find('h2', class_='deck-title'),
    soup.find('h1', class_='deck-title'),
    soup.find('h1'),
    soup.find('h2')
]

for i, title in enumerate(title_options):
    if title:
        print(f"  Option {i+1}: {title.text.strip()[:100]}")
        break

# 2. Find commander section
print("\n2. COMMANDER SECTION:")
board_sections = soup.find_all('div', class_='board-container')
print(f"  Found {len(board_sections)} board sections")

for i, section in enumerate(board_sections[:5]):
    header = section.find(['h3', 'h4'])
    if header:
        section_name = header.text.strip()
        cards_in_section = section.find_all('li', class_='member')
        print(f"  Section {i+1}: '{section_name}' ({len(cards_in_section)} cards)")
        
        if 'commander' in section_name.lower():
            print(f"    ✅ This is the Commander section!")
            # Get first card in this section
            if cards_in_section:
                first_card = cards_in_section[0]
                card_link = first_card.find('a', class_='card-link')
                if not card_link:
                    card_link = first_card.find('a')
                if card_link:
                    print(f"    Commander: {card_link.text.strip()}")

# 3. Analyze all board sections in detail
print("\n3. ALL BOARD SECTIONS:")
for i, section in enumerate(board_sections):
    header = section.find(['h3', 'h4'])
    section_name = header.text.strip() if header else "Unknown"
    cards_in_section = section.find_all('li', class_='member')
    
    print(f"\n  Section: '{section_name}'")
    print(f"  Cards: {len(cards_in_section)}")
    
    # Show first 3 cards
    for j, card_elem in enumerate(cards_in_section[:3]):
        qty_span = card_elem.find('span', class_='qty')
        qty = qty_span.text.strip() if qty_span else "1"
        
        card_link = card_elem.find('a', class_='card-link')
        if not card_link:
            card_link = card_elem.find('a')
        
        card_name = card_link.text.strip() if card_link else "Unknown"
        print(f"    {qty}x {card_name}")

# 4. Count total cards
print("\n4. TOTAL CARD COUNT:")
all_cards = soup.find_all('li', class_='member')
print(f"  Total card elements found: {len(all_cards)}")

# Group by section
cards_by_section = {}
for card_elem in all_cards:
    parent_board = card_elem.find_parent('div', class_='board-container')
    if parent_board:
        header = parent_board.find(['h3', 'h4'])
        section_name = header.text.strip() if header else "Unknown"
        cards_by_section[section_name] = cards_by_section.get(section_name, 0) + 1

print("\n  Cards by section:")
total_mainboard = 0
for section, count in sorted(cards_by_section.items()):
    print(f"    {section}: {count} cards")
    
    # Count mainboard (exclude maybe/sideboard)
    if 'maybe' not in section.lower() and 'sideboard' not in section.lower():
        total_mainboard += count

print(f"\n  Total MAINBOARD cards (excl. Maybe/Sideboard): {total_mainboard}")

# 5. Check for common section names
print("\n5. SECTION NAME PATTERNS:")
common_patterns = ['commander', 'maybe', 'sideboard', 'creatures', 'lands', 'artifacts', 'enchantments']
for pattern in common_patterns:
    matching = [s for s in cards_by_section.keys() if pattern in s.lower()]
    if matching:
        print(f"  '{pattern}' sections: {matching}")

print(f"\n{'='*60}")
print("RECOMMENDATION")
print("="*60)
print("""
Based on the analysis above, we need to:
1. Extract commander from the section labeled 'Commander' or similar
2. Filter out sections with 'maybe' or 'sideboard' in the name
3. Expected mainboard should be 99-100 cards (+ 1 commander)
""")
