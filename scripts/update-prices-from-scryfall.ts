/**
 * Update Card Prices from Scryfall
 * Downloads Scryfall bulk data and updates ONLY the prices field
 * using the name-based ID generation to match existing MTGJSON data.
 */

import { PrismaClient } from '@prisma/client';
import https from 'https';
import { createWriteStream, unlinkSync, readFileSync } from 'fs';
import path from 'path';

const prisma = new PrismaClient();

interface ScryfallCard {
    name: string;
    prices?: { [currency: string]: string | null };
    type_line: string;
}

/**
 * Download Scryfall bulk data file
 */
async function downloadBulkData(): Promise<string> {
    console.log('Fetching Scryfall bulk data info...');

    const bulkDataResponse = await fetch('https://api.scryfall.com/bulk-data');
    const bulkData = await bulkDataResponse.json();

    const defaultCards = bulkData.data.find(
        (item: any) => item.type === 'default_cards'
    );

    if (!defaultCards) {
        throw new Error('Could not find default cards bulk data');
    }

    const downloadUrl = defaultCards.download_uri;
    const fileSize = defaultCards.size;

    console.log(`Downloading ${(fileSize / 1024 / 1024).toFixed(2)} MB from Scryfall...`);

    const filePath = path.join(process.cwd(), '.cache', 'scryfall-prices.json');

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
 * Generate ID matching MTGJSON import logic
 */
function generateId(name: string): string {
    return name.toLowerCase().replace(/[^a-z0-9]/g, '-');
}

/**
 * Update prices
 */
async function updatePrices(filePath: string): Promise<void> {
    console.log('Reading and updating prices...');

    const fileContent = readFileSync(filePath, 'utf-8');
    const cards: ScryfallCard[] = JSON.parse(fileContent);

    console.log(`Found ${cards.length.toLocaleString()} cards in Scryfall data`);

    let updated = 0;
    let skipped = 0;
    let errors = 0;
    const batchSize = 100;

    // Create a map of Scryfall data for faster lookup by generated ID
    // This avoids trying to update cards that don't exist
    // However, with 300k+ cards, a map might be heavy.
    // Let's just iterate and try to update. Prisma updateMany is not ideal here because we have different data for each.
    // We can use $transaction with update (which throws if not found) or findMany first.

    // Better approach: Get ALL IDs from DB first, then iterate Scryfall data and update matches.
    console.log('Fetching existing card IDs from database...');
    const allCards = await prisma.card.findMany({
        select: { id: true }
    });
    const existingIds = new Set(allCards.map(c => c.id));
    console.log(`Found ${existingIds.size.toLocaleString()} cards in database`);

    const updates = [];

    for (const card of cards) {
        // Skip if no prices
        if (!card.prices) continue;

        const id = generateId(card.name);

        if (existingIds.has(id)) {
            updates.push(
                prisma.card.update({
                    where: { id },
                    data: { prices: JSON.stringify(card.prices) }
                })
            );
        }
    }

    console.log(`Prepared ${updates.length.toLocaleString()} updates. Executing in batches...`);

    for (let i = 0; i < updates.length; i += batchSize) {
        const batch = updates.slice(i, i + batchSize);
        try {
            await prisma.$transaction(batch);
            updated += batch.length;
            process.stdout.write(`\rUpdating... ${(updated / updates.length * 100).toFixed(1)}%`);
        } catch (error) {
            errors++;
            // If a batch fails, it might be due to a race condition or something, but we checked IDs.
            // We'll just log and continue.
            // console.error('Batch failed', error);
        }
    }

    console.log(`\n✅ Update complete!`);
    console.log(`   Updated: ${updated.toLocaleString()} cards`);
    console.log(`   Errors (batches): ${errors}`);
}

async function main() {
    try {
        const filePath = await downloadBulkData();
        await updatePrices(filePath);
        // unlinkSync(filePath); // Keep for now in case we need to debug
    } catch (error) {
        console.error('Failed:', error);
    } finally {
        await prisma.$disconnect();
    }
}

main();
