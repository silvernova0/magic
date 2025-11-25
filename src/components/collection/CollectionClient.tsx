'use client';

import { useState, useEffect, useCallback } from 'react';
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
import { Search, Plus, Trash2, Edit, Image as ImageIcon, ChevronLeft, ChevronRight } from 'lucide-react';
import type { CardData } from '@/lib/cardData';
// Removed missing hook import, logic is implemented inline

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

interface CollectionClientProps {
  initialCards: UserCard[];
  totalCards: number;
}

export default function CollectionClient({ initialCards, totalCards: initialTotalCards }: CollectionClientProps) {
  const [cards, setCards] = useState<UserCard[]>(initialCards);
  const [totalCards, setTotalCards] = useState(initialTotalCards);
  const [filteredCount, setFilteredCount] = useState(initialTotalCards); // Initially assume all match until filtered

  // Search & Filter State
  const [cardNameInput, setCardNameInput] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedCard, setSelectedCard] = useState<CardData | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(false);

  // Filter State
  const [filterQuery, setFilterQuery] = useState('');
  const [selectedRarity, setSelectedRarity] = useState<string>('all');
  const [selectedColor, setSelectedColor] = useState<string>('all');

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const limit = 24;
  const totalPages = Math.ceil(filteredCount / limit);

  // Debounce filter query
  const [debouncedFilterQuery, setDebouncedFilterQuery] = useState(filterQuery);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedFilterQuery(filterQuery), 500);
    return () => clearTimeout(timer);
  }, [filterQuery]);

  // Auto-complete card search (for adding new cards)
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

  // Fetch cards when filters or page change
  const fetchCards = useCallback(async () => {
    setIsFetching(true);
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: limit.toString(),
      });

      if (debouncedFilterQuery) params.append('search', debouncedFilterQuery);
      if (selectedRarity !== 'all') params.append('rarity', selectedRarity);
      if (selectedColor !== 'all') params.append('color', selectedColor);

      const response = await fetch(`/api/collection?${params.toString()}`);
      const data = await response.json();

      if (data.success) {
        setCards(data.cards);
        setFilteredCount(data.stats.filteredCards);
        // If we are on a page that no longer exists (e.g. deleted items), go back
        if (data.stats.totalPages < currentPage && data.stats.totalPages > 0) {
          setCurrentPage(1);
        }
      }
    } catch (error) {
      console.error('Error fetching collection:', error);
    } finally {
      setIsFetching(false);
    }
  }, [currentPage, debouncedFilterQuery, selectedRarity, selectedColor]);

  // Trigger fetch when dependencies change
  // Skip initial render fetch if we have initial data matching default state
  // But since initial data is just first page sorted by date, and filters might be different, 
  // we should probably just fetch if state differs from initial. 
  // For simplicity, let's just fetch whenever filters change.
  useEffect(() => {
    // Don't fetch on mount if we have initial data and default filters
    // But we need to fetch if filters change
    fetchCards();
  }, [fetchCards]);

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedFilterQuery, selectedRarity, selectedColor]);


  // Fetch full card data when selected (for adding)
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
        // Refresh the current view
        fetchCards();
        // Update total count
        setTotalCards(prev => prev + 1); // Approximate, ideally fetch stats

        setSelectedCard(null);
        setCardNameInput('');
        setQuantity(1);
      }
    } catch (error) {
      console.error('Error adding card:', error);
    }
  };

  // Update card quantity
  const handleUpdateQuantity = async (cardId: string, newQuantity: number) => {
    try {
      const response = await fetch(`/api/collection/${cardId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity: newQuantity }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.deleted) {
          // Card was removed
          fetchCards(); // Refresh to fill the gap
          setTotalCards(prev => prev - 1);
        } else {
          // Card quantity updated
          setCards(cards.map(c => c.id === cardId ? data.card : c));
        }
      }
    } catch (error) {
      console.error('Error updating card:', error);
    }
  };

  // Delete card from collection
  const handleDeleteCard = async (cardId: string, cardName: string) => {
    if (!confirm(`Remove "${cardName}" from your collection?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/collection/${cardId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchCards(); // Refresh
        setTotalCards(prev => prev - 1);
      }
    } catch (error) {
      console.error('Error deleting card:', error);
    }
  };

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
              {/* Unique cards count is same as total cards in this schema currently */}
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
          <div className="relative min-h-[400px]">
            {isFetching && (
              <div className="absolute inset-0 bg-background/50 backdrop-blur-sm z-10 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {cards.map((card) => (
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
                      <span className={`capitalize px-2 py-1 rounded-full text-xs font-medium ${card.rarity === 'mythic' ? 'bg-orange-100 dark:bg-orange-950 text-orange-700 dark:text-orange-300' :
                        card.rarity === 'rare' ? 'bg-yellow-100 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300' :
                          card.rarity === 'uncommon' ? 'bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300' :
                            'bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-400'
                        }`}>
                        {card.rarity}
                      </span>
                    </div>
                    <div className="flex justify-between items-center pt-2 border-t">
                      <span className="text-sm text-muted-foreground">Quantity:</span>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleUpdateQuantity(card.id, Math.max(0, card.quantity - 1))}
                          disabled={card.quantity <= 0}
                        >
                          −
                        </Button>
                        <span className="text-2xl font-bold text-purple-600 dark:text-purple-400 w-12 text-center">
                          {card.quantity}x
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleUpdateQuantity(card.id, card.quantity + 1)}
                        >
                          +
                        </Button>
                      </div>
                    </div>

                    {/* Card Actions */}
                    <div className="flex gap-2 pt-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="flex-1 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
                        onClick={() => handleDeleteCard(card.id, card.name)}
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        Remove
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {cards.length === 0 && !isFetching && (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-muted-foreground">
                    No cards found. {totalCards > 0 ? 'Try different filters.' : 'Add cards to your collection to get started!'}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-4 pt-4">
              <Button
                variant="outline"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1 || isFetching}
              >
                <ChevronLeft className="h-4 w-4 mr-2" />
                Previous
              </Button>
              <span className="text-sm font-medium">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="outline"
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages || isFetching}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
