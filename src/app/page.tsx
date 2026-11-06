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
import {
  Sparkles,
  Clock,
  Save,
  Zap,
  Database,
  Flame,
  ArrowRight,
  Compass,
  Upload,
} from 'lucide-react';
import ScraperQuickBar from '@/components/ScraperQuickBar';

export const dynamic = 'force-dynamic';

async function getDashboardData() {
  const user = await getCurrentUser();
  const [decks, cardCount, commanderCount, synergyCount] = await Promise.all([
    user
      ? prisma.deck.findMany({
          where: { userId: user.id },
          orderBy: { updatedAt: 'desc' },
        })
      : Promise.resolve([]),
    prisma.card.count(),
    prisma.card.count({ where: { isCommander: true } }),
    prisma.cardSynergy.count(),
  ]);

  return { decks, cardCount, commanderCount, synergyCount };
}

const DeckCard = ({ deck }: { deck: Deck }) => (
  <Link href={`/decks/${deck.id}`} className="block">
    <Card className="group h-full bg-slate-900/70 border-slate-800 hover:border-purple-500/60 hover:shadow-xl hover:shadow-purple-950/30 transition-all duration-300 hover:-translate-y-1">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg font-bold text-white mb-2 group-hover:text-purple-400 transition-colors truncate">
              {deck.name}
            </CardTitle>
            <CardDescription className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-purple-950/80 border border-purple-500/30 text-purple-300 rounded-full text-xs font-medium">
                <Zap className="h-3 w-3" />
                {deck.theme}
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-blue-950/80 border border-blue-500/30 text-blue-300 rounded-full text-xs font-medium">
                {deck.powerLevel}
              </span>
            </CardDescription>
          </div>
          {deck.status === 'SAVED' && (
            <Save className="h-5 w-5 text-emerald-400 shrink-0" />
          )}
        </div>
      </CardHeader>
      <CardContent>
        {deck.description && (
          <p className="text-xs text-slate-400 line-clamp-2 mb-3">
            {deck.description}
          </p>
        )}
        <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-800/80">
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            Updated {new Date(deck.updatedAt).toLocaleDateString()}
          </span>
          <span className="text-purple-400 font-medium flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
            Open Deck <ArrowRight className="h-3 w-3" />
          </span>
        </div>
      </CardContent>
    </Card>
  </Link>
);

const DeckList = ({
  title,
  decks,
  icon,
}: {
  title: string;
  decks: Deck[];
  icon: React.ReactNode;
}) => (
  <div className="space-y-5">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        {icon}
        <h2 className="text-2xl font-bold text-white">{title}</h2>
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300">
          {decks.length}
        </span>
      </div>
      {decks.length > 0 && (
        <Link
          href="/decks"
          className="text-sm text-purple-400 hover:text-purple-300 flex items-center gap-1"
        >
          View all <ArrowRight className="h-4 w-4" />
        </Link>
      )}
    </div>
    {decks.length > 0 ? (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {decks.map((deck) => (
          <DeckCard key={deck.id} deck={deck} />
        ))}
      </div>
    ) : (
      <Card className="border-dashed border-slate-800 bg-slate-900/30">
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <p className="text-slate-300 font-medium text-base">
            No decks in this category yet
          </p>
          <p className="text-sm text-slate-500 mt-1 mb-4">
            Use the Local AI Deck Builder to brew a 100-card Commander list in seconds
          </p>
          <Button
            asChild
            size="sm"
            className="bg-purple-600 hover:bg-purple-500 text-white"
          >
            <Link href="/deckbuilder">Launch Deck Builder</Link>
          </Button>
        </CardContent>
      </Card>
    )}
  </div>
);

export default async function Home() {
  const { decks: allDecks, cardCount, commanderCount, synergyCount } =
    await getDashboardData();
  const savedDecks = allDecks.filter((deck) => deck.status === DeckStatus.SAVED);
  const generatedDecks = allDecks.filter(
    (deck) => deck.status === DeckStatus.GENERATED
  );

  return (
    <div className="container mx-auto max-w-7xl space-y-8">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-900/40 via-indigo-950/50 to-slate-900 border border-purple-500/30 p-8 shadow-2xl">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/15 border border-purple-400/30 text-purple-300 text-xs font-semibold">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Powered by Local AI (jankbuild-commander) + Scryfall DB</span>
            </div>
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white">
              Brew Competitive &amp; Jank{' '}
              <span className="bg-gradient-to-r from-purple-400 via-indigo-400 to-cyan-400 bg-clip-text text-transparent">
                Commander Decks
              </span>
            </h1>
            <p className="text-base text-slate-300/90">
              100-card singleton deck generation backed by {cardCount.toLocaleString()} local cards,{' '}
              {commanderCount.toLocaleString()} legendary commanders, and{' '}
              {synergyCount.toLocaleString()} EDHREC synergy pairings.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 shrink-0">
            <Button
              asChild
              size="lg"
              className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-900/40"
            >
              <Link href="/deckbuilder" className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                Build New Deck
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-slate-700 bg-slate-900/60 hover:bg-slate-800 text-slate-200"
            >
              <Link href="/commander" className="flex items-center gap-2">
                <Compass className="h-5 w-5 text-purple-400" />
                Explore Commanders
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-slate-700 bg-slate-900/60 hover:bg-slate-800 text-slate-200"
            >
              <Link href="/import" className="flex items-center gap-2">
                <Upload className="h-5 w-5 text-cyan-400" />
                Import Collection
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Live Telemetry Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-slate-900/60 border-slate-800/80 backdrop-blur-xl">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Your Decks
                </p>
                <p className="text-3xl font-bold text-white mt-1">{allDecks.length}</p>
                <p className="text-xs text-emerald-400 mt-1">
                  {savedDecks.length} saved • {generatedDecks.length} generated
                </p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
                <Save className="h-6 w-6 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/60 border-slate-800/80 backdrop-blur-xl">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Local Card Database
                </p>
                <p className="text-3xl font-bold text-amber-400 mt-1">
                  {cardCount.toLocaleString()}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Scryfall Oracle cards indexed
                </p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center">
                <Database className="h-6 w-6 text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/60 border-slate-800/80 backdrop-blur-xl">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Commanders Available
                </p>
                <p className="text-3xl font-bold text-purple-400 mt-1">
                  {commanderCount.toLocaleString()}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Ranked by EDHREC popularity
                </p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center">
                <Sparkles className="h-6 w-6 text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/60 border-slate-800/80 backdrop-blur-xl">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  EDHREC Synergies
                </p>
                <p className="text-3xl font-bold text-cyan-400 mt-1">
                  {synergyCount.toLocaleString()}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  High-synergy card pairings
                </p>
              </div>
              <div className="h-12 w-12 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
                <Flame className="h-6 w-6 text-cyan-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Live Scraper & New Card Release Sync Bar */}
      <ScraperQuickBar />

      {/* Deck Lists */}
      <div className="space-y-10">
        <DeckList
          title="Saved Decks"
          decks={savedDecks}
          icon={<Save className="h-6 w-6 text-emerald-400" />}
        />
        <DeckList
          title="Recently Generated Decks"
          decks={generatedDecks}
          icon={<Sparkles className="h-6 w-6 text-purple-400" />}
        />
      </div>
    </div>
  );
}
