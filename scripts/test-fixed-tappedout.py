"""Quick test of fixed TappedOut scraper - just 5 decks"""
import sys
sys.path.insert(0, 'C:\\magicapp\\scripts')

import importlib.util
spec = importlib.util.spec_from_file_location("scraper", "C:\\magicapp\\scripts\\scrape-tappedout.py")
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)

scraper = scraper_module.TappedOutScraper()

print("Testing TappedOut scraper with 5 decks...\n")
decks = scraper.scrape_decks(num_decks=5, max_pages=1)

if decks:
    print(f"\n{'='*60}")
    print("SUCCESS - Scraped decks:")
    print('='*60)
    for i, deck in enumerate(decks, 1):
        print(f"\n{i}. {deck['name']}")
        print(f"   Commander: {deck['commander']}")
        print(f"   Cards: {len(deck['cards'])}")
        print(f"   URL: {deck['url']}")
        
        # Show first few cards
        print(f"   Sample cards:")
        for card in deck['cards'][:3]:
            print(f"     {card['quantity']}x {card['name']} ({card['category']})")
else:
    print("❌ No decks scraped")
