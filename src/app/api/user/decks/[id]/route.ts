/**
 * API endpoint for individual deck management
 * 
 * GET /api/user/decks/[id] - Get a specific deck
 * PATCH /api/user/decks/[id] - Update a deck
 * DELETE /api/user/decks/[id] - Delete a deck
 */

import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      );
    }

    const deck = await prisma.deck.findUnique({
      where: {
        id: params.id,
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

    if (!deck) {
      return NextResponse.json(
        { error: 'Deck not found' },
        { status: 404 }
      );
    }

    // Verify ownership
    if (deck.userId !== session.user.id) {
      return NextResponse.json(
        { error: 'Forbidden. You do not own this deck.' },
        { status: 403 }
      );
    }

    return NextResponse.json({
      success: true,
      deck,
    });
  } catch (error) {
    console.error('Error fetching deck:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch deck' 
      },
      { status: 500 }
    );
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      );
    }

    // Verify deck exists and user owns it
    const existingDeck = await prisma.deck.findUnique({
      where: { id: params.id },
    });

    if (!existingDeck) {
      return NextResponse.json(
        { error: 'Deck not found' },
        { status: 404 }
      );
    }

    if (existingDeck.userId !== session.user.id) {
      return NextResponse.json(
        { error: 'Forbidden. You do not own this deck.' },
        { status: 403 }
      );
    }

    const body = await request.json();
    const { name, description, theme, powerLevel, decklist, status } = body;

    // Build update data
    const updateData: any = {};
    if (name !== undefined) updateData.name = name;
    if (description !== undefined) updateData.description = description;
    if (theme !== undefined) updateData.theme = theme;
    if (powerLevel !== undefined) updateData.powerLevel = powerLevel;
    if (decklist !== undefined) updateData.decklist = decklist;
    if (status !== undefined) updateData.status = status;

    const deck = await prisma.deck.update({
      where: { id: params.id },
      data: updateData,
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
      message: 'Deck updated successfully',
      deck,
    });
  } catch (error) {
    console.error('Error updating deck:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to update deck' 
      },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      );
    }

    // Verify deck exists and user owns it
    const existingDeck = await prisma.deck.findUnique({
      where: { id: params.id },
    });

    if (!existingDeck) {
      return NextResponse.json(
        { error: 'Deck not found' },
        { status: 404 }
      );
    }

    if (existingDeck.userId !== session.user.id) {
      return NextResponse.json(
        { error: 'Forbidden. You do not own this deck.' },
        { status: 403 }
      );
    }

    await prisma.deck.delete({
      where: { id: params.id },
    });

    return NextResponse.json({
      success: true,
      message: 'Deck deleted successfully',
    });
  } catch (error) {
    console.error('Error deleting deck:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to delete deck' 
      },
      { status: 500 }
    );
  }
}
