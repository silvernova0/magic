import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { getCurrentUser } from '@/lib/user';
import { buildCommanderDeckWithAI, DeckBuildRequest } from '@/lib/gemini';

export async function POST(req: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'You must be logged in to build a deck.' }, { status: 401 });
    }

    const { commander, theme, colors, powerLevel, useCollectionOnly, collection } = await req.json();

    if (!theme || !powerLevel) {
      return NextResponse.json({ error: 'Missing required fields (theme, powerLevel)' }, { status: 400 });
    }

    // Prepare the deck build request
    const deckRequest: DeckBuildRequest = {
      commander: commander || undefined,
      theme,
      colors: colors || [],
      powerLevel,
      useCollectionOnly: useCollectionOnly || false,
      userCollection: useCollectionOnly ? collection : undefined,
    };

    // Build the deck using Gemini AI
    const decklist = await buildCommanderDeckWithAI(deckRequest);

    // Determine deck name
    const commanderName = decklist.commander[0] || 'Unknown';
    const deckName = commander 
      ? `${commanderName} ${theme}`
      : `${theme} Commander Deck`;

    // Save to database
    const newDeck = await prisma.deck.create({
      data: {
        name: deckName,
        description: decklist.description || `A ${theme} deck at power level ${powerLevel}`,
        theme,
        powerLevel: `Bracket ${powerLevel}`,
        decklist: decklist as any,
        userId: user.id,
      },
    });

    return NextResponse.json({ deck: newDeck, decklist });
  } catch (error) {
    console.error("Error generating or parsing decklist:", error);
    
    // Provide specific error messages
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    // Check if it's a card count validation error
    if (errorMessage.includes('100 cards')) {
      return NextResponse.json({ 
        error: errorMessage 
      }, { status: 400 });
    }
    
    return NextResponse.json({ 
      error: `Failed to generate a valid deck: ${errorMessage}. Please try again.` 
    }, { status: 500 });
  }
}

