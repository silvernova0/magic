// LM Studio OpenAI-compatible API
// Make sure LM Studio is running with local server enabled (default: http://127.0.0.1:1234)
const LM_STUDIO_BASE_URL = 'http://127.0.0.1:1234/v1';

interface DeckGenerationOptions {
  commander?: string;
  theme: string;
  colors: string[];
  powerLevel: number;
  budget?: string;
  excludeCards?: string;
  includeCards?: string;
  collection?: string;
  referenceDeck?: string;
}

interface ParsedDeck {
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
}

/**
 * Build a Commander deck using LM Studio (local AI with Intel Arc GPU support)
 */
export async function buildCommanderDeckWithOllama(
  options: DeckGenerationOptions,
  scrapedData: any
): Promise<ParsedDeck> {
  const prompt = buildPrompt(options, scrapedData);
  
  console.log('Calling LM Studio API (Intel Arc GPU accelerated)...');
  console.log('Prompt length:', prompt.length, 'characters');
  
  // JSON Schema for structured output
  const responseSchema = {
    type: "object",
    properties: {
      commander: {
        type: "array",
        items: { type: "string" },
        description: "Commander card name"
      },
      creatures: {
        type: "array",
        items: { type: "string" },
        description: "Creature cards in format: 1x Card Name"
      },
      instants: {
        type: "array",
        items: { type: "string" },
        description: "Instant cards in format: 1x Card Name"
      },
      sorceries: {
        type: "array",
        items: { type: "string" },
        description: "Sorcery cards in format: 1x Card Name"
      },
      artifacts: {
        type: "array",
        items: { type: "string" },
        description: "Artifact cards in format: 1x Card Name"
      },
      enchantments: {
        type: "array",
        items: { type: "string" },
        description: "Enchantment cards in format: 1x Card Name"
      },
      planeswalkers: {
        type: "array",
        items: { type: "string" },
        description: "Planeswalker cards in format: 1x Card Name"
      },
      lands: {
        type: "array",
        items: { type: "string" },
        description: "Land cards in format: 1x Card Name"
      },
      strategy: {
        type: "string",
        description: "Brief deck strategy description"
      }
    },
    required: ["commander", "creatures", "instants", "sorceries", "artifacts", "enchantments", "planeswalkers", "lands", "strategy"]
  };
  
  try {
    // Use OpenAI-compatible API from LM Studio
    const response = await fetch(`${LM_STUDIO_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'openai/gpt-oss-20b',
        messages: [
          {
            role: 'system',
            content: 'You are an expert Magic: The Gathering Commander/EDH deck builder. Generate complete 100-card decklists in the requested format.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.7,
        max_tokens: 16000, // High token limit for full deck
        stop: ["===END==="], // Custom stop sequence
        stream: false
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('LM Studio API error response:', errorText);
      throw new Error(`LM Studio API error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const data = await response.json();
    console.log('LM Studio response received');
    console.log('Response data:', JSON.stringify(data).substring(0, 500)); // Log first 500 chars
    
    // Check if response has expected structure
    if (!data.choices || !data.choices[0] || !data.choices[0].message) {
      console.error('Unexpected response structure:', data);
      throw new Error('Invalid response structure from LM Studio');
    }
    
    const messageContent = data.choices[0].message.content;
    console.log('Message content length:', messageContent.length);
    console.log('Message preview:', messageContent.substring(0, 300));
    
    // Parse text format instead of JSON
    const parsed = parseDecklistFromText(messageContent, options);
    
    console.log('Deck parsed successfully');
    console.log('Commander:', parsed.commander);
    console.log('Total creatures:', parsed.creatures.length);
    console.log('Total lands:', parsed.lands.length);
    
    return parsed;
  } catch (error: any) {
    console.error('Error generating deck with LM Studio:', error);
    throw new Error(`LM Studio error: ${error.message}`);
  }
}

/**
 * Build the prompt for deck generation
 */
function buildPrompt(options: DeckGenerationOptions, scrapedData: any): string {
  const { commander, theme, colors, powerLevel, budget, excludeCards, includeCards, collection, referenceDeck } = options;
  
  // Format color identity for strict checking
  const colorIdentityStr = colors.length > 0 
    ? colors.sort().join('') 
    : 'Colorless';
  
  let prompt = `You are an expert Magic: The Gathering Commander/EDH deck builder with deep knowledge of card synergies, metas, and strategies.

=== CRITICAL COLOR IDENTITY RULES ===
**COMMANDER COLOR IDENTITY: ${colorIdentityStr}**

YOU MUST FOLLOW THESE RULES STRICTLY:
1. EVERY card in the deck must have a color identity that is a SUBSET of [${colors.join(', ')}]
2. A card's color identity includes:
   - Mana cost colors
   - Color indicator colors
   - Colors in mana symbols in rules text (including activated abilities)
3. Examples for ${colorIdentityStr} deck:
   ${colors.includes('B') && colors.includes('G') 
     ? '✓ LEGAL: Golgari Signet (B/G), Overgrown Tomb (B/G), Assassin\'s Trophy (B/G)\n   ✗ ILLEGAL: Relic of Sauron (U/B/R), Nicol Bolas (U/B/R), anything with Red or Blue' 
     : '✓ Only use cards with mana symbols from: ' + colors.join(', ')}

=== DECK REQUIREMENTS ===
${commander ? `Commander: ${commander}` : `Commander: Suggest the best commander for this strategy`}
Theme/Strategy: ${theme}
Color Identity: ${colorIdentityStr} (${colors.join(' + ') || 'Any'})
Power Level: ${powerLevel}/10 (1=Casual, 5=Focused, 7=Optimized, 10=cEDH)
${budget ? `Budget: ${budget}` : 'Budget: No specific constraint'}

=== FORMAT REQUIREMENTS ===
- Total: 100 cards (1 Commander + 99 cards)
- Include 35-40 lands (basic lands + dual lands matching your colors ONLY)
- Include 8-12 ramp cards (Sol Ring, Arcane Signet, signets matching your colors)
- Include 8-10 card draw sources
- Include 5-8 removal spells
- Balance creatures, instants, sorceries, artifacts, and enchantments
- EVERY card must match the ${colorIdentityStr} color identity

`;

  // Add reference deck context if available
  if (referenceDeck) {
    prompt += `\n=== REFERENCE DECK ===
Use this as inspiration (but don't copy exactly):
${referenceDeck.substring(0, 2000)}
\n`;
  }

  // Add EDHREC/meta data (abbreviated)
  if (scrapedData?.edhrec?.length > 0) {
    const topCommanders = scrapedData.edhrec.slice(0, 10).map((c: any) => c.name).join(', ');
    prompt += `\n=== POPULAR COMMANDERS ===
${topCommanders}
\n`;
  }

  // Add collection constraint
  if (collection) {
    prompt += `\n=== COLLECTION CONSTRAINT ===
ONLY use cards from this list:
${collection.substring(0, 5000)}
\n`;
  }

  // Add card constraints
  if (includeCards) {
    prompt += `\n=== MUST INCLUDE ===
${includeCards}
\n`;
  }

  if (excludeCards) {
    prompt += `\n=== MUST EXCLUDE ===
${excludeCards}
\n`;
  }

  prompt += `
=== OUTPUT FORMAT (CRITICAL) ===
Generate the complete 100-card decklist in this EXACT format:

COMMANDER:
1x Card Name

CREATURES:
1x Card Name
1x Another Card
(continue until all creatures listed)

INSTANTS:
1x Card Name
(continue...)

SORCERIES:
1x Card Name
(continue...)

ARTIFACTS:
1x Card Name
(continue...)

ENCHANTMENTS:
1x Card Name
(continue...)

PLANESWALKERS:
1x Card Name
(continue...)

LANDS:
1x Card Name
(continue until you have 35-40 lands)

STRATEGY:
Brief 2-3 sentence description of how the deck wins.

===END===

CRITICAL REMINDERS:
- Generate ALL 100 cards (1 commander + 99 others)
- EVERY card must be legal in ${colorIdentityStr} color identity
- Include 35-40 lands that produce the correct colors
- Do NOT stop early - complete the entire decklist
- Use real Magic card names only
`;

  return prompt;
}

/**
 * Parse decklist from AI response text
 */
function parseDecklistFromText(text: string, options: DeckGenerationOptions): ParsedDeck {
  const lines = text.split('\n').map(line => line.trim()).filter(line => line);
  
  let commander = options.commander || '';
  const creatures: string[] = [];
  const instants: string[] = [];
  const sorceries: string[] = [];
  const artifacts: string[] = [];
  const enchantments: string[] = [];
  const planeswalkers: string[] = [];
  const lands: string[] = [];
  let strategy = '';
  let currentSection = '';
  
  // Extract commander
  const commanderMatch = text.match(/Commander:\s*\n\s*(\d+)x?\s*(.+)/i);
  if (commanderMatch) {
    commander = commanderMatch[2].trim();
  }
  
  // Extract cards by section
  const cardPattern = /^(\d+)x?\s+(.+)$/;
  
  for (const line of lines) {
    // Check for section headers
    if (line.match(/^Creatures/i)) currentSection = 'creatures';
    else if (line.match(/^Instants/i)) currentSection = 'instants';
    else if (line.match(/^Sorceries/i)) currentSection = 'sorceries';
    else if (line.match(/^Artifacts/i)) currentSection = 'artifacts';
    else if (line.match(/^Enchantments/i)) currentSection = 'enchantments';
    else if (line.match(/^Planeswalkers/i)) currentSection = 'planeswalkers';
    else if (line.match(/^Lands/i)) currentSection = 'lands';
    else if (line.match(/^Strategy:/i)) {
      const strategyMatch = line.match(/Strategy:\s*(.+)/i);
      if (strategyMatch) strategy = strategyMatch[1].trim();
      continue;
    }
    
    // Parse card line
    const match = line.match(cardPattern);
    if (match && currentSection) {
      const quantity = parseInt(match[1]);
      const name = match[2].trim();
      
      // Add card to appropriate section (repeat for quantity)
      const cardEntry = `${quantity}x ${name}`;
      
      switch (currentSection) {
        case 'creatures': creatures.push(cardEntry); break;
        case 'instants': instants.push(cardEntry); break;
        case 'sorceries': sorceries.push(cardEntry); break;
        case 'artifacts': artifacts.push(cardEntry); break;
        case 'enchantments': enchantments.push(cardEntry); break;
        case 'planeswalkers': planeswalkers.push(cardEntry); break;
        case 'lands': lands.push(cardEntry); break;
      }
    }
  }
  
  // Default strategy if not found
  if (!strategy) {
    strategy = `${options.theme} deck focused on ${options.colors.join('/')} color identity.`;
  }
  
  // Ensure we have cards
  const totalCards = creatures.length + instants.length + sorceries.length + 
                     artifacts.length + enchantments.length + planeswalkers.length + lands.length;
  
  if (totalCards === 0) {
    throw new Error('Failed to parse any cards from Ollama response');
  }
  
  return {
    commander: [commander],
    creatures,
    instants,
    sorceries,
    artifacts,
    enchantments,
    planeswalkers,
    lands,
    description: strategy,
    strategy
  };
}

/**
 * Check if LM Studio is available
 */
export async function isOllamaAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${LM_STUDIO_BASE_URL}/models`, {
      method: 'GET',
    });
    return response.ok;
  } catch (error) {
    return false;
  }
}
