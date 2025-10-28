"""Check the div.row after Commander h3"""
import requests
from bs4 import BeautifulSoup

url = 'https://tappedout.net/mtg-decks/mikaeus-extreme-sub-20-budget-edh/'
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Find the Commander h3
commander_h3 = soup.find('h3', string=lambda x: x and 'commander' in x.lower() and '(' in x)

if commander_h3:
    # Get the div.row that comes after it
    next_div = commander_h3.find_next('div', class_='row')
    print("Found div.row after Commander h3")
    print(f"Classes: {next_div.get('class', [])}")
    print(f"Inner HTML (first 500 chars):\n{str(next_div)[:500]}")
    print("\n" + "=" * 60 + "\n")
    
    # Look for any links in this div
    links = next_div.find_all('a', class_='card-link')
    print(f"Found {len(links)} card-link anchors in the div.row:")
    for link in links:
        print(f"  - {link.text.strip()}")
    
    # Also look for text that might be the commander name
    print("\nAll text in the div.row:")
    print(next_div.get_text(strip=True, separator=' | ')[:200])
