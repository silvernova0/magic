"""
Test Moxfield scraper with a small sample
"""
import sys
from pathlib import Path

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Import with full module path
import importlib.util
spec = importlib.util.spec_from_file_location("scraper", script_dir / "scrape-moxfield-decks.py")
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)
MoxfieldScraper = scraper_module.MoxfieldScraper

scraper = MoxfieldScraper()

print("Testing Moxfield API connection...")
results = scraper.search_commander_decks(page=1, page_size=5)

if results:
    print(f"✓ Found {len(results)} decks")
    print(f"\nSample decks:")
    for i, deck in enumerate(results[:3], 1):
        print(f"  {i}. {deck.get('name', 'Unknown')}")
        print(f"     Format: {deck.get('format', 'N/A')}")
        print(f"     Views: {deck.get('viewCount', 0)}")
    
    print(f"\nFetching full details for first deck...")
    deck_id = results[0].get('publicId')
    deck_data = scraper.get_deck_details(deck_id)
    
    if deck_data:
        parsed = scraper.parse_deck(deck_data)
        if parsed:
            print(f"✓ Successfully parsed deck:")
            print(f"  Commander: {parsed['commander']}")
            print(f"  Theme: {parsed['theme']}")
            print(f"  Colors: {', '.join(parsed['colors'])}")
            print(f"  Cards: {len(parsed['cards'])}")
            print(f"  Quality: {parsed['metadata']['quality_score']}")
        else:
            print("✗ Failed to parse deck")
    else:
        print("✗ Failed to fetch deck details")
else:
    print("✗ No results found")
