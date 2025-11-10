"""
Orchestrate deck scraping from multiple sources
Combines EDHREC average decklists with other sources
"""
import sys
from pathlib import Path
import json

def main():
    print("="*70)
    print("COMMANDER DECK SCRAPING PIPELINE")
    print("="*70)
    print()
    
    output_dir = Path('data/training')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_decks = []
    
    # ========================================
    # Source 1: EDHREC Average Decklists
    # ========================================
    print("\n" + "="*70)
    print("SOURCE 1: EDHREC")
    print("="*70)
    print("Strategy: Scrape average decklists for top commanders")
    print("Expected: 3,000-5,000 high-quality decks")
    print()
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "edhrec_scraper", 
            Path(__file__).parent / "scrape-edhrec-decks.py"
        )
        edhrec_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(edhrec_module)
        
        scraper = edhrec_module.EDHRECScraper(output_dir=str(output_dir))
        edhrec_decks = scraper.scrape_decks(num_decks=3000)
        
        all_decks.extend(edhrec_decks)
        print(f"\n✓ EDHREC: Collected {len(edhrec_decks)} decks")
        
    except Exception as e:
        print(f"\n✗ EDHREC scraping failed: {e}")
    
    # ========================================
    # Source 2: Archidekt (Alternative)
    # ========================================
    print("\n" + "="*70)
    print("SOURCE 2: ARCHIDEKT")
    print("="*70)
    print("Strategy: Public API for Commander decklists")
    print("Expected: 1,000-2,000 decks")
    print()
    
    try:
        print("Archidekt scraper not yet implemented")
        print("API endpoint: https://archidekt.com/api/decks/cards/")
        print("Requires: format=commander, orderBy=-viewCount")
    except Exception as e:
        print(f"✗ Archidekt scraping failed: {e}")
    
    # ========================================
    # Source 3: TappedOut (Web Scraping)
    # ========================================
    print("\n" + "="*70)
    print("SOURCE 3: TAPPEDOUT")
    print("="*70)
    print("Strategy: Scrape high-score Commander decks")
    print("Expected: 500-1,000 decks")
    print()
    
    try:
        print("TappedOut scraper not yet implemented")
        print("URL pattern: https://tappedout.net/mtg-decks/search/?q=&format=commander&order=score")
    except Exception as e:
        print(f"✗ TappedOut scraping failed: {e}")
    
    # ========================================
    # Summary
    # ========================================
    print("\n" + "="*70)
    print("SCRAPING SUMMARY")
    print("="*70)
    print(f"Total decks collected: {len(all_decks)}")
    
    if all_decks:
        # Analyze collected decks
        commanders = {}
        for deck in all_decks:
            cmd = deck.get('commander', 'Unknown')
            commanders[cmd] = commanders.get(cmd, 0) + 1
        
        print(f"Unique commanders: {len(commanders)}")
        print(f"Average cards per deck: {sum(len(d.get('cards', [])) for d in all_decks) / len(all_decks):.1f}")
        
        # Save combined dataset
        combined_file = output_dir / 'all_scraped_decks.jsonl'
        with open(combined_file, 'w', encoding='utf-8') as f:
            for deck in all_decks:
                f.write(json.dumps(deck) + '\n')
        
        print(f"\n✓ Combined dataset saved: {combined_file}")
        print(f"  Size: {combined_file.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print("\n⚠ No decks collected!")
        print("\nNext steps:")
        print("1. Check internet connection")
        print("2. Verify scraper selectors (websites may have changed)")
        print("3. Add delays to avoid rate limiting")
        print("4. Try alternative sources")

if __name__ == '__main__':
    main()
