"""
Debug EDHREC page structure
"""
import requests
from bs4 import BeautifulSoup

print("Fetching EDHREC commanders page...")
r = requests.get('https://edhrec.com/commanders', headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

soup = BeautifulSoup(r.text, 'html.parser')

print(f"Status: {r.status_code}")
print(f"Title: {soup.find('title').text if soup.find('title') else 'None'}")

# Find all divs with 'card' in class name
card_divs = soup.find_all('div', class_=lambda x: x and 'card' in str(x).lower())
print(f"\nFound {len(card_divs)} divs with 'card' in class")

# Show first 3 card structures
print("\nFirst 3 card class names:")
for i, card in enumerate(card_divs[:3], 1):
    print(f"  {i}. {card.get('class')}")

# Look for commander names
print("\nLooking for commander names...")
for selector in ['h3', 'h4', '.card-name', '[class*="name"]', 'a']:
    elements = soup.select(selector)
    if elements:
        print(f"\n{selector} ({len(elements)} found):")
        for elem in elements[:5]:
            text = elem.get_text(strip=True)
            if text and len(text) > 3 and len(text) < 50:
                print(f"  - {text}")

# Look for commander links
print("\nLooking for commander links...")
links = soup.find_all('a', href=lambda x: x and '/commanders/' in str(x))
print(f"Found {len(links)} links to commander pages")

# Filter for actual commander pages (not category pages)
commander_links = []
for link in links:
    href = link.get('href')
    text = link.get_text(strip=True)
    
    # Commander pages have at least 4 slashes: /commanders/color/commander-name
    if href.count('/') >= 4 and text and len(text) > 3:
        commander_links.append((text, href))

print(f"\n✓ Filtered to {len(commander_links)} actual commander links")
print("\nFirst 10 commanders:")
for i, (name, url) in enumerate(commander_links[:10], 1):
    print(f"  {i}. {name}")
    print(f"     {url}")

# Save sample HTML for one commander link
print("\n\nSaving sample commander link HTML...")
if links:
    sample_link = links[5] if len(links) > 5 else links[0]
    print(f"Sample: {sample_link.get('href')}")
    print(sample_link.prettify())
