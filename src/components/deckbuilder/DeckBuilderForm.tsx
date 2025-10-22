'use client';

import React, { useState, useEffect } from 'react';
import { MOXFIELD_BRACKETS, DECK_THEMES, MTG_COLORS } from '@/lib/constants';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface DeckBuilderFormProps {
  onSubmit: (params: {
    commander: string;
    theme: string;
    colors: string[];
    powerLevel: string;
    useCollectionOnly: boolean;
    collection: string;
  }) => void;
  isLoading: boolean;
}

const DeckBuilderForm: React.FC<DeckBuilderFormProps> = ({ onSubmit, isLoading }) => {
  const [commander, setCommander] = useState('');
  const [commanderSuggestions, setCommanderSuggestions] = useState<string[]>([]);
  const [theme, setTheme] = useState('Aggro');
  const [selectedColors, setSelectedColors] = useState<string[]>([]);
  const [powerLevel, setPowerLevel] = useState('3');
  const [useCollectionOnly, setUseCollectionOnly] = useState(false);
  const [collection, setCollection] = useState('');

  // Auto-complete commander search using local database
  useEffect(() => {
    const fetchCommanderSuggestions = async () => {
      if (commander.length < 2) {
        setCommanderSuggestions([]);
        return;
      }

      try {
        // Use local card database with commander tag and EDHREC ranking
        const params = new URLSearchParams({
          name: commander,
          tags: 'commander',
          sort: 'edhrecRank',
          limit: '10',
        });
        
        const response = await fetch(`/api/cards/search?${params}`);
        if (response.ok) {
          const data = await response.json();
          const suggestions = data.cards?.map((card: any) => card.name) || [];
          setCommanderSuggestions(suggestions);
        }
      } catch (error) {
        console.error('Error fetching commander suggestions:', error);
      }
    };

    const debounce = setTimeout(fetchCommanderSuggestions, 300);
    return () => clearTimeout(debounce);
  }, [commander]);

  const toggleColor = (color: string) => {
    setSelectedColors(prev =>
      prev.includes(color)
        ? prev.filter(c => c !== color)
        : [...prev, color]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (useCollectionOnly && !collection.trim()) {
      alert('Please provide your card collection or uncheck "Use Collection Only"');
      return;
    }
    onSubmit({
      commander,
      theme,
      colors: selectedColors,
      powerLevel,
      useCollectionOnly,
      collection,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Deck Configuration</CardTitle>
          <CardDescription>
            Configure your Commander deck with AI assistance using data from EDHREC, MTGTop8, and Moxfield
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Commander */}
          <div className="space-y-2 relative">
            <Label htmlFor="commander">Commander (Optional)</Label>
            <Input
              id="commander"
              value={commander}
              onChange={(e) => setCommander(e.target.value)}
              placeholder="e.g., Atraxa, Praetors' Voice (leave empty for AI suggestion)"
              disabled={isLoading}
            />
            
            {/* Commander Suggestions Dropdown */}
            {commanderSuggestions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-popover border rounded-md shadow-lg max-h-60 overflow-y-auto">
                {commanderSuggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setCommander(suggestion);
                      setCommanderSuggestions([]);
                    }}
                    className="w-full text-left px-4 py-2 hover:bg-accent transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
            
            <p className="text-xs text-muted-foreground">
              Leave empty to let AI suggest the best commander for your theme and colors
            </p>
          </div>

          {/* Theme */}
          <div className="space-y-2">
            <Label htmlFor="theme">Deck Theme/Archetype</Label>
            <select
              id="theme"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="w-full bg-background border border-input rounded-md p-2"
              disabled={isLoading}
            >
              {DECK_THEMES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              Choose the primary strategy for your deck
            </p>
          </div>

          {/* Color Identity */}
          <div className="space-y-2">
            <Label>Color Identity</Label>
            <div className="flex flex-wrap gap-2">
              {MTG_COLORS.map((color) => (
                <button
                  key={color.value}
                  type="button"
                  onClick={() => toggleColor(color.value)}
                  className={`px-4 py-2 rounded-md border-2 transition-all ${
                    selectedColors.includes(color.value)
                      ? 'border-primary bg-primary/20'
                      : 'border-muted hover:border-primary/50'
                  }`}
                  disabled={isLoading}
                >
                  <span className="mr-1">{color.symbol}</span>
                  {color.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Select colors to limit deck building (leave empty for any colors)
            </p>
          </div>

          {/* Power Level */}
          <div className="space-y-2">
            <Label htmlFor="power-level">Power Level (Moxfield Brackets)</Label>
            <select
              id="power-level"
              value={powerLevel}
              onChange={(e) => setPowerLevel(e.target.value)}
              className="w-full bg-background border border-input rounded-md p-2"
              disabled={isLoading}
            >
              {MOXFIELD_BRACKETS.map((bracket) => (
                <option key={bracket.value} value={bracket.value}>
                  {bracket.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              {MOXFIELD_BRACKETS.find(b => b.value === powerLevel)?.description}
            </p>
            <a
              href="https://moxfield.com/commanderbrackets"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline"
            >
              Learn more about Moxfield Commander Brackets →
            </a>
          </div>

          {/* Collection Option */}
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="use-collection"
                checked={useCollectionOnly}
                onChange={(e) => setUseCollectionOnly(e.target.checked)}
                className="rounded border-input"
                disabled={isLoading}
              />
              <Label htmlFor="use-collection" className="cursor-pointer">
                Build from my collection only
              </Label>
            </div>
            <p className="text-xs text-muted-foreground">
              Check this to only use cards you own. Uncheck to build from any cards.
            </p>
            <p className="text-xs text-green-600 dark:text-green-400 font-medium">
              💡 Basic lands (Forest, Island, Mountain, Plains, Swamp, Wastes) are always available in unlimited quantities
            </p>
          </div>

          {/* Collection Input */}
          {useCollectionOnly && (
            <div className="space-y-2">
              <Label htmlFor="collection">Your Card Collection</Label>
              <Textarea
                id="collection"
                value={collection}
                onChange={(e) => setCollection(e.target.value)}
                rows={8}
                placeholder="Paste your card list here, one card per line:&#10;Sol Ring&#10;Swords to Plowshares&#10;Rhystic Study&#10;..."
                disabled={isLoading}
              />
              <p className="text-xs text-muted-foreground">
                List your available cards (one per line)
              </p>
            </div>
          )}

          {/* Submit */}
          <Button
            type="submit"
            disabled={isLoading}
            className="w-full"
            size="lg"
          >
            {isLoading ? 'Building Deck with AI...' : 'Build My Commander Deck'}
          </Button>
        </CardContent>
      </Card>
    </form>
  );
};

export default DeckBuilderForm;
