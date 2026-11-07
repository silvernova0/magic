/**
 * API endpoint for individual card management in collection
 * 
 * GET /api/collection/[id] - Get a specific card
 * PATCH /api/collection/[id] - Update card quantity
 * DELETE /api/collection/[id] - Remove card from collection
 */

import { NextRequest, NextResponse } from 'next/server';
import { getCurrentUser } from '@/lib/user';
import { prisma } from '@/lib/prisma';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      );
    }

    const card = await prisma.userCard.findUnique({
      where: { id: params.id },
    });

    if (!card) {
      return NextResponse.json(
        { error: 'Card not found' },
        { status: 404 }
      );
    }

    // Verify ownership
    if (card.userId !== user.id) {
      return NextResponse.json(
        { error: 'Forbidden. You do not own this card.' },
        { status: 403 }
      );
    }

    return NextResponse.json({
      success: true,
      card,
    });
  } catch (error) {
    console.error('Error fetching card:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch card' 
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
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      );
    }

    // Verify card exists and user owns it
    const existingCard = await prisma.userCard.findUnique({
      where: { id: params.id },
    });

    if (!existingCard) {
      return NextResponse.json(
        { error: 'Card not found' },
        { status: 404 }
      );
    }

    if (existingCard.userId !== user.id) {
      return NextResponse.json(
        { error: 'Forbidden. You do not own this card.' },
        { status: 403 }
      );
    }

    const body = await request.json();
    const { quantity } = body;

    // Validate quantity
    if (quantity === undefined || quantity < 0) {
      return NextResponse.json(
        { error: 'Invalid quantity. Must be 0 or greater.' },
        { status: 400 }
      );
    }

    // If quantity is 0, delete the card
    if (quantity === 0) {
      await prisma.userCard.delete({
        where: { id: params.id },
      });

      return NextResponse.json({
        success: true,
        message: 'Card removed from collection',
        deleted: true,
      });
    }

    // Update quantity
    const card = await prisma.userCard.update({
      where: { id: params.id },
      data: { quantity },
    });

    return NextResponse.json({
      success: true,
      message: 'Card quantity updated',
      card,
    });
  } catch (error) {
    console.error('Error updating card:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to update card' 
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
    const user = await getCurrentUser();
    
    if (!user) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      );
    }

    // Verify card exists and user owns it
    const existingCard = await prisma.userCard.findUnique({
      where: { id: params.id },
    });

    if (!existingCard) {
      return NextResponse.json(
        { error: 'Card not found' },
        { status: 404 }
      );
    }

    if (existingCard.userId !== user.id) {
      return NextResponse.json(
        { error: 'Forbidden. You do not own this card.' },
        { status: 403 }
      );
    }

    await prisma.userCard.delete({
      where: { id: params.id },
    });

    return NextResponse.json({
      success: true,
      message: 'Card removed from collection',
    });
  } catch (error) {
    console.error('Error deleting card:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to delete card' 
      },
      { status: 500 }
    );
  }
}
