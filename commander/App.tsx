
import React, { useState, useCallback } from 'react';
import type { Decklist } from './types';
import { buildCommanderDeck } from './services/geminiService';
import Header from './components/Header';
import DeckBuilderForm from './components/DeckBuilderForm';
import DeckDisplay from './components/DeckDisplay';
import LoadingSpinner from './components/LoadingSpinner';

const App: React.FC = () => {
  const [decklist, setDecklist] = useState<Decklist | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleBuildDeck = useCallback(async (collection: string, theme: string, powerLevel: string) => {
    setIsLoading(true);
    setError(null);
    setDecklist(null);
    try {
      const result = await buildCommanderDeck(collection, theme, powerLevel);
      setDecklist(result);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'An unexpected error occurred. Check the console for details.');
    } finally {
      setIsLoading(false);
    }
  }, []);

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
              {decklist && !isLoading && <DeckDisplay decklist={decklist} />}
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

export default App;
