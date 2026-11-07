import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { getCurrentUser } from '@/lib/user';
import { analyzeLimitedPool } from '@/lib/limited';

export async function POST(req: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: 'You must be logged in to analyze a Limited pool.' }, { status: 401 });
    }

    const { poolText, saveDeck, selectedRank } = await req.json();

    if (!poolText || typeof poolText !== 'string' || !poolText.trim()) {
      return NextResponse.json({ error: 'Please provide a card pool to analyze.' }, { status: 400 });
    }

    const analysis = await analyzeLimitedPool(poolText);

    if (saveDeck && analysis.recommendations.length > 0) {
      const chosen =
        analysis.recommendations.find((r) => r.rank === Number(selectedRank)) ||
        analysis.recommendations[0];

      const saved = await prisma.deck.create({
        data: {
          name: `Limited (40) • ${chosen.archetypeTitle}`,
          description: chosen.summary,
          theme: `Limited — ${chosen.primarySynergies[0]?.tag || chosen.guildName}`,
          powerLevel: 'Limited (40-Card)',
          decklist: {
            commander: [],
            ...chosen.decklist,
            description: chosen.summary,
            strategy: chosen.summary,
          } as any,
          userId: user.id,
        },
      });

      return NextResponse.json({ analysis, savedDeckId: saved.id });
    }

    return NextResponse.json({ analysis });
  } catch (error: any) {
    console.error('Error analyzing Limited pool:', error);
    return NextResponse.json(
      { error: error?.message || 'Failed to analyze Limited pool' },
      { status: 500 }
    );
  }
}
