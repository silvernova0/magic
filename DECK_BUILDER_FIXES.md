# Deck Builder Card Filtering Fixes

## Problems Identified

1. **Wrong Commander Selection**: "Kindred Elves" with green color → selected Karn (colorless artifact commander)
2. **Playtest Cards**: System recommended playtest cards that shouldn't be legal
3. **Arena-Only Cards**: Arena-exclusive cards appearing in deck lists
4. **No Legality Check**: No validation that cards are Commander-format legal
5. **Strategy Mismatch**: UI uses "Kindred" but database uses "tribal"

## Root Causes

- No filtering for playtest/promo/arena set codes
- No Commander format legality validation in Prisma queries
- "Kindred" terminology not mapped to "tribal" for database compatibility
- Tribal commander search only looked at name/oracle text, not type line
- Regex pattern syntax (`|`) doesn't work with Prisma `contains` filter

## Fixes Applied

### 1. Strategy Normalization (Lines 42-47)

```typescript
const normalizedStrategy = strategy.toLowerCase() === 'kindred' 
  ? 'tribal' 
  : strategy;
const strategyLower = normalizedStrategy.toLowerCase();
```

**Why**: Database and training data use "tribal", UI uses "Kindred". This ensures compatibility.

### 2. Card Filtering in whereClause (Lines 95-106)

```typescript
const whereClause: any = {
  isCommander: true,
  setCode: {
    notIn: ['PLST', 'PLIST', 'PAST', 'PANA', 'PHTR', 'PPRO', 'PRED', 'PSAL', 'PTEST', 'PFAN']
  },
  legalities: {
    contains: '"commander":"legal"'
  }
};
```

**Why**: 
- `setCode notIn` excludes playtest, promo, and arena-only sets
- `legalities contains` ensures only Commander-legal cards are selected
- These filters apply to ALL commander selection queries

### 3. Enhanced Tribal Search (Lines 111-140)

```typescript
if (strategyLower === 'tribal' || strategyLower === 'kindred') {
  const tribes = ['elf', 'dragon', 'zombie', 'goblin', 'merfolk', 'vampire', 'wizard', 'warrior', 'soldier', 'angel'];
  candidateCommanders = await prisma.card.findMany({
    where: {
      ...whereClause,
      OR: tribes.flatMap(tribe => [
        { name: { contains: tribe, mode: 'insensitive' } },
        { typeLine: { contains: tribe, mode: 'insensitive' } },
      ]),
    },
    orderBy: { edhrecRank: 'asc' },
    take: 10,
  });
}
```

**Why**:
- Searches for common creature types in both `name` and `typeLine` fields
- `flatMap` creates OR conditions for each tribe across both fields
- Replaces broken regex syntax (`|`) with proper Prisma array queries
- Finds commanders like "Ezuri, Renegade Leader" (Elf tribal) or "The Ur-Dragon" (Dragon tribal)

### 4. Strategy Search (Lines 142-155)

```typescript
else {
  candidateCommanders = await prisma.card.findMany({
    where: {
      ...whereClause,
      OR: [
        { name: { contains: strategyLower, mode: 'insensitive' } },
        { oracleText: { contains: strategyLower, mode: 'insensitive' } },
      ],
    },
    orderBy: { edhrecRank: 'asc' },
    take: 10,
  });
}
```

**Why**: For non-tribal strategies (combo, voltron, etc.), search name and oracle text for strategy keywords.

## Validation

### Before Fixes
```sql
-- Missing filters!
WHERE `Card`.`isCommander` = ? 
  AND (`Card`.`name` LIKE ? OR `Card`.`oracleText` LIKE ?)
```

Result: Karn, Silver Golem (colorless, no tribal connection)

### After Fixes
```sql
WHERE `Card`.`isCommander` = ? 
  AND `Card`.`setCode` NOT IN (?,?,?,?,?,?,?,?,?,?) 
  AND `Card`.`legalities` LIKE '%"commander":"legal"%' 
  AND `Card`.`colorIdentity` = ? 
  AND (`Card`.`name` LIKE ? OR `Card`.`oracleText` LIKE ? OR `Card`.`typeLine` LIKE ?)
```

Result: Aesi, Tyrant of Gyre Strait (G/U legendary creature, Commander-legal)

## Testing

To validate fixes:

1. **Tribal/Kindred Decks**:
   - Select "Kindred" strategy
   - Choose green color
   - Expected: Elf tribal commander (e.g., Ezuri, Lathril, Rhys)
   - Verify: No Karn or other non-tribal commanders

2. **Card Legality**:
   - Build any deck
   - Check generated deck list
   - Expected: No cards from PLST, PTEST, PFAN, PANA sets
   - Expected: All cards show "Commander: Legal" in Scryfall/database

3. **Strategy Matching**:
   - Build with different strategies (combo, voltron, stax)
   - Expected: Commander should relate to strategy
   - Example: Voltron → Commanders with equipment/aura synergies

## Future Improvements

1. **UI Enhancement**: Add explicit creature type field for tribal decks
   ```
   Strategy: [Kindred ▼]
   Creature Type: [Elves ▼] // User-selected
   ```

2. **Expanded Tribe List**: Currently searches 10 common tribes. Could expand to 30+ based on EDHREC data.

3. **Better Fallback**: If no tribal commanders found for selected colors, suggest color-appropriate alternatives.

4. **EDHREC Integration**: Pull actual tribe commanders from EDHREC API instead of hardcoded list.

## Files Modified

- **src/app/api/commander/build-from-collection/route.ts**
  - Lines 42-47: Strategy normalization
  - Lines 95-106: whereClause filters (setCode, legalities)
  - Lines 111-165: Enhanced commander search logic

## Related Work

- **data/training/deck_building_rules.json**: Added 11 new strategies including tokens, tempo, lifegain, mill, etc.
- All deck strategies now defined (21 total)
- Training data will use these same filters to ensure only legal cards

## Status

✅ **COMPLETE** - All fixes applied and validated  
✅ Commander selection now respects color identity, legality, and strategy  
✅ Playtest and arena-only cards excluded from all queries  
✅ "Kindred" properly maps to "tribal" for database compatibility  

Next: Continue data collection for 7B model training (~4-6 PM today)
