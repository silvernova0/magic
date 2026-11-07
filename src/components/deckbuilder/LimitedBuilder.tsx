'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Sparkles, Layers, Trophy, Save, UploadCloud, CheckCircle2 } from 'lucide-react';

const SAMPLE_SEALED_POOL = `2 Hardened Scales
1 Branching Evolution
1 The Ozolith
2 Conclave Mentor
2 Llanowar Elves
1 Incubation Druid
1 Kami of Whispered Hopes
2Luminarch Aspirant
1 Siege Veteran
2 Botanical Brawler
1 Rishkar, Peema Renegade
1 Good-Fortune Unicorn
1 Renata, Called to the Hunt
1 Shalai, Voice of Plenty
2 Swords to Plowshares
1 Path to Exile
2 Nature's Claim
1 Heroic Intervention
1 Inspiring Call
1 Snakeskin Veil
1 Pledge of Unity
1 Basri's Solidarity
1 Cathars' Crusade
1 Felidar Retreat
1 Gavony Township
1 Temple Garden
1 Sunpetal Grove
2 Blossoming Sands
2 Counterspell
1 Negate
2 Opt
2 Lightning Bolt
2 Terminate
1 Doom Blade
1 Shock
1 Goblin Guide
1 Monastery Swiftspear`;

function compressCardList(cards: string[]): { name: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const c of cards) {
    counts.set(c, (counts.get(c) || 0) + 1);
  }
  return Array.from(counts.entries()).map(([name, count]) => ({ name, count }));
}

