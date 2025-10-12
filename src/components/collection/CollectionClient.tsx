'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Search, Plus, Trash2, Edit, Image as ImageIcon } from 'lucide-react';
import type { CardData } from '@/lib/cardData';

interface UserCard {
  id: string;
  name: string;
  manaCost: string;
  cmc: number;
  colors: string;
  type_line: string;
  oracleText: string | null;
  power: string | null;
  toughness: string | null;
  setName: string;
  rarity: string;
  imageUrl: string | null;
  quantity: number;
}

export default function CollectionClient({ initialCards }: { initialCards: UserCard[] }) {
  const [cards, setCards] = useState<UserCard[]>(initialCards);
  const [searchQuery, setSearchQuery] = useState('');
  const [cardNameInput, setCardNameInput] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedCard, setSelectedCard] = useState<CardData | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [filterQuery, setFilterQuery] = useState('');
  const [selectedRarity, setSelectedRarity] = useState<string>('all');
  const [selectedColor, setSelectedColor] = useState<string>('all');

  // Auto-complete card search
  useEffect(() => {
    const fetchSuggestions = async () => {
      if (cardNameInput.length < 2) {
        setSuggestions([]);
        return;
      }

      try {
        const response = await fetch(
          `/api/cards/lookup?name=${encodeURIComponent(cardNameInput)}&action=search`
        );
        const data = await response.json();
        setSuggestions(data.results || []);
      } catch (error) {
        console.error('Error fetching suggestions:', error);
      }
    };

    const debounce = setTimeout(fetchSuggestions, 300);
    return () => clearTimeout(debounce);
  }, [cardNameInput]);

  // Fetch full card data when selected
  const handleSelectCard = async (cardName: string) => {
    setIsLoading(true);
    setCardNameInput(cardName);
    setSuggestions([]);

    try {
      const response = await fetch(
        `/api/cards/lookup?name=${encodeURIComponent(cardName)}`
      );
      const data: CardData = await response.json();
      setSelectedCard(data);
    } catch (error) {
      console.error('Error fetching card:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Add card to collection
  const handleAddCard = async () => {
    if (!selectedCard) return;

    try {
      const response = await fetch('/api/collection/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: selectedCard.name,
          manaCost: selectedCard.manaCost,
          cmc: selectedCard.cmc,
          colors: selectedCard.colors.join(','),
          type_line: selectedCard.typeLine,
          oracleText: selectedCard.oracleText || '',
          power: selectedCard.power || '',
          toughness: selectedCard.toughness || '',
          setName: selectedCard.setName,
          rarity: selectedCard.rarity,
          imageUrl: selectedCard.images.scryfall?.normal || '',
          quantity,
        }),
      });

      if (response.ok) {
        const newCard = await response.json();
        setCards([...cards, newCard]);
        setSelectedCard(null);
        setCardNameInput('');
        setQuantity(1);
      }
    } catch (error) {
      console.error('Error adding card:', error);
    }
  };

  // Filter cards
  const filteredCards = cards.filter((card) => {
    const matchesSearch = card.name.toLowerCase().includes(filterQuery.toLowerCase());
    const matchesRarity = selectedRarity === 'all' || card.rarity === selectedRarity;
    const matchesColor =
      selectedColor === 'all' ||
      (selectedColor === 'colorless' && !card.colors) ||
      card.colors?.includes(selectedColor);

    return matchesSearch && matchesRarity && matchesColor;
  });

  // Stats
  const totalCards = cards.reduce((sum, card) => sum + card.quantity, 0);
  const uniqueCards = cards.length;

  return (
    <div className="container mx-auto max-w-7xl space-y-6">
      {/* Hero Header */}
      <div className="p-8 rounded-xl bg-gradient-to-br from-purple-500/10 via-indigo-500/10 to-blue-500/10 border border-purple-500/20">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 bg-clip-text text-transparent mb-2">
              My Collection
            </h1>
            <div className="flex flex-wrap gap-4 mt-3">
              <div className="flex items-center gap-2 px-4 py-2 bg-purple-100 dark:bg-purple-950 rounded-full">
                <span className="text-2xl font-bold text-purple-600 dark:text-purple-400">{totalCards}</span>
                <span className="text-sm text-purple-700 dark:text-purple-300">total cards</span>
              </div>
              <div className="flex items-center gap-2 px-4 py-2 bg-indigo-100 dark:bg-indigo-950 rounded-full">
                <span className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{uniqueCards}</span>
                <span className="text-sm text-indigo-700 dark:text-indigo-300">unique cards</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Add Card Panel */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="h-5 w-5" />
                Add Card
              </CardTitle>
              <CardDescription>
                Search for a card to add to your collection
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Card Search */}
              <div className="space-y-2 relative">
                <Label htmlFor="card-search">Card Name</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="card-search"
                    placeholder="Search for a card..."
                    value={cardNameInput}
                    onChange={(e) => setCardNameInput(e.target.value)}
                    className="pl-10"
                  />
                </div>

                {/* Suggestions */}
                {suggestions.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-popover border rounded-md shadow-lg max-h-60 overflow-y-auto">
                    {suggestions.map((suggestion, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSelectCard(suggestion)}
                        className="w-full text-left px-4 py-2 hover:bg-accent transition-colors"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Selected Card Preview */}
              {selectedCard && (
                <div className="space-y-4 border rounded-lg p-4">
                  <div className="flex gap-4">
                    {selectedCard.images.scryfall?.normal ? (
                      <img
                        src={selectedCard.images.scryfall.normal}
                        alt={selectedCard.name}
                        className="w-32 h-auto rounded-md"
                      />
                    ) : (
                      <div className="w-32 h-44 bg-muted rounded-md flex items-center justify-center">
                        <ImageIcon className="h-8 w-8 text-muted-foreground" />
                      </div>
                    )}

                    <div className="flex-1 space-y-2">
                      <h3 className="font-bold">{selectedCard.name}</h3>
                      <p className="text-sm text-muted-foreground">
                        {selectedCard.typeLine}
                      </p>
                      <p className="text-sm">{selectedCard.manaCost}</p>
                      <p className="text-xs text-muted-foreground">
                        {selectedCard.setName} • {selectedCard.rarity}
                      </p>
                      {selectedCard.prices?.usd && (
                        <p className="text-sm font-semibold text-green-500">
                          ${selectedCard.prices.usd}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Quantity Input */}
                  <div className="space-y-2">
                    <Label htmlFor="quantity">Quantity</Label>
                    <Input
                      id="quantity"
                      type="number"
                      min="1"
                      value={quantity}
                      onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                    />
                  </div>

                  <Button onClick={handleAddCard} className="w-full">
                    <Plus className="h-4 w-4 mr-2" />
                    Add to Collection
                  </Button>
                </div>
              )}

              {isLoading && (
                <div className="text-center py-4">
                  <p className="text-sm text-muted-foreground">Loading card data...</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Collection Display */}
        <div className="lg:col-span-2 space-y-4">
          {/* Filters */}
          <Card>
            <CardHeader>
              <CardTitle>Filters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="filter-search">Search</Label>
                  <Input
                    id="filter-search"
                    placeholder="Filter cards..."
                    value={filterQuery}
                    onChange={(e) => setFilterQuery(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="filter-rarity">Rarity</Label>
                  <select
                    id="filter-rarity"
                    value={selectedRarity}
                    onChange={(e) => setSelectedRarity(e.target.value)}
                    className="w-full h-10 rounded-md border border-input bg-background px-3"
                  >
                    <option value="all">All Rarities</option>
                    <option value="common">Common</option>
                    <option value="uncommon">Uncommon</option>
                    <option value="rare">Rare</option>
                    <option value="mythic">Mythic</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="filter-color">Color</Label>
                  <select
                    id="filter-color"
                    value={selectedColor}
                    onChange={(e) => setSelectedColor(e.target.value)}
                    className="w-full h-10 rounded-md border border-input bg-background px-3"
                  >
                    <option value="all">All Colors</option>
                    <option value="W">White</option>
                    <option value="U">Blue</option>
                    <option value="B">Black</option>
                    <option value="R">Red</option>
                    <option value="G">Green</option>
                    <option value="colorless">Colorless</option>
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredCards.map((card) => (
              <Card key={card.id} className="overflow-hidden group hover:shadow-xl transition-all duration-300 hover:scale-[1.02] border-2 hover:border-purple-500/50">
                {card.imageUrl && (
                  <div className="relative h-48 w-full bg-muted overflow-hidden">
                    <img
                      src={card.imageUrl}
                      alt={card.name}
                      className="object-contain w-full h-full group-hover:scale-110 transition-transform duration-300"
                    />
                  </div>
                )}
                <CardHeader>
                  <CardTitle className="text-lg group-hover:text-purple-600 transition-colors">{card.name}</CardTitle>
                  <CardDescription>{card.type_line}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Mana Cost:</span>
                    <span className="font-mono font-semibold">{card.manaCost || 'N/A'}</span>
                  </div>
                  {card.power && card.toughness && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">P/T:</span>
                      <span className="font-semibold">
                        {card.power}/{card.toughness}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Set:</span>
                    <span className="text-xs">{card.setName}</span>
                  </div>
                  <div className="flex justify-between text-sm items-center">
                    <span className="text-muted-foreground">Rarity:</span>
                    <span className={`capitalize px-2 py-1 rounded-full text-xs font-medium ${
                      card.rarity === 'mythic' ? 'bg-orange-100 dark:bg-orange-950 text-orange-700 dark:text-orange-300' :
                      card.rarity === 'rare' ? 'bg-yellow-100 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300' :
                      card.rarity === 'uncommon' ? 'bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300' :
                      'bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-400'
                    }`}>
                      {card.rarity}
                    </span>
                  </div>
                  <div className="flex justify-between items-center pt-2 border-t">
                    <span className="text-sm text-muted-foreground">Quantity:</span>
                    <span className="text-2xl font-bold text-purple-600 dark:text-purple-400">{card.quantity}x</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {filteredCards.length === 0 && (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">
                  No cards found. {cards.length > 0 ? 'Try different filters.' : 'Add cards to your collection to get started!'}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
