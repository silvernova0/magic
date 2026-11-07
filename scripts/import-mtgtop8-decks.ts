/**
 * Import MTGTop8 tournament decklists into database
 * Scrapes recent Commander decks and stores full decklists
 */

import { PrismaClient } from '@prisma/client';
import { scrapeMTGTop8, scrapeDeckDetails } from '../src/lib/scrapers/mtgtop8';

const prisma = new PrismaClient({
  log: ['error', 'warn'],
});

const RATE_LIMIT_DELAY = 1000; // 1 second between deck detail requests
const BATCH_SIZE = 10; // Process decks in batches

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function importMTGTop8Decks() {
  console.log('🎯 Starting MTGTop8 deck import...\n');

  try {
    // Step 1: Scrape recent decks list
    console.log('📥 Fetching recent Commander decks from MTGTop8...');
    const mtgtop8Data = await scrapeMTGTop8();
    
    console.log(`Found ${mtgtop8Data.recentDecks.length} recent decks\n`);

    if (mtgtop8Data.recentDecks.length === 0) {
      console.log('❌ No decks found. The scraper may need adjustments.');
      return;
    }

    let successCount = 0;
    let errorCount = 0;

    // Step 2: Process each deck in batches
    for (let i = 0; i < mtgtop8Data.recentDecks.length; i += BATCH_SIZE) {
      const batch = mtgtop8Data.recentDecks.slice(i, i + BATCH_SIZE);
      
      console.log(`\n📦 Processing batch ${Math.floor(i / BATCH_SIZE) + 1}/${Math.ceil(mtgtop8Data.recentDecks.length / BATCH_SIZE)}`);

      for (const deck of batch) {
        try {
          console.log(`  ⚙️  Processing: ${deck.name} (${deck.commander})`);

          // Scrape full decklist from deck page
          const deckDetails = await scrapeDeckDetails(deck.url);
          
          if (!deckDetails || deckDetails.mainboard.length === 0) {
            console.log(`     ⚠️  No decklist found, skipping...`);
            errorCount++;
            await sleep(RATE_LIMIT_DELAY);
            continue;
          }

          // Find commander card in database
          const commanderCard = await prisma.card.findFirst({
            where: { name: deck.commander },
            select: { id: true, colorIdentity: true },
          });

          // Extract colors from commander if found
          let colors: string[] = [];
          if (commanderCard && commanderCard.colorIdentity) {
            try {
              colors = JSON.parse(commanderCard.colorIdentity);
            } catch {
              colors = [];
            }
          }

          // Infer power level from event type and deck name
          const powerLevel = inferPowerLevel(deck.event, deck.name);

          // Store deck in database
          await prisma.commanderDeck.upsert({
            where: {
              // Use source + URL as unique identifier
              id: `mtgtop8-${deck.url.split('=').pop()}`,
            },
            create: {
              id: `mtgtop8-${deck.url.split('=').pop()}`,
              name: deck.name,
              commander: deck.commander,
              commanderId: commanderCard?.id,
              colors: JSON.stringify(colors),
              theme: inferTheme(deck.name),
              powerLevel,
              source: 'mtgtop8',
              sourceUrl: deck.url,
              decklist: JSON.stringify({
                mainboard: deckDetails.mainboard,
                sideboard: deckDetails.sideboard || [],
                event: deck.event,
                placement: deck.placement,
                date: deck.date,
              }),
              popularity: calculatePopularity(deck.placement),
            },
            update: {
              name: deck.name,
              commander: deck.commander,
              commanderId: commanderCard?.id,
              colors: JSON.stringify(colors),
              theme: inferTheme(deck.name),
              powerLevel,
              sourceUrl: deck.url,
              decklist: JSON.stringify({
                mainboard: deckDetails.mainboard,
                sideboard: deckDetails.sideboard || [],
                event: deck.event,
                placement: deck.placement,
                date: deck.date,
              }),
              popularity: calculatePopularity(deck.placement),
              updatedAt: new Date(),
            },
          });

          console.log(`     ✅ Stored deck (${deckDetails.mainboard.length} cards)`);
          successCount++;

          // Rate limiting
          await sleep(RATE_LIMIT_DELAY);
        } catch (error) {
          console.error(`     ❌ Error processing deck ${deck.name}:`, error);
          errorCount++;
        }
      }

      // Pause between batches
      if (i + BATCH_SIZE < mtgtop8Data.recentDecks.length) {
        console.log('\n⏸️  Pausing 5 seconds between batches...');
        await sleep(5000);
      }
    }

    // Summary
    console.log('\n' + '='.repeat(50));
    console.log('✅ Import Complete!');
    console.log('📊 Statistics:');
    console.log(`   - Decks Processed: ${mtgtop8Data.recentDecks.length}`);
    console.log(`   - Successfully Stored: ${successCount}`);
    console.log(`   - Errors: ${errorCount}`);
    console.log('='.repeat(50) + '\n');

  } catch (error) {
    console.error('❌ Fatal error during import:', error);
    throw error;
  } finally {
    await prisma.$disconnect();
  }
}

/**
 * Infer power level from event type and deck name
 */
function inferPowerLevel(event: string, deckName: string): number {
  const eventLower = event.toLowerCase();
  const nameLower = deckName.toLowerCase();

  // cEDH indicators = highest power
  if (nameLower.includes('cedh') || eventLower.includes('cedh')) {
    return 5;
  }

  // Tournament indicators = high power
  if (eventLower.includes('tournament') || eventLower.includes('championship')) {
    return 4;
  }

  // Competitive indicators
  if (nameLower.includes('turbo') || nameLower.includes('stax') || nameLower.includes('combo')) {
    return 4;
  }

  // Default to focused/optimized
  return 3;
}

/**
 * Infer theme from deck name
 */
function inferTheme(deckName: string): string {
  const name = deckName.toLowerCase();

  if (name.includes('cedh')) return 'cEDH';
  if (name.includes('stax')) return 'Stax';
  if (name.includes('combo')) return 'Combo';
  if (name.includes('aggro') || name.includes('voltron')) return 'Aggro';
  if (name.includes('control')) return 'Control';
  if (name.includes('midrange') || name.includes('value')) return 'Midrange';
  if (name.includes('tribal')) return 'Tribal';
  if (name.includes('tokens')) return 'Tokens';
  if (name.includes('aristocrats')) return 'Aristocrats';
  if (name.includes('lands')) return 'Lands Matter';
  if (name.includes('graveyard')) return 'Graveyard';
  if (name.includes('spellslinger')) return 'Spellslinger';

  // Try to extract from name (often format: "Commander - Theme")
  const parts = deckName.split('-').map(p => p.trim());
  if (parts.length > 1) {
    return parts[1].substring(0, 50); // Limit length
  }

  return 'Unknown';
}

/**
 * Calculate popularity score based on placement
 */
function calculatePopularity(placement: string): number {
  const place = placement.toLowerCase();
  
  if (place.includes('1st') || place === '1') return 100;
  if (place.includes('2nd') || place === '2') return 90;
  if (place.includes('3rd') || place === '3') return 80;
  if (place.includes('4th') || place === '4') return 70;
  if (place.includes('top 8') || place.includes('t8')) return 60;
  if (place.includes('top 16')) return 50;
  if (place.includes('top 32')) return 40;
  
  return 30; // Default for other placements
}

// Run the import
importMTGTop8Decks()
  .then(() => {
    console.log('Import script completed successfully');
    process.exit(0);
  })
  .catch((error) => {
    console.error('Import script failed:', error);
    process.exit(1);
  });