const LimitedBuilder: React.FC = () => {
  const [poolText, setPoolText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [loadingCollection, setLoadingCollection] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<any | null>(null);
  const [selectedRank, setSelectedRank] = useState<number>(1);
  const router = useRouter();

  const handleLoadUserCollection = async () => {
    setLoadingCollection(true);
    setError(null);
    try {
      const res = await fetch('/api/collection');
      if (res.ok) {
        const data = await res.json();
        if (data.success && Array.isArray(data.cards) && data.cards.length > 0) {
          const text = data.cards.map((c: any) => `${c.quantity} ${c.name}`).join('\n');
          setPoolText(text);
        } else {
          setError('Your collection is currently empty. Paste a Draft/Sealed pool below or click "Load Sample Pool".');
        }
      } else {
        setError('Could not load collection. Please make sure you are signed in.');
      }
    } catch {
      setError('Failed to fetch collection.');
    } finally {
      setLoadingCollection(false);
    }
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!poolText.trim()) {
      setError('Please paste your Draft or Sealed card pool first.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/limited/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ poolText, saveDeck: false }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to analyze pool');
      }
      setAnalysis(data.analysis);
      setSelectedRank(1);
    } catch (err: any) {
      setError(err?.message || 'Error analyzing Limited pool');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveDeck = async () => {
    if (!analysis) return;
    setIsSaving(true);
    try {
      const res = await fetch('/api/limited/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          poolText,
          saveDeck: true,
          selectedRank,
        }),
      });
      const data = await res.json();
      if (res.ok && data.savedDeckId) {
        router.push(`/decks/${data.savedDeckId}?new=true`);
      } else {
        setError(data.error || 'Failed to save Limited deck');
      }
    } catch {
      setError('Failed to save Limited deck');
    } finally {
      setIsSaving(false);
    }
  };

  const activeRec =
    analysis?.recommendations?.find((r: any) => r.rank === selectedRank) ||
    analysis?.recommendations?.[0];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-6">
      {/* Left Column: Pool Input */}
      <div className="lg:col-span-5 space-y-6">
        <Card className="bg-slate-900/70 border-slate-800/90 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Layers className="h-5 w-5 text-purple-400" />
              Limited Pool (Draft / Sealed)
            </CardTitle>
            <CardDescription>
              Paste the cards you drafted or opened in Sealed. We&apos;ll tag every card, detect mechanical clusters &amp; pairwise EDHREC synergies, and build the top 40-card decks (23 playables + 17 lands).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAnalyze} className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setPoolText(SAMPLE_SEALED_POOL)}
                  className="text-xs"
                >
                  <Sparkles className="h-3.5 w-3.5 mr-1.5 text-purple-400" />
                  Load Sample Pool
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleLoadUserCollection}
                  disabled={loadingCollection}
                  className="text-xs"
                >
                  <UploadCloud className="h-3.5 w-3.5 mr-1.5 text-cyan-400" />
                  {loadingCollection ? 'Loading Collection...' : 'Use My Collection'}
                </Button>
              </div>

              <div className="space-y-2">
                <Label htmlFor="pool-input">Card Pool (1 per line, e.g. &quot;2 Llanowar Elves&quot;)</Label>
                <Textarea
                  id="pool-input"
                  value={poolText}
                  onChange={(e) => setPoolText(e.target.value)}
                  rows={14}
                  placeholder={`2 Hardened Scales\n2 Conclave Mentor\n1 The Ozolith\n2 Swords to Plowshares\n...`}
                  className="font-mono text-xs bg-slate-950/80 border-slate-800"
                />
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-red-950/60 border border-red-500/40 text-xs text-red-300">
                  {error}
                </div>
              )}

              <Button type="submit" disabled={isLoading} className="w-full" size="lg">
                {isLoading ? 'Tagging Pool & Finding Synergies...' : 'Recommend 40-Card Limited Decks'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Pool Tag Breakdown */}
        {analysis && (
          <Card className="bg-slate-900/70 border-slate-800/90">
            <CardHeader className="pb-3">
              <CardTitle className="text-base text-white">Pool Synergy Tag Breakdown</CardTitle>
              <CardDescription className="text-xs">
                {analysis.poolSize} total cards analyzed ({analysis.uniqueCardsResolved} unique) in {(analysis.buildTimeMs / 1000).toFixed(2)}s
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-1.5">
                {analysis.poolTagSummary.map((item: { tag: string; count: number }) => (
                  <Badge key={item.tag} variant="secondary" className="text-xs">
                    {item.tag}: <span className="ml-1 font-bold text-purple-300">{item.count}</span>
                  </Badge>
                ))}
              </div>
              {analysis.unresolvedNames?.length > 0 && (
                <p className="text-[11px] text-amber-400 mt-3">
                  Unrecognized card names skipped: {analysis.unresolvedNames.slice(0, 5).join(', ')}
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Right Column: Recommended 40-Card Decks */}
      <div className="lg:col-span-7 space-y-6">
        {!analysis ? (
          <div className="h-full min-h-[480px] rounded-2xl bg-slate-900/60 border border-slate-800/80 p-8 flex flex-col items-center justify-center text-center space-y-4">
            <div className="h-16 w-16 rounded-2xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center">
              <Trophy className="h-8 w-8 text-purple-400" />
            </div>
            <h3 className="text-xl font-bold text-white">Limited Draft &amp; Sealed Deck Recommender</h3>
            <p className="text-sm text-slate-400 max-w-md">
              Paste your Draft or Sealed pool on the left (or click <strong>Load Sample Pool</strong>) to evaluate all 10 two-color Guild pairs, uncover mechanical tag clusters, and generate ready-to-play 40-card decks.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Top 3 Guild Archetype Selector */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {analysis.recommendations.map((rec: any) => {
                const isSelected = rec.rank === selectedRank;
                return (
                  <button
                    key={rec.rank}
                    type="button"
                    onClick={() => setSelectedRank(rec.rank)}
                    className={`text-left p-4 rounded-xl border transition-all ${
                      isSelected
                        ? 'bg-purple-950/40 border-purple-500 shadow-lg shadow-purple-950/40'
                        : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold uppercase tracking-wider text-purple-400">
                        #{rec.rank} Pick
                      </span>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                        Score: {rec.totalScore}
                      </span>
                    </div>
                    <div className="font-bold text-white text-sm truncate">{rec.guildName}</div>
                    <div className="text-xs text-purple-300 truncate mt-0.5">
                      {rec.primarySynergies[0]?.tag || 'Balanced Midrange'}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Active Recommendation Detail */}
            {activeRec && (
              <Card className="bg-slate-900/70 border-slate-800/90">
                <CardHeader className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800">
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge className="bg-purple-600 text-white">40-Card Limited</Badge>
                      <span className="text-xs text-slate-400">
                        Avg Mana Value: <strong>{activeRec.stats.avgCmc}</strong>
                      </span>
                    </div>
                    <CardTitle className="text-2xl text-white mt-1.5">
                      {activeRec.archetypeTitle}
                    </CardTitle>
                    <CardDescription className="mt-1 text-slate-300">
                      {activeRec.summary}
                    </CardDescription>
                  </div>
                  <Button onClick={handleSaveDeck} disabled={isSaving} className="shrink-0">
                    <Save className="h-4 w-4 mr-2" />
                    {isSaving ? 'Saving...' : 'Save to My Decks'}
                  </Button>
                </CardHeader>

                <CardContent className="space-y-6 pt-6">
                  {/* Detected Synergy Clusters */}
                  {activeRec.primarySynergies.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                        Detected Synergy Clusters in {activeRec.guildName}
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {activeRec.primarySynergies.map((syn: { tag: string; count: number }) => (
                          <span
                            key={syn.tag}
                            className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            {syn.tag} ({syn.count} cards)
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Key Standout Cards */}
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                      Key Standout Cards &amp; Synergies
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {activeRec.keyCards.map((kc: any) => (
                        <div
                          key={kc.name}
                          className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs"
                        >
                          <div className="font-bold text-white">{kc.name}</div>
                          <div className="text-slate-400 mt-0.5">{kc.reason}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 40-Card Maindeck Columns */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Creatures */}
                    <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
                      <h5 className="font-bold text-sm text-white mb-2 border-b border-slate-800 pb-1.5">
                        Creatures ({activeRec.decklist.creatures.length})
                      </h5>
                      <ul className="space-y-1 text-xs text-slate-300">
                        {compressCardList(activeRec.decklist.creatures).map((item) => (
                          <li key={item.name} className="flex justify-between">
                            <span>{item.name}</span>
                            <span className="text-purple-400 font-mono">{item.count}x</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Non-Creature Spells */}
                    <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
                      <h5 className="font-bold text-sm text-white mb-2 border-b border-slate-800 pb-1.5">
                        Spells &amp; Support ({activeRec.stats.nonCreatures})
                      </h5>
                      <ul className="space-y-1 text-xs text-slate-300">
                        {compressCardList([
                          ...activeRec.decklist.instants,
                          ...activeRec.decklist.sorceries,
                          ...activeRec.decklist.artifacts,
                          ...activeRec.decklist.enchantments,
                          ...activeRec.decklist.planeswalkers,
                        ]).map((item) => (
                          <li key={item.name} className="flex justify-between">
                            <span>{item.name}</span>
                            <span className="text-purple-400 font-mono">{item.count}x</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Lands (17) */}
                    <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
                      <h5 className="font-bold text-sm text-white mb-2 border-b border-slate-800 pb-1.5">
                        Lands ({activeRec.decklist.lands.length})
                      </h5>
                      <ul className="space-y-1 text-xs text-slate-300">
                        {compressCardList(activeRec.decklist.lands).map((item) => (
                          <li key={item.name} className="flex justify-between">
                            <span>{item.name}</span>
                            <span className="text-emerald-400 font-mono">{item.count}x</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Sideboard / Unused Pool */}
                  {activeRec.sideboard.length > 0 && (
                    <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/60">
                      <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                        Remaining Sideboard Pool ({activeRec.sideboard.reduce((s: number, c: any) => s + c.quantity, 0)} cards)
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {activeRec.sideboard.slice(0, 30).map((sb: any) => (
                          <span
                            key={sb.name}
                            className="text-[11px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400"
                          >
                            {sb.quantity}x {sb.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default LimitedBuilder;
