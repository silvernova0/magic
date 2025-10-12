import { prisma } from '@/lib/prisma';
import { getCurrentUser } from '../../lib/user';
import { Deck } from '@prisma/client';
import Link from 'next/link';
import DecksClient from '@/components/decks/DecksClient';

async function getDecks(): Promise<Deck[]> {
  const user = await getCurrentUser();
  if (!user) {
    return [];
  }
  return prisma.deck.findMany({
    where: { userId: user.id },
    orderBy: {
      createdAt: 'desc',
    },
  });
}

export default async function DecksPage() {
  const user = await getCurrentUser();

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 flex items-center justify-center p-6">
        <div className="text-center">
          <div className="text-6xl mb-4">🔒</div>
          <h2 className="text-2xl font-bold text-purple-300 mb-4">Please Log In</h2>
          <Link
            href="/login"
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-medium hover:scale-105 transition-transform inline-block"
          >
            Go to Login
          </Link>
        </div>
      </div>
    );
  }

  const allDecks = await getDecks();

  return <DecksClient initialDecks={allDecks} />;
}
