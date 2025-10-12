'use client';

import { Deck, DeckStatus } from '@prisma/client';
import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

const getStatusBadgeColor = (status: DeckStatus) => {
  switch (status) {
    case 'GENERATED':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    case 'SAVED':
      return 'bg-green-500/20 text-green-400 border-green-500/50';
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/50';
  }
};

const getDeckCardCount = (decklist: any) => {
  if (!decklist || typeof decklist !== 'object') return 0;
  
  return (
    (Array.isArray(decklist.commander) ? decklist.commander.length : 0) +
    (Array.isArray(decklist.creatures) ? decklist.creatures.length : 0) +
    (Array.isArray(decklist.instants) ? decklist.instants.length : 0) +
    (Array.isArray(decklist.sorceries) ? decklist.sorceries.length : 0) +
    (Array.isArray(decklist.artifacts) ? decklist.artifacts.length : 0) +
    (Array.isArray(decklist.enchantments) ? decklist.enchantments.length : 0) +
    (Array.isArray(decklist.planeswalkers) ? decklist.planeswalkers.length : 0) +
    (Array.isArray(decklist.lands) ? decklist.lands.length : 0)
  );
};

interface DecksClientProps {
  initialDecks: Deck[];
}

export default function DecksClient({ initialDecks }: DecksClientProps) {
  const [decks, setDecks] = useState<Deck[]>(initialDecks);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const router = useRouter();

  const stats = {
    total: decks.length,
    generated: decks.filter((d) => d.status === 'GENERATED').length,
    saved: decks.filter((d) => d.status === 'SAVED').length,
    imported: 0, // TODO: Add IMPORTED status after Prisma regeneration
  };

  const handleDelete = async (deckId: string, deckName: string) => {
    if (!confirm(`Are you sure you want to delete "${deckName}"? This action cannot be undone.`)) {
      return;
    }

    setDeletingId(deckId);
    try {
      const response = await fetch(`/api/decks/${deckId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete deck');
      }

      // Remove deck from local state
      setDecks(decks.filter(d => d.id !== deckId));
      
      // Refresh the page to update server data
      router.refresh();
    } catch (error) {
      console.error('Error deleting deck:', error);
      alert('Failed to delete deck. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-purple-900/40 via-blue-900/40 to-purple-900/40 border-2 border-purple-500/30 p-8 backdrop-blur-xl">
          <div className="relative z-10 flex justify-between items-center">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-300 via-blue-300 to-purple-300 bg-clip-text text-transparent mb-2">
                📚 My Deck Library
              </h1>
              <p className="text-purple-200/80">
                View and manage all your Commander decks
              </p>
            </div>
            <div className="flex gap-3">
              <Link
                href="/deckbuilder"
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-medium hover:scale-105 transition-transform"
              >
                🤖 Generate Deck
              </Link>
              <Link
                href="/import"
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:scale-105 transition-transform"
              >
                📥 Import
              </Link>
            </div>
          </div>
          <div className="absolute inset-0 bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-purple-500/10 animate-pulse" />
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl border-2 border-purple-500/30 rounded-xl p-6 hover:scale-105 transition-transform">
            <div className="text-3xl font-bold text-purple-300">{stats.total}</div>
            <div className="text-sm text-purple-200/60">Total Decks</div>
          </div>
          <div className="bg-gradient-to-br from-blue-900/90 to-blue-800/90 backdrop-blur-xl border-2 border-blue-500/30 rounded-xl p-6 hover:scale-105 transition-transform">
            <div className="text-3xl font-bold text-blue-300">{stats.generated}</div>
            <div className="text-sm text-blue-200/60">AI Generated</div>
          </div>
          <div className="bg-gradient-to-br from-green-900/90 to-green-800/90 backdrop-blur-xl border-2 border-green-500/30 rounded-xl p-6 hover:scale-105 transition-transform">
            <div className="text-3xl font-bold text-green-300">{stats.saved}</div>
            <div className="text-sm text-green-200/60">Saved</div>
          </div>
          <div className="bg-gradient-to-br from-purple-900/90 to-purple-800/90 backdrop-blur-xl border-2 border-purple-500/30 rounded-xl p-6 hover:scale-105 transition-transform">
            <div className="text-3xl font-bold text-purple-300">{stats.imported}</div>
            <div className="text-sm text-purple-200/60">Imported</div>
          </div>
        </div>

        {/* Decks Grid */}
        {decks.length === 0 ? (
          <div className="bg-slate-900/50 backdrop-blur-xl border-2 border-purple-500/30 rounded-xl p-12 text-center">
            <div className="text-6xl mb-4">🃏</div>
            <h3 className="text-2xl font-semibold text-purple-300 mb-2">No Decks Yet</h3>
            <p className="text-purple-200/60 mb-6">
              Start building your first Commander deck!
            </p>
            <div className="flex gap-4 justify-center">
              <Link
                href="/deckbuilder"
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-medium hover:scale-105 transition-transform"
              >
                🤖 Generate with AI
              </Link>
              <Link
                href="/import"
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:scale-105 transition-transform"
              >
                📥 Import Deck
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {decks.map((deck) => {
              const cardCount = getDeckCardCount(deck.decklist);
              const isValidDeck = cardCount === 100;
              const isDeleting = deletingId === deck.id;
              
              return (
                <div
                  key={deck.id}
                  className="group bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl border-2 border-purple-500/30 rounded-xl p-6 hover:border-purple-400/50 transition-all relative"
                >
                  {/* Delete Button */}
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      handleDelete(deck.id, deck.name);
                    }}
                    disabled={isDeleting}
                    className="absolute top-4 right-4 p-2 bg-red-500/20 hover:bg-red-500/40 text-red-400 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed z-10"
                    title="Delete deck"
                  >
                    {isDeleting ? '⏳' : '🗑️'}
                  </button>

                  <Link href={`/decks/${deck.id}`} className="block">
                    {/* Status Badge */}
                    <div className="flex items-center justify-between mb-4">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold border ${getStatusBadgeColor(
                          deck.status
                        )}`}
                      >
                        {deck.status}
                      </span>
                      <span
                        className={`text-sm font-medium ${
                          isValidDeck ? 'text-green-400' : 'text-red-400'
                        }`}
                      >
                        {cardCount}/100 cards
                      </span>
                    </div>

                    {/* Deck Name */}
                    <h3 className="text-xl font-bold text-purple-300 mb-2 group-hover:text-purple-200 transition-colors">
                      {deck.name}
                    </h3>

                    {/* Description */}
                    <p className="text-purple-200/60 text-sm mb-4 line-clamp-2">
                      {deck.description || 'No description provided'}
                    </p>

                    {/* Metadata */}
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-purple-400">🎯 Theme:</span>
                        <span className="text-purple-200/80">{deck.theme}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-purple-400">⚡ Power:</span>
                        <span className="text-purple-200/80">{deck.powerLevel}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-purple-400">📅 Created:</span>
                        <span className="text-purple-200/80">
                          {new Date(deck.createdAt).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    {/* View Arrow */}
                    <div className="mt-4 pt-4 border-t border-purple-500/20 flex items-center justify-between">
                      <span className="text-xs text-purple-300/60">Click to view details</span>
                      <span className="text-purple-400 group-hover:translate-x-2 transition-transform">
                        →
                      </span>
                    </div>
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
