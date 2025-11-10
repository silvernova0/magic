import { NextRequest, NextResponse } from 'next/server';
import { getCurrentUser } from '@/lib/user';
import { suggestCommanders } from '@/lib/gemini';

export async function POST(req: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'You must be logged in.' }, { status: 401 });
    }

    const { colors, theme, powerLevel } = await req.json();

    if (!theme || !powerLevel) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const suggestions = await suggestCommanders(colors || [], theme, powerLevel);

    return NextResponse.json({ suggestions });
  } catch (error: any) {
    console.error('Error getting commander suggestions:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to get suggestions' },
      { status: 500 }
    );
  }
}
