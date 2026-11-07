"""Find commander using card-hover class"""
import requests
from bs4 import BeautifulSoup

url = 'https://tappedout.net/mtg-decks/mikaeus-extreme-sub-20-budget-edh/'
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Find the Commander h3
commander_h3 = soup.find('h3', string=lambda x: x and 'commander' in x.lower() and '(' in x)

if commander_h3:
    # Get the div.row after it
    next_div = commander_h3.find_next('div', class_='row')
    
    # Look for card-hover links
    card_hover_links = next_div.find_all('a', class_='card-hover')
    print(f"Found {len(card_hover_links)} card-hover links in Commander section:")
    for link in card_hover_links:
        # Get the text - might be in the link itself or in a child
        text = link.get_text(strip=True)
        # Also check data-name attribute
        data_name = link.get('data-name', '')
        # Check href for card name
        href = link.get('href', '')
        
        print(f"\n  Link text: '{text}'")
        print(f"  data-name: '{data_name}'")
        print(f"  href: '{href}'")
        
        # The text is probably the commander name
        if text:
            print(f"  *** COMMANDER: {text} ***")
