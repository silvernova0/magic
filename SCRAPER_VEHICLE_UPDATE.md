# Scraper Update: Legendary Vehicle Commanders

## Issue Discovered
Both MTGGoldfish and EDHREC scrapers were using type-based queries that excluded legendary vehicles:

**OLD Query (MTGGoldfish)**:
```sql
WHERE ((typeLine LIKE '%Legendary%' AND typeLine LIKE '%Creature%')
   OR (typeLine LIKE '%Legendary%' AND typeLine LIKE '%Planeswalker%'))
```

**OLD Query (EDHREC)**:
```sql
WHERE typeLine LIKE '%Legendary%' AND typeLine LIKE '%Creature%'
```

This missed **22 unique legendary vehicle commanders** that are legal in Commander format.

## Legendary Vehicles (22 total)
1. Adrestia
2. Bessie, the Doctor's Roadster
3. Esika's Chariot
4. Golden Argosy
5. Grond, the Gatebreaker
6. Heart of Kiran
7. Jackdaw
8. Parhelion II
9. RMS Titanic
10. **Shorikai, Genesis Engine** ⭐ (Most popular - widely played)
11. Skysovereign, Consul Flagship
12. The Belligerent
13. The Falcon, Airship Restored
14. The Indomitable
15. The Last Ride
16. The Lunar Whale
17. The Prima Vista
18. The Prydwen, Steel Flagship
19. The Regalia
20. Valor's Flagship
21. Weatherlight
22. Weatherlight Compleated

## Fix Applied

**Files Updated**:
- `scripts/scrape-mtggoldfish-by-commander.py` (lines 60-80)
- `scripts/scrape-edhrec-average-decks.py` (lines 125-148)

**NEW Query**:
```sql
WHERE isCommander = 1
```

This uses the corrected `isCommander` field from the database that now includes:
- Legendary Creatures ✅
- Legendary Artifact — Vehicles ✅
- Cards with "can be your commander" text ✅
- NOT regular Legendary Artifacts ❌

## Impact Analysis

### Current Scraping Status
- **MTGGoldfish**: 1408/2500 commanders (56%), running with OLD query
- **Moxfield**: Running (uses API, no impact)
- **Archidekt**: Uses API (no impact)
- **EDHREC**: Not currently running

### Missing Data
```bash
# Confirmed: 0 vehicle commander decks scraped
grep '"instruction":"Build a Commander deck with Shorikai' data/training/mtggoldfish_by_commander_decks.jsonl
# Result: 0 matches
```

The 22 legendary vehicles represent approximately **0.7%** of total commanders (22/3011).

**Shorikai, Genesis Engine** is the most significant omission:
- Artifact/vehicle tribal commander
- Draw engine on a vehicle
- Popular budget-friendly option
- Unique "vehicles matter" archetype

## Options for Recovery

### Option 1: Let Current Scraper Finish (RECOMMENDED)
- **Pros**: Don't interrupt 56% complete scraper, vehicles are small % of total
- **Cons**: Miss ~22 vehicle commanders in current run
- **Action**: Wait for completion (~7:57 PM ETA), then run vehicle-focused scrape
- **Timeline**: +2 hours after main scraper completes

### Option 2: Kill and Restart Now
- **Pros**: Get complete commander coverage in single run
- **Cons**: Lose 3,297 decks already scraped (will re-scrape from start)
- **Action**: Kill PID 1035982, restart with new query
- **Timeline**: Restart from 0/2500, complete ~9 PM

### Option 3: Run Parallel Vehicle-Only Scrape
- **Pros**: Get vehicle data now without interrupting main scraper
- **Cons**: Need separate script/process, may hit rate limits
- **Action**: Create vehicle-specific scraper for 22 commanders
- **Timeline**: ~30 minutes to complete

## Recommendation: Option 1
**Let current scraper finish**, then run a targeted vehicle scrape.

**Rationale**:
1. Main scraper is 56% done (1408/2500)
2. Vehicles represent <1% of commanders (22/3011)
3. Most vehicle commanders have low deck counts except Shorikai
4. Interrupting now wastes 3,297 decks (2+ hours of work)
5. Can easily scrape 22 vehicles in 30-60 minutes after main completes

## Post-Completion Plan

### 1. Vehicle Commander Scrape (~8:00 PM)
```bash
# Create vehicle-specific scraper or modify existing with:
# --commanders "Shorikai, Genesis Engine,Parhelion II,Weatherlight,..."
# --decks-per-commander 25

nohup python3 scripts/scrape-vehicles-commanders.py > vehicles.log 2>&1 &
```

Expected results:
- **Shorikai**: 20-25 decks (high popularity)
- **Weatherlight/Parhelion II**: 5-15 decks each
- **Others**: 1-5 decks each
- **Total**: ~100-200 additional decks

### 2. Re-run EDHREC with Updated Query
```bash
# EDHREC scraper now uses isCommander = 1
nohup python3 scripts/scrape-edhrec-average-decks.py > edhrec_vehicles.log 2>&1 &
```

This will check all 3,011 commanders including vehicles.

### 3. Data Conversion & Training
```bash
# Convert all sources to v3 structured format
python3 scripts/convert-to-v3-training.py

# Package for Windows
bash scripts/package-training-data.sh

# Transfer to Windows
# SMB: smb://192.168.0.151/aitrainingv4/

# Train 7B model on RTX 5070 Ti
# Expected: ~38,000-38,200 examples (including vehicles)
```

## Future Prevention
All scrapers now use:
```python
cursor.execute("""
    SELECT DISTINCT name 
    FROM Card 
    WHERE isCommander = 1
    ORDER BY name
""")
```

This ensures complete commander coverage including:
- Legendary Creatures (standard)
- Legendary Vehicles (now included)
- Special commanders with text override

## Verification
```bash
# Check database has correct count
sqlite3 prisma/dev.db "SELECT COUNT(*) FROM Card WHERE isCommander = 1;"
# Expected: 3011

# List vehicle commanders
sqlite3 prisma/dev.db "SELECT name FROM Card WHERE isCommander = 1 AND typeLine LIKE '%Vehicle%';"
# Expected: 22 vehicles
```

## Notes
- Archidekt scraper uses their API and is not affected (API returns all legal commanders)
- Moxfield scraper uses API and is not affected
- Only database-querying scrapers (MTGGoldfish, EDHREC) needed updates
- The `isCommander` field is now the single source of truth for commander legality
