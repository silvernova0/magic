'use client';

import React, { useState, useCallback } from 'react';
import type { Deck, Decklist } from '../../types';
import DeckBuilderForm from '../../components/deckbuilder/DeckBuilderForm';
import DeckDisplay from '../../components/deckbuilder/DeckDisplay';
import LoadingSpinner from '../../components/deckbuilder/LoadingSpinner';
import SaveDeckForm from '../../components/deckbuilder/SaveDeckForm';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

const DeckBuilderPage: React.FC = () => {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [decklist, setDecklist] = useState<Decklist | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleBuildDeck = useCallback(async (params: {
    commander: string;
    theme: string;
    colors: string[];
    powerLevel: string;
    useCollectionOnly: boolean;
    collection: string;
  }) => {
    setIsLoading(true);
    setError(null);
    setDecklist(null);
    setDeck(null);
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
      setDeck(result.deck);
      setDecklist(result.decklist);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'An unexpected error occurred. Check the console for details.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleDeckSaved = (updatedDeck: Deck) => {
    setDeck(updatedDeck);
  };

  return (
    <div className="container mx-auto max-w-7xl">
      <header className="mb-6 flex justify-between items-center">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
          MTG AI Commander Deck Builder
        </h1>
        <Button asChild>
          <Link href="/decks">My Decks</Link>
        </Button>
      </header>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-card rounded-lg shadow-lg p-6 border">
          <DeckBuilderForm onSubmit={handleBuildDeck} isLoading={isLoading} />
        </div>
        <div className="bg-card rounded-lg shadow-lg p-6 border min-h-[500px] flex flex-col">
          {isLoading && (
            <div className="m-auto text-center">
              <LoadingSpinner />
              <p className="mt-4 text-lg text-purple-600 animate-pulse">Brewing your masterpiece...</p>
            </div>
          )}
          {error && (
             <div className="m-auto text-center text-red-500 bg-red-50 dark:bg-red-950 p-6 rounded-lg border border-red-200 dark:border-red-800">
              <h3 className="text-xl font-bold mb-2">Error</h3>
              <p>{error}</p>
            </div>
          )}
          {deck && decklist && !isLoading && (
            <>
              <DeckDisplay decklist={decklist} initialDeckName={deck.name} isSaved={deck.status === 'SAVED'} />
              {deck.status === 'GENERATED' && (
                <SaveDeckForm deckId={deck.id} onDeckSaved={handleDeckSaved} />
              )}
            </>
          )}
          {!decklist && !isLoading && !error && (
            <div className="m-auto text-center text-muted-foreground">
              <p className="text-xl">Your generated deck will appear here.</p>
              <p className="mt-2 text-sm">Fill out the form and let the magic begin!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DeckBuilderPage;