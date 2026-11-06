import { NextResponse } from 'next/server';
import { fetchEdhrecCommanderPage, parseEdhrecCommanderPage, fetchDeckFromUrl } from '@/lib/edhrec';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { source, query } = body;
    if (source !== 'edhrec') return NextResponse.json({ error: 'Unsupported source' }, { status: 400 });

    const html = await fetchEdhrecCommanderPage(query);
    if (!html) return NextResponse.json({ error: 'Commander page not found' }, { status: 404 });

    const links = parseEdhrecCommanderPage(html);
    const results = [] as any[];
    for (const link of links.slice(0, 6)) {
      const deck = await fetchDeckFromUrl(link);
      if (deck) results.push(deck);
    }

    return NextResponse.json({ commander: query, links, samples: results });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
