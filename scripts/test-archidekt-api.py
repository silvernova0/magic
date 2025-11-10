"""
Test Archidekt API endpoints
"""
import requests
import json

print("Testing Archidekt API...")
print("="*60)

# Try different API endpoints
endpoints = [
    'https://archidekt.com/api/decks/cards/',
    'https://archidekt.com/api/decks/',
    'https://www.archidekt.com/api/decks/cards/',
    'https://archidekt.com/api/v1/decks/',
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

for endpoint in endpoints:
    print(f"\nTrying: {endpoint}")
    
    params = {
        'formats': 7,  # Commander format ID
        'orderBy': '-viewCount',
        'pageSize': 5
    }
    
    try:
        r = requests.get(endpoint, params=params, headers=headers, timeout=10)
        print(f"  Status: {r.status_code}")
        
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"  Type: {type(data)}")
                if isinstance(data, dict):
                    print(f"  Keys: {list(data.keys())}")
                    if 'results' in data:
                        print(f"  Results: {len(data['results'])}")
                        if data['results']:
                            print(f"  First deck: {data['results'][0].get('name', 'N/A')}")
                elif isinstance(data, list):
                    print(f"  Count: {len(data)}")
                    if data:
                        print(f"  First deck: {data[0].get('name', 'N/A')}")
            except:
                print(f"  Body: {r.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

# Try web scraping approach
print("\n" + "="*60)
print("Testing web scraping approach...")
print("="*60)

try:
    r = requests.get('https://archidekt.com/search/decks/', headers=headers)
    print(f"\nWeb page status: {r.status_code}")
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Look for deck links
    deck_links = soup.find_all('a', href=lambda x: x and '/decks/' in str(x))
    print(f"Found {len(deck_links)} deck links")
    
    # Check for any API calls in the page source
    if 'api/decks' in r.text:
        print("\n✓ Page contains API calls - inspecting...")
        import re
        api_calls = re.findall(r'https?://[^"\']+/api/decks[^"\']*', r.text)
        if api_calls:
            print(f"Found {len(set(api_calls))} unique API endpoints:")
            for call in list(set(api_calls))[:5]:
                print(f"  - {call}")
                
except Exception as e:
    print(f"Error: {e}")
