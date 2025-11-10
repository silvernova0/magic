/**
 * Comprehensive MTGJson Data Importer
 * Imports card data from multiple MTGJson files for rich deck building
 * https://mtgjson.com/
 * 
 * Imports from:
 * - AtomicCards.json: Core card data with EDHREC rankings
 * - AllPrintings.json: All printings with prices, images, artists
 * - Keywords.json: All Magic keywords for filtering
 * - CardTypes.json: All card types for validation
 * 
 * Usage: Place MTGJson files in ./data/mtgjson/ directory
 * Then run: npm run import:mtgjson:full
 */

import { PrismaClient } from '@prisma/client';
import { readFileSync, existsSync, createReadStream } from 'fs';
import { join } from 'path';
import { createInterface } from 'readline';

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

interface AllPrintingsCard extends MTGJsonCard {
  uuid: string;
  artist?: string;
  flavorText?: string;
  rarity: string;
  setCode: string;
  number: string;
  identifiers?: {
    scryfallId?: string;
    scryfallOracleId?: string;
  };
  prices?: {
    paper?: { [date: string]: number };
    paperFoil?: { [date: string]: number };
  };
  imageUris?: {
    small?: string;
    normal?: string;
    large?: string;
    png?: string;
    artCrop?: string;
    borderCrop?: string;
  };
}

interface AllPrintingsSet {
  name: string;
  code: string;
  releaseDate?: string;
  type: string;
  cards: AllPrintingsCard[];
}

