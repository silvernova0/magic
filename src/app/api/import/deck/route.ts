import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { fetchScryfallCard } from '@/lib/scryfall';
import { getCurrentUser } from '@/lib/user';

export async function POST(req: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'You must be logged in' }, { status: 401 });
    }

    const { deck, enrich } = await req.json();
    if (!deck) {
      return NextResponse.json({ error: 'Deck data is required' }, { status: 400 });
    }

    // Validate data size (2MB limit)
    const dataSize = new TextEncoder().encode(deck).length;
    const maxSize = 2 * 1024 * 1024; // 2MB
    if (dataSize > maxSize) {
      return NextResponse.json(
        { error: `Data is too large (${(dataSize / 1024 / 1024).toFixed(2)}MB). Maximum size is 2MB.` },
        { status: 413 }
      );
    }

    // Basic validation - check for suspicious content
    if (deck.includes('<script') || deck.includes('javascript:')) {
      return NextResponse.json({ error: 'Invalid file content detected' }, { status: 400 });
    }

    const lines = deck.split('\n').map((l: string) => l.trim()).filter(Boolean);
    let imported = 0;

    for (const line of lines) {
      // Expected formats: "1 Card Name (SET) 123" or "8 Snow-Covered Forest (KHM) 284"
      const match = line.match(/^(\d+)\s+(.+?)(?:\s+\(([^)]+)\))?(?:\s+(\S+))?$/);
      if (!match) continue;

      const qty = parseInt(match[1]);
      const name = match[2];
      const edition = match[3] || '';
      const setName = edition;

      let scry = null;
      if (enrich) {
        scry = await fetchScryfallCard(name, edition || undefined);
      }

      const existing = await prisma.userCard.findFirst({
        where: { name, setName, userId: user.id },
      });

      if (existing) {
        await prisma.userCard.update({
          where: { id: existing.id },
          data: { quantity: existing.quantity + qty },
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
            quantity: qty,
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
    console.error('Deck import error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to import deck' },
      { status: 500 }
    );
  }
}
