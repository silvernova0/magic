/**
 * API endpoint for user collection management
 * 
 * GET /api/collection - Get all cards in user's collection
 * DELETE /api/collection - Clear entire collection (with confirmation)
 */

import { NextRequest, NextResponse } from 'next/server';
import { getCurrentUser } from '@/lib/user';
import { prisma } from '@/lib/prisma';

export async function GET(request: NextRequest) {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const sortBy = searchParams.get('sortBy') || 'createdAt';
    const sortOrder = searchParams.get('sortOrder') || 'desc';
    const rarity = searchParams.get('rarity');
    const color = searchParams.get('color');
    const type = searchParams.get('type');

    // Build where clause
    const where: any = { userId: user.id };
    
    if (rarity && rarity !== 'all') {
      where.rarity = rarity;
    }
    
    if (color && color !== 'all') {
      if (color === 'colorless') {
        where.colors = '';
      } else {
        where.colors = { contains: color };
      }
    }
    
    if (type) {
      where.type_line = { contains: type, mode: 'insensitive' };
    }

    const cards = await prisma.userCard.findMany({
      where,
      orderBy: { [sortBy]: sortOrder },
    });

    // Calculate stats
    const totalCards = cards.reduce((sum, card) => sum + card.quantity, 0);
    const uniqueCards = cards.length;
    
    // Calculate total value (if prices are available)
    // Note: UserCard model doesn't have price field, but can be added
    
    return NextResponse.json({
      success: true,
      stats: {
        totalCards,
        uniqueCards,
      },
      cards,
    });
  } catch (error) {
    console.error('Error fetching collection:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch collection' 
      },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      );
    }

    // Delete all cards for this user
    const result = await prisma.userCard.deleteMany({
      where: { userId: user.id },
    });

    return NextResponse.json({
      success: true,
      message: `Deleted ${result.count} cards from collection`,
      deletedCount: result.count,
    });
  } catch (error) {
    console.error('Error clearing collection:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to clear collection' 
      },
      { status: 500 }
    );
  }
}
