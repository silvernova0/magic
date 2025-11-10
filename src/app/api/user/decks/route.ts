/**
 * API endpoint for user deck management
 * 
 * GET /api/user/decks - Get current user's saved decks
 * POST /api/user/decks - Save a new deck for current user
 */

import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const status = searchParams.get('status'); // GENERATED, SAVED, IMPORTED
    const sortBy = searchParams.get('sortBy') || 'updatedAt';
    const sortOrder = searchParams.get('sortOrder') || 'desc';

    const where: any = { userId: session.user.id };
    
    if (status) {
      where.status = status;
    }

    const decks = await prisma.deck.findMany({
      where,
      orderBy: { [sortBy]: sortOrder },
      include: {
        user: {
          select: {
            id: true,
            name: true,
            email: true,
          }
        }
      }
    });

    return NextResponse.json({
      success: true,
      count: decks.length,
      decks,
    });
  } catch (error) {
    console.error('Error fetching decks:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch decks' 
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { name, description, theme, powerLevel, decklist, status } = body;

    // Validation
    if (!name || !decklist) {
      return NextResponse.json(
        { error: 'Name and decklist are required' },
        { status: 400 }
      );
    }

    // Validate decklist format (should be JSON with commander, mainboard, etc.)
    if (typeof decklist !== 'object') {
      return NextResponse.json(
        { error: 'Decklist must be a JSON object' },
        { status: 400 }
      );
    }

    // Create deck
    const deck = await prisma.deck.create({
      data: {
        name,
        description: description || null,
        theme: theme || 'Unknown',
        powerLevel: powerLevel || 'Unknown',
        decklist,
        status: status || 'SAVED',
        userId: session.user.id,
      },
      include: {
        user: {
          select: {
            id: true,
            name: true,
            email: true,
          }
        }
      }
    });

    return NextResponse.json({
      success: true,
      message: 'Deck saved successfully',
      deck,
    });
  } catch (error) {
    console.error('Error saving deck:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to save deck' 
      },
      { status: 500 }
    );
  }
}
