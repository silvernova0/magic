"""
Test fixed EDHREC scraper
"""
import sys
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location(
    "scraper", 
    Path(__file__).parent / "scrape-edhrec-decks.py"
)
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)

scraper = scraper_module.EDHRECScraper()

print("Testing commander detection...")
commanders = scraper.get_top_commanders(limit=10)

print(f"\n✓ Found {len(commanders)} commanders:\n")
for i, cmd in enumerate(commanders, 1):
    print(f"  {i}. {cmd['name']}")
    print(f"     {cmd['url']}")

if commanders:
    print(f"\nTesting deck scraping for first commander...")
    deck = scraper.scrape_commander_page(commanders[0]['url'], commanders[0]['name'])
    
    if deck:
        print(f"\n✓ Deck scraped successfully:")
        print(f"  Commander: {deck['commander']}")
        print(f"  Theme: {deck['theme']}")
        print(f"  Colors: {', '.join(deck['colors'])}")
        print(f"  Cards: {len(deck['cards'])}")
        
        if deck['cards']:
            print(f"\n  Sample cards:")
            for card in deck['cards'][:5]:
                print(f"    - {card['name']} ({card['category']})")
    else:
        print("\n✗ Failed to scrape deck")
