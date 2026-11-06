"""Deep dive into the 3 accessible sources"""
import requests
from bs4 import BeautifulSoup
import json
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("="*60)
print("1. CEDH DECKLIST DATABASE")
print("="*60)

# This site is a static JSON database - jackpot!
response = requests.get('https://cedh-decklist-database.com/', headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Look for JSON data in scripts
scripts = soup.find_all('script')
for script in scripts:
    script_text = script.string or ''
    if 'moxfield.com/decks' in script_text or 'archidekt.com/decks' in script_text:
        print("✅ Found deck links in JavaScript!")
        # Look for JSON data
        json_match = re.search(r'var\s+data\s*=\s*(\{.*?\});', script_text, re.DOTALL)
        if json_match:
            print("✅ Found JSON data variable!")
        
        # Count deck links
        moxfield_links = re.findall(r'https://moxfield\.com/decks/[a-zA-Z0-9_-]+', script_text)
        archidekt_links = re.findall(r'https://archidekt\.com/decks/\d+', script_text)
        
        print(f"  Moxfield decks: {len(moxfield_links)}")
        print(f"  Archidekt decks: {len(archidekt_links)}")
        
        if moxfield_links:
            print(f"  Sample: {moxfield_links[0]}")
        break

print("\n" + "="*60)
print("2. MTGGOLDFISH COMMANDER META")
print("="*60)

response = requests.get('https://www.mtggoldfish.com/metagame/commander#paper', headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Look for deck tables
tables = soup.find_all('table', class_='table-striped')
print(f"Found {len(tables)} tables")

# Look for commander names and deck links
commander_links = soup.find_all('a', href=re.compile(r'/archetype/'))
print(f"Found {len(commander_links)} commander archetypes")

if commander_links:
    print(f"Sample archetype: {commander_links[0].get('href')}")
    print(f"Commander: {commander_links[0].text.strip()}")
    
# Check if archetypes have deck lists
if commander_links:
    archetype_url = 'https://www.mtggoldfish.com' + commander_links[0].get('href')
    print(f"\nTesting archetype page: {archetype_url}")
    arch_response = requests.get(archetype_url, headers=headers)
    arch_soup = BeautifulSoup(arch_response.text, 'html.parser')
    
    # Look for deck list
    deck_link = arch_soup.find('a', href=re.compile(r'/deck/'))
    if deck_link:
        print(f"✅ Found deck link: {deck_link.get('href')}")

print("\n" + "="*60)
print("3. TAPPEDOUT")
print("="*60)

# Try to find Commander decks
response = requests.get('https://tappedout.net/mtg-deck-folders/all/?format=23', headers=headers)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for deck links
    deck_links = soup.find_all('a', href=re.compile(r'/mtg-decks/'))
    print(f"Found {len(deck_links)} deck links")
    
    if deck_links:
        # Get unique deck URLs
        unique_decks = list(set([link.get('href') for link in deck_links]))
        print(f"Unique decks: {len(unique_decks)}")
        print(f"Sample: https://tappedout.net{unique_decks[0]}")
        
        # Test fetching a single deck
        if unique_decks:
            deck_url = 'https://tappedout.net' + unique_decks[0]
            print(f"\nTesting deck page: {deck_url}")
            deck_response = requests.get(deck_url, headers=headers)
            print(f"Deck page status: {deck_response.status_code}")
            
            if deck_response.status_code == 200:
                deck_soup = BeautifulSoup(deck_response.text, 'html.parser')
                
                # Look for card list
                card_links = deck_soup.find_all('a', class_='card')
                print(f"✅ Found {len(card_links)} cards in deck")

print("\n" + "="*60)
print("RECOMMENDATION")
print("="*60)

print("""
Best sources in order:

1. ✅ cEDH Decklist Database (cedh-decklist-database.com)
   - Static JSON embedded in page
   - Links to Moxfield/Archidekt decks
   - High-quality cEDH lists
   - Easy to scrape (just parse HTML once)
   - Estimated: 200-300 decks

2. ✅ MTGGoldfish (mtggoldfish.com)
   - Shows popular Commander archetypes
   - Links to sample decklists
   - Can scrape multiple decks per archetype
   - HTML scraping required
   - Estimated: 500-1000 decks

3. ✅ TappedOut (tappedout.net)
   - Large collection of user decks
   - Format filtering available (Commander = format 23)
   - HTML scraping required
   - Can sort by rating/popularity
   - Estimated: 1000s of decks available

Recommended approach:
1. Start with cEDH Database (quick, high quality, 200-300 decks)
2. Add MTGGoldfish popular archetypes (500-1000 decks)
3. Supplement with TappedOut top-rated decks (1000+ decks)
""")
