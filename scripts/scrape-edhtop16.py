#!/usr/bin/env python3
"""
EDHTop16 Tournament Scraper

Scrapes tournament data from EDHTop16.com including:
- Tournament winning deck commanders
- Player names and standings
- Tournament size and competitiveness
- Direct links to full decklists

This source provides actual cEDH tournament results.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
from pathlib import Path

class EDHTop16Scraper:
    def __init__(self, skip_existing=True):
        self.base_url = "https://edhtop16.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.scraped_tournaments = set()
        self.skip_existing = skip_existing
        
        # Load existing tournaments to skip re-scraping
        if skip_existing:
            self._load_existing_tournaments()
    
    def _load_existing_tournaments(self):
        """Load previously scraped tournaments to avoid re-scraping"""
        output_dir = Path(__file__).parent.parent / 'data' / 'training'
        output_file = output_dir / 'edhtop16_tournaments.json'
        
        if output_file.exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_tournaments = json.load(f)
                
                # Extract URLs from existing tournaments
                for tournament in existing_tournaments:
                    url = tournament.get('url', '')
                    if url:
                        # Store just the path part (e.g., "/tournament/name")
                        path = url.replace(self.base_url, '')
                        self.scraped_tournaments.add(path)
                
                print(f"✓ Loaded {len(self.scraped_tournaments)} existing tournaments (will skip)")
            except Exception as e:
                print(f"⚠️  Could not load existing tournaments: {e}")
        else:
            print(f"ℹ️  No existing tournaments file found - will scrape all")
        
    def get_tournaments_page(self, cursor=None):
        """Fetch tournaments list page"""
        try:
            url = f"{self.base_url}/tournaments"
            if cursor:
                url += f"?cursor={cursor}"
                print(f"Fetching tournaments page (cursor: {cursor[:20]}...)...")
            else:
                print(f"Fetching tournaments page (initial load)...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching tournaments page: {e}")
            return None
    
    def get_tournament_details(self, tournament_url):
        """Fetch individual tournament details"""
        try:
            full_url = f"{self.base_url}{tournament_url}"
            print(f"  Fetching tournament: {full_url}")
            response = self.session.get(full_url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"  Error fetching tournament details: {e}")
            return None
    
    def parse_tournaments_list(self, html):
        """Extract tournament links from listing page and pagination cursor"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find tournament links in the grid
        tournament_links = []
        tournament_cards = soup.find_all('a', href=re.compile(r'^/tournament/'))
        
        for card in tournament_cards:
            href = card.get('href')
            if href and href not in self.scraped_tournaments:
                tournament_links.append(href)
        
        # Extract cursor from window.__router_ops for pagination
        next_cursor = None
        has_next_page = False
        
        script_tags = soup.find_all('script', id='_R_')
        for script in script_tags:
            if not script.string or 'window.__router_ops' not in script.string:
                continue
                
            try:
                start_marker = 'window.__router_ops = '
                start_idx = script.string.find(start_marker)
                if start_idx == -1:
                    continue
                    
                start_idx += len(start_marker)
                end_idx = script.string.find(';', start_idx)
                
                if end_idx == -1:
                    continue
                    
                json_str = script.string[start_idx:end_idx]
                json_str = json_str.replace(':undefined', ':null')
                json_str = json_str.replace(',undefined', ',null')
                
                data = json.loads(json_str)
                
                # Navigate to pageInfo with cursor
                # Structure: [[fragment, {response: {edges: [...], pageInfo: {endCursor, hasNextPage}}}]]
                if isinstance(data, list) and len(data) > 0:
                    for item in data:
                        if isinstance(item, list) and len(item) > 1:
                            response_data = item[1]
                            if isinstance(response_data, dict) and 'response' in response_data:
                                response = response_data['response']
                                if isinstance(response, dict) and 'pageInfo' in response:
                                    page_info = response['pageInfo']
                                    next_cursor = page_info.get('endCursor')
                                    has_next_page = page_info.get('hasNextPage', False)
                                    break
                
                if next_cursor and has_next_page:
                    break
                    
            except Exception as e:
                print(f"    Error parsing pagination cursor: {e}")
                continue
        
        print(f"Found {len(tournament_links)} new tournaments on this page")
        if has_next_page:
            print(f"  Next cursor available: {next_cursor}")
        else:
            print(f"  No more pages available")
            
        return tournament_links, next_cursor, has_next_page
    
    def parse_tournament_page(self, html, tournament_url):
        """Extract tournament details and decklists from embedded JSON"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find the script tag with window.__router_ops
        script_tags = soup.find_all('script', id='_R_')
        
        tournament_data = {
            'name': 'Unknown Tournament',
            'url': tournament_url,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'size': 0,
            'entries': [],
            'source': 'edhtop16',
            'scraped_at': datetime.now().isoformat()
        }
        
        for script in script_tags:
            if not script.string or 'window.__router_ops' not in script.string:
                continue
                
            try:
                # Extract the JSON: find "window.__router_ops = " and get everything until ";</script>"
                start_marker = 'window.__router_ops = '
                end_marker = ';</script>'
                
                start_idx = script.string.find(start_marker)
                if start_idx == -1:
                    continue
                    
                start_idx += len(start_marker)
                end_idx = script.string.find(end_marker, start_idx)
                
                if end_idx == -1:
                    # Try without </script> - just find the semicolon
                    end_idx = script.string.find(';', start_idx)
                
                if end_idx == -1:
                    continue
                    
                json_str = script.string[start_idx:end_idx]
                
                # Fix JavaScript-specific values that aren't valid JSON
                json_str = json_str.replace(':undefined', ':null')
                json_str = json_str.replace(',undefined', ',null')
                
                data = json.loads(json_str)
                
                # Navigate through the nested structure
                # data is [[fragment_data, tournament_response], ...]
                for item in data:
                    if not isinstance(item, list) or len(item) < 2:
                        continue
                    
                    # Second element has actual tournament data
                    response_data = item[1]
                    if not isinstance(response_data, dict) or 'tournament' not in response_data:
                        continue
                    
                    tournament = response_data['tournament']
                    
                    # Extract tournament metadata
                    tournament_data['name'] = tournament.get('name', 'Unknown Tournament')
                    tournament_data['size'] = tournament.get('size', 0)
                    tournament_data['date'] = tournament.get('tournamentDate', '').split('T')[0] if tournament.get('tournamentDate') else datetime.now().strftime('%Y-%m-%d')
                    
                    # Extract entries
                    entries_raw = tournament.get('entries', [])
                    
                    for entry in entries_raw:
                        player_name = entry.get('player', {}).get('name', 'Unknown')
                        standing = entry.get('standing', 999)
                        wins = entry.get('wins', 0)
                        losses = entry.get('losses', 0)
                        draws = entry.get('draws', 0)
                        decklist_url = entry.get('decklist', '')
                        
                        # Extract commander info
                        commander_data = entry.get('commander', {})
                        commander_name = commander_data.get('name', 'Unknown Commander')
                        commander_cards = commander_data.get('cards', [])
                        
                        # Get card image URLs
                        card_images = []
                        for card in commander_cards:
                            images = card.get('imageUrls', [])
                            if images:
                                card_images.append(images[0])  # Take first image
                        
                        tournament_data['entries'].append({
                            'player': player_name,
                            'commander': commander_name,
                            'commander_images': card_images,
                            'position': standing,
                            'wins': wins,
                            'losses': losses,
                            'draws': draws,
                            'decklist_url': decklist_url
                        })
                    
                    # Sort by standing
                    tournament_data['entries'].sort(key=lambda x: x.get('position', 999))
                    
                    break  # Found the tournament data
                    
            except json.JSONDecodeError as e:
                print(f"    JSON parse error at position {e.pos if hasattr(e, 'pos') else 'unknown'}")
                continue
            except Exception as e:
                print(f"    Error parsing tournament data: {e}")
                continue
        
        return tournament_data
    
    def scrape_tournaments(self, max_tournaments=None):
        """Main scraping function with cursor-based pagination support"""
        all_tournaments = []
        all_tournament_links = []
        
        cursor = None
        has_next_page = True
        page_num = 0
        
        # Paginate through all available tournaments
        while has_next_page:
            page_num += 1
            print(f"\n=== PAGE {page_num} ===")
            
            # Fetch page
            html = self.get_tournaments_page(cursor)
            if not html:
                print("Failed to fetch tournaments page")
                break
            
            # Parse page
            tournament_links, next_cursor, has_next_page = self.parse_tournaments_list(html)
            all_tournament_links.extend(tournament_links)
            
            print(f"📊 Pagination status:")
            print(f"   - Found {len(tournament_links)} new links on this page")
            print(f"   - Total collected so far: {len(all_tournament_links)}")
            print(f"   - Next cursor: {next_cursor[:30] if next_cursor else 'None'}...")
            print(f"   - Has next page: {has_next_page}")
            
            # Update cursor for next iteration
            cursor = next_cursor
            
            # Optional: limit total tournaments
            if max_tournaments and len(all_tournament_links) >= max_tournaments:
                print(f"\nReached max_tournaments limit ({max_tournaments})")
                all_tournament_links = all_tournament_links[:max_tournaments]
                break
            
            # Stop if no more pages
            if not has_next_page:
                print(f"\n✓ Reached end of pagination (no more pages)")
                break
            
            # Rate limiting between pagination requests
            if has_next_page:
                print(f"⏱️  Rate limiting... (1.0s)")
                time.sleep(1.0)
        
        print(f"\n{'='*50}")
        print(f"Total unique tournament links collected: {len(all_tournament_links)}")
        print(f"{'='*50}\n")
        
        # Now scrape details for each tournament
        print(f"Scraping details for {len(all_tournament_links)} tournaments...")
        
        skipped_no_entries = 0
        skipped_no_decklists = 0
        
        for i, link in enumerate(all_tournament_links, 1):
            print(f"\n[{i}/{len(all_tournament_links)}]", end=" ")
            
            tournament_html = self.get_tournament_details(link)
            if not tournament_html:
                continue
            
            tournament_data = self.parse_tournament_page(tournament_html, link)
            
            # Check if tournament has any usable data
            if tournament_data['size'] == 0 or len(tournament_data['entries']) == 0:
                print(f"  ⊘ {tournament_data['name']} - No entries found, skipping")
                skipped_no_entries += 1
                self.scraped_tournaments.add(link)
                time.sleep(0.5)
                continue
            
            # Check if any entries have actual decklist URLs
            entries_with_decklists = [e for e in tournament_data['entries'] if e.get('decklist_url')]
            
            if len(entries_with_decklists) == 0:
                print(f"  ⊘ {tournament_data['name']} ({tournament_data['size']} players) - No decklists available, skipping")
                skipped_no_decklists += 1
                self.scraped_tournaments.add(link)
                time.sleep(0.5)
                continue
            
            # Tournament has valid data - add it
            all_tournaments.append(tournament_data)
            print(f"  ✓ {tournament_data['name']} ({tournament_data['size']} players, {tournament_data['date']})")
            print(f"     Winner: {tournament_data['entries'][0]['player']} with {tournament_data['entries'][0]['commander']}")
            print(f"     Decklists available: {len(entries_with_decklists)}/{len(tournament_data['entries'])}")
            
            self.scraped_tournaments.add(link)
            
            # Rate limiting
            time.sleep(0.5)
        
        print(f"\n{'='*50}")
        print(f"Skipped tournaments: {skipped_no_entries + skipped_no_decklists}")
        print(f"  - No entries: {skipped_no_entries}")
        print(f"  - No decklists: {skipped_no_decklists}")
        print(f"{'='*50}")
        
        return all_tournaments
    
    def save_tournaments(self, tournaments, filename='edhtop16_tournaments.json', merge=True):
        """Save tournament data to JSON file, optionally merging with existing data"""
        output_dir = Path(__file__).parent.parent / 'data' / 'training'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / filename
        
        # Merge with existing data if requested
        if merge and output_file.exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_tournaments = json.load(f)
                
                # Create a set of existing tournament URLs to avoid duplicates
                existing_urls = {t.get('url', '') for t in existing_tournaments}
                
                # Add new tournaments that don't already exist
                new_count = 0
                for tournament in tournaments:
                    if tournament.get('url', '') not in existing_urls:
                        existing_tournaments.append(tournament)
                        new_count += 1
                
                print(f"ℹ️  Merging: {len(existing_tournaments)} existing + {new_count} new = {len(existing_tournaments)} total")
                tournaments = existing_tournaments
            except Exception as e:
                print(f"⚠️  Could not merge with existing data: {e}")
                print(f"   Will overwrite file instead")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tournaments, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved {len(tournaments)} tournaments to {output_file}")
        return output_file

def main():
    print("EDHTop16 Tournament Scraper")
    print("=" * 50)
    
    # skip_existing=True will load and skip already-scraped tournaments
    scraper = EDHTop16Scraper(skip_existing=True)
    
    # Scrape tournaments (set max_tournaments=None for unlimited, or a number to limit)
    # Example: max_tournaments=200 will stop after collecting 200 tournaments
    tournaments = scraper.scrape_tournaments(max_tournaments=None)
    
    # Save results (merge=True will add to existing file)
    if tournaments:
        scraper.save_tournaments(tournaments, merge=True)
        
        # Print summary
        print("\n" + "=" * 50)
        print("SCRAPING SUMMARY")
        print("=" * 50)
        print(f"Total tournaments scraped: {len(tournaments)}")
        
        total_players = sum(t['size'] for t in tournaments)
        print(f"Total player entries: {total_players}")
        
        if tournaments:
            avg_size = total_players / len(tournaments)
            print(f"Average tournament size: {avg_size:.1f} players")
    else:
        print("\n✗ No tournaments scraped")

if __name__ == "__main__":
    main()
