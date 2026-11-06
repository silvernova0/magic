"""
Debug mono-blue commander page
"""
import requests
from bs4 import BeautifulSoup

url = 'https://edhrec.com/commanders/mono-blue'
print(f"Fetching {url}...")

r = requests.get(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

soup = BeautifulSoup(r.text, 'html.parser')

print(f"Status: {r.status_code}")
print(f"Title: {soup.find('title').text if soup.find('title') else 'None'}\n")

# Find all links on the page
all_links = soup.find_all('a', href=True)
print(f"Total links: {len(all_links)}\n")

# Filter for commander links
commander_links = []
for link in all_links:
    href = link.get('href')
    text = link.get_text(strip=True)
    
    if href and '/commanders/mono-blue/' in href:
        commander_links.append((text, href))

print(f"Commander links found: {len(commander_links)}\n")
print("First 10:")
for i, (text, href) in enumerate(commander_links[:10], 1):
    print(f"  {i}. {text[:50]}")
    print(f"     {href}")
