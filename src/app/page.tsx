import { prisma } from '../lib/prisma';
import { getCurrentUser } from '../lib/user';
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
import { Sparkles, Clock, Save, Zap } from 'lucide-react';

async function getDecks(): Promise<Deck[]> {
  const user = await getCurrentUser();
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
  <Card className="group hover:shadow-xl transition-all duration-300 hover:scale-[1.02] border-2 hover:border-purple-500/50">
    <CardHeader>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <CardTitle className="text-xl mb-2 group-hover:text-purple-600 transition-colors">
            {deck.name}
          </CardTitle>
          <CardDescription className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300 rounded-full text-xs font-medium">
              <Zap className="h-3 w-3" />
              {deck.theme}
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 rounded-full text-xs font-medium">
              {deck.powerLevel}
            </span>
          </CardDescription>
        </div>
        {deck.status === 'SAVED' && (
          <Save className="h-5 w-5 text-green-500" />
        )}
      </div>
    </CardHeader>
    <CardContent>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Clock className="h-4 w-4" />
        <span>Updated {new Date(deck.updatedAt).toLocaleDateString()}</span>
      </div>
    </CardContent>
  </Card>
);

const DeckList = ({ title, decks, icon, total }: { title: string, decks: Deck[], icon: React.ReactNode, total: number }) => (
  <div className="space-y-6">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        {icon}
        <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
          {title}
        </h2>
        <span className="text-2xl font-bold text-muted-foreground">
          ({total})
        </span>
      </div>
      {total > 12 && (
        <Button asChild variant="outline" size="sm">
          <Link href="/decks">View All {total} Decks</Link>
        </Button>
      )}
    </div>
    {decks.length > 0 ? (
      <>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {decks.map((deck) => (
            <DeckCard key={deck.id} deck={deck} />
          ))}
        </div>
        {total > 12 && (
          <div className="text-center pt-4">
            <p className="text-sm text-muted-foreground">
              Showing 12 of {total} decks
            </p>
          </div>
        )}
      </>
    ) : (
      <Card className="border-dashed border-2">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <p className="text-muted-foreground text-lg">No decks found in this category</p>
          <p className="text-sm text-muted-foreground mt-2">Start building to see decks here</p>
        </CardContent>
      </Card>
    )}
  </div>
);

export default async function Home() {
  const allDecks = await getDecks();
  const savedDecks = allDecks.filter((deck) => deck.status === DeckStatus.SAVED).slice(0, 12);
  const generatedDecks = allDecks.filter(
    (deck) => deck.status === DeckStatus.GENERATED
  ).slice(0, 12);
  const totalSaved = allDecks.filter((deck) => deck.status === DeckStatus.SAVED).length;
  const totalGenerated = allDecks.filter((deck) => deck.status === DeckStatus.GENERATED).length;

  return (
    <div className="container mx-auto max-w-7xl">
      {/* Hero Header */}
      <div className="mb-8 p-8 rounded-xl bg-gradient-to-br from-purple-500/10 via-indigo-500/10 to-blue-500/10 border border-purple-500/20">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 bg-clip-text text-transparent mb-2">
              🎴 JankBuild
            </h1>
            <p className="text-lg text-muted-foreground">
              AI-Powered Commander Deck Builder & Collection Manager
            </p>
          </div>
          <Button asChild size="lg" className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700">
            <Link href="/deckbuilder" className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              Build New Deck
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Saved Decks</p>
                <p className="text-3xl font-bold text-green-600 dark:text-green-400">{totalSaved}</p>
              </div>
              <Save className="h-12 w-12 text-green-600/50 dark:text-green-400/50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Generated Decks</p>
                <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">{totalGenerated}</p>
              </div>
              <Sparkles className="h-12 w-12 text-blue-600/50 dark:text-blue-400/50" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-purple-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Decks</p>
                <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">{allDecks.length}</p>
              </div>
              <Zap className="h-12 w-12 text-purple-600/50 dark:text-purple-400/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Deck Lists */}
      <div className="space-y-12">
        <DeckList 
          title="Saved Decks" 
          decks={savedDecks}
          total={totalSaved}
          icon={<Save className="h-8 w-8 text-green-600" />}
        />
        <DeckList 
          title="Generated Decks" 
          decks={generatedDecks}
          total={totalGenerated}
          icon={<Sparkles className="h-8 w-8 text-blue-600" />}
        />
      </div>
    </div>
  );
}