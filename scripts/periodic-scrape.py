#!/usr/bin/env python3
"""
Periodic Deck Scraper
---------------------
Orchestrates incremental scraping of new Commander decks from multiple sources.
Designed to be run periodically (e.g., weekly) to keep the database fresh.

Usage:
    python3 scripts/periodic-scrape.py --days 14
    python3 scripts/periodic-scrape.py --days 7 --source moxfield
"""

import argparse
import sys
import os
from datetime import datetime, timedelta, timezone
import importlib.util

# Import scrapers dynamically to avoid path issues
def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

try:
    moxfield_script = os.path.join(os.path.dirname(__file__), 'scrape-moxfield-decks.py')
    mtggoldfish_script = os.path.join(os.path.dirname(__file__), 'scrape-mtggoldfish-decks.py')
    
    moxfield = import_module_from_path('moxfield_scraper', moxfield_script)
    mtggoldfish = import_module_from_path('mtggoldfish_scraper', mtggoldfish_script)
except Exception as e:
    print(f"Error importing scrapers: {e}")
    sys.exit(1)

def run_moxfield_update(days, dry_run=False):
    """Run incremental Moxfield scrape"""
    print(f"\n{'='*60}")
    print(f"MOXFIELD UPDATE (Last {days} days)")
    print(f"{'='*60}")
    
    if dry_run:
        print("DRY RUN: Would scrape Moxfield decks updated in the last", days, "days")
        return
    
    min_date = datetime.now(timezone.utc) - timedelta(days=days)
    scraper = moxfield.MoxfieldScraper()
    
    # Scrape decks sorted by 'updated' until we hit the date limit
    # We lower the quality threshold for new decks since they haven't accumulated views yet
    scraper.scrape_decks(
        num_decks=500,  # Cap at 500 new decks per run
        min_quality=10, # Lower quality threshold for recent decks
        min_date=min_date,
        sort_by='updated'
    )

def run_mtggoldfish_update(dry_run=False):
    """Run incremental MTGGoldfish scrape"""
    print(f"\n{'='*60}")
    print(f"MTGGOLDFISH UPDATE")
    print(f"{'='*60}")
    
    if dry_run:
        print("DRY RUN: Would scrape new MTGGoldfish decks (deduplicated by ID)")
        return
    
    scraper = mtggoldfish.MTGGoldfishScraper()
    
    # MTGGoldfish scraper automatically skips existing IDs
    # We just run it to check for new archetypes/decks
    scraper.scrape_archetypes(
        target_decks=200, # Cap at 200 new decks per run
        decks_per_archetype=10 # Check top 10 of each archetype
    )

def main():
    parser = argparse.ArgumentParser(description="Periodic deck scraper for incremental updates")
    parser.add_argument('--days', type=int, default=14, help="Look for decks updated in the last N days (Moxfield only)")
    parser.add_argument('--source', choices=['all', 'moxfield', 'mtggoldfish'], default='all', help="Which source to scrape")
    parser.add_argument('--dry-run', action='store_true', help="Simulate run without scraping")
    
    args = parser.parse_args()
    
    print(f"Starting periodic scrape (Window: {args.days} days)")
    
    if args.source in ['all', 'moxfield']:
        run_moxfield_update(args.days, args.dry_run)
        
    if args.source in ['all', 'mtggoldfish']:
        run_mtggoldfish_update(args.dry_run)
        
    print("\nPeriodic scrape complete!")

if __name__ == '__main__':
    main()
