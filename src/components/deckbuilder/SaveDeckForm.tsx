'use client';

import React, { useState } from 'react';
import type { Deck } from '@/types';

interface SaveDeckFormProps {
  deckId: string;
  onDeckSaved: (updatedDeck: Deck) => void;
}

const SaveDeckForm: React.FC<SaveDeckFormProps> = ({ deckId, onDeckSaved }) => {
  const [deckName, setDeckName] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deckName.trim()) {
      setError('Deck name cannot be empty.');
      return;
    }
    setIsSaving(true);
    setError(null);

    try {
      const response = await fetch(`/api/decks/${deckId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: deckName }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to save deck');
      }

      const updatedDeck: Deck = await response.json();
      onDeckSaved(updatedDeck);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mt-4 p-4 border-t border-gray-700">
      <div className="flex items-center gap-4">
        <input
          type="text"
          value={deckName}
          onChange={(e) => setDeckName(e.target.value)}
          placeholder="Enter deck name to save"
          className="flex-grow bg-gray-700 text-white rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
          disabled={isSaving}
        />
        <button
          type="submit"
          className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded-md transition-colors disabled:opacity-50"
          disabled={isSaving}
        >
          {isSaving ? 'Saving...' : 'Save Deck'}
        </button>
      </div>
      {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
    </form>
  );
};

export default SaveDeckForm;