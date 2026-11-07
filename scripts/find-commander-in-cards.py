"""Find commander by looking at the actual cards on the page"""
import requests
from bs4 import BeautifulSoup

url = 'https://tappedout.net/mtg-decks/mikaeus-extreme-sub-20-budget-edh/'
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Get ALL card elements
card_elements = soup.find_all('li', class_='member')

print(f"Found {len(card_elements)} card elements\n")

# Check first 10 cards for metadata
for i, card in enumerate(card_elements[:10]):
    # Get card name
    name_link = card.find('a', class_='card-link')
    name = name_link.text.strip() if name_link else "Unknown"
    
    # Get quantity
    qty_span = card.find('span', class_='qty')
    qty = qty_span.text.strip() if qty_span else "1"
    
    # Get category (board type)
    category = card.get('data-board-type', 'unknown')
    
    # Check for commander indicator
    is_commander = 'commander' in card.get('class', [])
    data_attrs = {k: v for k, v in card.attrs.items() if k.startswith('data-')}
    
    print(f"Card {i+1}: {qty}x {name}")
    print(f"  Category: {category}")
    print(f"  Is commander class: {is_commander}")
    print(f"  Data attributes: {data_attrs}")
    print()

# Also check for any text that says "Commander"
commander_text = soup.find_all(string=lambda x: x and 'commander' in x.lower())
print(f"\nFound {len(commander_text)} mentions of 'commander' in text")
for text in commander_text[:5]:
    print(f"  - {text.strip()[:80]}")
