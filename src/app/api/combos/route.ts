/**
 * Get Combos API
 * Retrieve combo data, optionally filtered by colors or cards
 */

import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    
    const colors = searchParams.get('colors')?.split(',').filter(Boolean) || [];
    const cardName = searchParams.get('cardName');
    const limit = parseInt(searchParams.get('limit') || '50');
    const page = parseInt(searchParams.get('page') || '1');
    const skip = (page - 1) * limit;

    // Build where clause
    const where: any = {};

    // Filter by colors (combos that use these colors)
    if (colors.length > 0) {
      where.colors = {
        contains: colors[0], // Simple containment check
      };
    }

    // Filter by card name (find combos that include this card)
    if (cardName) {
      const card = await prisma.card.findFirst({
        where: { name: { contains: cardName } },
        select: { id: true },
      });

      if (card) {
        where.cards = {
          some: {
            cardId: card.id,
          },
        };
      }
    }

    // Get combos
    const [combos, total] = await Promise.all([
      prisma.combo.findMany({
        where,
        include: {
          cards: {
            include: {
              card: {
                select: {
                  id: true,
                  name: true,
                  typeLine: true,
                  manaCost: true,
                  cmc: true,
                  colors: true,
                  colorIdentity: true,
                  oracleText: true,
                },
              },
            },
          },
        },
        orderBy: {
          popularity: 'desc',
        },
        take: limit,
        skip,
      }),
      prisma.combo.count({ where }),
    ]);

    // Parse JSON fields and format response
    const formattedCombos = combos.map(combo => ({
      id: combo.id,
      name: combo.name,
      description: combo.description,
      colors: JSON.parse(combo.colors),
      steps: JSON.parse(combo.steps),
      result: combo.result,
      popularity: combo.popularity,
      source: combo.source,
      sourceUrl: combo.sourceUrl,
      cards: combo.cards.map(cc => ({
        cardId: cc.cardId,
        card: cc.card,
        quantity: cc.quantity,
      })),
      createdAt: combo.createdAt,
    }));

    return NextResponse.json({
      combos: formattedCombos,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (error) {
    console.error('Error fetching combos:', error);
    return NextResponse.json(
      { error: 'Failed to fetch combos' },
      { status: 500 }
    );
  }
}
