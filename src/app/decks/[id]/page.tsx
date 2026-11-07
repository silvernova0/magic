import { prisma } from '@/lib/prisma';
import { getCurrentUser } from '@/lib/user';
import { notFound, redirect } from 'next/navigation';
import DeckViewClient from '@/components/decks/DeckViewClient';

interface Props {
  params: {
    id: string;
  };
}

async function getDeck(id: string) {
  return prisma.deck.findUnique({
    where: { id },
    include: {
      user: {
        select: {
          id: true,
          name: true,
          email: true,
        },
      },
    },
  });
}

export default async function DeckViewPage({ params }: Props) {
  const user = await getCurrentUser();
  const deck = await getDeck(params.id);

  if (!deck) {
    notFound();
  }

  // Check if user owns this deck
  const isOwner = user?.id === deck.userId;

  if (!isOwner && !user) {
    // If not logged in and not owner, redirect to login
    redirect('/login');
  }

  return <DeckViewClient deck={deck} isOwner={isOwner} />;
}
