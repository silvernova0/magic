/**
 * Scryfall Bulk Data Importer
 * Downloads complete card database from Scryfall's bulk data API
 * https://scryfall.com/docs/api/bulk-data
 */

import { PrismaClient } from '@prisma/client';
import https from 'https';
import { createWriteStream, createReadStream, unlinkSync, readFileSync } from 'fs';
import { createInterface } from 'readline';
import path from 'path';

const prisma = new PrismaClient();

interface ScryfallCard {
  id: string;
  oracle_id?: string;
  name: string;
  mana_cost?: string;
  cmc: number;
  colors?: string[];
  color_identity?: string[];
  type_line: string;
  oracle_text?: string;
  power?: string;
  toughness?: string;
  loyalty?: string;
  keywords?: string[];
  legalities: { [format: string]: string };
  rarity: string;
  set: string;
  set_name: string;
  collector_number: string;
  image_uris?: { [size: string]: string };
  prices?: { [currency: string]: string | null };
  edhrec_rank?: number;
  penny_rank?: number;
  artist?: string;
  flavor_text?: string;
  released_at?: string;
}

/**
 * Download Scryfall bulk data file
 */
async function downloadBulkData(): Promise<string> {
  console.log('Fetching Scryfall bulk data info...');
  
  // Get bulk data download URL
  const bulkDataResponse = await fetch('https://api.scryfall.com/bulk-data');
  const bulkData = await bulkDataResponse.json();
  
  // Find the "Default Cards" bulk data (all game cards)
  const defaultCards = bulkData.data.find(
    (item: any) => item.type === 'default_cards'
  );
  
  if (!defaultCards) {
    throw new Error('Could not find default cards bulk data');
  }
  
  const downloadUrl = defaultCards.download_uri;
  const fileSize = defaultCards.size;
  
  console.log(`Downloading ${(fileSize / 1024 / 1024).toFixed(2)} MB from Scryfall...`);
  console.log(`URL: ${downloadUrl}`);
  
  const filePath = path.join(process.cwd(), '.cache', 'scryfall-cards.json');
  
  // Download file
  return new Promise((resolve, reject) => {
    https.get(downloadUrl, (response) => {
      const fileStream = createWriteStream(filePath);
      response.pipe(fileStream);
      
      let downloaded = 0;
      response.on('data', (chunk) => {
        downloaded += chunk.length;
        const percent = ((downloaded / fileSize) * 100).toFixed(1);
        process.stdout.write(`\rDownloading... ${percent}%`);
      });
      
      fileStream.on('finish', () => {
        fileStream.close();
        console.log('\nDownload complete!');
        resolve(filePath);
      });
      
      fileStream.on('error', (err) => {
        unlinkSync(filePath);
        reject(err);
      });
    });
  });
}

/**
 * Import cards from downloaded file into database
 */
async function importCards(filePath: string): Promise<void> {
  console.log('Reading and importing cards...');
  
  const fileContent = readFileSync(filePath, 'utf-8');
  const cards: ScryfallCard[] = JSON.parse(fileContent);
  
  console.log(`Found ${cards.length.toLocaleString()} cards to import`);
  
  let imported = 0;
  let skipped = 0;
  const batchSize = 100;
  
  for (let i = 0; i < cards.length; i += batchSize) {
    const batch = cards.slice(i, i + batchSize);
    
    try {
      await prisma.$transaction(
        batch.map((card) => {
          // Skip tokens, emblems, and other non-playable cards
          if (
            card.type_line.includes('Token') ||
            card.type_line.includes('Emblem') ||
            card.type_line.includes('Card')
          ) {
            skipped++;
            return prisma.$queryRaw`SELECT 1`; // No-op
          }
          
          // Determine if card can be a commander
          const isCommander = 
            card.type_line.includes('Legendary') &&
            card.type_line.includes('Creature') &&
            card.legalities.commander === 'legal';
          
          return prisma.card.upsert({
            where: { id: card.id },
            create: {
              id: card.id,
              oracleId: card.oracle_id,
              name: card.name,
              manaCost: card.mana_cost || '',
              cmc: card.cmc,
              colors: JSON.stringify(card.colors || []),
              colorIdentity: JSON.stringify(card.color_identity || []),
              typeLine: card.type_line,
              oracleText: card.oracle_text,
              power: card.power,
              toughness: card.toughness,
              loyalty: card.loyalty,
              keywords: JSON.stringify(card.keywords || []),
              legalities: JSON.stringify(card.legalities),
              rarity: card.rarity,
              setCode: card.set,
              setName: card.set_name,
              collectorNumber: card.collector_number,
              imageUris: card.image_uris ? JSON.stringify(card.image_uris) : null,
              prices: card.prices ? JSON.stringify(card.prices) : null,
              edhrecRank: card.edhrec_rank,
              artist: card.artist,
              flavorText: card.flavor_text,
              releasedAt: card.released_at ? new Date(card.released_at) : null,
              isCommander,
            },
            update: {
              name: card.name,
              manaCost: card.mana_cost || '',
              cmc: card.cmc,
              colors: JSON.stringify(card.colors || []),
              colorIdentity: JSON.stringify(card.color_identity || []),
              typeLine: card.type_line,
              oracleText: card.oracle_text,
              power: card.power,
              toughness: card.toughness,
              loyalty: card.loyalty,
              keywords: JSON.stringify(card.keywords || []),
              legalities: JSON.stringify(card.legalities),
              rarity: card.rarity,
              prices: card.prices ? JSON.stringify(card.prices) : null,
              edhrecRank: card.edhrec_rank,
              isCommander,
              updatedAt: new Date(),
            },
          });
        })
      );
      
      imported += batch.length - (skipped - imported);
      const percent = ((i / cards.length) * 100).toFixed(1);
      process.stdout.write(`\rImporting... ${percent}% (${imported.toLocaleString()} cards)`);
    } catch (error) {
      console.error(`Error importing batch at index ${i}:`, error);
    }
  }
  
  console.log(`\n✅ Import complete!`);
  console.log(`   Imported: ${imported.toLocaleString()} cards`);
  console.log(`   Skipped: ${skipped.toLocaleString()} non-playable cards`);
}

/**
 * Main import function
 */
export async function importScryfallBulkData(): Promise<void> {
  const startTime = Date.now();
  
  // Create scrape job record
  const job = await prisma.scrapeJob.create({
    data: {
      jobType: 'scryfall',
      status: 'running',
    },
  });
  
  try {
    // Download bulk data
    const filePath = await downloadBulkData();
    
    // Import into database
    await importCards(filePath);
    
    // Clean up file
    unlinkSync(filePath);
    
    const duration = Date.now() - startTime;
    
    // Update job status
    await prisma.scrapeJob.update({
      where: { id: job.id },
      data: {
        status: 'completed',
        completedAt: new Date(),
        duration,
      },
    });
    
    console.log(`\n🎉 Scryfall import completed in ${(duration / 1000 / 60).toFixed(2)} minutes`);
  } catch (error) {
    console.error('❌ Import failed:', error);
    
    await prisma.scrapeJob.update({
      where: { id: job.id },
      data: {
        status: 'failed',
        errors: JSON.stringify([error instanceof Error ? error.message : String(error)]),
        completedAt: new Date(),
      },
    });
    
    throw error;
  } finally {
    await prisma.$disconnect();
  }
}

// Run if executed directly
if (require.main === module) {
  importScryfallBulkData()
    .then(() => process.exit(0))
    .catch((error) => {
      console.error(error);
      process.exit(1);
    });
}
