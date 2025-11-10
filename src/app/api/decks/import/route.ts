import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { fetchScryfallCard } from '@/lib/scryfall';
import { getCurrentUser } from '@/lib/user';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { deck, enrich = true } = body;
    if (!deck || !deck.cards) return NextResponse.json({ error: 'Invalid deck' }, { status: 400 });

    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    let importedCount = 0;
    for (const c of deck.cards) {
      const name = c.name;
      const qty = c.qty || 1;

      let scry = null;
      if (enrich) {
        scry = await fetchScryfallCard(name);
      }

      const setName = scry?.set_name || deck.url || '';

      const existing = await prisma.userCard.findFirst({ where: { name, setName, userId: user.id } });
      if (existing) {
        await prisma.userCard.update({ where: { id: existing.id }, data: { quantity: existing.quantity + qty } });
      } else {
        await prisma.userCard.create({ data: {
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
          userId: user.id,
        } });
      }

      importedCount += qty;
    }

    return NextResponse.json({ importedCount });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
