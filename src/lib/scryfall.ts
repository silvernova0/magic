export type ScryfallCard = {
  name: string;
  mana_cost?: string;
  cmc?: number;
  colors?: string[];
  type_line?: string;
  oracle_text?: string;
  power?: string | null;
  toughness?: string | null;
  image_uri?: string | null;
  set_name?: string | null;
  set?: string | null;
  rarity?: string | null;
};

export async function fetchScryfallCard(name: string, setCode?: string): Promise<ScryfallCard | null> {
  try {
    const base = 'https://api.scryfall.com/cards/named';
    const params = new URLSearchParams();
    params.set('fuzzy', name);
    if (setCode) params.set('set', setCode);

    const url = `${base}?${params.toString()}`;
    const res = await fetch(url, { next: { revalidate: 0 } });
    if (!res.ok) return null;
    const data = await res.json();
    const image = data.image_uris?.normal || data.image_uris?.large || (data.card_faces?.[0]?.image_uris?.normal) || null;

    const out: ScryfallCard = {
      name: data.name,
      mana_cost: data.mana_cost || data.card_faces?.[0]?.mana_cost || '',
      cmc: Number(data.cmc || 0),
      colors: data.colors || data.card_faces?.[0]?.colors || [],
      type_line: data.type_line || data.card_faces?.[0]?.type_line || '',
      oracle_text: data.oracle_text || data.card_faces?.[0]?.oracle_text || '',
      power: data.power ?? data.card_faces?.[0]?.power ?? null,
      toughness: data.toughness ?? data.card_faces?.[0]?.toughness ?? null,
      image_uri: image,
      set_name: data.set_name || null,
      set: data.set || null,
      rarity: data.rarity || null,
    };

    return out;
  } catch (err) {
    return null;
  }
}

export async function searchScryfallCards(query: string, limit = 12): Promise<{ name: string; set?: string; set_name?: string }[]> {
  try {
    // Use Scryfall search endpoint; restrict to cards with the query in the name
    const q = `name:${query} lang:en`;
    const url = `https://api.scryfall.com/cards/search?q=${encodeURIComponent(q)}`;
    const res = await fetch(url, { next: { revalidate: 0 } });
    if (!res.ok) return [];
    const data = await res.json();
    const items = Array.isArray(data.data) ? data.data : [];
    const seen = new Set<string>();
    const out: { name: string; set?: string; set_name?: string }[] = [];
    for (const it of items) {
      if (out.length >= limit) break;
      const name = it.name as string;
      if (seen.has(name.toLowerCase())) continue;
      seen.add(name.toLowerCase());
      out.push({ name, set: it.set, set_name: it.set_name });
    }
    return out;
  } catch (err) {
    return [];
  }
}
