#!/usr/bin/env python3
"""
Scrape EDHREC combo data
URL: https://edhrec.com/combos/{color-identity}
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from pathlib import Path

def scrape_combos_for_colors(colors):
    """Scrape combos for a specific color identity"""
    
    # Convert ["W", "U"] to "wu"
    color_slug = "".join(colors).lower() if colors else "colorless"
    url = f"https://edhrec.com/combos/{color_slug}"
    
    print(f"Scraping combos: {color_slug.upper() or 'Colorless'} ({url})")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"  ❌ Error {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        combos = []
        
        # Find combo containers
        # EDHREC combos page structure varies, try multiple selectors
        combo_containers = soup.find_all(['div', 'article'], class_=re.compile(r'combo', re.I))
        
        if not combo_containers:
            # Alternative: find by card links grouped together
            # Look for sections with multiple card links
            all_sections = soup.find_all(['div', 'section'])
            for section in all_sections:
                card_links = section.find_all('a', href=re.compile(r'/cards/'))
                if len(card_links) >= 2:  # Combo needs at least 2 cards
                    combo_containers.append(section)
        
        print(f"  Found {len(combo_containers)} potential combos")
        
        for container in combo_containers:
            # Extract card names
            card_links = container.find_all('a', href=re.compile(r'/cards/'))
            card_names = [link.text.strip() for link in card_links if link.text.strip()]
            
            if len(card_names) < 2:
                continue  # Not a valid combo
            
            # Extract result/description
            result = "Unknown"
            result_elem = container.find(['p', 'div', 'span'], class_=re.compile(r'result|description|effect', re.I))
            if result_elem:
                result = result_elem.text.strip()
            else:
                # Try to find any text that looks like a description
                text_content = container.get_text()
                # Look for phrases like "Infinite damage" "Win the game" etc
                for line in text_content.split('\n'):
                    line = line.strip()
                    if any(keyword in line.lower() for keyword in ['infinite', 'win', 'draw', 'mana', 'damage', 'life']):
                        result = line
                        break
            
            # Extract popularity (number of decks)
            popularity = 0
            pop_elem = container.find(['span', 'div'], class_=re.compile(r'popularity|decks?|count', re.I))
            if pop_elem:
                pop_text = pop_elem.text.strip()
                match = re.search(r'(\d+(?:,\d+)*)', pop_text)
                if match:
                    popularity = int(match.group(1).replace(',', ''))
            
            # Determine tags from result text
            tags = []
            result_lower = result.lower()
            if 'infinite' in result_lower:
                tags.append('infinite')
            if 'win' in result_lower or 'game' in result_lower:
                tags.append('win_con')
            if 'token' in result_lower:
                tags.append('tokens')
            if 'damage' in result_lower:
                tags.append('damage')
            if 'life' in result_lower:
                tags.append('lifegain')
            if 'mana' in result_lower:
                tags.append('mana')
            if 'draw' in result_lower:
                tags.append('draw')
            if 'mill' in result_lower:
                tags.append('mill')
            
            combo_data = {
                "combo_id": "-".join([slugify(name) for name in card_names[:3]]),
                "name": " + ".join(card_names),
                "cards": card_names,
                "colors": list(colors.upper()) if colors else [],
                "result": result[:200],  # Limit length
                "tags": tags,
                "popularity": popularity,
                "power_level": estimate_power_level(tags, len(card_names))
            }
            
            combos.append(combo_data)
        
        print(f"  ✅ Extracted {len(combos)} combos")
        return combos
        
    except requests.Timeout:
        print(f"  ❌ Timeout")
        return []
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:100]}")
        return []

def slugify(name):
    """Convert card name to slug"""
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = slug.replace(",", "")
    slug = slug.replace(" ", "-")
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    return slug

def estimate_power_level(tags, num_cards):
    """Estimate combo power level based on characteristics"""
    base_power = 7
    
    if 'infinite' in tags:
        base_power += 1
    if 'win_con' in tags:
        base_power += 1
    if num_cards == 2:
        base_power += 1  # 2-card combos are better
    elif num_cards >= 4:
        base_power -= 1  # 4+ card combos are weaker
    
    return min(10, max(1, base_power))

def scrape_all_combos():
    """Scrape combos for all color combinations"""
    
    output_file = Path(__file__).parent.parent / "data" / "training" / "edhrec_combos.jsonl"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # All color combinations (32 total)
    color_combos = [
        # Colorless
        "",
        # Mono
        "w", "u", "b", "r", "g",
        # Two-color (guilds)
        "wu", "wb", "ub", "ur", "br", "bg", "rg", "gw", "gu", "rw",
        # Three-color (shards/wedges)
        "wub", "ubr", "brg", "rgw", "gwu",  # Shards
        "wbg", "urw", "bgu", "rwb", "gur",  # Wedges
        # Four-color
        "wubr", "ubrg", "brgw", "rgwu", "gwub",
        # Five-color
        "wubrg"
    ]
    
    print(f"\n{'='*60}")
    print(f"Scraping EDHREC combos for {len(color_combos)} color combinations")
    print(f"Output: {output_file}")
    print(f"{'='*60}\n")
    
    all_combos = []
    total_scraped = 0
    
    with open(output_file, 'w') as f:
        for i, colors in enumerate(color_combos, 1):
            print(f"\n[{i}/{len(color_combos)}] ", end="")
            
            combos = scrape_combos_for_colors(colors)
            
            for combo in combos:
                # Save as JSONL
                f.write(json.dumps(combo) + '\n')
                f.flush()
                total_scraped += 1
            
            all_combos.extend(combos)
            
            # Rate limiting
            if i < len(color_combos):
                time.sleep(1.0)
            
            # Progress update
            if i % 10 == 0:
                print(f"\n{'='*60}")
                print(f"Progress: {i}/{len(color_combos)} color combos")
                print(f"Total combos scraped: {total_scraped}")
                print(f"{'='*60}")
    
    print(f"\n{'='*60}")
    print(f"✅ COMBO SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"Total combos: {total_scraped}")
    print(f"Unique combos: {len(set(c['combo_id'] for c in all_combos))}")
    
    # Statistics
    by_colors = {}
    for combo in all_combos:
        color_key = "".join(combo['colors']) or "Colorless"
        by_colors[color_key] = by_colors.get(color_key, 0) + 1
    
    print(f"\nCombos by color:")
    for color, count in sorted(by_colors.items(), key=lambda x: -x[1])[:10]:
        print(f"  {color}: {count}")
    
    print(f"\nOutput saved to: {output_file}")
    print(f"{'='*60}\n")
    
    return total_scraped

if __name__ == "__main__":
    total_combos = scrape_all_combos()
    
    if total_combos > 0:
        print("✅ Combo data ready!")
        print("Next: Create deck building rules database")
    else:
        print("⚠️  No combos scraped. EDHREC may have changed their HTML structure.")
        print("Check the website manually and update selectors if needed.")
