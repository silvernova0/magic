import { NextResponse } from 'next/server';

// Temporarily simplified - avoiding fetch calls that trigger File global issue
export async function POST(req: Request) {
  try {
    const { query } = await req.json();
    if (!query) return NextResponse.json({ error: 'Missing query' }, { status: 400 });

    // Return empty results for now - autocomplete still works via /api/cards/search
    // EDHREC and Scryfall integration disabled due to Next.js 15 + undici File global bug
    return NextResponse.json({ 
      query, 
      links: [], 
      scry: [],
      message: 'EDHREC/Scryfall integration temporarily disabled. Use autocomplete to find commanders.'
    });
  } catch (err) {
    console.error('Commander search error:', err);
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
