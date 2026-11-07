import { NextRequest, NextResponse } from 'next/server';
import Papa from 'papaparse';
import { prisma } from '@/lib/prisma';
import { fetchScryfallCard } from '@/lib/scryfall';
import { getCurrentUser } from '@/lib/user';

export async function POST(req: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'You must be logged in' }, { status: 401 });
    }

    const { collection, enrich } = await req.json();
    if (!collection) {
      return NextResponse.json({ error: 'Collection data is required' }, { status: 400 });
    }

    // Validate data size (2MB limit)
    const dataSize = new TextEncoder().encode(collection).length;
    const maxSize = 2 * 1024 * 1024; // 2MB
    if (dataSize > maxSize) {
      return NextResponse.json(
        { error: `Data is too large (${(dataSize / 1024 / 1024).toFixed(2)}MB). Maximum size is 2MB.` },
        { status: 413 }
      );
    }

    // Basic CSV validation - check for suspicious content
    if (collection.includes('<script') || collection.includes('javascript:')) {
      return NextResponse.json({ error: 'Invalid file content detected' }, { status: 400 });
    }

    const parsed = Papa.parse(collection, { header: true, skipEmptyLines: true });
    const data: any[] = parsed.data as any[];
    let imported = 0;

    for (const row of data) {
      const count = parseInt(row['Count'] || row['count'] || '1');
      const name = row['Name'] || row['name'];
      if (!name) continue;

      const setName = row['Edition'] || row['edition'] || '';

      let scry = null;
      if (enrich) {
        const setCodeMatch = (row['Edition'] || row['edition'] || '').match(/[A-Za-z0-9]+/);
        const setCode = setCodeMatch ? setCodeMatch[0] : undefined;
        scry = await fetchScryfallCard(name, setCode);
      }

      const existing = await prisma.userCard.findFirst({
        where: { name, setName, userId: user.id },
      });

      if (existing) {
        await prisma.userCard.update({
          where: { id: existing.id },
          data: { quantity: existing.quantity + count },
        });
      } else {
        await prisma.userCard.create({
          data: {
            name,
            manaCost: scry?.mana_cost || '',
            cmc: scry?.cmc || 0,
            colors: (scry?.colors || []).join(','),
            type_line: scry?.type_line || '',
            oracleText: scry?.oracle_text || '',
            power: scry?.power || '',
            toughness: scry?.toughness || '',
            setName: scry?.set_name || setName,
            rarity: scry?.rarity || '',
            imageUrl: scry?.image_uri || '',
            quantity: count,
            userId: user.id,
          },
        });
      }
      imported++;
    }

    return NextResponse.json({
      success: true,
      imported,
      message: `Successfully imported ${imported} cards`,
    });
  } catch (error) {
    console.error('Collection import error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to import collection' },
      { status: 500 }
    );
  }
}
