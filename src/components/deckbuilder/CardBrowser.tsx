'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle, Star, Zap, Crown } from 'lucide-react';

interface CardData {
  id: number;
  name: string;
  manaCost: string | null;
  cmc: number;
  type: string;
  text: string | null;
  power: string | null;
  toughness: string | null;
  colors: string[];
  colorIdentity: string[];
  rarity: string;
  edhrecRank: number | null;
  edhrecSaltiness: number | null;
  tags: string[];
  powerLevel: number;
  isCommander: boolean;
}

interface CardBrowserProps {
  onCardSelect?: (card: CardData) => void;
  initialFilters?: {
    colors?: string[];
    tags?: string[];
  };
}

const POPULAR_TAGS = [
  'card-draw',
  'removal',
  'tutor',
  'ramp',
  'counterspell',
  'game-changer',
  'high-salt',
  'commander',
  'token',
  'graveyard',
  'sacrifice',
  'extra-turns',
  'copy',
  'storm',
  'cascade',
];

const CARD_TYPE_FILTERS = [
  'creature',
  'instant',
  'sorcery',
  'enchantment',
  'artifact',
  'planeswalker',
  'land',
];

const CardBrowser: React.FC<CardBrowserProps> = ({ onCardSelect, initialFilters }) => {
  const [searchName, setSearchName] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>(initialFilters?.tags || []);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedColors, setSelectedColors] = useState<string[]>(initialFilters?.colors || []);
  const [cards, setCards] = useState<CardData[]>([]);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState<'name' | 'cmc' | 'edhrecRank' | 'powerLevel'>('edhrecRank');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchCards = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: '50',
        page: page.toString(),
        sort: sortBy,
      });

      if (searchName) params.append('name', searchName);
      if (selectedTags.length > 0) params.append('tags', selectedTags.join(','));
      if (selectedTypes.length > 0) params.append('type', selectedTypes.join(','));
      if (selectedColors.length > 0) params.append('colorIdentity', selectedColors.join(','));

      const response = await fetch(`/api/cards/search?${params}`);
      if (response.ok) {
        const data = await response.json();
        setCards(page === 1 ? data.cards : [...cards, ...data.cards]);
        setHasMore(data.cards.length === 50);
      }
    } catch (error) {
      console.error('Error fetching cards:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCards();
  }, [searchName, selectedTags, selectedTypes, selectedColors, sortBy, page]);

  const toggleTag = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
    setPage(1);
  };

  const toggleType = (type: string) => {
    setSelectedTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    );
    setPage(1);
  };

  const toggleColor = (color: string) => {
    setSelectedColors(prev =>
      prev.includes(color) ? prev.filter(c => c !== color) : [...prev, color]
    );
    setPage(1);
  };

  const getPowerLevelColor = (level: number) => {
    if (level >= 8) return 'text-red-500';
    if (level >= 6) return 'text-orange-500';
    if (level >= 4) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getSaltinessColor = (saltiness: number | null) => {
    if (!saltiness) return '';
    if (saltiness >= 2.0) return 'bg-red-500';
    if (saltiness >= 1.0) return 'bg-orange-500';
    if (saltiness >= 0.5) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Card Browser</CardTitle>
        <CardDescription>
          Browse 31,483+ cards from your local database with advanced filtering
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search */}
        <div className="space-y-2">
          <Label htmlFor="card-search">Search by Name</Label>
          <Input
            id="card-search"
            value={searchName}
            onChange={(e) => {
              setSearchName(e.target.value);
              setPage(1);
            }}
            placeholder="Search cards..."
          />
        </div>

        {/* Tag Filters */}
        <div className="space-y-2">
          <Label>Filter by Tags</Label>
          <div className="flex flex-wrap gap-2">
            {POPULAR_TAGS.map((tag) => (
              <Badge
                key={tag}
                variant={selectedTags.includes(tag) ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => toggleTag(tag)}
              >
                {tag}
              </Badge>
            ))}
          </div>
        </div>

        {/* Type Filters */}
        <div className="space-y-2">
          <Label>Filter by Type</Label>
          <div className="flex flex-wrap gap-2">
            {CARD_TYPE_FILTERS.map((type) => (
              <Badge
                key={type}
                variant={selectedTypes.includes(type) ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => toggleType(type)}
              >
                {type}
              </Badge>
            ))}
          </div>
        </div>

        {/* Color Filters */}
        <div className="space-y-2">
          <Label>Filter by Color Identity</Label>
          <div className="flex flex-wrap gap-2">
            {[
              { value: 'W', label: 'White', symbol: '⚪' },
              { value: 'U', label: 'Blue', symbol: '🔵' },
              { value: 'B', label: 'Black', symbol: '⚫' },
              { value: 'R', label: 'Red', symbol: '🔴' },
              { value: 'G', label: 'Green', symbol: '🟢' },
            ].map((color) => (
              <Badge
                key={color.value}
                variant={selectedColors.includes(color.value) ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => toggleColor(color.value)}
              >
                <span className="mr-1">{color.symbol}</span>
                {color.label}
              </Badge>
            ))}
          </div>
        </div>

        {/* Sort Options */}
        <div className="space-y-2">
          <Label>Sort By</Label>
          <select
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value as any);
              setPage(1);
            }}
            className="w-full bg-background border border-input rounded-md p-2"
          >
            <option value="edhrecRank">EDHREC Popularity</option>
            <option value="powerLevel">Power Level</option>
            <option value="name">Name</option>
            <option value="cmc">Mana Cost</option>
          </select>
        </div>

        {/* Results */}
        <div className="space-y-2 max-h-[600px] overflow-y-auto border rounded-md p-4">
          {loading && cards.length === 0 && (
            <p className="text-center text-muted-foreground">Loading cards...</p>
          )}
          {cards.length === 0 && !loading && (
            <p className="text-center text-muted-foreground">No cards found</p>
          )}
          {cards.map((card) => (
            <div
              key={card.id}
              className="p-3 border rounded-md hover:bg-accent transition-colors cursor-pointer"
              onClick={() => onCardSelect?.(card)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold">{card.name}</h4>
                    {card.isCommander && <Crown className="w-4 h-4 text-yellow-500" />}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {card.manaCost} • {card.type}
                  </p>
                  {card.text && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {card.text}
                    </p>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1">
                  {/* Power Level */}
                  <div className="flex items-center gap-1">
                    <Star className={`w-4 h-4 ${getPowerLevelColor(card.powerLevel)}`} />
                    <span className={`text-sm font-semibold ${getPowerLevelColor(card.powerLevel)}`}>
                      {card.powerLevel.toFixed(1)}
                    </span>
                  </div>
                  {/* Saltiness Warning */}
                  {card.edhrecSaltiness !== null && card.edhrecSaltiness >= 1.0 && (
                    <div className="flex items-center gap-1">
                      <AlertTriangle className="w-4 h-4 text-orange-500" />
                      <span className="text-xs font-medium text-orange-500">
                        Salt: {card.edhrecSaltiness.toFixed(2)}
                      </span>
                    </div>
                  )}
                  {/* EDHREC Rank */}
                  {card.edhrecRank !== null && card.edhrecRank <= 1000 && (
                    <Badge variant="secondary" className="text-xs">
                      #{card.edhrecRank}
                    </Badge>
                  )}
                </div>
              </div>
              {/* Tags */}
              {card.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {card.tags.slice(0, 5).map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                  {card.tags.length > 5 && (
                    <Badge variant="outline" className="text-xs">
                      +{card.tags.length - 5}
                    </Badge>
                  )}
                </div>
              )}
            </div>
          ))}
          {hasMore && !loading && (
            <Button
              onClick={() => setPage(page + 1)}
              variant="outline"
              className="w-full"
            >
              Load More
            </Button>
          )}
          {loading && cards.length > 0 && (
            <p className="text-center text-sm text-muted-foreground">Loading more...</p>
          )}
        </div>

        {/* Stats */}
        <div className="text-xs text-muted-foreground text-center">
          Showing {cards.length} cards • Local database with 31,483+ cards
        </div>
      </CardContent>
    </Card>
  );
};

export default CardBrowser;
