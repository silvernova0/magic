/**
 * Local Model Integration - Gemma 3 4B Commander Deck Builder
 * Connects to FastAPI server running on localhost:8000
 */

export interface LocalModelRequest {
  commander?: string;
  theme: string;
  colors: string[];
  powerLevel: string; // "1"-"5" (Moxfield brackets)
  useCollectionOnly?: boolean;
  userCollection?: string;
}

export interface LocalModelResponse {
  commander: string;
  strategy: string;
  power_level: number;
  bracket: number;
  card_selection: {
    [category: string]: {
      count: number;
      filters: Array<{
        types?: string[];
        subtypes?: string[];
        tags?: string[];
        cmc_max?: number;
        cmc_min?: number;
        instant_speed?: boolean;
        colors_within?: string[];
        reason?: string;
      }>;
    };
  };
  priority_cards?: string[];
}

export interface DeckCard {
  name: string;
  category: string;
  cmc: number;
  type: string;
  colorIdentity?: string[];
}

export interface ExecutedDeck {
  commander: string;
  commanders: DeckCard[];
  mainboard: DeckCard[];
  total_cards: number;
}

/**
 * Check if local model API is available
 */
export async function checkLocalModelStatus(): Promise<boolean> {
  try {
    const response = await fetch('http://localhost:8000/health', {
      method: 'GET',
      signal: AbortSignal.timeout(2000), // 2 second timeout
    });
    return response.ok;
  } catch (error) {
    return false;
  }
}

/**
 * Generate deck structure using local Gemma 3 4B model
 * Returns the structured JSON that can be passed to the database executor
 */
export async function generateDeckWithLocalModel(
  request: LocalModelRequest
): Promise<LocalModelResponse> {
  const response = await fetch('http://localhost:8000/api/deck/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
    signal: AbortSignal.timeout(120000), // 2 minute timeout for model generation
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(
      `Local model API error: ${error.detail || response.statusText}`
    );
  }

  return response.json();
}

/**
 * Build Commander deck using local model
 * Note: This only generates the structure. For full 100-card deck,
 * the structure needs to be processed by execute-deck-structure.ts
 * via Next.js API route that calls the TypeScript executor.
 */
export async function buildDeckWithLocalModel(
  request: LocalModelRequest
): Promise<{
  structure: LocalModelResponse;
  generationTime: number;
}> {
  const startGen = Date.now();
  
  // Generate deck structure with AI
  const structure = await generateDeckWithLocalModel(request);
  const generationTime = Date.now() - startGen;

  return {
    structure,
    generationTime,
  };
}

/**
 * Convert executed deck to display format
 */
export function formatDeckForDisplay(deck: ExecutedDeck): string {
  const lines: string[] = [];

  // Commander section
  lines.push('Commander:');
  for (const card of deck.commanders) {
    lines.push(`1x ${card.name}`);
  }
  lines.push('');

  // Group mainboard by category
  const categories = new Map<string, DeckCard[]>();
  for (const card of deck.mainboard) {
    const category = card.category || 'Other';
    if (!categories.has(category)) {
      categories.set(category, []);
    }
    categories.get(category)!.push(card);
  }

  // Output each category
  for (const [category, cards] of Array.from(categories.entries()).sort()) {
    const categoryName = category.charAt(0).toUpperCase() + category.slice(1);
    lines.push(`${categoryName} (${cards.length}):`);
    
    // Count duplicates
    const cardCounts = new Map<string, number>();
    for (const card of cards) {
      cardCounts.set(card.name, (cardCounts.get(card.name) || 0) + 1);
    }
    
    // Output sorted by name
    for (const [name, count] of Array.from(cardCounts.entries()).sort()) {
      lines.push(`${count}x ${name}`);
    }
    lines.push('');
  }

  return lines.join('\n');
}
