/**
 * Multi-source MTG Card Data Service
 * Integrates: Scryfall, MTG API, MTGJSON, and MTGPics
 */

// Card data from multiple sources
export interface CardData {
  // Basic info
  name: string;
  manaCost: string;
  cmc: number;
  colors: string[];
  colorIdentity: string[];

  // Type info
  typeLine: string;
  types: string[];
  subtypes: string[];
  supertypes: string[];

  // Card text
  oracleText?: string;
  flavorText?: string;

  // Stats
  power?: string;
  toughness?: string;
  loyalty?: string;

  // Set info
  setCode: string;
  setName: string;
  rarity: string;
  collectorNumber?: string;

  // Images from multiple sources
  images: {
    scryfall?: {
      small: string;
      normal: string;
      large: string;
      artCrop: string;
      borderCrop: string;
    };
    mtgpics?: string;
    gatherer?: string;
  };

  // Pricing (from Scryfall)
  prices?: {
    usd?: string;
    usdFoil?: string;
    eur?: string;
    tix?: string;
  };

  // Legality
  legalities?: {
    standard?: string;
    pioneer?: string;
    modern?: string;
    legacy?: string;
    vintage?: string;
    commander?: string;
    pauper?: string;
  };

  // Metadata
  scryfallId?: string;
  oracleId?: string;
  mtgApiId?: string;
  multiverseId?: number;
}

/**
 * Scryfall API - Primary source (best data quality)
 * Docs: https://scryfall.com/docs/api
 */
export async function fetchFromScryfall(cardName: string, set?: string): Promise<CardData | null> {
  try {
    let url = `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(cardName)}`;
    if (set) {
      url += `&set=${encodeURIComponent(set)}`;
    }

    const response = await fetch(url);
    if (!response.ok) return null;

    const data = await response.json();

    return {
      name: data.name,
      manaCost: data.mana_cost || '',
      cmc: data.cmc || 0,
      colors: data.colors || [],
      colorIdentity: data.color_identity || [],
      typeLine: data.type_line || '',
      types: data.type_line?.split('—')[0]?.trim().split(' ') || [],
      subtypes: data.type_line?.split('—')[1]?.trim().split(' ') || [],
      supertypes: [],
      oracleText: data.oracle_text,
      flavorText: data.flavor_text,
      power: data.power,
      toughness: data.toughness,
      loyalty: data.loyalty,
      setCode: data.set,
      setName: data.set_name,
      rarity: data.rarity,
      collectorNumber: data.collector_number,
      images: {
        scryfall: {
          small: data.image_uris?.small || data.card_faces?.[0]?.image_uris?.small || '',
          normal: data.image_uris?.normal || data.card_faces?.[0]?.image_uris?.normal || '',
          large: data.image_uris?.large || data.card_faces?.[0]?.image_uris?.large || '',
          artCrop: data.image_uris?.art_crop || data.card_faces?.[0]?.image_uris?.art_crop || '',
          borderCrop: data.image_uris?.border_crop || data.card_faces?.[0]?.image_uris?.border_crop || '',
        },
      },
      prices: data.prices,
      legalities: data.legalities,
      scryfallId: data.id,
      oracleId: data.oracle_id,
      multiverseId: data.multiverse_ids?.[0],
    };
  } catch (error) {
    console.error('Scryfall fetch error:', error);
    return null;
  }
}

/**
 * MTG API - Fallback source
 * Docs: https://docs.magicthegathering.io/
 */
export async function fetchFromMTGApi(cardName: string, set?: string): Promise<CardData | null> {
  try {
    let url = `https://api.magicthegathering.io/v1/cards?name=${encodeURIComponent(cardName)}`;
    if (set) {
      url += `&set=${encodeURIComponent(set)}`;
    }

    const response = await fetch(url);
    if (!response.ok) return null;

    const data = await response.json();
    if (!data.cards || data.cards.length === 0) return null;

    const card = data.cards[0];

    return {
      name: card.name,
      manaCost: card.manaCost || '',
      cmc: card.cmc || 0,
      colors: card.colors || [],
      colorIdentity: card.colorIdentity || [],
      typeLine: card.type || '',
      types: card.types || [],
      subtypes: card.subtypes || [],
      supertypes: card.supertypes || [],
      oracleText: card.text,
      flavorText: card.flavor,
      power: card.power,
      toughness: card.toughness,
      loyalty: card.loyalty,
      setCode: card.set || '',
      setName: card.setName || '',
      rarity: card.rarity || '',
      collectorNumber: card.number,
      images: {
        gatherer: card.imageUrl,
      },
      legalities: card.legalities,
      mtgApiId: card.id,
      multiverseId: card.multiverseId,
    };
  } catch (error) {
    console.error('MTG API fetch error:', error);
    return null;
  }
}

