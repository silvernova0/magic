"""Check actual deck titles to improve commander extraction"""
import requests
from bs4 import BeautifulSoup

decks_to_check = [
    'https://tappedout.net/mtg-decks/mikaeus-extreme-sub-20-budget-edh/',
    'https://tappedout.net/mtg-decks/gitrog-land-combo/',
    'https://tappedout.net/mtg-decks/dominus-dreamcrusher-edition/',
    'https://tappedout.net/mtg-decks/food-chain-sliver/',
    'https://tappedout.net/mtg-decks/eight-and-a-half-tails-equipment-voltron/'
]

headers = {'User-Agent': 'Mozilla/5.0'}

for url in decks_to_check:
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Get h1
    h1 = soup.find('h1')
    title = h1.text.strip() if h1 else "No title"
    
    # Look for specific commander info
    commander_span = soup.find('span', string=lambda x: x and 'commander' in x.lower())
    
    # Check deck description
    desc = soup.find('div', class_='deck-description')
    
    print(f"\nURL: {url}")
    print(f"Title (h1): {title}")
    print(f"Commander span: {commander_span.text if commander_span else 'Not found'}")
    
    # Check for deck_id in URL to find commander in data
    import re
    deck_id_match = re.search(r'/mtg-decks/([^/]+)/', url)
    if deck_id_match:
        slug = deck_id_match.group(1)
        print(f"Deck slug: {slug}")
        
        # Try to infer commander from slug
        # Common pattern: commander-name-description
        slug_parts = slug.split('-')
        if len(slug_parts) >= 2:
            potential_commander = ' '.join(slug_parts[:3])  # First 3 words
            print(f"From slug: {potential_commander}")
    
    print("-" * 60)
