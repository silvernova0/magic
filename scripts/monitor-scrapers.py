#!/usr/bin/env python3
"""
Real-time monitoring dashboard for all active scrapers
Shows progress, deck counts, and strategy distribution
"""

import os
import json
import time
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def count_lines(filepath):
    """Count lines in a file"""
    try:
        with open(filepath, 'r') as f:
            return sum(1 for _ in f)
    except:
        return 0

def get_file_size(filepath):
    """Get human-readable file size"""
    try:
        size = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
    except:
        return "0B"

def analyze_strategies(filepath):
    """Analyze strategy distribution from v3 training file"""
    strategies = Counter()
    try:
        with open(filepath, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    output = data.get('output', {})
                    if isinstance(output, dict):
                        strategy = output.get('strategy', 'unknown')
                        strategies[strategy] += 1
                except:
                    continue
    except:
        pass
    return strategies

def check_process(process_name):
    """Check if a process is running"""
    result = os.popen(f"ps aux | grep '{process_name}' | grep -v grep").read()
    return bool(result.strip())

def tail_log(filepath, lines=5):
    """Get last N lines from log file"""
    try:
        with open(filepath, 'r') as f:
            all_lines = f.readlines()
            return ''.join(all_lines[-lines:]) if all_lines else "No output yet"
    except:
        return "Log not available"

def monitor_scrapers():
    """Main monitoring loop"""
    
    training_dir = Path("data/training")
    
    # File tracking
    files_to_monitor = {
        'edhrec_tag_decks.jsonl': ('EDHREC Tags', 'edhrec_tags.log'),
        'edhtop16_decks.jsonl': ('EDHTop16', 'edhtop16.log'),
        'mtggoldfish_by_commander_decks.jsonl': ('MTGGoldfish', 'mtggoldfish_commander.log'),
        'moxfield_decks.jsonl': ('Moxfield', 'moxfield_themes.log'),
        'v3_structured_training.jsonl': ('v3 Training Data', None),
    }
    
    # Process tracking
    processes = {
        'scrape-edhrec-tags': 'EDHREC Tags',
        'scrape-edhtop16': 'EDHTop16',
        'scrape-mtggoldfish': 'MTGGoldfish',
        'scrape-moxfield': 'Moxfield',
    }
    
    start_time = time.time()
    
    while True:
        clear_screen()
        
        # Header
        elapsed = time.time() - start_time
        elapsed_min = int(elapsed / 60)
        elapsed_sec = int(elapsed % 60)
        
        print("=" * 80)
        print(f"{'MTG COMMANDER DECK SCRAPER DASHBOARD':^80}")
        print(f"{'Monitoring Active Scrapers':^80}")
        print("=" * 80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Elapsed: {elapsed_min}m {elapsed_sec}s")
        print("=" * 80)
        print()
        
        # Active Processes
        print("🔄 ACTIVE PROCESSES")
        print("-" * 80)
        active_count = 0
        for process_name, display_name in processes.items():
            is_running = check_process(process_name)
            status = "🟢 RUNNING" if is_running else "⚫ STOPPED"
            print(f"  {display_name:20} {status}")
            if is_running:
                active_count += 1
        print(f"\n  Total active: {active_count}/{len(processes)}")
        print()
        
        # File Statistics
        print("📊 DECK COLLECTION STATUS")
        print("-" * 80)
        print(f"{'Source':<25} {'Decks':>10} {'Size':>10} {'Status'}")
        print("-" * 80)
        
        total_decks = 0
        for filename, (source_name, log_file) in files_to_monitor.items():
            filepath = training_dir / filename
            deck_count = count_lines(filepath)
            file_size = get_file_size(filepath)
            
            # Determine status
            if deck_count == 0:
                status = "⚪ Empty"
            elif source_name in ['EDHREC Tags', 'EDHTop16'] and check_process(f"scrape-{source_name.lower().replace(' ', '-')}"):
                status = "🟡 Collecting"
            else:
                status = "✅ Complete"
            
            print(f"  {source_name:<23} {deck_count:>10,} {file_size:>10} {status}")
            total_decks += deck_count
        
        print("-" * 80)
        print(f"  {'TOTAL DECKS':<23} {total_decks:>10,}")
        print()
        
        # v3 Training Data Analysis
        v3_file = training_dir / 'v3_structured_training.jsonl'
        if v3_file.exists():
            print("🎯 v3 TRAINING DATA - STRATEGY DISTRIBUTION")
            print("-" * 80)
            
            strategies = analyze_strategies(v3_file)
            total_examples = sum(strategies.values())
            
            if total_examples > 0:
                # Show top 10 strategies
                print(f"{'Strategy':<20} {'Count':>10} {'%':>8}")
                print("-" * 80)
                
                for strategy, count in strategies.most_common(10):
                    pct = (count / total_examples) * 100
                    print(f"  {strategy:<18} {count:>10,} {pct:>7.1f}%")
                
                # Show underrepresented (bottom 10)
                print()
                print("⚠️  UNDERREPRESENTED STRATEGIES (needs balancing):")
                print("-" * 80)
                bottom_10 = strategies.most_common()[-10:]
                bottom_10.reverse()
                
                for strategy, count in bottom_10:
                    if count < 100:
                        pct = (count / total_examples) * 100
                        needed = 100 - count
                        print(f"  {strategy:<18} {count:>10,} {pct:>7.1f}%  (need {needed:>3} more)")
            print()
        
        # Recent Log Activity
        print("📝 RECENT SCRAPER ACTIVITY")
        print("-" * 80)
        
        for filename, (source_name, log_file) in files_to_monitor.items():
            if log_file and Path(log_file).exists():
                print(f"\n{source_name}:")
                recent = tail_log(log_file, 3)
                for line in recent.split('\n')[:3]:
                    if line.strip():
                        print(f"  {line[:76]}")
        
        print()
        print("=" * 80)
        print("Press Ctrl+C to exit monitoring")
        print("=" * 80)
        
        # Wait before refresh
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n\n✓ Monitoring stopped")
            break

if __name__ == '__main__':
    try:
        monitor_scrapers()
    except KeyboardInterrupt:
        print("\n\n✓ Monitoring stopped")
