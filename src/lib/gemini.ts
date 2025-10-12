import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold, SchemaType } from '@google/generative-ai';

if (!process.env.GEMINI_API_KEY) {
  throw new Error('GEMINI_API_KEY environment variable not set');
}

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

// Using gemini-2.5-flash - latest stable Flash model with 1M token context
const model = genAI.getGenerativeModel({
  model: 'gemini-2.5-flash',
});

const generationConfig = {
  temperature: 0.7, // Lower temperature for more consistent format
  topP: 0.95,
  topK: 40,
  maxOutputTokens: 16384, // Increased to handle full response
  responseMimeType: 'application/json',
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

export interface DeckBuildRequest {
  commander?: string; // Specific commander requested
  theme: string; // Aggro, Control, Stax, etc.
  colors: string[]; // ['W', 'U', 'B', 'R', 'G'] or subset
  powerLevel: string; // Moxfield bracket 1-5
  useCollectionOnly: boolean; // true = only use user's cards, false = any cards
  userCollection?: string; // User's card collection (one per line)
}

export interface DeckBuildResponse {
  commander: string[];
  creatures: string[];
  instants: string[];
  sorceries: string[];
  artifacts: string[];
  enchantments: string[];
  planeswalkers: string[];
  lands: string[];
  description?: string;
  strategy?: string;
  keyCards?: string[];
}

/**
 * Build a Commander deck using Gemini AI with context from popular EDH sources
 */
export async function buildCommanderDeckWithAI(
  request: DeckBuildRequest
): Promise<DeckBuildResponse> {
  const {
    commander,
    theme,
    colors,
    powerLevel,
    useCollectionOnly,
    userCollection,
  } = request;

  // Build comprehensive system instruction with EDH knowledge
  const systemInstruction = `You are an expert Magic: The Gathering Commander (EDH) deck builder with extensive knowledge from:
- EDHREC.com (the most popular commander database and statistics site)
- MTGTop8.com (tournament results and meta decks)
- Moxfield.com (deck building platform with power level brackets 1-5)

Your task is to build a 100-card singleton Commander deck following these principles:

POWER LEVEL GUIDELINES (Moxfield Brackets):
- Bracket 1: Precon-level, basic lands, simple synergies, no fast mana
- Bracket 2: Upgraded precons, some ramp, basic tutors, kindred synergies
- Bracket 3: Focused strategy, good card quality, tutors, some combos, efficient ramp
- Bracket 4: Highly optimized, fast mana (Sol Ring, Mana Crypt), powerful tutors, strong combos
- Bracket 5: cEDH, aims to win turns 1-4, best cards, instant-win combos, minimal interaction

DECK ARCHETYPES:
- Aggro: Fast creatures, combat damage, low curve
- Tempo: Efficient threats + disruption, bounce/counter spells
- Control: Counter spells, removal, board wipes, card draw, win late game
- Stax: Tax effects, resource denial, asymmetric effects, slow the game
- Combo: Assemble 2-3 card combos for instant wins
- Midrange: Value engines, resilient threats, good stuff
- Kindred: Creature type synergies
- Voltron: Commander damage, auras/equipment
- Tokens: Create many creatures, go wide strategies
- Aristocrats: Sacrifice outlets + death triggers
- Reanimator: Graveyard recursion, cheat big creatures into play

DECK BUILDING RULES:
1. CRITICAL: Exactly 100 cards total (including commander) - NOT 99, NOT 101, EXACTLY 100
2. Commander must be legendary creature(s) in chosen colors
3. All cards must match commander's color identity
4. Singleton format (max 1 copy except basic lands)
5. Basic lands have NO LIMIT - you can use as many Forest, Island, Mountain, Plains, Swamp, and Wastes as needed
6. Include 35-40 lands for most decks (adjust for power level)
7. Include 8-12 ramp sources (Sol Ring, signets, land ramp)
8. Include 8-10 card draw sources
9. Include 8-10 removal/interaction pieces
10. Build around commander's abilities and chosen theme
11. Reference popular cards from EDHREC for the commander/theme
12. VERIFY: Count all cards before returning - commander + creatures + instants + sorceries + artifacts + enchantments + planeswalkers + lands = 100

POPULAR STAPLES BY POWER LEVEL:
Bracket 1-2: Sol Ring, Command Tower, Arcane Signet, Cultivate, Swords to Plowshares
Bracket 3: Rhystic Study, Smothering Tithe, Cyclonic Rift, Demonic Tutor, Mana Drain
Bracket 4-5: Mana Crypt, Force of Will, Gaea's Cradle, Timetwister, The One Ring, Jeweled Lotus

OUTPUT FORMAT REQUIREMENTS:
1. Return ONLY valid JSON - no markdown, no code blocks, no explanation
2. Each card category must be an array of STRINGS (card names only)
3. Do NOT include card objects with "name", "set", or "collector_number" fields
4. Do NOT use nested structures like "mainboard" or "sideboard"
5. Start with { and end with } - nothing else

REQUIRED JSON STRUCTURE (use EXACTLY this format):
{
  "commander": ["Commander Name"],
  "creatures": ["Card Name", "Card Name", ...],
  "instants": ["Card Name", ...],
  "sorceries": ["Card Name", ...],
  "artifacts": ["Card Name", ...],
  "enchantments": ["Card Name", ...],
  "planeswalkers": ["Card Name", ...],
  "lands": ["Card Name", ...],
  "description": "Brief deck description",
  "strategy": "How to pilot the deck",
  "keyCards": ["Card 1", "Card 2", "Card 3"]
}

IMPORTANT: Use simple string arrays for all card lists. Example:
CORRECT: "creatures": ["Sol Ring", "Birds of Paradise", "Llanowar Elves"]
WRONG: "creatures": [{"name": "Sol Ring", "set": "LTR"}]

Start your response with { and end with } - nothing else!`;

  // Build the user prompt
  let prompt = `Build a Commander deck with these specifications:

REQUIREMENTS:
- Theme/Archetype: ${theme}
- Color Identity: ${colors.length > 0 ? colors.join(', ') : 'Any colors'}
- Power Level: Bracket ${powerLevel} (Moxfield scale)
${commander ? `- Commander: ${commander}` : '- Commander: Choose the best commander for this theme and colors'}
${useCollectionOnly ? '- IMPORTANT: Only use cards from the provided collection below' : '- Use any cards from Magic: The Gathering history'}

`;

  if (useCollectionOnly && userCollection) {
    prompt += `
MY CARD COLLECTION:
---
${userCollection}

BASIC LANDS (Always Available - No Limit in Commander):
- Forest (unlimited)
- Island (unlimited)
- Mountain (unlimited)
- Plains (unlimited)
- Swamp (unlimited)
- Wastes (unlimited)
---

BUILD RULES:
- You MUST use only cards from the collection above
- Basic lands (Forest, Island, Mountain, Plains, Swamp, Wastes) are ALWAYS available regardless of collection
- You can use as many basic lands as needed for the mana base
- If the collection is insufficient for non-land cards, include a note in the description
- Prioritize the best cards available in the collection for this theme
`;
  } else {
    prompt += `
BUILD RULES:
- Use the most popular and effective cards for this theme (reference EDHREC, MTGTop8, Moxfield)
- Include staples appropriate for the power level
- Build a cohesive strategy with strong synergies
`;
  }

  prompt += `
ADDITIONAL CONTEXT:
- Consider popular commanders and strategies from EDHREC for ${theme} decks
- Include combos and synergies commonly seen on MTGTop8 and competitive lists
- Ensure the power level matches Bracket ${powerLevel} on the Moxfield scale
- Balance threats, answers, ramp, and card draw appropriately

Build the deck now and return valid JSON only.`;

  console.log('Prompt length:', prompt.length);
  console.log('Prompt preview (first 500 chars):', prompt.substring(0, 500));
  console.log('Generation config:', JSON.stringify(generationConfig));

  try {
    console.log('Calling Gemini API...');
    const result = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig,
      safetySettings,
    });
    console.log('Gemini API call completed');

    const response = result.response;
    
    // Detailed response debugging
    console.log('Gemini response object:', JSON.stringify({
      candidates: result.response.candidates?.length,
      promptFeedback: result.response.promptFeedback,
      usageMetadata: result.response.usageMetadata,
    }));
    
    // Check if response was blocked
    if (result.response.promptFeedback?.blockReason) {
      console.error('Prompt was blocked:', result.response.promptFeedback);
      throw new Error(`AI prompt was blocked: ${result.response.promptFeedback.blockReason}. Try different parameters.`);
    }
    
    if (!response || !response.text) {
      console.error('Gemini response blocked or empty:', response);
      console.error('Full result:', JSON.stringify(result, null, 2));
      throw new Error('AI response was blocked or empty. Please try different parameters.');
    }

    const jsonText = response.text();
    console.log('Raw Gemini response length:', jsonText.length);
    console.log('Raw Gemini response preview:', jsonText.substring(0, 200));
    console.log('Raw Gemini response end:', jsonText.substring(Math.max(0, jsonText.length - 200)));
    
    // Try to parse JSON, handle potential code blocks
    let cleanedJson = jsonText.trim();
    if (cleanedJson.startsWith('```json')) {
      cleanedJson = cleanedJson.replace(/```json\n?/g, '').replace(/```\n?$/g, '');
    } else if (cleanedJson.startsWith('```')) {
      cleanedJson = cleanedJson.replace(/```\n?/g, '').replace(/```\n?$/g, '');
    }
    
    let decklist: DeckBuildResponse = JSON.parse(cleanedJson);

    // Helper function to convert card objects to string arrays
    const normalizeCardArray = (cards: any): string[] => {
      if (!cards) return [];
      if (!Array.isArray(cards)) return [];
      
      return cards.map((card: any) => {
        // If it's already a string, return as-is
        if (typeof card === 'string') return card;
        // If it's an object with a "name" field, extract the name
        if (card && typeof card === 'object' && card.name) return card.name;
        // Otherwise try to stringify it
        return String(card);
      });
    };

    // Handle nested structure (some responses have "mainboard" wrapper)
    if ((decklist as any).mainboard) {
      console.log('Detected nested mainboard structure, flattening...');
      const mainboard = (decklist as any).mainboard;
      decklist = {
        commander: normalizeCardArray((decklist as any).commander),
        creatures: normalizeCardArray(mainboard.creatures),
        instants: normalizeCardArray(mainboard.instants),
        sorceries: normalizeCardArray(mainboard.sorceries),
        artifacts: normalizeCardArray(mainboard.artifacts),
        enchantments: normalizeCardArray(mainboard.enchantments),
        planeswalkers: normalizeCardArray(mainboard.planeswalkers),
        lands: normalizeCardArray(mainboard.lands),
        description: (decklist as any).description || '',
        strategy: (decklist as any).strategy || '',
        keyCards: normalizeCardArray((decklist as any).keyCards),
      };
    } else {
      // Normalize all card arrays even if not nested
      decklist.commander = normalizeCardArray(decklist.commander);
      decklist.creatures = normalizeCardArray(decklist.creatures);
      decklist.instants = normalizeCardArray(decklist.instants);
      decklist.sorceries = normalizeCardArray(decklist.sorceries);
      decklist.artifacts = normalizeCardArray(decklist.artifacts);
      decklist.enchantments = normalizeCardArray(decklist.enchantments);
      decklist.planeswalkers = normalizeCardArray(decklist.planeswalkers);
      decklist.lands = normalizeCardArray(decklist.lands);
      decklist.keyCards = normalizeCardArray(decklist.keyCards);
    }

    // Ensure all card category properties are arrays (backup validation)
    decklist.commander = Array.isArray(decklist.commander) 
      ? decklist.commander 
      : typeof decklist.commander === 'string'
      ? [decklist.commander]
      : [];
    decklist.creatures = Array.isArray(decklist.creatures) ? decklist.creatures : [];
    decklist.instants = Array.isArray(decklist.instants) ? decklist.instants : [];
    decklist.sorceries = Array.isArray(decklist.sorceries) ? decklist.sorceries : [];
    decklist.artifacts = Array.isArray(decklist.artifacts) ? decklist.artifacts : [];
    decklist.enchantments = Array.isArray(decklist.enchantments) ? decklist.enchantments : [];
    decklist.planeswalkers = Array.isArray(decklist.planeswalkers) ? decklist.planeswalkers : [];
    decklist.lands = Array.isArray(decklist.lands) ? decklist.lands : [];

    // Validation
    const totalCards = 
      (decklist.commander?.length || 0) +
      (decklist.creatures?.length || 0) +
      (decklist.instants?.length || 0) +
      (decklist.sorceries?.length || 0) +
      (decklist.artifacts?.length || 0) +
      (decklist.enchantments?.length || 0) +
      (decklist.planeswalkers?.length || 0) +
      (decklist.lands?.length || 0);

    console.log(`Generated deck has ${totalCards} cards`);
    console.log('Deck breakdown:', {
      commander: decklist.commander?.length,
      creatures: decklist.creatures?.length,
      instants: decklist.instants?.length,
      sorceries: decklist.sorceries?.length,
      artifacts: decklist.artifacts?.length,
      enchantments: decklist.enchantments?.length,
      planeswalkers: decklist.planeswalkers?.length,
      lands: decklist.lands?.length,
    });

    if (totalCards !== 100) {
      throw new Error(
        `Generated deck has ${totalCards} cards but Commander format requires exactly 100 cards. ` +
        `Please try generating again - the AI needs to adjust the deck composition.`
      );
    }

    if (!decklist.commander || decklist.commander.length === 0) {
      throw new Error('Deck is missing a commander');
    }

    return decklist;
  } catch (error: any) {
    console.error('Error generating deck with Gemini:', error);
    
    // Provide more specific error messages
    if (error instanceof SyntaxError) {
      throw new Error('AI returned invalid data format. Please try again.');
    }
    
    if (error.message?.includes('API key')) {
      throw new Error('API configuration error. Please contact administrator.');
    }
    
    if (error.message?.includes('quota') || error.message?.includes('rate limit')) {
      throw new Error('AI service is temporarily unavailable. Please try again in a moment.');
    }
    
    throw new Error(error.message || 'Failed to generate deck. Please try again with different parameters.');
  }
}

