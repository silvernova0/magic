"""Find the Commander section header"""
import requests
from bs4 import BeautifulSoup

url = 'https://tappedout.net/mtg-decks/mikaeus-extreme-sub-20-budget-edh/'
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

print("Looking for board sections...\n")

# Find all h3 tags (section headers)
h3_tags = soup.find_all('h3')
for h3 in h3_tags:
    text = h3.text.strip()
    print(f"H3: {text}")
    
    # If this is a Commander section, look for cards after it
    if 'commander' in text.lower():
        print(f"  *** FOUND COMMANDER SECTION ***")
        # Find the next ul with cards
        next_ul = h3.find_next('ul', class_='boardlist')
        if next_ul:
            cards_in_section = next_ul.find_all('li', class_='member')
            print(f"  Cards in this section: {len(cards_in_section)}")
            for card in cards_in_section[:3]:
                name_link = card.find('a', class_='card-link')
                name = name_link.text.strip() if name_link else "Unknown"
                print(f"    - {name}")
        print()

# Also check for div.board containers
print("\nChecking div.board containers...")
board_divs = soup.find_all('div', class_='board')
for i, board in enumerate(board_divs):
    header = board.find('h3')
    header_text = header.text.strip() if header else "No header"
    
    cards = board.find_all('li', class_='member')
    print(f"Board {i+1}: {header_text} ({len(cards)} cards)")
    
    if 'commander' in header_text.lower() and cards:
        print(f"  *** COMMANDER FOUND ***")
        for card in cards[:3]:
            name_link = card.find('a', class_='card-link')
            name = name_link.text.strip() if name_link else "Unknown"
            print(f"    - {name}")
