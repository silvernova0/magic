'use client';

import React, { useState, useCallback } from 'react';
import type { Deck, Decklist } from '@/types';
import Header from '@/components/deckbuilder/Header';
import DeckBuilderForm from '@/components/deckbuilder/DeckBuilderForm';
import DeckDisplay from '@/components/deckbuilder/DeckDisplay';
import LoadingSpinner from '@/components/deckbuilder/LoadingSpinner';
import SaveDeckForm from '@/components/deckbuilder/SaveDeckForm';

const DeckBuilderPage: React.FC = () => {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [decklist, setDecklist] = useState<Decklist | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleBuildDeck = useCallback(async (collection: string, theme: string, powerLevel: string) => {
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
        body: JSON.stringify({ collection, theme, powerLevel }),
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
    <div className="min-h-screen bg-gray-900 text-gray-100 font-sans p-4 sm:p-6 lg:p-8">
      <div
        className="fixed inset-0 z-0 bg-cover bg-center opacity-10"
        style={{backgroundImage: "url('https://picsum.photos/seed/magic/1920/1080')"}}
      ></div>
      <div className="relative z-10 container mx-auto max-w-7xl">
        <Header />
        <main className="mt-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-gray-800 bg-opacity-80 backdrop-blur-sm rounded-lg shadow-2xl p-6 border border-gray-700">
              <DeckBuilderForm onSubmit={handleBuildDeck} isLoading={isLoading} />
            </div>
            <div className="bg-gray-800 bg-opacity-80 backdrop-blur-sm rounded-lg shadow-2xl p-6 border border-gray-700 min-h-[500px] flex flex-col">
              {isLoading && (
                <div className="m-auto text-center">
                  <LoadingSpinner />
                  <p className="mt-4 text-lg text-purple-400 animate-pulse">Brewing your masterpiece...</p>
                </div>
              )}
              {error && (
                 <div className="m-auto text-center text-red-400 bg-red-900 bg-opacity-50 p-6 rounded-lg">
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
                <div className="m-auto text-center text-gray-400">
                  <p className="text-xl">Your generated deck will appear here.</p>
                  <p className="mt-2 text-sm">Fill out the form and let the magic begin!</p>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default DeckBuilderPage;
