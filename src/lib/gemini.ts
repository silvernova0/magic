import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold, SchemaType } from '@google/generative-ai';
import { getScrapedData } from './scrapers';
import { formatScrapedDataForPrompt, getScraperSummary } from './scraperFormatter';
import { removeBannedCards, findBannedCards } from './bannedCards';

if (!process.env.GEMINI_API_KEY) {
  throw new Error('GEMINI_API_KEY environment variable not set');
}

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

// Using gemini-2.5-flash - latest Flash model
const model = genAI.getGenerativeModel({
  model: 'gemini-2.5-flash',
});

const generationConfig = {
  temperature: 0.9, // Higher temperature for more variety in card selection
  topP: 0.95,
  topK: 64,
  maxOutputTokens: 16384, // Increased to handle full response
  // Removed responseMimeType to allow free-form JSON that we'll parse manually
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
  referenceDecks?: any[]; // Reference decks from EDHREC/MTGTop8/Moxfield for this commander
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
    referenceDecks,
  } = request;

  // Fetch real-time meta data from scrapers
  console.log('Fetching real-time meta data from EDHREC, MTGTop8, and Moxfield...');
  let scrapedData;
  let metaContext = '';
  
  try {
    scrapedData = await getScrapedData();
    metaContext = formatScrapedDataForPrompt(scrapedData, theme, powerLevel);
    console.log('Scraped data loaded:', getScraperSummary(scrapedData));
  } catch (error) {
    console.warn('Failed to load scraped data, continuing without real-time meta:', error);
  }

  // Add reference decks if available
  if (referenceDecks && referenceDecks.length > 0) {
    metaContext += `\n\n=== REFERENCE DECKS FOR ${commander?.toUpperCase()} ===\n`;
    metaContext += `Found ${referenceDecks.length} popular decks featuring this commander:\n\n`;
    
    referenceDecks.slice(0, 5).forEach((deck: any, i: number) => {
      metaContext += `${i + 1}. ${deck.name} (${deck.source})\n`;
      metaContext += `   Power Level: Bracket ${deck.powerLevel || 'Unknown'}\n`;
      metaContext += `   Theme: ${deck.theme || 'Unknown'}\n`;
      
      if (deck.decklist) {
        try {
          const cardList = JSON.parse(deck.decklist);
          metaContext += `   Sample Cards: ${cardList.slice(0, 10).join(', ')}\n`;
        } catch {
          metaContext += `   Decklist available\n`;
        }
      }
      metaContext += '\n';
    });
    
    metaContext += 'Use these decks as inspiration for popular card choices and synergies.\n\n';
  }

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
7. Include 8-12 ramp sources (signets, land ramp, but avoid banned fast mana)
8. Include 8-10 card draw sources
9. Include 8-10 removal/interaction pieces
10. Build around commander's abilities and chosen theme
11. Reference popular cards from EDHREC for the commander/theme
12. VERIFY: Count all cards before returning - commander + creatures + instants + sorceries + artifacts + enchantments + planeswalkers + lands = 100
13. DO NOT include any banned cards (see list below)

BANNED CARDS - DO NOT INCLUDE THESE:
Mana Crypt, Jeweled Lotus, Dockside Extortionist, Black Lotus, Mox Emerald, Mox Jet, Mox Pearl, Mox Ruby, Mox Sapphire, Time Walk, Ancestral Recall, Tinker, Karakas, Griselbrand, Emrakul the Aeons Torn, Primeval Titan, Iona Shield of Emeria, Golos Tireless Pilgrim, Nadu Winged Wisdom, Hullbreacher, Leovold Emissary of Trest, Prophet of Kruphix, Paradox Engine, Library of Alexandria, Tolarian Academy, Rofellos Llanowar Emissary, Fastbond, Channel, Flash, Balance, Biorhythm, Limited Resources, Trade Secrets, Upheaval, and others. Use legal alternatives instead.

