'use client';

import React, { useState, useEffect } from 'react';
import { MOXFIELD_BRACKETS, DECK_THEMES, MTG_COLORS, KINDRED_TYPES } from '@/lib/constants';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { SummoningCircle } from '@/components/ui/SummoningCircle';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

interface DeckBuilderFormProps {
  onSubmit: (params: {
    commander: string;
    partner?: string;
    theme: string;
    colors: string[];
    powerLevel: string;
    useCollectionOnly: boolean;
    useLocalModel?: boolean;
    avoidSaltCards: boolean;
    collection: string;
  }) => void;
  isLoading: boolean;
}

const DeckBuilderForm: React.FC<DeckBuilderFormProps> = ({ onSubmit, isLoading }) => {
  const [commander, setCommander] = useState('');
  const [commanderSuggestions, setCommanderSuggestions] = useState<{ name: string; colorIdentity: string[] }[]>([]);
  const [commanderColors, setCommanderColors] = useState<string[]>([]);
  const [partner, setPartner] = useState('');
  const [partnerSuggestions, setPartnerSuggestions] = useState<{ name: string; colorIdentity: string[] }[]>([]);
  const [partnerColors, setPartnerColors] = useState<string[]>([]);
  const [showPartner, setShowPartner] = useState(false);
  const [theme, setTheme] = useState('Aggro');
  const [kindredType, setKindredType] = useState('Elves');
  const [selectedColors, setSelectedColors] = useState<string[]>([]);
  const [powerLevel, setPowerLevel] = useState('3');
  const [useCollectionOnly, setUseCollectionOnly] = useState(false);
  const [useLocalModel, setUseLocalModel] = useState(true);
  const [avoidSaltCards, setAvoidSaltCards] = useState(false);
  const [collection, setCollection] = useState('');
  const [collectionStats, setCollectionStats] = useState<{ totalCards: number; uniqueCards: number; legendaryCreatures: number } | null>(null);
  const [loadingCollection, setLoadingCollection] = useState(false);

  // Fetch user's collection when "use collection only" is enabled
  useEffect(() => {
    const fetchUserCollection = async () => {
      if (!useCollectionOnly) {
        setCollection('');
        setCollectionStats(null);
        return;
      }

      setLoadingCollection(true);
      try {
        const response = await fetch('/api/collection');
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.cards) {
            const collectionText = data.cards
              .map((card: any) => `${card.quantity} ${card.name}`)
              .join('\n');
            setCollection(collectionText);
            setCollectionStats(data.stats);
          }
        } else if (response.status === 401) {
          alert('Please sign in to use your collection');
          setUseCollectionOnly(false);
        }
      } catch (error) {
        console.error('Error fetching collection:', error);
        alert('Failed to load your collection. Please try again.');
        setUseCollectionOnly(false);
      } finally {
        setLoadingCollection(false);
      }
    };

    fetchUserCollection();
  }, [useCollectionOnly]);

  // Auto-complete commander search & Auto-color selection
  useEffect(() => {
    const fetchCommanderSuggestions = async () => {
      if (commander.length < 2) {
        setCommanderSuggestions([]);
        return;
      }

      try {
        const params = new URLSearchParams({
          name: commander,
          isCommander: 'true',
          sortBy: 'edhrecRank',
          sortOrder: 'asc',
          limit: '10',
        });

        const response = await fetch(`/api/cards/search?${params}`);
        if (response.ok) {
          const data = await response.json();
          const suggestions = (data.cards || [])
            .map((card: any) => ({ name: card.name, colorIdentity: card.colorIdentity }));

          // Filter out exact match from suggestions list to avoid clutter, 
          // BUT check for exact match to auto-set colors
          const exactMatch = suggestions.find((s: any) => s.name.toLowerCase() === commander.toLowerCase());

          if (exactMatch) {
            // Auto-set colors if not already set or if different
            // We only do this if the user hasn't manually messed with colors too much? 
            // Actually, for a commander deck, you almost always want the commander's colors.
            setCommanderColors(exactMatch.colorIdentity);
            const merged = Array.from(new Set([...exactMatch.colorIdentity, ...partnerColors]));
            setSelectedColors(merged);
          }

          setCommanderSuggestions(suggestions.filter((s: any) => s.name.toLowerCase() !== commander.toLowerCase()));
        }
      } catch (error) {
        console.error('Error fetching commander suggestions:', error);
      }
    };

    const debounce = setTimeout(fetchCommanderSuggestions, 300);
    return () => clearTimeout(debounce);
  }, [commander, partnerColors]);

  // Auto-complete partner search
  useEffect(() => {
    const fetchPartnerSuggestions = async () => {
      if (partner.length < 2) {
        setPartnerSuggestions([]);
        return;
      }

      try {
        const params = new URLSearchParams({
          name: partner,
          isCommander: 'true',
          sortBy: 'edhrecRank',
          sortOrder: 'asc',
          limit: '10',
        });

        const response = await fetch(`/api/cards/search?${params}`);
        if (response.ok) {
          const data = await response.json();
          const suggestions = (data.cards || [])
            .map((card: any) => ({ name: card.name, colorIdentity: card.colorIdentity }))
            .filter((s: any) => s.name.toLowerCase() !== partner.toLowerCase());
          setPartnerSuggestions(suggestions);
        }
      } catch (error) {
        console.error('Error fetching partner suggestions:', error);
      }
    };

    const debounce = setTimeout(fetchPartnerSuggestions, 300);
    return () => clearTimeout(debounce);
  }, [partner]);

  const toggleColor = (color: string) => {
    setSelectedColors(prev =>
      prev.includes(color)
        ? prev.filter(c => c !== color)
        : [...prev, color]
    );
  };

  const handleCommanderSelect = (suggestion: { name: string; colorIdentity: string[] }) => {
    setCommander(suggestion.name);
    setCommanderColors(suggestion.colorIdentity);
    const merged = Array.from(new Set([...suggestion.colorIdentity, ...partnerColors]));
    setSelectedColors(merged);
    setCommanderSuggestions([]);
  };

  const handlePartnerSelect = (suggestion: { name: string; colorIdentity: string[] }) => {
    setPartner(suggestion.name);
    setPartnerColors(suggestion.colorIdentity);
    const merged = Array.from(new Set([...commanderColors, ...suggestion.colorIdentity]));
    setSelectedColors(merged);
    setPartnerSuggestions([]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (useCollectionOnly && (!collection.trim() || !collectionStats)) {
      alert('Please import your collection first or uncheck "Build from my collection only"');
      return;
    }

    const finalTheme = theme === 'Kindred' ? `Kindred - ${kindredType}` : theme;

    onSubmit({
      commander,
      partner: showPartner ? partner : undefined,
      theme: finalTheme,
      colors: selectedColors,
      powerLevel,
      useCollectionOnly,
      useLocalModel,
      avoidSaltCards,
      collection,
    });
  };

  return (
    <div className="relative">
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-background/80 backdrop-blur-md"
          >
            <SummoningCircle size={250} />
            <motion.p
              className="mt-8 text-xl font-serif text-primary animate-pulse font-bold tracking-wider"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              Consulting the Arcane Oracle...
            </motion.p>
            <motion.p
              className="mt-2 text-sm text-muted-foreground"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 1 }}
            >
              Weaving mana strands into a deck
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>

      <form onSubmit={handleSubmit} className={cn("space-y-6 transition-opacity duration-500", isLoading ? "opacity-20 pointer-events-none" : "opacity-100")}>
        <Card className="glass-panel border-primary/20 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 pointer-events-none" />

          <CardHeader className="relative">
            <CardTitle className="text-2xl font-serif text-gradient-mystic">Deck Configuration</CardTitle>
            <CardDescription className="text-muted-foreground">
              Configure your Commander deck with AI assistance using data from EDHREC, MTGTop8, and Moxfield
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6 relative">
            {/* Commander */}
            <div className="space-y-2 relative group">
              <Label htmlFor="commander" className="text-foreground/80 group-focus-within:text-primary transition-colors">
                Commander (Optional)
              </Label>
              <div className="relative">
                <Input
                  id="commander"
                  value={commander}
                  onChange={(e) => setCommander(e.target.value)}
                  placeholder="e.g., Atraxa, Praetors' Voice (leave empty for AI suggestion)"
                  disabled={isLoading}
                  autoComplete="off"
                  className="bg-background/50 border-primary/20 focus:border-primary focus:ring-primary/20 transition-all"
                />

                {/* Commander Suggestions Dropdown */}
                <AnimatePresence>
                  {commanderSuggestions.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="absolute z-50 w-full mt-1 bg-card/95 backdrop-blur-md border border-primary/20 rounded-md shadow-xl max-h-60 overflow-y-auto"
                    >
                      {commanderSuggestions.map((suggestion, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            handleCommanderSelect(suggestion);
                          }}
                          className="w-full text-left px-4 py-2 hover:bg-primary/10 transition-colors border-b border-primary/10 last:border-b-0 text-sm"
                        >
                          <span className="font-medium text-foreground">{suggestion.name}</span>
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground italic">
                  Leave empty to let AI suggest the best commander
                </p>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowPartner(!showPartner)}
                  className="text-xs h-6 px-2 text-primary hover:text-primary/80 hover:bg-primary/10"
                >
                  {showPartner ? '- Remove Partner' : '+ Add Partner / Background'}
                </Button>
              </div>
            </div>

            {/* Partner (Optional) */}
            <AnimatePresence>
              {showPartner && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-2 relative overflow-hidden"
                >
                  <Label htmlFor="partner">Partner / Background</Label>
                  <div className="relative">
                    <Input
                      id="partner"
                      value={partner}
                      onChange={(e) => setPartner(e.target.value)}
                      placeholder="e.g., Ravos, Soultender or Raised by Giants"
                      disabled={isLoading}
                      autoComplete="off"
                      className="bg-background/50 border-purple-200 focus:border-purple-500"
                    />

                    {/* Partner Suggestions Dropdown */}
                    {partnerSuggestions.length > 0 && (
                      <div
                        className="absolute z-50 w-full mt-1 bg-card/95 backdrop-blur-md border border-primary/20 rounded-md shadow-xl max-h-60 overflow-y-auto"
                      >
                        {partnerSuggestions.map((suggestion, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onMouseDown={(e) => {
                              e.preventDefault();
                              handlePartnerSelect(suggestion);
                            }}
                            className="w-full text-left px-4 py-2 hover:bg-primary/10 transition-colors border-b border-primary/10 last:border-b-0 text-sm"
                          >
                            {suggestion.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Must have "Partner", "Friends Forever", "Doctor's Companion", or be a Background
                  </p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Theme & Kindred */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="theme">Deck Theme/Archetype</Label>
                <select
                  id="theme"
                  value={theme}
                  onChange={(e) => setTheme(e.target.value)}
                  className="w-full bg-background/50 border border-primary/20 rounded-md p-2 focus:ring-primary/20 focus:border-primary transition-all"
                  disabled={isLoading}
                >
                  {DECK_THEMES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              {theme === 'Kindred' && (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="space-y-2"
                >
                  <Label htmlFor="kindredType">Creature Type</Label>
                  <select
                    id="kindredType"
                    value={kindredType}
                    onChange={(e) => setKindredType(e.target.value)}
                    className="w-full bg-background/50 border border-primary/20 rounded-md p-2 focus:ring-primary/20 focus:border-primary transition-all"
                    disabled={isLoading}
                  >
                    {KINDRED_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </motion.div>
              )}
            </div>

            {/* Color Identity */}
            <div className="space-y-2">
              <Label>Color Identity</Label>
              <div className="flex flex-wrap gap-2">
                {MTG_COLORS.map((color) => {
                  const isSelected = selectedColors.includes(color.value);

                  // Dynamic styles based on color identity
                  let activeClass = "border-primary bg-primary/20 shadow-[0_0_10px_-2px_var(--primary)]";
                  let textClass = "text-foreground";

                  if (isSelected) {
                    switch (color.value) {
                      case 'W': activeClass = "border-yellow-400 bg-yellow-400/20 shadow-[0_0_15px_-2px_rgba(250,204,21,0.5)]"; textClass = "text-yellow-200"; break;
                      case 'U': activeClass = "border-blue-400 bg-blue-400/20 shadow-[0_0_15px_-2px_rgba(96,165,250,0.5)]"; textClass = "text-blue-300"; break;
                      case 'B': activeClass = "border-gray-500 bg-gray-500/30 shadow-[0_0_15px_-2px_rgba(107,114,128,0.5)]"; textClass = "text-gray-300"; break;
                      case 'R': activeClass = "border-red-500 bg-red-500/20 shadow-[0_0_15px_-2px_rgba(239,68,68,0.5)]"; textClass = "text-red-300"; break;
                      case 'G': activeClass = "border-green-500 bg-green-500/20 shadow-[0_0_15px_-2px_rgba(34,197,94,0.5)]"; textClass = "text-green-300"; break;
                    }
                  }

                  return (
                    <motion.button
                      key={color.value}
                      type="button"
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => toggleColor(color.value)}
                      className={cn(
                        "px-4 py-2 rounded-md border transition-all duration-300 flex items-center gap-2",
                        isSelected
                          ? activeClass
                          : "border-muted hover:border-primary/50 hover:bg-primary/5 opacity-70 hover:opacity-100"
                      )}
                      disabled={isLoading}
                    >
                      <span className={cn("text-lg font-bold", isSelected ? textClass : "")}>{color.symbol}</span>
                      <span className={cn("font-medium", isSelected ? "text-white" : "")}>{color.label}</span>
                    </motion.button>
                  );
                })}
              </div>
              <p className="text-xs text-muted-foreground">
                Select colors to limit deck building (leave empty for any colors)
              </p>
            </div>

            {/* Power Level */}
            <div className="space-y-2">
              <Label htmlFor="power-level">Power Level (Moxfield Brackets)</Label>
              <div className="relative">
                <select
                  id="power-level"
                  value={powerLevel}
                  onChange={(e) => setPowerLevel(e.target.value)}
                  className="w-full bg-background/50 border border-primary/20 rounded-md p-2 focus:ring-primary/20 focus:border-primary transition-all appearance-none"
                  disabled={isLoading}
                >
                  {MOXFIELD_BRACKETS.map((bracket) => (
                    <option key={bracket.value} value={bracket.value}>
                      {bracket.label}
                    </option>
                  ))}
                </select>
                <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground">
                  ▼
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {MOXFIELD_BRACKETS.find(b => b.value === powerLevel)?.description}
              </p>
            </div>

            {/* Advanced Options */}
            <div className="space-y-4 pt-4 border-t border-primary/10">
              <div className="flex flex-col gap-3">
                {/* Collection Toggle */}
                <div className="flex items-center space-x-2 group">
                  <input
                    type="checkbox"
                    id="use-collection"
                    checked={useCollectionOnly}
                    onChange={(e) => setUseCollectionOnly(e.target.checked)}
                    className="rounded border-primary/30 text-primary focus:ring-primary/50"
                    disabled={isLoading}
                  />
                  <Label htmlFor="use-collection" className="cursor-pointer group-hover:text-primary transition-colors">
                    Build from my collection only
                  </Label>
                </div>

                {/* Local AI Toggle */}
                <div className="flex items-center space-x-2 group">
                  <input
                    type="checkbox"
                    id="use-local-model"
                    checked={useLocalModel}
                    onChange={(e) => setUseLocalModel(e.target.checked)}
                    className="rounded border-primary/30 text-primary focus:ring-primary/50"
                    disabled={isLoading}
                  />
                  <Label htmlFor="use-local-model" className="cursor-pointer group-hover:text-primary transition-colors">
                    🤖 Use Local AI (Slower but smarter)
                  </Label>
                </div>

                {/* Salt Toggle */}
                <div className="flex items-center space-x-2 group">
                  <input
                    type="checkbox"
                    id="avoid-salt"
                    checked={avoidSaltCards}
                    onChange={(e) => setAvoidSaltCards(e.target.checked)}
                    className="rounded border-primary/30 text-primary focus:ring-primary/50"
                    disabled={isLoading}
                  />
                  <Label htmlFor="avoid-salt" className="cursor-pointer group-hover:text-primary transition-colors">
                    Avoid "salty" cards 🧂
                  </Label>
                </div>
              </div>

              {/* Collection Stats Display */}
              <AnimatePresence>
                {useCollectionOnly && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    {loadingCollection ? (
                      <div className="bg-muted/30 rounded-lg p-4 text-center animate-pulse">
                        <p className="text-sm text-muted-foreground">Accessing your library...</p>
                      </div>
                    ) : collectionStats ? (
                      <div className="bg-gradient-to-br from-primary/10 to-secondary/10 rounded-lg p-4 border border-primary/20 shadow-inner">
                        <h4 className="font-serif font-semibold text-sm mb-2 flex items-center gap-2 text-primary">
                          <span className="text-lg">📚</span>
                          Your Grimoire
                        </h4>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div className="bg-background/40 p-2 rounded">
                            <p className="text-muted-foreground text-xs uppercase tracking-wider">Total Cards</p>
                            <p className="font-bold text-lg">{collectionStats.totalCards}</p>
                          </div>
                          <div className="bg-background/40 p-2 rounded">
                            <p className="text-muted-foreground text-xs uppercase tracking-wider">Unique Spells</p>
                            <p className="font-bold text-lg">{collectionStats.uniqueCards}</p>
                          </div>
                        </div>
                        {(collectionStats.totalCards < 500 || (collectionStats.legendaryCreatures || 0) < 10) && (
                          <div className="mt-2 text-xs text-amber-600 dark:text-amber-400 bg-amber-500/10 p-2 rounded border border-amber-500/20">
                            ⚠️ Collection too small for optimal building.
                            {collectionStats.totalCards < 500 && ` Need ${500 - collectionStats.totalCards} more cards.`}
                            {(collectionStats.legendaryCreatures || 0) < 10 && ` Need ${10 - (collectionStats.legendaryCreatures || 0)} more legends.`}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="bg-orange-500/10 rounded-lg p-4 border border-orange-500/20">
                        <p className="text-sm text-orange-700 dark:text-orange-300">
                          ⚠️ No collection found. Please <a href="/import" className="underline font-semibold hover:text-orange-600">import your collection</a> first.
                        </p>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Submit Button */}
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-14 text-lg font-serif font-bold tracking-wide text-white bg-gradient-to-r from-violet-600 via-fuchsia-600 to-violet-600 bg-[length:200%_100%] animate-shimmer hover:shadow-[0_0_25px_rgba(139,92,246,0.6)] hover:brightness-110 transition-all border-none shadow-xl"
              >
                {isLoading ? 'Channeling Magic...' : '✨ Conjure Deck ✨'}
              </Button>
            </motion.div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
};

export default DeckBuilderForm;
