"""
Test multiple Commander deck sources to find which are scrapable
"""
import requests
from bs4 import BeautifulSoup
import json
import time

def test_source(name, url, check_api=None):
    """Test if a source is accessible and scrapable"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print('='*60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # Test main page
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"Content-Length: {len(response.text)} bytes")
        
        if response.status_code != 200:
            print(f"❌ Failed: HTTP {response.status_code}")
            return False
        
        # Check for API endpoints in page source
        if 'application/json' in response.headers.get('Content-Type', ''):
            print("✅ JSON API detected!")
            data = response.json()
            print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'List response'}")
            return True
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for API calls in scripts
        scripts = soup.find_all('script')
        api_urls = set()
        for script in scripts:
            script_text = script.string or ''
            if '/api/' in script_text:
                # Extract potential API URLs
                import re
                urls = re.findall(r'["\']([^"\']*?/api/[^"\']*?)["\']', script_text)
                api_urls.update(urls)
        
        if api_urls:
            print(f"🔍 Found {len(api_urls)} potential API endpoints in page:")
            for api_url in list(api_urls)[:5]:
                print(f"  - {api_url}")
        
        # Look for deck links
        deck_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if any(keyword in href.lower() for keyword in ['deck', 'list', 'commander', 'edh']):
                deck_links.append(href)
        
        print(f"🔗 Found {len(deck_links)} potential deck links")
        if deck_links:
            print(f"  Sample: {deck_links[0]}")
        
        # Check if custom API exists
        if check_api:
            print(f"\n🧪 Testing custom API endpoint...")
            api_response = requests.get(check_api, headers=headers, timeout=10)
            print(f"  API Status: {api_response.status_code}")
            if api_response.status_code == 200:
                print(f"  ✅ API works!")
                if 'json' in api_response.headers.get('Content-Type', ''):
                    data = api_response.json()
                    print(f"  Response keys: {list(data.keys()) if isinstance(data, dict) else 'List'}")
                return True
        
        print(f"✅ Page accessible, HTML scraping possible")
        return True
        
    except requests.exceptions.Timeout:
        print(f"❌ Timeout after 10 seconds")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Test all sources
sources = [
    {
        'name': 'TappedOut',
        'url': 'https://tappedout.net/mtg-decks/search/',
        'api': 'https://tappedout.net/api/collection/collection:deck/'
    },
    {
        'name': 'MTGGoldfish Commander Meta',
        'url': 'https://www.mtggoldfish.com/metagame/commander#paper',
        'api': None
    },
    {
        'name': 'cEDH Decklist Database',
        'url': 'https://cedh-decklist-database.com/',
        'api': 'https://cedh-decklist-database.com/api/decks'
    },
    {
        'name': 'Moxfield Precons',
        'url': 'https://moxfield.com/decks/public?q=eyJmb3JtYXQiOiJjb21tYW5kZXJQcmVjb25zIn0%3D',
        'api': None
    },
    {
        'name': 'MTGDecks.net',
        'url': 'https://mtgdecks.net/Commander/decklists',
        'api': None
    },
    {
        'name': 'AetherHub',
        'url': 'https://aetherhub.com/Decks/Commander/',
        'api': 'https://aetherhub.com/API/Deck/GetDecks'
    }
]

results = []

for source in sources:
    result = test_source(
        source['name'],
        source['url'],
        source.get('api')
    )
    results.append({
        'name': source['name'],
        'accessible': result
    })
    time.sleep(2)  # Be polite between requests

print(f"\n\n{'='*60}")
print("SUMMARY")
print('='*60)

for result in results:
    status = '✅' if result['accessible'] else '❌'
    print(f"{status} {result['name']}")

accessible_count = sum(1 for r in results if r['accessible'])
print(f"\nAccessible sources: {accessible_count}/{len(results)}")