POPULAR STAPLES BY POWER LEVEL (all legal):
Bracket 1-2: Sol Ring, Command Tower, Arcane Signet, Cultivate, Swords to Plowshares, Thought Vessel
Bracket 3: Rhystic Study, Smothering Tithe, Cyclonic Rift, Demonic Tutor, Mana Drain, Sensei's Divining Top
Bracket 4-5: Force of Will, Gaea's Cradle, The One Ring, Chrome Mox, Fierce Guardianship, Deflecting Swat

OUTPUT FORMAT REQUIREMENTS - CRITICAL:
1. Return ONLY valid JSON starting with { and ending with }
2. Do NOT wrap in "deck" or any other object
3. Do NOT include markdown code blocks, explanations, or any text outside the JSON
4. Each card category MUST be an array of STRING card names
5. Do NOT use objects with "name" fields - ONLY plain strings

MANDATORY JSON STRUCTURE - COPY THIS EXACTLY:
{
  "commander": ["Commander Name Here"],
  "creatures": ["Creature 1", "Creature 2", "Creature 3", ...],
  "instants": ["Instant 1", "Instant 2", ...],
  "sorceries": ["Sorcery 1", "Sorcery 2", ...],
  "artifacts": ["Artifact 1", "Artifact 2", ...],
  "enchantments": ["Enchantment 1", "Enchantment 2", ...],
  "planeswalkers": ["Planeswalker 1", "Planeswalker 2", ...],
  "lands": ["Land 1", "Land 2", "Land 3", ...],
  "description": "Brief deck description",
  "strategy": "How to pilot the deck",
  "keyCards": ["Key Card 1", "Key Card 2", "Key Card 3"]
}

CRITICAL EXAMPLES:
✅ CORRECT: "creatures": ["Sol Ring", "Arcane Signet", "Command Tower"]
❌ WRONG: "creatures": [{"name": "Sol Ring"}, {"name": "Arcane Signet"}]
❌ WRONG: {"deck": {"creatures": [...]}}
❌ WRONG: Including "name", "color_identity", "power_level" fields at root

YOU MUST INCLUDE ALL 100 CARDS IN THE ARRAYS ABOVE. Count carefully!`;

  // Build the user prompt with real-time meta data
  let prompt = metaContext; // Start with real-time data
  
  prompt += `Build a Commander deck with these specifications:

REQUIREMENTS:
- Theme/Archetype: ${theme}
- Color Identity: ${colors.length > 0 ? colors.join(', ') : 'Any colors'}
- Power Level: Bracket ${powerLevel} (Moxfield scale)
${commander ? `- Commander: ${commander}` : '- Commander: Choose the best commander for this theme and colors'}
${useCollectionOnly ? '- IMPORTANT: Only use cards from the provided collection below' : '- Use any cards from Magic: The Gathering history'}

CRITICAL COLOR IDENTITY RULES:
${commander ? `- The commander is ${commander}. You MUST determine its color identity first.` : ''}
- EVERY card in the deck (creatures, instants, sorceries, artifacts, enchantments, planeswalkers, AND lands) MUST match the commander's color identity.
- Color identity includes mana symbols in the card's mana cost AND text box.
- Example: If commander is mono-red (R), you can ONLY use red and colorless cards. NO blue, white, black, or green cards.
- Example: If commander is Azorius (W/U), you can ONLY use white, blue, and colorless cards. NO red, black, or green cards.
- Lands with color symbols in their text (like Tropical Island, Breeding Pool) count as that color and cannot be used outside that identity.
- Colorless lands (Wastes, Command Tower, Reliquary Tower) can be used in any deck.
- Basic lands (Forest, Island, Mountain, Plains, Swamp) can only be used if that color is in the commander's identity.

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

