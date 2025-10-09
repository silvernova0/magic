import { prisma } from '../lib/prisma';
import { getDefaultUser } from '../lib/user';
import { Deck, DeckStatus } from '@prisma/client';
import Link from 'next/link';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';

async function getDecks(): Promise<Deck[]> {
  const user = await getDefaultUser();
  if (!user) {
    return [];
  }
  return prisma.deck.findMany({
    where: { userId: user.id },
    orderBy: {
      updatedAt: 'desc',
    },
  });
}

const DeckCard = ({ deck }: { deck: Deck }) => (
  <Card>
    <CardHeader>
      <CardTitle>{deck.name}</CardTitle>
      <CardDescription>
        Theme: {deck.theme} | Power: {deck.powerLevel}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <p className="text-sm text-gray-500">
        Last updated: {new Date(deck.updatedAt).toLocaleDateString()}
      </p>
    </CardContent>
  </Card>
);

const DeckList = ({ title, decks }: { title: string, decks: Deck[] }) => (
  <div>
    <h2 className="text-3xl font-bold mb-4">{title}</h2>
    {decks.length > 0 ? (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {decks.map((deck) => (
          <DeckCard key={deck.id} deck={deck} />
        ))}
      </div>
    ) : (
      <p className="text-gray-500">No decks found.</p>
    )}
  </div>
);

export default async function Home() {
  const allDecks = await getDecks();
  const savedDecks = allDecks.filter((deck) => deck.status === DeckStatus.SAVED);
  const generatedDecks = allDecks.filter(
    (deck) => deck.status === DeckStatus.GENERATED
  );

  return (
    <main className="container mx-auto p-4 sm:p-6 lg:p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold">Your Deck Library</h1>
        <Button asChild>
          <Link href="/deckbuilder">Build a New Deck</Link>
        </Button>
      </div>

      <div className="space-y-12">
        <DeckList title="Saved Decks" decks={savedDecks} />
        <DeckList title="Generated Decks" decks={generatedDecks} />
      </div>
    </main>
  );
}