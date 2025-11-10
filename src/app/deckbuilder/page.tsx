'use client';

import React, { useState, useCallback } from 'react';
import DeckBuilderForm from '../../components/deckbuilder/DeckBuilderForm';
import LoadingSpinner from '../../components/deckbuilder/LoadingSpinner';
import CardBrowser from '../../components/deckbuilder/CardBrowser';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const DeckBuilderPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleBuildDeck = useCallback(async (params: {
    commander: string;
    theme: string;
    colors: string[];
    powerLevel: string;
    useCollectionOnly: boolean;
    avoidSaltCards: boolean;
    collection: string;
  }) => {
    setIsLoading(true);
    setError(null);
    try {
      // Always use v3 deck builder endpoint (build-from-collection)
      // It supports both collection-only and all-cards modes
      const endpoint = '/api/commander/build-from-collection';
      
      const requestBody = {
        commander: params.commander,
        strategy: params.theme.toLowerCase(),
        powerLevel: parseInt(params.powerLevel),
        bracket: parseInt(params.powerLevel),
        useCollectionOnly: params.useCollectionOnly, // Pass the checkbox state
        avoidSaltCards: params.avoidSaltCards, // Pass salt avoidance preference
        colors: params.colors, // Pass color restrictions
      };
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to build deck');
      }

      const result = await response.json();
      
      // Redirect to the generated deck instead of showing it here
      if (result.deck && result.deck.id) {
        router.push(`/decks/${result.deck.id}?new=true`);
      }
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'An unexpected error occurred. Check the console for details.');
      setIsLoading(false);
    }
  }, [router]);

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
      
      <Tabs defaultValue="builder" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="builder">Deck Builder</TabsTrigger>
          <TabsTrigger value="browser">Card Browser</TabsTrigger>
        </TabsList>
        
        <TabsContent value="builder">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-6">
            <div className="bg-card rounded-lg shadow-lg p-6 border">
              <DeckBuilderForm onSubmit={handleBuildDeck} isLoading={isLoading} />
            </div>
            <div className="bg-card rounded-lg shadow-lg p-6 border min-h-[500px] flex flex-col">
              {isLoading && (
                <div className="m-auto text-center">
                  <LoadingSpinner />
                  <div className="mt-6 space-y-3">
                    <p className="text-lg text-purple-600 font-semibold animate-pulse">Brewing your masterpiece...</p>
                    <p className="text-sm text-muted-foreground">Analyzing commander synergies and meta decks</p>
                    <p className="text-sm text-muted-foreground">Selecting the perfect 100 cards</p>
                    <p className="text-xs text-muted-foreground mt-4">You'll be redirected when complete</p>
                  </div>
                </div>
              )}
              {error && (
                <div className="m-auto text-center">
                  <div className="text-red-500 bg-red-50 dark:bg-red-950 p-6 rounded-lg border border-red-200 dark:border-red-800">
                    <h3 className="text-xl font-bold mb-2">Error</h3>
                    <p>{error}</p>
                  </div>
                  <Button 
                    onClick={() => setError(null)} 
                    variant="outline" 
                    className="mt-4"
                  >
                    Try Again
                  </Button>
                </div>
              )}
              {!isLoading && !error && (
                <div className="m-auto text-center text-muted-foreground">
                  <p className="text-xl mb-4">Ready to build your Commander deck?</p>
                  <p className="text-sm mb-2">Fill out the form and click "Build Deck"</p>
                  <p className="text-xs text-muted-foreground">Your deck will be generated and saved automatically</p>
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