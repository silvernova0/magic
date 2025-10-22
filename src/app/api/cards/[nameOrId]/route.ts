/**
 * Get Card by Name/ID API
 * Retrieve detailed information about a specific card
 */

import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET(
  request: NextRequest,
  { params }: { params: { nameOrId: string } }
) {
  try {
    const nameOrId = decodeURIComponent(params.nameOrId);
    
    // Try to find by ID first, then by name
    const card = await prisma.card.findFirst({
      where: {
        OR: [
          { id: nameOrId },
          { name: { equals: nameOrId, mode: 'insensitive' } },
        ],
      },
    });

    if (!card) {
      return NextResponse.json(
        { error: 'Card not found' },
        { status: 404 }
      );
    }

    // Parse JSON fields
    const keywords = card.keywords?.split(',').filter(Boolean) || [];
    const colors = card.colors?.split(',').filter(Boolean) || [];
    const colorIdentity = card.colorIdentity?.split(',').filter(Boolean) || [];
    
    // Extract tags
    const tags: string[] = [];
    const text = card.oracleText?.toLowerCase() || '';
    
    if (text.includes('draw')) tags.push('card-draw');
    if (text.includes('tutor') || text.includes('search your library')) tags.push('tutor');
    if (text.includes('destroy')) tags.push('removal');
    if (text.includes('exile')) tags.push('exile');
    if (text.includes('counter')) tags.push('counterspell');
    if (text.includes('token')) tags.push('token');
    if (text.includes('graveyard')) tags.push('graveyard');
    if (text.includes('sacrifice')) tags.push('sacrifice');
    if (text.includes('extra turn')) tags.push('extra-turns');
    if (text.includes('copy')) tags.push('copy');
    if (card.edhrecSaltiness && card.edhrecSaltiness > 1.0) tags.push('high-salt');
    if (card.edhrecSaltiness && card.edhrecSaltiness > 2.0) tags.push('very-high-salt');
    if (card.edhrecRank && card.edhrecRank < 500) tags.push('game-changer');
    if (card.edhrecRank && card.edhrecRank < 100) tags.push('top-100');
    if (card.isCommander) tags.push('commander');
    
    // Determine power level (0-10)
    let powerLevel = 5;
    if (card.edhrecRank) {
      if (card.edhrecRank < 100) powerLevel = 10;
      else if (card.edhrecRank < 500) powerLevel = 9;
      else if (card.edhrecRank < 1000) powerLevel = 8;
      else if (card.edhrecRank < 5000) powerLevel = 7;
      else if (card.edhrecRank < 10000) powerLevel = 6;
    }
    
    const enhancedCard = {
      ...card,
      keywords,
      colors,
      colorIdentity,
      tags,
      powerLevel,
      legalities: card.legalities ? JSON.parse(card.legalities) : {},
      imageUris: card.imageUris ? JSON.parse(card.imageUris) : null,
      prices: card.prices ? JSON.parse(card.prices) : null,
    };

    return NextResponse.json({ card: enhancedCard });
  } catch (error) {
    console.error('Error fetching card:', error);
    return NextResponse.json(
      { error: 'Failed to fetch card' },
      { status: 500 }
    );
  }
}
