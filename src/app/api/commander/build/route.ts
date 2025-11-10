import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { getCurrentUser } from '@/lib/user';
import { buildCommanderDeckWithAI, DeckBuildRequest } from '@/lib/gemini';
import { buildCommanderDeckWithOllama, isOllamaAvailable } from '@/lib/ollama';

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

    // If commander is specified, fetch reference decks from database
    let referenceDecks: any[] = [];
    if (commander && commander.trim()) {
      try {
        // Search for scraped decks featuring this commander from EDHREC, MTGTop8, and Moxfield
        const commanderDecks = await prisma.commanderDeck.findMany({
          where: {
            commander: {
              contains: commander,
            },
          },
          take: 10,
          orderBy: [
            { popularity: 'desc' },
            { scrapedAt: 'desc' },
          ],
        });

        referenceDecks = commanderDecks;
        console.log(`Found ${referenceDecks.length} reference decks for ${commander} from ${[...new Set(commanderDecks.map(d => d.source))].join(', ')}`);
      } catch (error) {
        console.warn('Failed to fetch reference decks:', error);
      }
    }

    // Prepare the deck build request
    const deckRequest: DeckBuildRequest = {
      commander: commander || undefined,
      theme,
      colors: colors || [],
      powerLevel,
      useCollectionOnly: useCollectionOnly || false,
      userCollection: useCollectionOnly ? collection : undefined,
      referenceDecks, // Pass reference decks to AI
    };

    let decklist;
    let aiProvider = 'Gemini';

    // Retry logic for Gemini with exponential backoff
    const maxRetries = 3;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.log(`Attempting deck generation with Gemini (attempt ${attempt}/${maxRetries})...`);
        decklist = await buildCommanderDeckWithAI(deckRequest);
        console.log(`Deck generated successfully using ${aiProvider}`);
        break; // Success, exit loop
      } catch (geminiError: any) {
        console.error(`Gemini API failed (attempt ${attempt}/${maxRetries}):`, geminiError.message);
        
        // Check if it's a 503 (overloaded) or rate limit error
        const isOverloaded = geminiError.message?.includes('503') || 
                            geminiError.message?.includes('overloaded') ||
                            geminiError.message?.includes('rate limit');
        
        if (isOverloaded && attempt < maxRetries) {
          // Wait before retrying (exponential backoff: 2s, 4s, 8s)
          const waitTime = Math.pow(2, attempt) * 1000;
          console.log(`Waiting ${waitTime/1000}s before retry...`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
          continue; // Retry
        }
        
        // If all retries failed, give up
        if (attempt === maxRetries) {
          console.error('All Gemini retries exhausted.');
          throw new Error(`Gemini API is consistently overloaded after ${maxRetries} attempts. Please try again in a few minutes.`);
        }
        
        // For non-503 errors, throw immediately
        if (!isOverloaded) {
          throw geminiError;
        }
      }
    }
    
    // Ensure decklist was generated
    if (!decklist) {
      throw new Error('Failed to generate deck after all retry attempts.');
    }

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

