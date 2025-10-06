import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenAI, Type } from '@google/genai';
import type { Decklist } from '@/types';
import prisma from '../../../../lib/db';
import { getDefaultUser } from '../../../../lib/user';

if (!process.env.GEMINI_API_KEY) {
  throw new Error('GEMINI_API_KEY environment variable not set');
}

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const DECK_SCHEMA = {
    type: Type.OBJECT,
    properties: {
      commander: {
        type: Type.ARRAY,
        description: "The commander(s) of the deck. Must be 1-2 legendary creature cards.",
        items: { type: Type.STRING }
      },
      creatures: {
        type: Type.ARRAY,
        description: "All non-commander creature cards in the deck.",
        items: { type: Type.STRING }
      },
      sorceries: {
        type: Type.ARRAY,
        description: "All sorcery cards in the deck.",
        items: { type: Type.STRING }
      },
      instants: {
        type: Type.ARRAY,
        description: "All instant cards in the deck.",
        items: { type: Type.STRING }
      },
      artifacts: {
        type: Type.ARRAY,
        description: "All non-creature artifact cards in the deck.",
        items: { type: Type.STRING }
      },
      enchantments: {
        type: Type.ARRAY,
        description: "All non-creature enchantment cards in the deck.",
        items: { type: Type.STRING }
      },
      planeswalkers: {
        type: Type.ARRAY,
        description: "All planeswalker cards in the deck.",
        items: { type: Type.STRING }
      },
      lands: {
        type: Type.ARRAY,
        description: "All land cards in the deck. Typically 35-40 cards.",
        items: { type: Type.STRING }
      }
    },
    required: ["commander", "creatures", "sorceries", "instants", "artifacts", "enchantments", "planeswalkers", "lands"]
  };

export async function POST(req: NextRequest) {
  try {
    const { collection, theme, powerLevel } = await req.json();

    if (!collection || !theme || !powerLevel) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const systemInstruction = `You are an expert Magic: The Gathering deck builder specializing in the Commander (EDH) format. Your task is to create a 100-card singleton decklist. The deck must include one or two legendary creatures as the commander(s).
- You must build the deck using the provided card collection as the primary source.
- Prioritize cards that fit the requested theme and power level.
- If the collection lacks key cards for the theme, you may suggest a few essential cards not in the collection, but clearly mark them by appending "(suggested)" to the card name.
- The final decklist must total exactly 100 cards.
- Return the complete decklist in the specified JSON format. Do not include any explanatory text outside of the JSON structure.`

    const prompt = `
      Please build a Commander deck with the following specifications:
      - Theme: ${theme}
      - Power Level: ${powerLevel}

      My Card Collection (one card per line):
      ---
      ${collection}
      ---
    `;

    const result = await ai.getGenerativeModel({ model: "gemini-1.5-flash",
    systemInstruction: {
      role: "model",
      parts: [{text: systemInstruction}]
  }
  }).generateContent({contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: {
        responseMimeType: "application/json",
        responseSchema: DECK_SCHEMA,
    },
});

    const jsonText = result.response.text();
    const decklist: Decklist = JSON.parse(jsonText);

    // Simple validation
    const totalCards = Object.values(decklist).reduce((sum, category) => sum + (category?.length || 0), 0);
    if (totalCards < 90 || totalCards > 105) { // Allow some leeway
        console.warn(`Generated deck has ${totalCards} cards, which is not 100. The model may have made a mistake.`);
    }
    if (!decklist.commander || decklist.commander.length === 0) {
        throw new Error("The generated decklist is missing a commander.");
    }

    const user = await getDefaultUser();
    const newDeck = await prisma.deck.create({
      data: {
        name: `New ${theme} Deck`,
        theme,
        powerLevel,
        decklist: decklist as any,
        userId: user.id,
      },
    });

    return NextResponse.json({ deck: newDeck, decklist });
  } catch (error) {
    console.error("Error generating or parsing decklist:", error);
    return NextResponse.json({ error: "Failed to generate a valid deck. The model might be busy or the request was invalid. Please try again with a more detailed collection or theme." }, { status: 500 });
  }
}
