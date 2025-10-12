
import React from 'react';
import type { Decklist, CardCategory } from '@/types';

interface DeckDisplayProps {
  decklist: Decklist;
  initialDeckName: string;
  isSaved: boolean;
}

const CATEGORY_ORDER: CardCategory[] = [
  'commander', 'creatures', 'planeswalkers', 'sorceries',
  'instants', 'artifacts', 'enchantments', 'lands'
];

const CategoryDisplay: React.FC<{ title: string; cards: string[] | undefined }> = ({ title, cards }) => {
  // Ensure cards is an array
  if (!cards || !Array.isArray(cards) || cards.length === 0) return null;

  const formattedTitle = title.charAt(0).toUpperCase() + title.slice(1);

  return (
    <div className="mb-4 break-inside-avoid">
      <h3 className="text-lg font-bold text-purple-400 mb-2 sticky top-0 bg-gray-800 py-1">
        {formattedTitle} ({cards.length})
      </h3>
      <ul className="space-y-1">
        {cards.map((card, index) => (
          <li key={`${card}-${index}`} className="text-gray-300 text-sm hover:text-white transition-colors duration-200">
            {card}
          </li>
        ))}
      </ul>
    </div>
  );
};

const DeckDisplay: React.FC<DeckDisplayProps> = ({ decklist, initialDeckName, isSaved }) => {
  const totalCards = Object.values(decklist).reduce((sum, category) => {
    return sum + (Array.isArray(category) ? category.length : 0);
  }, 0);

  return (
    <div className="h-full flex flex-col">
      <div className="flex-shrink-0 mb-4 pb-4 border-b border-gray-700">
        <div className="flex justify-center items-center gap-4">
          <h2 className="text-2xl font-bold text-center text-gray-100">{initialDeckName}</h2>
          {isSaved && (
            <span className="bg-green-500 text-white text-xs font-bold px-2 py-1 rounded-full">
              Saved
            </span>
          )}
        </div>
        <p className="text-center text-gray-400">Total Cards: {totalCards}</p>
      </div>
      <div className="flex-grow overflow-y-auto pr-2">
        <div className="columns-2 md:columns-3 gap-6">
          {CATEGORY_ORDER.map(category => (
            <CategoryDisplay key={category} title={category} cards={decklist[category]} />
          ))}
        </div>
      </div>
    </div>
  );
};

export default DeckDisplay;
