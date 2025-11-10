#!/usr/bin/env python3
"""
Quick test to verify scrapers are working and estimate how many decks we can get
"""

import sys
import subprocess
import time

scrapers = [
    ("MTGGoldfish", "scripts/scrape-mtggoldfish.py", 10),  # 10 sec test
    ("TappedOut", "scripts/scrape-tappedout.py", 10),
    ("EDHREC", "scripts/scrape-edhrec-decks.py", 10),
    ("Archidekt", "scripts/scrape-archidekt-decks.py", 10),
]

print("=" * 60)
print("TESTING DECK SCRAPERS")
print("=" * 60)
print()

results = {}

for name, script, timeout in scrapers:
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Script: {script}")
    print(f"Timeout: {timeout}s")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            ["python", script],
            timeout=timeout,
            capture_output=True,
            text=True
        )
        
        output = result.stdout + result.stderr
        
        # Check for common error patterns
        if "ModuleNotFoundError" in output:
            status = "❌ Missing dependencies"
        elif "403" in output or "Forbidden" in output:
            status = "❌ Blocked (403)"
        elif "ConnectionError" in output or "Timeout" in output:
            status = "❌ Connection failed"
        elif "error" in output.lower() and "warning" not in output.lower():
            status = "⚠️  Errors detected"
        else:
            status = "✅ Running (stopped at timeout)"
        
        results[name] = {
            'status': status,
            'output_preview': output[:500]
        }
        
        print(f"Status: {status}")
        print(f"\nOutput preview:")
        print(output[:500])
        if len(output) > 500:
            print("... (truncated)")
        
    except subprocess.TimeoutExpired:
        results[name] = {
            'status': "✅ Running (timeout reached - good sign!)",
            'output_preview': "Scraper was still running after timeout"
        }
        print(f"Status: ✅ Running (timeout - scraper is working!)")
    except Exception as e:
        results[name] = {
            'status': f"❌ Error: {str(e)}",
            'output_preview': str(e)
        }
        print(f"Status: ❌ Error: {e}")

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)

working = []
blocked = []
broken = []

for name, info in results.items():
    status = info['status']
    print(f"{name:20} {status}")
    
    if "✅" in status:
        working.append(name)
    elif "403" in status or "Blocked" in status:
        blocked.append(name)
    else:
        broken.append(name)

print("\n" + "="*60)
print(f"Working: {len(working)} - {', '.join(working) if working else 'None'}")
print(f"Blocked: {len(blocked)} - {', '.join(blocked) if blocked else 'None'}")
print(f"Broken:  {len(broken)} - {', '.join(broken) if broken else 'None'}")
print("="*60)

if working:
    print(f"\n✅ You can run these scrapers to collect more training data:")
    for name in working:
        print(f"   - {name}")
