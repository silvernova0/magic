
import React, { useState } from 'react';
import { POWER_LEVELS } from '../constants';

interface DeckBuilderFormProps {
  onSubmit: (collection: string, theme: string, powerLevel: string) => void;
  isLoading: boolean;
}

const DeckBuilderForm: React.FC<DeckBuilderFormProps> = ({ onSubmit, isLoading }) => {
  const [collection, setCollection] = useState('');
  const [theme, setTheme] = useState('');
  const [powerLevel, setPowerLevel] = useState(POWER_LEVELS[0]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!collection.trim() || !theme.trim()) {
        alert("Please provide your card collection and a deck theme.");
        return;
    }
    onSubmit(collection, theme, powerLevel);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="collection" className="block text-sm font-medium text-purple-300 mb-1">
          Your Card Collection
        </label>
        <textarea
          id="collection"
          value={collection}
          onChange={(e) => setCollection(e.target.value)}
          rows={12}
          className="w-full bg-gray-900 border border-gray-600 rounded-md shadow-sm focus:ring-purple-500 focus:border-purple-500 text-gray-200 p-3 transition"
          placeholder="Paste your card list here, one card per line. e.g.&#10;Sol Ring&#10;Swords to Plowshares&#10;Rhystic Study"
          required
        />
      </div>
      
      <div>
        <label htmlFor="theme" className="block text-sm font-medium text-purple-300 mb-1">
          Deck Theme
        </label>
        <input
          type="text"
          id="theme"
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          className="w-full bg-gray-900 border border-gray-600 rounded-md shadow-sm focus:ring-purple-500 focus:border-purple-500 text-gray-200 p-3 transition"
          placeholder="e.g., Dragon Tribal, Vampire Lifegain, Artifacts Matter"
          required
        />
      </div>

      <div>
        <label htmlFor="power-level" className="block text-sm font-medium text-purple-300 mb-1">
          Power Level
        </label>
        <select
          id="power-level"
          value={powerLevel}
          onChange={(e) => setPowerLevel(e.target.value)}
          className="w-full bg-gray-900 border border-gray-600 rounded-md shadow-sm focus:ring-purple-500 focus:border-purple-500 text-gray-200 p-3 transition"
        >
          {POWER_LEVELS.map((level) => (
            <option key={level} value={level}>{level}</option>
          ))}
        </select>
      </div>
      
      <button
        type="submit"
        disabled={isLoading}
        className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-lg text-lg font-bold text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:bg-gray-500 disabled:cursor-not-allowed transition-all duration-300 transform hover:scale-105 disabled:scale-100"
      >
        {isLoading ? 'Brewing...' : 'Build My Deck'}
      </button>
    </form>
  );
};

export default DeckBuilderForm;
