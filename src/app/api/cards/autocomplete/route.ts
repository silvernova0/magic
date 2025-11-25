/**
 * Local card autocomplete endpoint
 * Replaces Scryfall API with local database search
 */

import { NextRequest, NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams;
    const query = searchParams.get('q');

    if (!query || query.length < 2) {
        return NextResponse.json({ data: [] });
    }

    try {
        // Search for cards matching the query
        // Use raw SQL for case-insensitive search since SQLite doesn't support mode parameter
        const cards = await prisma.$queryRaw<Array<{ name: string }>>`
      SELECT DISTINCT name 
      FROM Card 
      WHERE LOWER(name) LIKE LOWER(${`%${query}%`})
      ORDER BY 
        CASE WHEN edhrecRank IS NULL THEN 1 ELSE 0 END,
        edhrecRank ASC,
        name ASC
      LIMIT 20
    `;

        // Return in Scryfall-compatible format
        return NextResponse.json({
            data: cards.map(c => c.name)
        });

    } catch (error) {
        console.error('Autocomplete error:', error);
        return NextResponse.json({ data: [] }, { status: 500 });
    }
}
