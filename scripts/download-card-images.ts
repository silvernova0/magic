#!/usr/bin/env node
/**
 * Download popular card images for local caching
 * Downloads commanders and top EDHREC cards for offline use
 */

import { PrismaClient } from '@prisma/client';
import https from 'https';
import fs from 'fs';
import path from 'path';

const prisma = new PrismaClient();

// Configuration
const IMAGE_DIR = path.join(process.cwd(), 'public', 'card-images');
const EDHREC_RANK_THRESHOLD = 5000; // Download top 5000 cards by EDHREC rank
const BATCH_SIZE = 50; // Download in batches to avoid overwhelming the server
const DELAY_MS = 100; // Delay between downloads to be respectful

interface CardImage {
    id: string;
    name: string;
    imageUris: string | null;
}

/**
 * Download a single image
 */
async function downloadImage(url: string, filepath: string): Promise<boolean> {
    return new Promise((resolve) => {
        const file = fs.createWriteStream(filepath);

        https.get(url, (response) => {
            if (response.statusCode !== 200) {
                fs.unlinkSync(filepath);
                resolve(false);
                return;
            }

            response.pipe(file);
            file.on('finish', () => {
                file.close();
                resolve(true);
            });
        }).on('error', (err) => {
            fs.unlinkSync(filepath);
            console.error(`Error downloading ${url}:`, err.message);
            resolve(false);
        });
    });
}

/**
 * Get image URL from imageUris JSON
 */
function getImageUrl(imageUrisJson: string | null): string | null {
    if (!imageUrisJson) return null;

    try {
        const uris = JSON.parse(imageUrisJson);
        // Prefer normal size for balance between quality and file size
        return uris.normal || uris.large || uris.png || uris.small || null;
    } catch (e) {
        return null;
    }
}

/**
 * Main download function
 */
async function downloadCardImages() {
    console.log('🖼️  Starting card image download...\n');

    // Ensure image directory exists
    if (!fs.existsSync(IMAGE_DIR)) {
        fs.mkdirSync(IMAGE_DIR, { recursive: true });
        console.log(`✅ Created directory: ${IMAGE_DIR}\n`);
    }

    // Get cards to download
    console.log('📊 Fetching cards to download...');
    const cards = await prisma.card.findMany({
        where: {
            OR: [
                { isCommander: true },
                { edhrecRank: { lte: EDHREC_RANK_THRESHOLD } }
            ],
            imageUris: { not: null }
        },
        select: {
            id: true,
            name: true,
            imageUris: true
        }
    });

    console.log(`Found ${cards.length} cards to download\n`);

    let downloaded = 0;
    let skipped = 0;
    let failed = 0;

    // Process in batches
    for (let i = 0; i < cards.length; i += BATCH_SIZE) {
        const batch = cards.slice(i, i + BATCH_SIZE);

        for (const card of batch) {
            const filepath = path.join(IMAGE_DIR, `${card.id}.jpg`);

            // Skip if already exists
            if (fs.existsSync(filepath)) {
                skipped++;
                continue;
            }

            const imageUrl = getImageUrl(card.imageUris);
            if (!imageUrl) {
                failed++;
                continue;
            }

            const success = await downloadImage(imageUrl, filepath);
            if (success) {
                downloaded++;
                process.stdout.write(`\rDownloaded: ${downloaded} | Skipped: ${skipped} | Failed: ${failed}`);
            } else {
                failed++;
            }

            // Small delay to be respectful to Scryfall
            await new Promise(resolve => setTimeout(resolve, DELAY_MS));
        }
    }

    console.log('\n\n✅ Download complete!');
    console.log(`📊 Stats:`);
    console.log(`   - Downloaded: ${downloaded}`);
    console.log(`   - Skipped (already exists): ${skipped}`);
    console.log(`   - Failed: ${failed}`);
    console.log(`   - Total: ${cards.length}`);

    // Calculate storage used
    const files = fs.readdirSync(IMAGE_DIR);
    let totalSize = 0;
    files.forEach(file => {
        const stats = fs.statSync(path.join(IMAGE_DIR, file));
        totalSize += stats.size;
    });

    console.log(`\n💾 Storage used: ${(totalSize / 1024 / 1024 / 1024).toFixed(2)} GB`);
}

// Run
downloadCardImages()
    .catch(console.error)
    .finally(async () => await prisma.$disconnect());
