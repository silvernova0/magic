#!/usr/bin/env python3
"""
Scrape EDHREC average decks for all commanders
URL pattern: https://edhrec.com/average-decks/{commander-slug}
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from pathlib import Path

def slugify(name):
    """Convert commander name to EDHREC URL slug"""
    # "The Ur-Dragon" → "the-ur-dragon"
    # "Atraxa, Praetors' Voice" → "atraxa-praetors-voice"
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = slug.replace(",", "")
    slug = slug.replace(" ", "-")
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    return slug

def scrape_average_deck(commander_name):
    """Scrape EDHREC average deck for a single commander"""
    
    slug = slugify(commander_name)
    url = f"https://edhrec.com/average-decks/{slug}"
    
    print(f"Scraping: {commander_name} ({url})")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            print(f"  ⚠️  No average deck found for {commander_name}")
            return None
        
        if response.status_code != 200:
            print(f"  ❌ Error {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        deck_data = {
            "commander": commander_name,
            "slug": slug,
            "url": url,
            "categories": {},
            "all_cards": [],
            "themes": [],
            "card_count_by_type": {},
            "total_cards": 0
        }
        
        # Find all card containers
        # EDHREC uses different class names, try multiple approaches
        
        # Method 1: Find card sections by headers
        card_sections = soup.find_all(['div', 'section'], class_=re.compile(r'Card.*Section|card.*section', re.I))
        
        if not card_sections:
            # Method 2: Find all card links and group them
            all_card_links = soup.find_all('a', href=re.compile(r'/cards/'))
            if all_card_links:
                deck_data["all_cards"] = [link.text.strip() for link in all_card_links[:99]]  # Max 99 mainboard
                deck_data["total_cards"] = len(deck_data["all_cards"])
        else:
            # Process sections
            for section in card_sections:
                # Find section title
                title_elem = section.find(['h2', 'h3', 'h4', 'span'], class_=re.compile(r'title|header', re.I))
                category = title_elem.text.strip() if title_elem else "Other"
                
                # Find cards in section
                card_links = section.find_all('a', href=re.compile(r'/cards/'))
                cards_in_category = []
                
                for link in card_links:
                    card_name = link.text.strip()
                    if card_name and card_name not in deck_data["all_cards"]:
                        cards_in_category.append(card_name)
                        deck_data["all_cards"].append(card_name)
                
                if cards_in_category:
                    deck_data["categories"][category] = {
                        "count": len(cards_in_category),
                        "cards": cards_in_category
                    }
        
        deck_data["total_cards"] = len(deck_data["all_cards"])
        
        # Extract themes/tags if available
        theme_elements = soup.find_all(['span', 'div'], class_=re.compile(r'theme|tag', re.I))
        deck_data["themes"] = [elem.text.strip() for elem in theme_elements[:10]]  # Limit to 10
        
        # Try to extract card type distribution
        type_elements = soup.find_all(['div', 'span'], class_=re.compile(r'type.*count|distribution', re.I))
        for elem in type_elements:
            text = elem.text.strip()
            # Look for patterns like "Creatures: 25" or "25 Creatures"
            match = re.search(r'(\d+)\s*(\w+)', text)
            if match:
                count, card_type = match.groups()
                deck_data["card_count_by_type"][card_type] = int(count)
        
        if deck_data["total_cards"] > 0:
            print(f"  ✅ Found {deck_data['total_cards']} cards")
            return deck_data
        else:
            print(f"  ⚠️  No cards found")
            return None
            
    except requests.Timeout:
        print(f"  ❌ Timeout")
        return None
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:100]}")
        return None

def get_commander_list_from_db():
    """Get list of legendary creatures from database"""
    import sqlite3
    
    db_path = Path(__file__).parent.parent / "prisma" / "dev.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all legendary creatures (excluding Arena variants with A- prefix)
    cursor.execute("""
        SELECT DISTINCT name 
        FROM Card 
        WHERE typeLine LIKE '%Legendary%' 
          AND typeLine LIKE '%Creature%'
          AND name NOT LIKE 'A-%'
        ORDER BY name
    """)
    
    commanders = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"Found {len(commanders)} legendary creatures in database")
    return commanders

def scrape_all_average_decks(limit=None):
    """Scrape average decks for all commanders"""
    
    output_file = Path(__file__).parent.parent / "data" / "training" / "edhrec_average_decks.jsonl"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    commanders = get_commander_list_from_db()
    
    if limit:
        commanders = commanders[:limit]
        print(f"Limiting to first {limit} commanders for testing")
    
    print(f"\n{'='*60}")
    print(f"Scraping EDHREC average decks for {len(commanders)} commanders")
    print(f"Output: {output_file}")
    print(f"{'='*60}\n")
    
    scraped_count = 0
    failed_count = 0
    
    with open(output_file, 'w') as f:
        for i, commander in enumerate(commanders, 1):
            print(f"\n[{i}/{len(commanders)}] ", end="")
            
            deck_data = scrape_average_deck(commander)
            
            if deck_data:
                # Save as JSONL (one JSON object per line)
                f.write(json.dumps(deck_data) + '\n')
                f.flush()
                scraped_count += 1
            else:
                failed_count += 1
            
            # Rate limiting - be nice to EDHREC
            if i < len(commanders):
                time.sleep(1.5)  # 1.5 seconds between requests
            
            # Progress update every 50 commanders
            if i % 50 == 0:
                print(f"\n{'='*60}")
                print(f"Progress: {i}/{len(commanders)} ({i/len(commanders)*100:.1f}%)")
                print(f"Scraped: {scraped_count} | Failed: {failed_count}")
                print(f"{'='*60}")
    
    print(f"\n{'='*60}")
    print(f"✅ SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"Total commanders: {len(commanders)}")
    print(f"Successfully scraped: {scraped_count}")
    print(f"Failed/Not found: {failed_count}")
    print(f"Success rate: {scraped_count/len(commanders)*100:.1f}%")
    print(f"\nOutput saved to: {output_file}")
    print(f"{'='*60}\n")
    
    return scraped_count

if __name__ == "__main__":
    import sys
    
    # Optional: limit for testing
    # python scripts/scrape-edhrec-average-decks.py 10
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    scraped_count = scrape_all_average_decks(limit=limit)
    
    if scraped_count > 0:
        print("✅ Ready for next step: scrape EDHREC combos")
    else:
        print("❌ No decks scraped. Check database connection.")
