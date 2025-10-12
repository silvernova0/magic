import { NextRequest, NextResponse } from 'next/server';
import { getCardData, searchCards, getCardPrintings } from '@/lib/cardData';

// GET /api/cards/lookup?name=Card+Name&set=SET
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const name = searchParams.get('name');
    const set = searchParams.get('set') || undefined;
    const action = searchParams.get('action') || 'lookup';

    if (!name) {
      return NextResponse.json({ error: 'Card name is required' }, { status: 400 });
    }

    switch (action) {
      case 'lookup':
        const cardData = await getCardData(name, set);
        if (!cardData) {
          return NextResponse.json({ error: 'Card not found' }, { status: 404 });
        }
        return NextResponse.json(cardData);

      case 'printings':
        const printings = await getCardPrintings(name);
        return NextResponse.json({ printings });

      case 'search':
        const results = await searchCards(name);
        return NextResponse.json({ results });

      default:
        return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
    }
  } catch (error: any) {
    console.error('Card lookup error:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to lookup card' },
      { status: 500 }
    );
  }
}
