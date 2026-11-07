"""Deep dive into Commander section structure"""
import requests
from bs4 import BeautifulSoup

url = 'https://tappedout.net/mtg-decks/mikaeus-extreme-sub-20-budget-edh/'
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Find the Commander h3
commander_h3 = soup.find('h3', string=lambda x: x and 'commander' in x.lower() and '(' in x)
print(f"Found Commander header: {commander_h3.text.strip() if commander_h3 else 'Not found'}\n")

if commander_h3:
    print("Next 5 siblings after Commander h3:")
    print("-" * 60)
    for i, sibling in enumerate(commander_h3.next_siblings):
        if i >= 10:  # Check first 10 siblings
            break
        if sibling.name:  # Only elements, not text nodes
            print(f"{i+1}. Tag: {sibling.name}, Classes: {sibling.get('class', [])}")
            
            # If it's a ul, show the cards
            if sibling.name == 'ul':
                cards = sibling.find_all('li', class_='member')
                print(f"   Found {len(cards)} cards in this ul")
                for card in cards[:5]:
                    name_link = card.find('a', class_='card-link')
                    name = name_link.text.strip() if name_link else "Unknown"
                    print(f"     - {name}")
                break  # Found the cards, stop
            
            # Show some text content
            text = sibling.text.strip()[:100] if sibling.text else ""
            if text:
                print(f"   Text: {text}...")
    
    # Also try looking for the parent structure
    print("\n" + "=" * 60)
    print("Looking at parent structure...")
    parent = commander_h3.parent
    print(f"Parent tag: {parent.name}, Classes: {parent.get('class', [])}")
    
    # Find all card lists in parent
    if parent:
        card_lists = parent.find_all('ul', class_='boardlist')
        print(f"Found {len(card_lists)} card lists in parent")
        
        for i, card_list in enumerate(card_lists):
            # Find the h3 before this card list
            prev_h3 = card_list.find_previous('h3')
            h3_text = prev_h3.text.strip() if prev_h3 else "No h3"
            cards = card_list.find_all('li', class_='member')
            
            print(f"\nList {i+1}: {h3_text} ({len(cards)} cards)")
            if 'commander' in h3_text.lower():
                print("  *** THIS IS THE COMMANDER LIST ***")
                for card in cards[:3]:
                    name_link = card.find('a', class_='card-link')
                    name = name_link.text.strip() if name_link else "Unknown"
                    print(f"    - {name}")