/**
 * Get commander suggestions based on colors and theme
 */
export async function suggestCommanders(
  colors: string[],
  theme: string,
  powerLevel: string
): Promise<string[]> {
  const prompt = `Suggest 5 popular Commander options for a ${theme} deck in ${colors.join('/')} colors at power level ${powerLevel} (Moxfield bracket).

Reference popular commanders from EDHREC.com and competitive lists.

Return JSON array of commander names only:
["Commander Name 1", "Commander Name 2", ...]`;

  try {
    const result = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: { ...generationConfig, maxOutputTokens: 1024 },
      safetySettings,
    });

    const jsonText = result.response.text();
    return JSON.parse(jsonText);
  } catch (error) {
    console.error('Error getting commander suggestions:', error);
    return [];
  }
}

/**
 * Analyze a deck and provide improvement suggestions
 */
export async function analyzeDeck(
  decklist: DeckBuildResponse,
  targetPowerLevel: string
): Promise<{
  currentPowerLevel: string;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
}> {
  const decklistText = JSON.stringify(decklist, null, 2);

  const prompt = `Analyze this Commander deck and provide feedback:

${decklistText}

Target Power Level: Bracket ${targetPowerLevel}

Provide analysis in this JSON format:
{
  "currentPowerLevel": "Estimated bracket 1-5",
  "strengths": ["Strength 1", "Strength 2", ...],
  "weaknesses": ["Weakness 1", "Weakness 2", ...],
  "suggestions": ["Suggestion 1", "Suggestion 2", ...]
}`;

  try {
    const result = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: { ...generationConfig, maxOutputTokens: 2048 },
      safetySettings,
    });

    const jsonText = result.response.text();
    return JSON.parse(jsonText);
  } catch (error) {
    console.error('Error analyzing deck:', error);
    throw new Error('Failed to analyze deck');
  }
}
