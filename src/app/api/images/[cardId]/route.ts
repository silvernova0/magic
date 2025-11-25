/**
 * Image proxy endpoint
 * Serves local images when available, fetches and caches from Scryfall otherwise
 */

import { NextRequest, NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';
import https from 'https';

const prisma = new PrismaClient();
const IMAGE_DIR = path.join(process.cwd(), 'public', 'card-images');

/**
 * Download and cache an image
 */
async function downloadAndCache(url: string, filepath: string): Promise<boolean> {
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
        }).on('error', () => {
            if (fs.existsSync(filepath)) {
                fs.unlinkSync(filepath);
            }
            resolve(false);
        });
    });
}

export async function GET(
    request: NextRequest,
    { params }: { params: { cardId: string } }
) {
    const { cardId } = params;

    // Check for local image first
    const localPath = path.join(IMAGE_DIR, `${cardId}.jpg`);

    if (fs.existsSync(localPath)) {
        // Serve local image
        const imageBuffer = fs.readFileSync(localPath);
        return new NextResponse(imageBuffer, {
            headers: {
                'Content-Type': 'image/jpeg',
                'Cache-Control': 'public, max-age=31536000, immutable',
            },
        });
    }

    // Image not cached, fetch from database to get Scryfall URL
    try {
        const card = await prisma.card.findUnique({
            where: { id: cardId },
            select: { imageUris: true }
        });

        if (!card || !card.imageUris) {
            return new NextResponse('Image not found', { status: 404 });
        }

        const imageUris = JSON.parse(card.imageUris);
        const imageUrl = imageUris.normal || imageUris.large || imageUris.png;

        if (!imageUrl) {
            return new NextResponse('Image URL not available', { status: 404 });
        }

        // Ensure directory exists
        if (!fs.existsSync(IMAGE_DIR)) {
            fs.mkdirSync(IMAGE_DIR, { recursive: true });
        }

        // Download and cache
        const success = await downloadAndCache(imageUrl, localPath);

        if (success && fs.existsSync(localPath)) {
            // Serve newly cached image
            const imageBuffer = fs.readFileSync(localPath);
            return new NextResponse(imageBuffer, {
                headers: {
                    'Content-Type': 'image/jpeg',
                    'Cache-Control': 'public, max-age=31536000, immutable',
                },
            });
        }

        // If caching failed, redirect to Scryfall
        return NextResponse.redirect(imageUrl);

    } catch (error) {
        console.error('Error serving image:', error);
        return new NextResponse('Internal server error', { status: 500 });
    }
}
