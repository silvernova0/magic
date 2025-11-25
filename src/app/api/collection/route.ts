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
    const search = searchParams.get('search');

    // Pagination params
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '24');
    const skip = (page - 1) * limit;

    // Build where clause
    const where: any = { userId: user.id };

    if (search) {
      where.name = { contains: search, mode: 'insensitive' };
    }

    if (rarity && rarity !== 'all') {
      where.rarity = { equals: rarity, mode: 'insensitive' };
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

    // Get total count for pagination
    const totalCards = await prisma.userCard.count({ where });

    // Get paginated cards
    const cards = await prisma.userCard.findMany({
      where,
      orderBy: { [sortBy]: sortOrder },
      skip,
      take: limit,
    });

    // Calculate aggregate stats (needs separate query if filters applied, 
    // or we can just return total collection stats separately if needed, 
    // but for now let's just return the count of filtered items)

    // For the "Total Cards" and "Unique Cards" badges in the UI, 
    // we might want the UNFILTERED counts. Let's fetch those if it's the first page
    // or just always fetch them (lightweight count query).
    const totalCollectionCount = await prisma.userCard.count({ where: { userId: user.id } });
    // Unique count is just total count in this schema since each UserCard is an entry, 
    // unless we group by name. For now, let's stick to simple counts.

    return NextResponse.json({
      success: true,
      stats: {
        totalCards: totalCollectionCount, // Total in entire collection
        filteredCards: totalCards,        // Total matching current filters
        totalPages: Math.ceil(totalCards / limit),
        currentPage: page,
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