/**
 * MTGPics - Image source
 * Docs: https://mtgpics.com/
 */
export function getMTGPicsUrl(cardName: string, set?: string): string {
  const encodedName = encodeURIComponent(cardName);
  if (set) {
    return `https://mtgpics.com/card?ref=${encodedName}&set=${set}`;
  }
  return `https://mtgpics.com/card?ref=${encodedName}`;
}

/**
 * Search cards with autocomplete
 */
export async function getCardSuggestions(query: string): Promise<string[]> {
  if (!query || query.length < 2) {
    return [];
  }

  try {
    // Use local autocomplete API instead of Scryfall
    const response = await fetch(
      `/api/cards/autocomplete?q=${encodeURIComponent(query)}`
    );

    if (!response.ok) {
      console.error('Autocomplete failed:', response.statusText);
      return [];
    }

    const data = await response.json();
    return data.data || [];
  } catch (error) {
    console.error('Error fetching card suggestions:', error);
    return [];
  }
}

/**
 * Get card with data from multiple sources (best quality first)
 */
export async function getCardData(cardName: string, set?: string): Promise<CardData | null> {
  // Try Scryfall first (best data quality)
  let cardData = await fetchFromScryfall(cardName, set);

  if (cardData) {
    // Enhance with MTGPics image
    cardData.images.mtgpics = getMTGPicsUrl(cardName, set);
    return cardData;
  }

  // Fallback to MTG API
  cardData = await fetchFromMTGApi(cardName, set);

  if (cardData) {
    cardData.images.mtgpics = getMTGPicsUrl(cardName, set);
    return cardData;
  }

  return null;
}

/**
 * Batch fetch cards (with rate limiting)
 */
export async function batchFetchCards(
  cardNames: string[],
  delayMs: number = 100
): Promise<Map<string, CardData>> {
  const results = new Map<string, CardData>();

  for (const name of cardNames) {
    const data = await getCardData(name);
    if (data) {
      results.set(name, data);
    }
    // Rate limiting
    await new Promise(resolve => setTimeout(resolve, delayMs));
  }

  return results;
}

/**
 * Get random card (for testing)
 */
export async function getRandomCard(): Promise<CardData | null> {
  try {
    const response = await fetch('https://api.scryfall.com/cards/random');
    if (!response.ok) return null;

    const data = await response.json();
    return fetchFromScryfall(data.name);
  } catch (error) {
    console.error('Random card fetch error:', error);
    return null;
  }
}

/**
 * Get card by Scryfall ID
 */
export async function getCardById(scryfallId: string): Promise<CardData | null> {
  try {
    const response = await fetch(`https://api.scryfall.com/cards/${scryfallId}`);
    if (!response.ok) return null;

    const data = await response.json();
    return fetchFromScryfall(data.name);
  } catch (error) {
    console.error('Card fetch by ID error:', error);
    return null;
  }
}

/**
 * Get all printings of a card
 */
export async function getCardPrintings(cardName: string): Promise<CardData[]> {
  try {
    const response = await fetch(
      `https://api.scryfall.com/cards/search?q=!"${encodeURIComponent(cardName)}"`
    );

    if (!response.ok) return [];

    const data = await response.json();
    const printings: CardData[] = [];

    for (const card of data.data) {
      const cardData = await fetchFromScryfall(card.name, card.set);
      if (cardData) {
        printings.push(cardData);
      }
    }

    return printings;
  } catch (error) {
    console.error('Card printings fetch error:', error);
    return [];
  }
}
