/**
 * Get Card Synergies API
 * Retrieve synergy data for a specific card/commander
 */

import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET(
  request: NextRequest,
  { params }: { params: { cardId: string } }
) {
  try {
    const cardId = params.cardId;
    const { searchParams } = new URL(request.url);
    
    const limit = parseInt(searchParams.get('limit') || '50');
    const minScore = parseFloat(searchParams.get('minScore') || '0');
    const sortBy = searchParams.get('sortBy') || 'score'; // 'score' or 'inclusion'

    // Get synergies for this card
    const synergies = await prisma.cardSynergy.findMany({
      where: {
        cardId: cardId,
        score: {
          gte: minScore,
        },
      },
      include: {
        card: {
          select: {
            id: true,
            name: true,
            typeLine: true,
            manaCost: true,
            cmc: true,
            colors: true,
            rarity: true,
            edhrecRank: true,
            edhrecSaltiness: true,
          },
        },
      },
      orderBy: sortBy === 'score' ? { score: 'desc' } : undefined,
      take: limit,
    });

    // Get synergy cards data
    const synergyCards = await prisma.card.findMany({
      where: {
        id: {
          in: synergies.map(s => s.synergyId),
        },
      },
      select: {
        id: true,
        name: true,
        typeLine: true,
        manaCost: true,
        cmc: true,
        colors: true,
        colorIdentity: true,
        rarity: true,
        edhrecRank: true,
        edhrecSaltiness: true,
        oracleText: true,
      },
    });

    // Map synergy data
    const result = synergies.map(syn => {
      const synergyCard = synergyCards.find(c => c.id === syn.synergyId);
      return {
        synergyId: syn.id,
        cardId: syn.cardId,
        synergyCardId: syn.synergyId,
        synergyCardName: synergyCard?.name || 'Unknown',
        synergyCard: synergyCard,
        score: syn.score,
        source: syn.source,
        commander: syn.commander,
        createdAt: syn.createdAt,
      };
    });

    return NextResponse.json({
      cardId,
      synergies: result,
      total: result.length,
    });
  } catch (error) {
    console.error('Error fetching synergies:', error);
    return NextResponse.json(
      { error: 'Failed to fetch synergies' },
      { status: 500 }
    );
  }
}
