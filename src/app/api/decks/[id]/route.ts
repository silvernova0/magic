import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { getCurrentUser } from '@/lib/user';

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id: deckId } = await context.params;

    const deck = await prisma.deck.findFirst({
      where: { 
        id: deckId,
        userId: user.id // Ensure user can only access their own decks
      },
    });

    if (!deck) {
      return NextResponse.json({ error: 'Deck not found' }, { status: 404 });
    }

    return NextResponse.json(deck);
  } catch (error) {
    console.error(`Error fetching deck:`, error);
    return NextResponse.json({ error: 'Failed to fetch deck' }, { status: 500 });
  }
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id: deckId } = await context.params;

    // Verify the deck belongs to the user before deleting
    const deck = await prisma.deck.findFirst({
      where: { 
        id: deckId,
        userId: user.id
      },
    });

    if (!deck) {
      return NextResponse.json({ error: 'Deck not found or unauthorized' }, { status: 404 });
    }

    await prisma.deck.delete({
      where: { id: deckId },
    });

    return NextResponse.json({ message: 'Deck deleted successfully' });
  } catch (error) {
    console.error(`Error deleting deck:`, error);
    return NextResponse.json({ error: 'Failed to delete deck' }, { status: 500 });
  }
}

export async function PATCH(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { name, status } = await req.json();
    const { id: deckId } = await context.params;

    if (!name && !status) {
      return NextResponse.json({ error: 'Name or status is required' }, { status: 400 });
    }

    // Verify the deck belongs to the user before updating
    const deck = await prisma.deck.findFirst({
      where: { 
        id: deckId,
        userId: user.id
      },
    });

    if (!deck) {
      return NextResponse.json({ error: 'Deck not found or unauthorized' }, { status: 404 });
    }

    const updatedDeck = await prisma.deck.update({
      where: { id: deckId },
      data: {
        ...(name && { name }),
        ...(status && { status }),
      },
    });

    return NextResponse.json(updatedDeck);
  } catch (error) {
    console.error(`Error updating deck:`, error);
    return NextResponse.json({ error: 'Failed to update deck' }, { status: 500 });
  }
}