"""Test the Archidekt scraper with just 2 decks"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Import the scraper class by loading the module
import importlib.util
spec = importlib.util.spec_from_file_location("scraper", "C:\\magicapp\\scripts\\scrape-archidekt-decks.py")
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)

scraper = scraper_module.ArchidektScraper()

# Test with just 2 decks
print("Testing Archidekt scraper with 2 decks...\n")
decks = scraper.scrape_decks(num_decks=2, min_views=10000)

if decks:
    print(f"\n✓ Success! Scraped {len(decks)} decks")
    print(f"\nFirst deck:")
    d = decks[0]
    print(f"  Commander: {d['commander']}")
    print(f"  Name: {d['name']}")
    print(f"  Cards: {len(d['cards'])}")
    print(f"  Views: {d['metadata']['views']:,}")
else:
    print("✗ Failed to scrape any decks")
