'use client';

import React, { useState, useCallback, useEffect } from 'react';
import DeckBuilderForm from '../../components/deckbuilder/DeckBuilderForm';
import LoadingSpinner from '../../components/deckbuilder/LoadingSpinner';
import CardBrowser from '../../components/deckbuilder/CardBrowser';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Sparkles, ShieldCheck, Layers, Cpu, Trophy } from 'lucide-react';

interface CommanderSpotlight {
  name: string;
  typeLine: string;
  oracleText?: string;
  colorIdentity?: string[];
  edhrecRank?: number;
  imageUrl?: string;
}

const COLOR_BADGE: Record<string, { label: string; cls: string }> = {
  W: { label: 'W • White', cls: 'bg-amber-100 text-amber-950 border-amber-300' },
  U: { label: 'U • Blue', cls: 'bg-blue-500/20 text-blue-300 border-blue-500/40' },
  B: { label: 'B • Black', cls: 'bg-slate-800 text-slate-200 border-slate-600' },
  R: { label: 'R • Red', cls: 'bg-red-500/20 text-red-300 border-red-500/40' },
  G: { label: 'G • Green', cls: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
};

const DeckBuilderPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCommander, setSelectedCommander] = useState<string>('');
  const [spotlight, setSpotlight] = useState<CommanderSpotlight | null>(null);
  const router = useRouter();

  // Fetch live Commander spotlight art & oracle text when commander input changes
  useEffect(() => {
    if (!selectedCommander || selectedCommander.trim().length < 3) {
      setSpotlight(null);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const res = await fetch(
          `/api/cards/search?name=${encodeURIComponent(selectedCommander.trim())}&isCommander=true&limit=1`
        );
        if (res.ok) {
          const data = await res.json();
          const card = data.cards?.[0];
          if (card) {
            setSpotlight({
              name: card.name,
              typeLine: card.typeLine,
              oracleText: card.oracleText,
              colorIdentity: Array.isArray(card.colorIdentity)
                ? card.colorIdentity
                : typeof card.colorIdentity === 'string'
                ? card.colorIdentity.split(',').filter(Boolean)
                : [],
              edhrecRank: card.edhrecRank,
              imageUrl:
                card.imageUris?.normal ||
                card.imageUris?.large ||
                card.imageUris?.art_crop ||
                `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(card.name)}&format=image&version=normal`,
            });
          }
        }
      } catch {
        // ignore preview fetch errors
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [selectedCommander]);

  const handleBuildDeck = useCallback(
    async (params: {
      commander: string;
      theme: string;
      colors: string[];
      powerLevel: string;
      useCollectionOnly: boolean;
      collection: string;
    }) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/commander/build', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(params),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to build deck');
        }

        const result = await response.json();

        if (result.deck && result.deck.id) {
          router.push(`/decks/${result.deck.id}?new=true`);
        }
      } catch (err) {
        console.error(err);
        setError(
          err instanceof Error
            ? err.message
            : 'An unexpected error occurred. Check the console for details.'
        );
        setIsLoading(false);
      }
    },
    [router]
  );

  return (
    <div className="container mx-auto max-w-7xl space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-xl">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-purple-400 mb-1">
            <Cpu className="h-3.5 w-3.5" />
            <span>Local AI Engine • 31,483 Scryfall Cards • 21,817 Synergies</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-white">
            AI Commander Deck Studio
          </h1>
        </div>
        <Button asChild variant="outline" className="border-slate-700 bg-slate-900 hover:bg-slate-800">
          <Link href="/decks">View My Decks</Link>
        </Button>
      </header>

      <Tabs defaultValue="builder" className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-2 bg-slate-900 border border-slate-800">
          <TabsTrigger value="builder">AI Deck Builder</TabsTrigger>
          <TabsTrigger value="browser">Card Database Browser</TabsTrigger>
        </TabsList>

        <TabsContent value="builder">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-6">
            <div className="lg:col-span-7 bg-slate-900/70 rounded-2xl shadow-xl p-6 border border-slate-800/90 backdrop-blur-xl">
              <DeckBuilderForm
                onSubmit={handleBuildDeck}
                isLoading={isLoading}
                onCommanderChange={setSelectedCommander}
              />
            </div>

            <div className="lg:col-span-5 bg-slate-900/70 rounded-2xl shadow-xl p-6 border border-slate-800/90 backdrop-blur-xl flex flex-col justify-between min-h-[520px]">
              {isLoading ? (
                <div className="m-auto text-center py-12">
                  <LoadingSpinner />
                  <div className="mt-6 space-y-2.5">
                    <p className="text-lg text-purple-400 font-bold animate-pulse">
                      Brewing your 100-card Commander deck...
                    </p>
                    <p className="text-sm text-slate-300">
                      Querying 21,817 EDHREC synergies &amp; local card database
                    </p>
                    <p className="text-sm text-slate-400">
                      Curating ramp, card draw, removal &amp; mana base with Local AI
                    </p>
                  </div>
                </div>
              ) : error ? (
                <div className="m-auto text-center w-full">
                  <div className="text-red-300 bg-red-950/60 p-6 rounded-xl border border-red-500/40">
                    <h3 className="text-lg font-bold mb-2">Generation Error</h3>
                    <p className="text-sm">{error}</p>
                  </div>
                  <Button
                    onClick={() => setError(null)}
                    variant="outline"
                    className="mt-4"
                  >
                    Try Again
                  </Button>
                </div>
              ) : spotlight ? (
                <div className="space-y-5">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <span className="text-xs font-semibold uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5" />
                      Commander Spotlight
                    </span>
                    {spotlight.edhrecRank && (
                      <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                        <Trophy className="h-3 w-3" />
                        EDHREC #{spotlight.edhrecRank}
                      </span>
                    )}
                  </div>

                  <div className="flex flex-col items-center">
                    <img
                      src={spotlight.imageUrl}
                      alt={spotlight.name}
                      className="w-60 rounded-2xl shadow-2xl shadow-purple-950/60 border border-white/10 transition-transform hover:scale-[1.02]"
                    />
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-xl font-bold text-white">{spotlight.name}</h3>
                    <p className="text-xs font-medium text-purple-300">{spotlight.typeLine}</p>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {(spotlight.colorIdentity && spotlight.colorIdentity.length > 0
                        ? spotlight.colorIdentity
                        : ['C']
                      ).map((c) => {
                        const badge = COLOR_BADGE[c] || {
                          label: 'Colorless',
                          cls: 'bg-slate-800 text-slate-300 border-slate-700',
                        };
                        return (
                          <span
                            key={c}
                            className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${badge.cls}`}
                          >
                            {badge.label}
                          </span>
                        );
                      })}
                    </div>

                    {spotlight.oracleText && (
                      <div className="mt-3 p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-300 whitespace-pre-line leading-relaxed">
                        {spotlight.oracleText}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="my-auto space-y-6 text-center px-4">
                  <div className="mx-auto h-16 w-16 rounded-2xl bg-gradient-to-br from-purple-600/20 to-indigo-600/20 border border-purple-500/30 flex items-center justify-center">
                    <Sparkles className="h-8 w-8 text-purple-400" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-xl font-bold text-white">
                      Local AI Commander Architect
                    </h3>
                    <p className="text-sm text-slate-400">
                      Type a Commander name on the left to preview its card art, oracle text, and EDHREC rank—or leave it blank and let the Local AI pick a Commander for your theme and colors.
                    </p>
                  </div>

                  <div className="grid grid-cols-3 gap-3 pt-4 text-left">
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                      <ShieldCheck className="h-4 w-4 text-emerald-400 mb-1.5" />
                      <div className="text-xs font-bold text-white">100% Legal</div>
                      <div className="text-[11px] text-slate-400">
                        Strict color identity &amp; banlist check
                      </div>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                      <Layers className="h-4 w-4 text-purple-400 mb-1.5" />
                      <div className="text-xs font-bold text-white">Balanced 99</div>
                      <div className="text-[11px] text-slate-400">
                        10+ ramp, 10+ draw, 8+ removal, 37 lands
                      </div>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                      <Cpu className="h-4 w-4 text-cyan-400 mb-1.5" />
                      <div className="text-xs font-bold text-white">Zero Cloud</div>
                      <div className="text-[11px] text-slate-400">
                        Runs locally on socialnode
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="browser">
          <div className="mt-6">
            <CardBrowser />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default DeckBuilderPage;