FINAL REMINDER - THIS IS CRITICAL:
You MUST return a JSON object with arrays containing EXACTLY 100 card names total (no more, no less).
Count: 1 commander + creatures + instants + sorceries + artifacts + enchantments + planeswalkers + lands = MUST EQUAL 100.
Do NOT return 99, 101, 102, 103, 104, 105, or any number other than 100.
Do NOT return deck metadata like "deck_name", "color_identity", "power_level", "theme".
Do NOT provide explanations, suggestions, or strategy tips as separate fields.
ONLY return the exact structure with card name arrays as specified above.
ALL cards must match the commander's color identity - check every single card before including it.

Example of what you MUST return (with real card names, not placeholders):
{
  "commander": ["Atraxa, Praetors' Voice"],
  "creatures": ["Seedborn Muse", "Eternal Witness", "Birds of Paradise", ...30 more creatures...],
  "instants": ["Counterspell", "Path to Exile", "Swords to Plowshares", ...7 more instants...],
  "sorceries": ["Kodama's Reach", "Cultivate", "Diabolic Tutor", ...7 more sorceries...],
  "artifacts": ["Sol Ring", "Arcane Signet", "Commander's Sphere", ...12 more artifacts...],
  "enchantments": ["Rhystic Study", "Smothering Tithe", ...8 more enchantments...],
  "planeswalkers": ["Teferi, Hero of Dominaria", "Jace, the Mind Sculptor"],
  "lands": ["Command Tower", "Exotic Orchard", "Forest", "Island", ...32 more lands...],
  "description": "Brief strategy description here",
  "strategy": "How to pilot this deck",
  "keyCards": ["Key Card 1", "Key Card 2", "Key Card 3"]
}

COUNT YOUR CARDS: 1 + 33 + 10 + 10 + 15 + 10 + 2 + 36 = 117 (TOO MANY - adjust the numbers to equal exactly 100!)

