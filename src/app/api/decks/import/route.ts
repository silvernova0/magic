import { NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';
import { fetchScryfallCard } from '@/lib/scryfall';

const prisma = new PrismaClient();

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { deck, enrich = true } = body;
    if (!deck || !deck.cards) return NextResponse.json({ error: 'Invalid deck' }, { status: 400 });

    let importedCount = 0;
    for (const c of deck.cards) {
      const name = c.name;
      const qty = c.qty || 1;

      let scry = null;
      if (enrich) {
        scry = await fetchScryfallCard(name);
      }

      const setName = scry?.set_name || deck.url || '';

      const existing = await prisma.card.findFirst({ where: { name, setName } });
      if (existing) {
        await prisma.card.update({ where: { id: existing.id }, data: { quantity: existing.quantity + qty } });
      } else {
        await prisma.card.create({ data: {
          name,
          manaCost: scry?.mana_cost || '',
          cmc: scry?.cmc || 0,
          colors: (scry?.colors || []).join(','),
          type_line: scry?.type_line || '',
          oracleText: scry?.oracle_text || '',
          power: scry?.power || '',
          toughness: scry?.toughness || '',
          setName,
          rarity: scry?.rarity || '',
          imageUrl: scry?.image_uri || '',
          quantity: qty,
        } });
      }

      importedCount += qty;
    }

    return NextResponse.json({ importedCount });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
