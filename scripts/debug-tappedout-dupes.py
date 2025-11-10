"""
Debug TappedOut deck parsing - focus on card duplication issue
"""
import requests
from bs4 import BeautifulSoup
import re

deck_url = 'https://tappedout.net/mtg-decks/mikaeus-extreme-sub-20-budget-edh/'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print(f"Analyzing: {deck_url}\n")

response = requests.get(deck_url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

print("="*60)
print("LOOKING FOR DECK LIST CONTAINERS")
print("="*60)

# Strategy 1: Look for specific deck list areas
print("\n1. Looking for board-container divs:")
board_containers = soup.find_all('div', class_='board-container')
print(f"   Found: {len(board_containers)}")

print("\n2. Looking for li.member elements:")
all_members = soup.find_all('li', class_='member')
print(f"   Total found: {len(all_members)}")

# Check for duplicate data-card-id
card_ids = {}
for member in all_members:
    card_id = member.get('data-card-id')
    if card_id:
        card_ids[card_id] = card_ids.get(card_id, 0) + 1

duplicates = {cid: count for cid, count in card_ids.items() if count > 1}
print(f"   Unique cards: {len(card_ids)}")
print(f"   Duplicated cards: {len(duplicates)}")

if duplicates:
    print(f"\n   Sample duplicates:")
    for cid, count in list(duplicates.items())[:5]:
        # Find the card name
        member = soup.find('li', attrs={'data-card-id': cid})
        if member:
            link = member.find('a')
            name = link.text.strip() if link else "Unknown"
            print(f"     {name}: appears {count} times")

print("\n3. Looking for main deck vs other views:")
# TappedOut might have multiple views of the deck (visual, list, etc.)
deck_views = soup.find_all('div', id=re.compile(r'deck|board'))
print(f"   Found {len(deck_views)} deck/board divs")

for dv in deck_views[:3]:
    div_id = dv.get('id', 'no-id')
    members_in_view = dv.find_all('li', class_='member')
    print(f"     {div_id}: {len(members_in_view)} cards")

print("\n4. Looking for the PRIMARY board (well-board):")
well_board = soup.find('div', class_='well-board')
if well_board:
    print("   ✅ Found well-board div")
    members_in_well = well_board.find_all('li', class_='member')
    print(f"   Cards in well-board: {len(members_in_well)}")
    
    # Get sections within well-board
    sections_in_well = well_board.find_all('div', class_='board-container')
    print(f"   Sections in well-board: {len(sections_in_well)}")
    
    for section in sections_in_well:
        header = section.find(['h3', 'h4'])
        section_name = header.text.strip() if header else "Unknown"
        cards = section.find_all('li', class_='member')
        print(f"     {section_name}: {len(cards)} cards")
else:
    print("   ✗ No well-board found")

print("\n5. Looking for commander specifically:")
# Check page title or deck info
commander_elem = soup.find('span', class_='commander')
if commander_elem:
    print(f"   ✅ Found commander span: {commander_elem.text.strip()}")

# Check h1 title
h1 = soup.find('h1')
if h1:
    print(f"   Deck title (h1): {h1.text.strip()}")
    # Commander name often in deck title before comma
    title = h1.text.strip()
    if ',' in title:
        potential_commander = title.split(',')[0]
        print(f"   Potential commander from title: {potential_commander}")

print("\n" + "="*60)
print("SOLUTION")
print("="*60)
print("""
The issue is likely that TappedOut has multiple HTML representations
of the same deck on one page (visual view, list view, etc.).

Solution:
1. Only parse cards from the 'well-board' div (if it exists)
2. Or use data-card-id to deduplicate
3. Extract commander from deck title (before first comma)
""")
