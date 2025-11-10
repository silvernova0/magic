"""
Scrape diverse Commander decks from Moxfield at different power levels
Collects decks across multiple strategies, commanders, and archetypes
"""
import sys
import time
import random
from pathlib import Path
import importlib.util

# Load MoxfieldScraper from scrape-moxfield.py
spec = importlib.util.spec_from_file_location("scrape_moxfield", Path(__file__).parent / "scrape-moxfield.py")
scrape_moxfield = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scrape_moxfield)
MoxfieldScraper = scrape_moxfield.MoxfieldScraper

def scrape_diverse_decks():
    """Scrape diverse Commander decks across multiple categories"""
    
    scraper = MoxfieldScraper(output_dir='data/training')
    
    print("="*60)
    print("DIVERSE MOXFIELD DECK SCRAPER")
    print("="*60)
    print("Target: 2000+ diverse Commander decks")
    print("Strategy: Multiple power levels, themes, and commanders")
    print("="*60)
    print()
    
    # Define search strategies to get diverse decks
    search_strategies = [
        # Popular tribal strategies
        {"name": "Dragon Tribal", "archetype": "dragon tribal", "decks": 50},
        {"name": "Elf Tribal", "archetype": "elf tribal", "decks": 40},
        {"name": "Vampire Tribal", "archetype": "vampire tribal", "decks": 40},
        {"name": "Zombie Tribal", "archetype": "zombie tribal", "decks": 40},
        {"name": "Goblin Tribal", "archetype": "goblin tribal", "decks": 40},
        {"name": "Wizard Tribal", "archetype": "wizard tribal", "decks": 30},
        {"name": "Angel Tribal", "archetype": "angel tribal", "decks": 30},
        {"name": "Knight Tribal", "archetype": "knight tribal", "decks": 30},
        
        # Popular strategies
        {"name": "Tokens", "archetype": "token", "decks": 50},
        {"name": "Voltron", "archetype": "voltron", "decks": 50},
        {"name": "Control", "archetype": "control", "decks": 50},
        {"name": "Combo", "archetype": "combo", "decks": 50},
        {"name": "Aggro", "archetype": "aggro", "decks": 40},
        {"name": "Aristocrats", "archetype": "aristocrats", "decks": 40},
        {"name": "Reanimator", "archetype": "reanimator", "decks": 40},
        {"name": "Spellslinger", "archetype": "spellslinger", "decks": 40},
        {"name": "Landfall", "archetype": "landfall", "decks": 30},
        {"name": "Enchantments", "archetype": "enchantment", "decks": 30},
        {"name": "Artifacts", "archetype": "artifact", "decks": 30},
        {"name": "Counters", "archetype": "+1/+1 counter", "decks": 30},
        
        # Power levels (using different sort methods)
        {"name": "Most Viewed (cEDH)", "sort": "views", "decks": 200},
        {"name": "Recently Updated (Mid Power)", "sort": "updated", "decks": 200},
        {"name": "Recently Created (Casual)", "sort": "created", "decks": 200},
        {"name": "Most Liked (Optimized)", "sort": "likes", "decks": 200},
        
        # Popular commanders
        {"name": "Atraxa Decks", "commander": "Atraxa, Praetors' Voice", "decks": 30},
        {"name": "The Ur-Dragon Decks", "commander": "The Ur-Dragon", "decks": 30},
        {"name": "Edgar Markov Decks", "commander": "Edgar Markov", "decks": 30},
        {"name": "Muldrotha Decks", "commander": "Muldrotha, the Gravetide", "decks": 30},
        {"name": "Krenko Decks", "commander": "Krenko, Mob Boss", "decks": 30},
        {"name": "Kumena Decks", "commander": "Kumena, Tyrant of Orazca", "decks": 30},
        {"name": "Omnath Decks", "commander": "Omnath, Locus of Creation", "decks": 30},
        {"name": "Prosper Decks", "commander": "Prosper, Tome-Bound", "decks": 30},
    ]
    
    total_target = sum(s["decks"] for s in search_strategies)
    print(f"Total target decks: {total_target}")
    print(f"Search strategies: {len(search_strategies)}")
    print()
    
    total_scraped = 0
    total_failed = 0
    
    for i, strategy in enumerate(search_strategies, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(search_strategies)}] {strategy['name']}")
        print(f"{'='*60}")
        
        # Prepare search parameters
        sort_by = strategy.get("sort", "views")
        commander = strategy.get("commander")
        archetype = strategy.get("archetype")
        target_decks = strategy["decks"]
        
        print(f"Target: {target_decks} decks")
        if commander:
            print(f"Commander: {commander}")
        if archetype:
            print(f"Archetype: {archetype}")
        print(f"Sort by: {sort_by}")
        print()
        
        # Scrape decks for this strategy
        try:
            # Modified scrape call - we need to update the scrape method
            decks = scrape_strategy(scraper, target_decks, sort_by, commander, archetype)
            total_scraped += len(decks)
            print(f"✓ Scraped {len(decks)} decks for {strategy['name']}")
            
        except Exception as e:
            print(f"✗ Error scraping {strategy['name']}: {e}")
            total_failed += 1
            continue
        
        # Pause between strategies
        if i < len(search_strategies):
            wait_time = random.uniform(5, 10)
            print(f"\n⏳ Waiting {wait_time:.1f}s before next strategy...")
            time.sleep(wait_time)
    
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total decks scraped: {total_scraped}")
    print(f"Failed strategies: {total_failed}")
    print(f"Success rate: {(len(search_strategies) - total_failed) / len(search_strategies) * 100:.1f}%")
    print(f"\n✓ Diverse deck collection complete!")
    print(f"📁 Saved to: data/training/moxfield_decks.jsonl")


