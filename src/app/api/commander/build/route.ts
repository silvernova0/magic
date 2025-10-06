import { NextRequest, NextResponse } from 'next/server';
import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold, Part } from '@google/generative-ai';
import type { Decklist } from '@/types';
import prisma from '../../../../lib/db';
import { getDefaultUser } from '../../../../lib/user';

if (!process.env.GEMINI_API_KEY) {
  throw new Error('GEMINI_API_KEY environment variable not set');
}

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

const model = genAI.getGenerativeModel({
  model: "gemini-1.5-flash",
});

const generationConfig = {
  temperature: 1,
  topP: 0.95,
  topK: 64,
  maxOutputTokens: 8192,
  responseMimeType: "application/json",
};

const safetySettings = [
  {
    category: HarmCategory.HARM_CATEGORY_HARASSMENT,
    threshold: HarmBlockThreshold.BLOCK_NONE,
  },
  {
    category: HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    threshold: HarmBlockThreshold.BLOCK_NONE,
  },
  {
    category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    threshold: HarmBlockThreshold.BLOCK_NONE,
  },
  {
    category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    threshold: HarmBlockThreshold.BLOCK_NONE,
  },
];

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
- Return the complete decklist in the specified JSON format. Do not include any explanatory text outside of the JSON structure.`;

    const prompt = `
      Please build a Commander deck with the following specifications:
      - Theme: ${theme}
      - Power Level: ${powerLevel}

      My Card Collection (one card per line):
      ---
      ${collection}
      ---
    `;
    const result = await model.generateContent({
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig,
      safetySettings,
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
