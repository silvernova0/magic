"""Check Falcon Syndicate MTG Rando for deck generation API"""
import requests
from bs4 import BeautifulSoup
import json

url = 'https://www.falconsyndicate.net/mtg-rando/'
headers = {'User-Agent': 'Mozilla/5.0'}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Content length: {len(response.text)}")
print("\n" + "="*60)
print("HTML Content:")
print("="*60)
print(response.text[:2000])

# Check if there's an API endpoint
soup = BeautifulSoup(response.text, 'html.parser')

# Look for script tags that might have API calls
scripts = soup.find_all('script')
print(f"\n\nFound {len(scripts)} script tags")

for i, script in enumerate(scripts):
    if script.string and ('api' in script.string.lower() or 'fetch' in script.string.lower()):
        print(f"\n--- Script {i+1} (API related) ---")
        print(script.string[:500])