interface AllPrintings {
  data: {
    [setCode: string]: AllPrintingsSet;
  };
  meta: {
    date: string;
    version: string;
  };
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

interface KeywordsData {
  data: {
    abilityWords: string[];
    keywordAbilities: string[];
    keywordActions: string[];
  };
  meta: {
    date: string;
    version: string;
  };
}

interface CardTypesData {
  data: {
    artifact: { subTypes: string[]; superTypes: string[] };
    conspiracy: { subTypes: string[]; superTypes: string[] };
    creature: { subTypes: string[]; superTypes: string[] };
    enchantment: { subTypes: string[]; superTypes: string[] };
    instant: { subTypes: string[]; superTypes: string[] };
    land: { subTypes: string[]; superTypes: string[] };
    phenomenon: { subTypes: string[]; superTypes: string[] };
    plane: { subTypes: string[]; superTypes: string[] };
    planeswalker: { subTypes: string[]; superTypes: string[] };
    scheme: { subTypes: string[]; superTypes: string[] };
    sorcery: { subTypes: string[]; superTypes: string[] };
    tribal: { subTypes: string[]; superTypes: string[] };
    vanguard: { subTypes: string[]; superTypes: string[] };
  };
  meta: {
    date: string;
    version: string;
  };
}

/**
 * Determine if a card is a "game changer" based on various factors
 */
function isGameChanger(card: MTGJsonCard | AllPrintingsCard): boolean {
  const text = card.text?.toLowerCase() || '';
  
  // Check for game-changing keywords/effects
  const gameChangingTerms = [
    'extra turn',
    'win the game',
    'you lose the game',
    'can\'t lose',
    'destroy all',
    'exile all',
    'sacrifice all',
    'double',
    'copy',
    'tutor',
    'search your library',
    'infinite',
    'cascade',
    'storm',
    'dredge',
  ];
  
  const hasGameChangingEffect = gameChangingTerms.some(term => text.includes(term));
  
  // High EDHREC rank (lower number = more popular = potentially game changer)
  const isHighlyRanked = (card.edhrecRank && card.edhrecRank < 500) || false;
  
  // Reserved list cards are often game changers
  const isReservedList = card.isReserved === true;
  
  // High saltiness score indicates game-changing effects
  const isHighSalt = (card.edhrecSaltiness && card.edhrecSaltiness > 1.0) || false;
  
  return hasGameChangingEffect || isHighlyRanked || isReservedList || isHighSalt;
}

/**
 * Extract card tags for filtering and search
 */
function extractCardTags(card: MTGJsonCard | AllPrintingsCard): string[] {
  const tags: string[] = [];
  const text = card.text?.toLowerCase() || '';
  
  // Mechanical tags
  if (text.includes('draw')) tags.push('card-draw');
  if (text.includes('tutor') || text.includes('search your library')) tags.push('tutor');
  if (text.includes('destroy')) tags.push('removal');
  if (text.includes('exile')) tags.push('exile');
  if (text.includes('counter')) tags.push('counterspell');
  if (text.includes('token')) tags.push('token');
  if (text.includes('graveyard')) tags.push('graveyard');
  if (text.includes('sacrifice')) tags.push('sacrifice');
  if (text.includes('life')) tags.push('life-matters');
  if (text.includes('mana')) tags.push('mana');
  if (text.includes('extra turn')) tags.push('extra-turns');
  if (text.includes('combat')) tags.push('combat');
  if (text.includes('+1/+1 counter')) tags.push('counters');
  if (text.includes('copy')) tags.push('copy');
  if (text.includes('storm')) tags.push('storm');
  if (text.includes('cascade')) tags.push('cascade');
  
  // Reserved list
  if (card.isReserved) tags.push('reserved-list');
  
  // High salt
  if (card.edhrecSaltiness && card.edhrecSaltiness > 1.0) tags.push('high-salt');
  if (card.edhrecSaltiness && card.edhrecSaltiness > 2.0) tags.push('very-high-salt');
  
  // Game changer
  if (isGameChanger(card)) tags.push('game-changer');
  
  // Leadership
  if (card.leadership?.commander) tags.push('commander');
  if (card.leadership?.brawl) tags.push('brawl-commander');
  if (card.leadership?.oathbreaker) tags.push('oathbreaker');
  
  // Card types
  if (card.types.includes('Creature')) tags.push('creature');
  if (card.types.includes('Instant')) tags.push('instant');
  if (card.types.includes('Sorcery')) tags.push('sorcery');
  if (card.types.includes('Enchantment')) tags.push('enchantment');
  if (card.types.includes('Artifact')) tags.push('artifact');
  if (card.types.includes('Planeswalker')) tags.push('planeswalker');
  if (card.types.includes('Land')) tags.push('land');
  
  return [...new Set(tags)]; // Remove duplicates
}

/**
 * Import from AtomicCards.json with enhanced tagging and metadata
 */
async function importAtomicCards(filePath: string): Promise<number> {
  console.log('📖 Reading AtomicCards.json...');
  
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
  const batchSize = 50;
  
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
            
            // Extract tags for filtering and search
            const tags = extractCardTags(card);
            const tagsJson = JSON.stringify(tags);
            
            // Determine if game changer
            const isGameChangerCard = isGameChanger(card);
            
            // Calculate a "power level" score (0-10)
            let powerLevel = 5; // Default
            if (card.edhrecRank) {
              if (card.edhrecRank < 100) powerLevel = 10;
              else if (card.edhrecRank < 500) powerLevel = 9;
              else if (card.edhrecRank < 1000) powerLevel = 8;
              else if (card.edhrecRank < 5000) powerLevel = 7;
              else if (card.edhrecRank < 10000) powerLevel = 6;
            }
            if (isGameChangerCard) powerLevel = Math.min(10, powerLevel + 1);
            
            // Store additional metadata
            const metadata = JSON.stringify({
              tags,
              isGameChanger: isGameChangerCard,
              powerLevel,
              isReservedList: card.isReserved || false,
              canBeBrawlCommander: card.leadership?.brawl || false,
              canBeOathbreaker: card.leadership?.oathbreaker || false,
            });

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
                rarity: 'common', // AtomicCards doesn't have rarity
                setCode: 'atomic',
                setName: 'Atomic',
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
                setCode: 'atomic',
                setName: 'Atomic',
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

      // Count skipped funny cards
      skipped += batch.filter(card => card.isFunny).length;

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
  
  return imported;
}

/**
 * Import from AllPrintings.json (most comprehensive)
 */
async function importAllPrintings(filePath: string): Promise<number> {
  console.log('📚 Reading AllPrintings.json...');
  
  if (!existsSync(filePath)) {
    console.log('⚠️  AllPrintings.json not found, skipping...');
    return 0;
  }

  const fileContent = readFileSync(filePath, 'utf-8');
  const allPrintings: AllPrintings = JSON.parse(fileContent);
  
  console.log(`Found ${Object.keys(allPrintings.data).length} sets`);
  console.log(`MTGJson version: ${allPrintings.meta.version} (${allPrintings.meta.date})`);
  
  // Collect all unique cards (by name)
  const cardMap = new Map<string, AllPrintingsCard>();
  
  for (const [setCode, set] of Object.entries(allPrintings.data)) {
    for (const card of set.cards) {
      // Skip funny cards
      if (card.isFunny) continue;
      
      // Use the first printing we encounter, or update if this one has better data
      const existing = cardMap.get(card.name);
      if (!existing || (card.edhrecRank && (!existing.edhrecRank || card.edhrecRank < existing.edhrecRank))) {
        cardMap.set(card.name, card);
      }
    }
  }
  
  const cards = Array.from(cardMap.values());
  console.log(`Found ${cards.length.toLocaleString()} unique cards to import`);

  let imported = 0;
  let updated = 0;
  let errors = 0;
  const batchSize = 50; // Smaller batches for safety
  
  for (let i = 0; i < cards.length; i += batchSize) {
    const batch = cards.slice(i, i + batchSize);
    
    try {
      await prisma.$transaction(
        batch.map((card) => {
          // Check if card can be commander
          const isCommander = 
            card.leadership?.commander === true ||
            card.isCommander === true ||
            card.text?.toLowerCase().includes('can be your commander') ||
            false;

          // Generate a unique ID
          const cardId = card.identifiers?.scryfallId || card.uuid || card.name.toLowerCase().replace(/[^a-z0-9]/g, '-');

          // Get latest price
          const latestPrice = card.prices?.paper ? 
            Object.values(card.prices.paper).filter(p => p !== null).pop() : 
            null;
          
          const pricesJson = card.prices ? JSON.stringify(card.prices) : null;

          // Prepare legalities JSON
          const legalities = JSON.stringify(card.legalities || {});
          
          // Extract tags
          const tags = extractCardTags(card);
          const isGameChangerCard = isGameChanger(card);

          // Get image URIs
          const imageUris = card.imageUris ? JSON.stringify(card.imageUris) : null;

          return prisma.card.upsert({
            where: { id: cardId },
            update: {
              name: card.name,
              oracleId: card.identifiers?.scryfallOracleId || null,
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
              rarity: card.rarity,
              setCode: card.setCode,
              setName: card.setCode,
              collectorNumber: card.number,
              imageUris,
              prices: pricesJson,
              edhrecRank: card.edhrecRank || null,
              edhrecSaltiness: card.edhrecSaltiness || null,
              artist: card.artist || null,
              flavorText: card.flavorText || null,
              releasedAt: null,
              isCommander,
            },
            create: {
              id: cardId,
              name: card.name,
              oracleId: card.identifiers?.scryfallOracleId || null,
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
              rarity: card.rarity,
              setCode: card.setCode,
              setName: card.setCode,
              collectorNumber: card.number,
              imageUris,
              prices: pricesJson,
              edhrecRank: card.edhrecRank || null,
              edhrecSaltiness: card.edhrecSaltiness || null,
              artist: card.artist || null,
              flavorText: card.flavorText || null,
              releasedAt: null,
              isCommander,
            },
          });
        })
      );

      imported += batch.length;

      // Progress update every 500 cards
      if ((i + batchSize) % 500 === 0 || i + batchSize >= cards.length) {
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

  console.log('\n✅ AllPrintings import complete!');
  console.log(`   Imported/Updated: ${imported.toLocaleString()} cards`);
  console.log(`   Errors: ${errors.toLocaleString()}`);
  
  return imported;
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
  const startedAt = new Date();
  await prisma.scrapeJob.create({
    data: {
      jobType,
      status,
      itemsScraped,
      errors,
      startedAt,
      completedAt: new Date(),
    },
  });
}

/**
 * Main execution
 */
async function main() {
  console.log('🎴 MTGJson Comprehensive Card Database Importer\n');

  const dataDir = join(process.cwd(), 'data', 'mtgjson');
  const atomicCardsPath = join(dataDir, 'AtomicCards.json');

  // Note: AllPrintings.json is too large for Node.js memory limits
  // Using AtomicCards.json instead which has all unique cards with EDHREC data
  console.log('ℹ️  Using AtomicCards.json (unique cards with EDHREC data)');
  console.log('   AllPrintings.json is too large to load into memory\n');

  try {
    const startTime = Date.now();

    const cardsImported = await importAtomicCards(atomicCardsPath);

    const duration = ((Date.now() - startTime) / 1000 / 60).toFixed(1);
    console.log(`\n⏱️  Total time: ${duration} minutes`);

    // Count cards in database
    const totalCards = await prisma.card.count();
    const commanders = await prisma.card.count({
      where: { isCommander: true },
    });
    
    // Get some interesting stats
    const highSalt = await prisma.card.count({
      where: {
        edhrecSaltiness: { gte: 1.0 }
      }
    });
    
    const topRanked = await prisma.card.count({
      where: {
        edhrecRank: { lte: 1000 }
      }
    });

    console.log('\n📊 Database Statistics:');
    console.log(`   Total cards: ${totalCards.toLocaleString()}`);
    console.log(`   Legal commanders: ${commanders.toLocaleString()}`);
    console.log(`   High saltiness (>1.0): ${highSalt.toLocaleString()}`);
    console.log(`   Top 1000 EDHREC: ${topRanked.toLocaleString()}`);

    await recordScrapeJob('mtgjson-comprehensive', 'completed', totalCards);
    
    console.log('\n✨ Import complete! Your database is ready for deck building!');
  } catch (error) {
    console.error('❌ Import failed:', error);
    await recordScrapeJob(
      'mtgjson-comprehensive',
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
