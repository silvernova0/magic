"""Test the improved TappedOut search"""
import requests
from bs4 import BeautifulSoup
import re

url = 'https://tappedout.net/mtg-decks/search/'
params = {
    'q': '',
    'format': 'edh',
    'is_top': 'on',
    'o': '-date_updated',
    'page': 1,
    'submit': 'Filter+results'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("Testing TappedOut search with improved URL...")
print(f"URL: {url}")
print(f"Params: {params}\n")

response = requests.get(url, params=params, headers=headers)
print(f"Status: {response.status_code}")
print(f"Content length: {len(response.text)} bytes\n")

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Try multiple strategies to find deck links
    print("Strategy 1: Look for deck-list-item divs")
    deck_items = soup.find_all('div', class_='deck-list-item')
    print(f"  Found {len(deck_items)} items")
    
    print("\nStrategy 2: Look for any /mtg-decks/ links")
    deck_links = soup.find_all('a', href=re.compile(r'/mtg-decks/[^/]+/$'))
    print(f"  Found {len(deck_links)} links")
    
    if deck_links:
        print(f"\nSample deck links:")
        for link in deck_links[:5]:
            print(f"  - {link.get('href')}")
            print(f"    Text: {link.text.strip()}")
    
    print("\nStrategy 3: Look for table rows with deck info")
    table_rows = soup.find_all('tr', class_='deck-row')
    print(f"  Found {len(table_rows)} rows")
    
    print("\nStrategy 4: Look for links in search-results div")
    results_div = soup.find('div', id='search-results')
    if results_div:
        print("  ✅ Found search-results div")
        links_in_results = results_div.find_all('a', href=re.compile(r'/mtg-decks/'))
        print(f"  Found {len(links_in_results)} links in results")
        
        if links_in_results:
            print(f"\nDeck links from search-results:")
            unique_decks = list(set([l.get('href') for l in links_in_results if '/mtg-decks/' in l.get('href', '')]))
            for deck_url in unique_decks[:10]:
                print(f"  - {deck_url}")
    else:
        print("  ✗ No search-results div found")
    
    # Check page structure
    print("\nPage structure:")
    print(f"  Total links: {len(soup.find_all('a'))}")
    print(f"  Links with /mtg-decks/: {len([a for a in soup.find_all('a') if '/mtg-decks/' in a.get('href', '')])}")
    
    # Look for pagination
    pagination = soup.find('div', class_='pagination')
    if pagination:
        print(f"  ✅ Pagination found")
    else:
        print(f"  ✗ No pagination found")
