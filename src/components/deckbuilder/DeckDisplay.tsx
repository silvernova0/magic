
import React, { useState, useEffect } from 'react';
import type { Decklist, CardCategory } from '@/types';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, Star } from 'lucide-react';

interface CardMetadata {
  name: string;
  edhrecSaltiness: number | null;
  powerLevel: number;
  tags: string[];
}

interface DeckDisplayProps {
  decklist: Decklist;
  initialDeckName: string;
  isSaved: boolean;
}

const CATEGORY_ORDER: CardCategory[] = [
  'commander', 'creatures', 'planeswalkers', 'sorceries',
  'instants', 'artifacts', 'enchantments', 'lands'
];

const CategoryDisplay: React.FC<{ 
  title: string; 
  cards: string[] | undefined;
  cardMetadata: Map<string, CardMetadata>;
}> = ({ title, cards, cardMetadata }) => {
  // Ensure cards is an array
  if (!cards || !Array.isArray(cards) || cards.length === 0) return null;

  const formattedTitle = title.charAt(0).toUpperCase() + title.slice(1);

  const getPowerLevelColor = (level: number) => {
    if (level >= 8) return 'text-red-500';
    if (level >= 6) return 'text-orange-500';
    if (level >= 4) return 'text-yellow-500';
    return 'text-green-500';
  };

  return (
    <div className="mb-4 break-inside-avoid">
      <h3 className="text-lg font-bold text-purple-400 mb-2 sticky top-0 bg-gray-800 py-1">
        {formattedTitle} ({cards.length})
      </h3>
      <ul className="space-y-1">
        {cards.map((card, index) => {
          const metadata = cardMetadata.get(card);
          const isHighSalt = metadata && metadata.edhrecSaltiness !== null && metadata.edhrecSaltiness >= 1.0;
          const hasGameChangerTag = metadata?.tags.includes('game-changer');
          
          return (
            <li 
              key={`${card}-${index}`} 
              className="text-gray-300 text-sm hover:text-white transition-colors duration-200 flex items-center gap-2"
            >
              <span className="flex-1">{card}</span>
              <div className="flex items-center gap-1">
                {/* Power Level */}
                {metadata && (
                  <div className="flex items-center gap-0.5">
                    <Star className={`w-3 h-3 ${getPowerLevelColor(metadata.powerLevel)}`} />
                    <span className={`text-xs ${getPowerLevelColor(metadata.powerLevel)}`}>
                      {metadata.powerLevel.toFixed(1)}
                    </span>
                  </div>
                )}
                {/* Saltiness Warning */}
                {isHighSalt && (
                  <div className="flex items-center gap-0.5" title={`Saltiness: ${metadata.edhrecSaltiness?.toFixed(2)}`}>
                    <AlertTriangle className="w-3 h-3 text-orange-500" />
                    <span className="text-xs text-orange-500">
                      {metadata.edhrecSaltiness?.toFixed(1)}
                    </span>
                  </div>
                )}
                {/* Game Changer Badge */}
                {hasGameChangerTag && (
                  <Badge variant="destructive" className="text-xs py-0 px-1">
                    ⚡
                  </Badge>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

const DeckDisplay: React.FC<DeckDisplayProps> = ({ decklist, initialDeckName, isSaved }) => {
  const [cardMetadata, setCardMetadata] = useState<Map<string, CardMetadata>>(new Map());
  const [loadingMetadata, setLoadingMetadata] = useState(false);

  // Fetch metadata for all cards in the deck
  useEffect(() => {
    const fetchCardMetadata = async () => {
      setLoadingMetadata(true);
      const allCards = new Set<string>();
      
      // Collect all unique card names
      Object.values(decklist).forEach(category => {
        if (Array.isArray(category)) {
          category.forEach(card => allCards.add(card));
        }
      });

      const metadataMap = new Map<string, CardMetadata>();

      // Fetch metadata for each card (batch requests would be better, but this works)
      const fetchPromises = Array.from(allCards).map(async (cardName) => {
        try {
          const response = await fetch(`/api/cards/${encodeURIComponent(cardName)}`);
          if (response.ok) {
            const data = await response.json();
            metadataMap.set(cardName, {
              name: data.name,
              edhrecSaltiness: data.edhrecSaltiness,
              powerLevel: data.powerLevel,
              tags: data.tags || [],
            });
          }
        } catch (error) {
          console.error(`Error fetching metadata for ${cardName}:`, error);
        }
      });

      await Promise.all(fetchPromises);
      setCardMetadata(metadataMap);
      setLoadingMetadata(false);
    };

    fetchCardMetadata();
  }, [decklist]);

  const totalCards = Object.values(decklist).reduce((sum, category) => {
    return sum + (Array.isArray(category) ? category.length : 0);
  }, 0);

  // Calculate deck statistics
  const highSaltCards = Array.from(cardMetadata.values()).filter(
    card => card.edhrecSaltiness !== null && card.edhrecSaltiness >= 1.0
  ).length;
  
  const gameChangerCards = Array.from(cardMetadata.values()).filter(
    card => card.tags.includes('game-changer')
  ).length;

  const avgPowerLevel = cardMetadata.size > 0
    ? Array.from(cardMetadata.values()).reduce((sum, card) => sum + card.powerLevel, 0) / cardMetadata.size
    : 0;

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
        
        {/* Deck Statistics */}
        {!loadingMetadata && cardMetadata.size > 0 && (
          <div className="mt-3 flex justify-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <Star className="w-4 h-4 text-yellow-500" />
              <span className="text-gray-300">
                Avg Power: {avgPowerLevel.toFixed(1)}
              </span>
            </div>
            {highSaltCards > 0 && (
              <div className="flex items-center gap-1">
                <AlertTriangle className="w-4 h-4 text-orange-500" />
                <span className="text-orange-500">
                  {highSaltCards} High-Salt
                </span>
              </div>
            )}
            {gameChangerCards > 0 && (
              <Badge variant="destructive" className="text-xs">
                ⚡ {gameChangerCards} Game-Changers
              </Badge>
            )}
          </div>
        )}
        
        {loadingMetadata && (
          <p className="text-center text-gray-500 text-sm mt-2">Loading card metadata...</p>
        )}
      </div>
      <div className="flex-grow overflow-y-auto pr-2">
        <div className="columns-2 md:columns-3 gap-6">
          {CATEGORY_ORDER.map(category => (
            <CategoryDisplay 
              key={category} 
              title={category} 
              cards={decklist[category]} 
              cardMetadata={cardMetadata}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default DeckDisplay;
