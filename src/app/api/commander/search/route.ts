import { NextResponse } from 'next/server';
import { fetchEdhrecCommanderPage, parseEdhrecCommanderPage } from '@/lib/edhrec';
import { searchScryfallCards } from '@/lib/scryfall';

export async function POST(req: Request) {
  try {
    const { query } = await req.json();
    if (!query) return NextResponse.json({ error: 'Missing query' }, { status: 400 });

    // Try EDHREC direct slug
    const edhHtml = await fetchEdhrecCommanderPage(query);
    const links = edhHtml ? parseEdhrecCommanderPage(edhHtml) : [];

    // Use Scryfall to get candidate names
    const scry = await searchScryfallCards(query, 12);

    return NextResponse.json({ query, links, scry });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
