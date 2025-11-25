/**
 * Card Search API
 * Search and filter cards from local database
 * Supports: name search, color filtering, type filtering, keyword search, saltiness, tags
 */

import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    // Search parameters
    const query = searchParams.get('q') || searchParams.get('name') || '';
    const colors = searchParams.get('colors')?.split(',').filter(Boolean) || [];
    const colorIdentity = searchParams.get('colorIdentity')?.split(',').filter(Boolean) || [];
    const types = searchParams.get('types')?.split(',').filter(Boolean) || [];
    const keywords = searchParams.get('keywords')?.split(',').filter(Boolean) || [];
    const minCmc = searchParams.get('minCmc') ? parseInt(searchParams.get('minCmc')!) : undefined;
    const maxCmc = searchParams.get('maxCmc') ? parseInt(searchParams.get('maxCmc')!) : undefined;
    const isCommander = searchParams.get('isCommander') === 'true';
    const minEdhrecRank = searchParams.get('minEdhrecRank') ? parseInt(searchParams.get('minEdhrecRank')!) : undefined;
    const maxEdhrecRank = searchParams.get('maxEdhrecRank') ? parseInt(searchParams.get('maxEdhrecRank')!) : undefined;
    const minSaltiness = searchParams.get('minSaltiness') ? parseFloat(searchParams.get('minSaltiness')!) : undefined;
    const maxSaltiness = searchParams.get('maxSaltiness') ? parseFloat(searchParams.get('maxSaltiness')!) : undefined;
    const rarity = searchParams.get('rarity');
    const limit = Math.min(parseInt(searchParams.get('limit') || '100'), 500);
    const offset = parseInt(searchParams.get('offset') || '0');
    const sortBy = searchParams.get('sortBy') || 'name';
    const sortOrder = searchParams.get('sortOrder') === 'desc' ? 'desc' : 'asc';

    // Build where clause
    const where: any = {};

    if (query) {
      where.OR = [
        { name: { contains: query } },
        { oracleText: { contains: query } },
        { typeLine: { contains: query } },
      ];
    }

    if (colors.length > 0) {
      // Cards that contain ALL specified colors
      where.AND = colors.map(color => ({
        colors: { contains: color }
      }));
    }

    if (colorIdentity.length > 0) {
      // Cards with EXACT color identity (for Commander)
      const ciString = colorIdentity.sort().join(',');
      where.colorIdentity = ciString;
    }

    if (types.length > 0) {
      where.AND = [
        ...(where.AND || []),
        ...types.map(type => ({
          typeLine: { contains: type }
        }))
      ];
    }

    if (keywords.length > 0) {
      where.AND = [
        ...(where.AND || []),
        ...keywords.map(keyword => ({
          keywords: { contains: keyword }
        }))
      ];
    }

    if (minCmc !== undefined || maxCmc !== undefined) {
      where.cmc = {};
      if (minCmc !== undefined) where.cmc.gte = minCmc;
      if (maxCmc !== undefined) where.cmc.lte = maxCmc;
    }

    if (isCommander) {
      where.isCommander = true;
    }

    if (minEdhrecRank !== undefined || maxEdhrecRank !== undefined) {
      where.edhrecRank = { not: null };
      if (minEdhrecRank !== undefined) {
        where.edhrecRank = { ...where.edhrecRank, gte: minEdhrecRank };
      }
      if (maxEdhrecRank !== undefined) {
        where.edhrecRank = { ...where.edhrecRank, lte: maxEdhrecRank };
      }
    }

    if (minSaltiness !== undefined || maxSaltiness !== undefined) {
      where.edhrecSaltiness = { not: null };
      if (minSaltiness !== undefined) {
        where.edhrecSaltiness = { ...where.edhrecSaltiness, gte: minSaltiness };
      }
      if (maxSaltiness !== undefined) {
        where.edhrecSaltiness = { ...where.edhrecSaltiness, lte: maxSaltiness };
      }
    }

    if (rarity) {
      where.rarity = rarity;
    }

    // Determine sort field
    let orderBy: any = {};
    switch (sortBy) {
      case 'cmc':
        orderBy = { cmc: sortOrder };
        break;
      case 'edhrecRank':
        orderBy = { edhrecRank: sortOrder };
        break;
      case 'edhrecSaltiness':
        orderBy = { edhrecSaltiness: sortOrder };
        break;
      case 'name':
      default:
        orderBy = { name: sortOrder };
        break;
    }

    // Execute query
    const [cards, totalCount] = await Promise.all([
      prisma.card.findMany({
        where,
        orderBy,
        take: limit,
        skip: offset,
        select: {
          id: true,
          name: true,
          manaCost: true,
          cmc: true,
          colors: true,
          colorIdentity: true,
          typeLine: true,
          oracleText: true,
          power: true,
          toughness: true,
          loyalty: true,
          keywords: true,
          rarity: true,
          edhrecRank: true,
          edhrecSaltiness: true,
          isCommander: true,
          imageUris: true,
          prices: true,
        },
        distinct: ['name'],
      }),
      prisma.card.count({ where }),
    ]);

    // Parse JSON fields and add computed properties
    // Helper to parse array fields (JSON or CSV)
    const parseArrayField = (field: string | null): string[] => {
      if (!field) return [];
      try {
        // Try JSON first
        const parsed = JSON.parse(field);
        if (Array.isArray(parsed)) return parsed;
      } catch (e) {
        // Not JSON, ignore
      }
      // Fallback to CSV
      return field.split(',').map(s => s.trim()).filter(Boolean);
    };

    const enhancedCards = cards.map((card: any) => {
      const keywords = parseArrayField(card.keywords);
      const colors = parseArrayField(card.colors);
      const colorIdentity = parseArrayField(card.colorIdentity);

      // Determine tags based on card properties
      const tags: string[] = [];
      const text = card.oracleText?.toLowerCase() || '';

      if (text.includes('draw')) tags.push('card-draw');
      if (text.includes('tutor') || text.includes('search your library')) tags.push('tutor');
      if (text.includes('destroy')) tags.push('removal');
      if (text.includes('counter')) tags.push('counterspell');
      if (text.includes('token')) tags.push('token');
      if (text.includes('extra turn')) tags.push('extra-turns');
      if (card.edhrecSaltiness && card.edhrecSaltiness > 1.0) tags.push('high-salt');
      if (card.edhrecRank && card.edhrecRank < 500) tags.push('game-changer');

      return {
        ...card,
        keywords,
        colors,
        colorIdentity,
        tags,
        imageUris: card.imageUris ? JSON.parse(card.imageUris) : null,
        prices: card.prices ? JSON.parse(card.prices) : null,
      };
    });

    return NextResponse.json({
      cards: enhancedCards,
      pagination: {
        total: totalCount,
        limit,
        offset,
        hasMore: offset + limit < totalCount,
      },
    });
  } catch (error) {
    console.error('Error searching cards:', error);
    return NextResponse.json(
      { error: 'Failed to search cards' },
      { status: 500 }
    );
  }
}
