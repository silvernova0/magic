import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { getCurrentUser } from '@/lib/user';
import { DeckBuildRequest } from '@/lib/gemini';
import { buildCommanderDeckWithOllama } from '@/lib/ollama';

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

    const deckRequest: DeckBuildRequest = {
      commander: commander || undefined,
      theme,
      colors: colors || [],
      powerLevel: String(powerLevel),
      useCollectionOnly: useCollectionOnly || false,
      userCollection: useCollectionOnly ? collection : undefined,
    };

    console.log('Generating Commander deck using Local AI + Card Database...');
    const decklist = await buildCommanderDeckWithOllama(deckRequest);

    const commanderName = decklist.commander[0] || 'Unknown';
    const deckName = `${commanderName} — ${theme}`;

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
    console.error('Error generating decklist with Local AI:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    return NextResponse.json(
      { error: `Failed to generate deck: ${errorMessage}` },
      { status: 500 }
    );
  }
}