Now build the deck and return ONLY the JSON with card lists. COUNT CAREFULLY to ensure exactly 100 cards total.`;

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
    
    let parsed = JSON.parse(cleanedJson);
    
    // Handle "deck" wrapper that Gemini sometimes adds
    if (parsed.deck && typeof parsed.deck === 'object') {
      console.log('Detected "deck" wrapper, unwrapping...');
      parsed = parsed.deck;
    }
    
    // Validate that we have the expected structure
    if (!parsed.commander && !parsed.creatures && !parsed.lands) {
      console.error('Invalid response structure:', parsed);
      throw new Error(
        'AI returned invalid format. Expected arrays of card names but got: ' +
        Object.keys(parsed).join(', ') +
        '. Please try again.'
      );
    }
    
    let decklist: DeckBuildResponse = parsed;

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

    // Validation and auto-correction
    let totalCards = 
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

    // Auto-correct if not exactly 100 cards
    if (totalCards > 100) {
      console.log(`Deck has ${totalCards} cards, trimming to 100...`);
      const excess = totalCards - 100;
      
      // Remove excess from the largest non-essential categories first
      let remaining = excess;
      
      // 1. Try removing from creatures if we have many
      if (remaining > 0 && decklist.creatures && decklist.creatures.length > 25) {
        const toRemove = Math.min(remaining, decklist.creatures.length - 25);
        decklist.creatures = decklist.creatures.slice(0, decklist.creatures.length - toRemove);
        remaining -= toRemove;
        console.log(`Removed ${toRemove} creatures`);
      }
      
      // 2. Try removing from lands if we have many
      if (remaining > 0 && decklist.lands && decklist.lands.length > 35) {
        const toRemove = Math.min(remaining, decklist.lands.length - 35);
        decklist.lands = decklist.lands.slice(0, decklist.lands.length - toRemove);
        remaining -= toRemove;
        console.log(`Removed ${toRemove} lands`);
      }
      
      // 3. Remove from artifacts if needed
      if (remaining > 0 && decklist.artifacts && decklist.artifacts.length > 0) {
        const toRemove = Math.min(remaining, decklist.artifacts.length);
        decklist.artifacts = decklist.artifacts.slice(0, decklist.artifacts.length - toRemove);
        remaining -= toRemove;
        console.log(`Removed ${toRemove} artifacts`);
      }
      
      // 4. Last resort: remove from any remaining category
      if (remaining > 0) {
        const categories = [
          { name: 'instants', array: decklist.instants },
          { name: 'sorceries', array: decklist.sorceries },
          { name: 'enchantments', array: decklist.enchantments },
          { name: 'planeswalkers', array: decklist.planeswalkers },
        ];
        
        for (const cat of categories) {
          if (remaining > 0 && cat.array && cat.array.length > 0) {
            const toRemove = Math.min(remaining, cat.array.length);
            (decklist as any)[cat.name] = cat.array.slice(0, cat.array.length - toRemove);
            remaining -= toRemove;
            console.log(`Removed ${toRemove} ${cat.name}`);
          }
        }
      }
      
      totalCards = 100;
    } else if (totalCards < 100) {
      console.log(`Deck has ${totalCards} cards, adding basic lands to reach 100...`);
      // Add basic Plains (or appropriate basic land) to reach 100
      const needed = 100 - totalCards;
      const basicsToAdd = Array(needed).fill('Plains');
      decklist.lands = [...(decklist.lands || []), ...basicsToAdd];
      console.log(`Added ${needed} Plains to reach 100 cards`);
      totalCards = 100;
    }

    if (totalCards !== 100) {
      throw new Error(
        `Generated deck has ${totalCards} cards but Commander format requires exactly 100 cards. ` +
        `Please try generating again - the AI needs to adjust the deck composition.`
      );
    }

    // Check for and remove banned cards
    const allCards = [
      ...(decklist.commander || []),
      ...(decklist.creatures || []),
      ...(decklist.instants || []),
      ...(decklist.sorceries || []),
      ...(decklist.artifacts || []),
      ...(decklist.enchantments || []),
      ...(decklist.planeswalkers || []),
      ...(decklist.lands || []),
    ];
    
    const bannedFound = findBannedCards(allCards);
    
    if (bannedFound.length > 0) {
      console.log(`Found ${bannedFound.length} banned cards, removing:`, bannedFound);
      
      // Remove banned cards from each category
      decklist.commander = removeBannedCards(decklist.commander || []);
      decklist.creatures = removeBannedCards(decklist.creatures || []);
      decklist.instants = removeBannedCards(decklist.instants || []);
      decklist.sorceries = removeBannedCards(decklist.sorceries || []);
      decklist.artifacts = removeBannedCards(decklist.artifacts || []);
      decklist.enchantments = removeBannedCards(decklist.enchantments || []);
      decklist.planeswalkers = removeBannedCards(decklist.planeswalkers || []);
      decklist.lands = removeBannedCards(decklist.lands || []);
      
      // Recalculate total and add basic lands to compensate
      const newTotal = 
        (decklist.commander?.length || 0) +
        (decklist.creatures?.length || 0) +
        (decklist.instants?.length || 0) +
        (decklist.sorceries?.length || 0) +
        (decklist.artifacts?.length || 0) +
        (decklist.enchantments?.length || 0) +
        (decklist.planeswalkers?.length || 0) +
        (decklist.lands?.length || 0);
      
      if (newTotal < 100) {
        const needed = 100 - newTotal;
        const basicsToAdd = Array(needed).fill('Plains');
        decklist.lands = [...(decklist.lands || []), ...basicsToAdd];
        console.log(`Added ${needed} Plains to replace banned cards and reach 100 cards`);
      }
      
      // Add warning to description
      const bannedList = bannedFound.join(', ');
      if (decklist.description) {
        decklist.description += `\n\nNote: Removed banned cards (${bannedList}) and replaced with basic lands.`;
      } else {
        decklist.description = `Note: Removed banned cards (${bannedList}) and replaced with basic lands.`;
      }
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
