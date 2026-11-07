import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { getCurrentUser } from '@/lib/user';

export async function POST(req: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const {
      name,
      manaCost,
      cmc,
      colors,
      type_line,
      oracleText,
      power,
      toughness,
      setName,
      rarity,
      imageUrl,
      quantity,
    } = await req.json();

    // Check if card already exists in user's collection
    const existing = await prisma.userCard.findFirst({
      where: {
        userId: user.id,
        name,
        setName,
      },
    });

    if (existing) {
      // Update quantity if card already exists
      const updated = await prisma.userCard.update({
        where: { id: existing.id },
        data: { quantity: existing.quantity + quantity },
      });
      return NextResponse.json(updated);
    }

    // Create new card
    const newCard = await prisma.userCard.create({
      data: {
        name,
        manaCost: manaCost || '',
        cmc: cmc || 0,
        colors: colors || '',
        type_line: type_line || '',
        oracleText: oracleText || null,
        power: power || null,
        toughness: toughness || null,
        setName: setName || '',
        rarity: rarity || '',
        imageUrl: imageUrl || null,
        quantity: quantity || 1,
        userId: user.id,
      },
    });

    return NextResponse.json(newCard);
  } catch (error: any) {
    console.error('Error adding card:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to add card' },
      { status: 500 }
    );
  }
}
