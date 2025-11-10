/**
 * MTGJson Data Importer
 * Imports card data from locally downloaded MTGJson files
 * https://mtgjson.com/
 * 
 * Usage: Place MTGJson files in ./data/mtgjson/ directory
 * Then run: npm run import:mtgjson
 */

import { PrismaClient } from '@prisma/client';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const prisma = new PrismaClient();

interface MTGJsonCard {
  name: string;
  faceName?: string;
  manaCost?: string;
  manaValue: number;
  colors?: string[];
  colorIdentity?: string[];
  type: string;
  types: string[];
  subtypes?: string[];
  supertypes?: string[];
  text?: string;
  power?: string;
  toughness?: string;
  loyalty?: string;
  defense?: string;
  keywords?: string[];
  edhrecRank?: number;
  edhrecSaltiness?: number;
  isReserved?: boolean;
  isCommander?: boolean;
  isFunny?: boolean;
  leadership?: {
    brawl?: boolean;
    commander?: boolean;
    oathbreaker?: boolean;
  };
  legalities?: {
    commander?: string;
    brawl?: string;
    duel?: string;
    legacy?: string;
    modern?: string;
    pauper?: string;
    penny?: string;
    pioneer?: string;
    standard?: string;
    vintage?: string;
  };
  purchaseUrls?: {
    cardKingdom?: string;
    cardmarket?: string;
    tcgplayer?: string;
  };
  rulings?: Array<{
    date: string;
    text: string;
  }>;
}

interface AtomicCards {
  data: {
    [cardName: string]: MTGJsonCard[];
  };
  meta: {
    date: string;
    version: string;
  };
}

/**
 * Import cards from MTGJson AtomicCards file
 */
async function importAtomicCards(filePath: string): Promise<void> {
  console.log('📖 Reading MTGJson AtomicCards file...');
  
  if (!existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const fileContent = readFileSync(filePath, 'utf-8');
  const atomicData: AtomicCards = JSON.parse(fileContent);
  
  console.log(`Found ${Object.keys(atomicData.data).length.toLocaleString()} unique cards`);
  console.log(`MTGJson version: ${atomicData.meta.version} (${atomicData.meta.date})`);
  
  // Flatten to array of cards (take first printing for atomic data)
  const cards = Object.entries(atomicData.data).map(([name, printings]) => {
    const card = printings[0]; // Use first printing for atomic data
    return { ...card, name }; // Ensure name is set
  });

  let imported = 0;
  let skipped = 0;
  let errors = 0;
  const batchSize = 100;
  
  for (let i = 0; i < cards.length; i += batchSize) {
    const batch = cards.slice(i, i + batchSize);
    
    try {
      await prisma.$transaction(
        batch
          .filter((card) => !card.isFunny) // Filter out funny cards before processing
          .map((card) => {

          // Check if card can be commander
          const isCommander = 
            card.leadership?.commander === true ||
            card.isCommander === true ||
            card.text?.toLowerCase().includes('can be your commander') ||
            false;

          // Generate a unique ID (use card name as base)
          const cardId = card.name.toLowerCase().replace(/[^a-z0-9]/g, '-');

          // Prepare legalities JSON
          const legalities = JSON.stringify(card.legalities || {});

          imported++;
          return prisma.card.upsert({
            where: { id: cardId },
            update: {
              name: card.name,
              manaCost: card.manaCost || null,
              cmc: card.manaValue || 0,
              colors: card.colors?.join(',') || '',
              colorIdentity: card.colorIdentity?.join(',') || '',
              typeLine: card.type,
              oracleText: card.text || null,
              power: card.power || null,
              toughness: card.toughness || null,
              loyalty: card.loyalty || null,
              keywords: card.keywords?.join(',') || null,
              legalities,
              rarity: 'common', // MTGJson AtomicCards doesn't have rarity
              setCode: 'default',
              setName: 'Default',
              collectorNumber: '1',
              imageUris: null,
              prices: card.purchaseUrls ? JSON.stringify(card.purchaseUrls) : null,
              edhrecRank: card.edhrecRank || null,
              edhrecSaltiness: card.edhrecSaltiness || null,
              artist: null,
              flavorText: null,
              releasedAt: null,
              isCommander,
            },
            create: {
              id: cardId,
              name: card.name,
              manaCost: card.manaCost || null,
              cmc: card.manaValue || 0,
              colors: card.colors?.join(',') || '',
              colorIdentity: card.colorIdentity?.join(',') || '',
              typeLine: card.type,
              oracleText: card.text || null,
              power: card.power || null,
              toughness: card.toughness || null,
              loyalty: card.loyalty || null,
              keywords: card.keywords?.join(',') || null,
              legalities,
              rarity: 'common',
              setCode: 'default',
              setName: 'Default',
              collectorNumber: '1',
              imageUris: null,
              prices: card.purchaseUrls ? JSON.stringify(card.purchaseUrls) : null,
              edhrecRank: card.edhrecRank || null,
              edhrecSaltiness: card.edhrecSaltiness || null,
              artist: null,
              flavorText: null,
              releasedAt: null,
              isCommander,
            },
          });
        })
      );

      // Progress update every 1000 cards
      if ((i + batchSize) % 1000 === 0 || i + batchSize >= cards.length) {
        const progress = Math.min(100, ((i + batchSize) / cards.length) * 100);
        console.log(
          `Progress: ${progress.toFixed(1)}% (${(i + batchSize).toLocaleString()}/${cards.length.toLocaleString()} cards)`
        );
      }
    } catch (error) {
      errors++;
      console.error(`❌ Error importing batch at index ${i}:`, error);
    }
  }

  console.log('\n✅ Import complete!');
  console.log(`   Imported: ${imported.toLocaleString()} cards`);
  console.log(`   Skipped: ${skipped.toLocaleString()} (funny cards)`);
  console.log(`   Errors: ${errors.toLocaleString()}`);
}

/**
 * Record import job in database
 */
async function recordScrapeJob(
  jobType: string,
  status: string,
  itemsScraped: number,
  errors?: string
): Promise<void> {
  await prisma.scrapeJob.create({
    data: {
      jobType,
      status,
      itemsScraped,
      errors,
      startedAt: new Date(),
      completedAt: new Date(),
    },
  });
}

/**
 * Main execution
 */
async function main() {
  console.log('🎴 MTGJson Card Database Importer\n');

  const dataDir = join(process.cwd(), 'data', 'mtgjson');
  const atomicCardsPath = join(dataDir, 'AtomicCards.json');

  try {
    const startTime = Date.now();

    await importAtomicCards(atomicCardsPath);

    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`\n⏱️  Total time: ${duration}s`);

    // Count cards in database
    const totalCards = await prisma.card.count();
    const commanders = await prisma.card.count({
      where: { isCommander: true },
    });

    console.log('\n📊 Database Statistics:');
    console.log(`   Total cards: ${totalCards.toLocaleString()}`);
    console.log(`   Legal commanders: ${commanders.toLocaleString()}`);

    await recordScrapeJob('mtgjson-atomic', 'completed', totalCards);
  } catch (error) {
    console.error('❌ Import failed:', error);
    await recordScrapeJob(
      'mtgjson-atomic',
      'failed',
      0,
      error instanceof Error ? error.message : String(error)
    );
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

main();