def scrape_strategy(scraper, num_decks, sort_by="views", commander=None, archetype=None):
    """Scrape decks for a specific strategy"""
    decks = []
    page_num = 1
    max_pages = 20  # Limit pages per strategy
    
    while len(decks) < num_decks and page_num <= max_pages:
        try:
            results, total = scraper.search_commander_decks(
                page_num=page_num,
                page_size=32,
                sort_by=sort_by,
                commander_name=commander,
                archetype=archetype
            )
            
            if not results:
                print(f"  No more results (page {page_num})")
                break
            
            print(f"  Page {page_num}: Found {len(results)} decks")
            
            for deck_summary in results:
                if len(decks) >= num_decks:
                    break
                
                try:
                    deck_id = deck_summary.get('publicId', '')
                    deck_name = deck_summary.get('name', 'Unknown')
                    
                    # Get full deck details
                    deck_data = scraper.get_deck_details(deck_id)
                    
                    if not deck_data:
                        continue
                    
                    # Parse deck
                    parsed_deck = scraper.parse_deck(deck_data)
                    
                    if not parsed_deck:
                        continue
                    
                    # Save to file in append mode
                    training_example = {
                        'instruction': f"Build a Commander deck with {parsed_deck['commander']} focused on {parsed_deck['theme']}.",
                        'output': scraper._format_deck_output(parsed_deck),
                        'metadata': {
                            'type': 'deck_building',
                            'commander': parsed_deck['commander'],
                            'theme': parsed_deck['theme'],
                            'colors': parsed_deck['colors'],
                            'source': 'moxfield',
                            'quality_score': parsed_deck['metadata']['quality_score']
                        }
                    }
                    
                    # Append to file
                    import json
                    output_file = Path('data/training/moxfield_decks_diverse.jsonl')
                    with open(output_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(training_example) + '\n')
                    
                    decks.append(parsed_deck)
                    
                    # Rate limiting
                    time.sleep(random.uniform(0.5, 1.5))
                    
                except Exception as e:
                    print(f"    Error processing deck: {e}")
                    continue
            
            page_num += 1
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"  Error on page {page_num}: {e}")
            break
    
    return decks


if __name__ == '__main__':
    scrape_diverse_decks()
