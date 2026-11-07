/**
 * Card Preview Component
 * Shows card image and details on hover or click
 * 
 * Features:
 * - Hover to show preview
 * - Click to expand full view
 * - Keyboard shortcuts (ESC to close)
 * - Uses Scryfall API for card images
 * - Fallback to text details if image unavailable
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { X, ExternalLink } from 'lucide-react';

interface CardPreviewProps {
  cardName: string;
  children: React.ReactNode;
  showOnHover?: boolean;
  className?: string;
}

interface CardData {
  name: string;
  image_uris?: {
    normal?: string;
    large?: string;
    png?: string;
  };
  mana_cost?: string;
  type_line?: string;
  oracle_text?: string;
  power?: string;
  toughness?: string;
  loyalty?: string;
  colors?: string[];
  rarity?: string;
  set_name?: string;
  scryfall_uri?: string;
  prices?: {
    usd?: string;
    usd_foil?: string;
  };
}

export function CardPreview({ cardName, children, showOnHover = true, className = '' }: CardPreviewProps) {
  const [isHovering, setIsHovering] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [cardData, setCardData] = useState<CardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch card data from Scryfall
  useEffect(() => {
    if ((isHovering || isExpanded) && !cardData && !loading) {
      fetchCardData();
    }
  }, [isHovering, isExpanded]);

  // Handle ESC key to close expanded view
  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isExpanded) {
        setIsExpanded(false);
      }
    };

    if (isExpanded) {
      document.addEventListener('keydown', handleEsc);
      return () => document.removeEventListener('keydown', handleEsc);
    }
  }, [isExpanded]);

  const fetchCardData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(cardName)}`
      );

      if (!response.ok) {
        throw new Error('Card not found');
      }

      const data = await response.json();
      setCardData(data);
    } catch (err) {
      console.error('Error fetching card data:', err);
      setError('Could not load card data');
    } finally {
      setLoading(false);
    }
  };

  const handleMouseEnter = () => {
    if (showOnHover) {
      // Delay showing preview to avoid flickering
      timeoutRef.current = setTimeout(() => {
        setIsHovering(true);
      }, 300);
    }
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsHovering(false);
  };

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsExpanded(true);
  };

  const renderManaSymbols = (manaCost: string) => {
    // Simple mana symbol rendering (can be enhanced with actual mana symbols)
    return manaCost.replace(/{/g, '').replace(/}/g, ' ').trim();
  };

  const renderCardContent = (isFullView: boolean = false) => {
    if (loading) {
      return (
        <div className="flex items-center justify-center p-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      );
    }

    if (error || !cardData) {
      return (
        <div className="p-4 text-center text-gray-500">
          <p>{error || 'Card not found'}</p>
          <p className="text-sm mt-2">{cardName}</p>
        </div>
      );
    }

    const imageUrl = cardData.image_uris?.large || cardData.image_uris?.normal || cardData.image_uris?.png;

    return (
      <div className={`${isFullView ? 'max-w-2xl' : 'w-64'}`}>
        {imageUrl && !imageError ? (
          <div className="relative">
            <Image
              src={imageUrl}
              alt={cardData.name}
              width={isFullView ? 488 : 256}
              height={isFullView ? 680 : 357}
              className="rounded-lg shadow-lg"
              onError={() => setImageError(true)}
              priority={isFullView}
            />
          </div>
        ) : (
          // Fallback to text-based card view
          <div className="bg-gray-800 text-white rounded-lg shadow-lg p-4 border-2 border-gray-700">
            <div className="mb-3">
              <h3 className="text-lg font-bold">{cardData.name}</h3>
              {cardData.mana_cost && (
                <p className="text-sm text-gray-300">{renderManaSymbols(cardData.mana_cost)}</p>
              )}
            </div>

            <div className="border-t border-gray-600 pt-2 mb-2">
              <p className="text-sm text-gray-300">{cardData.type_line}</p>
            </div>

            {cardData.oracle_text && (
              <div className="text-sm mb-3 space-y-1">
                {cardData.oracle_text.split('\n').map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
              </div>
            )}

            <div className="border-t border-gray-600 pt-2 flex justify-between text-sm">
              {(cardData.power && cardData.toughness) && (
                <span className="font-bold">{cardData.power}/{cardData.toughness}</span>
              )}
              {cardData.loyalty && (
                <span className="font-bold">Loyalty: {cardData.loyalty}</span>
              )}
              {cardData.rarity && (
                <span className="text-gray-400 capitalize">{cardData.rarity}</span>
              )}
            </div>

            {cardData.set_name && (
              <div className="text-xs text-gray-400 mt-2">
                {cardData.set_name}
              </div>
            )}

            {cardData.prices?.usd && (
              <div className="text-xs text-green-400 mt-2">
                ${cardData.prices.usd}
              </div>
            )}
          </div>
        )}

        {isFullView && cardData.scryfall_uri && (
          <div className="mt-4 text-center">
            <a
              href={cardData.scryfall_uri}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-blue-500 hover:text-blue-400 text-sm"
            >
              View on Scryfall <ExternalLink size={14} />
            </a>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Hoverable/Clickable wrapper */}
      <span
        className={`relative inline-block ${className}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
      >
        <span className="cursor-pointer hover:text-blue-500 transition-colors border-b border-dotted border-current">
          {children}
        </span>

        {/* Hover preview tooltip */}
        {showOnHover && isHovering && !isExpanded && (
          <div className="absolute z-50 left-0 top-full mt-2 pointer-events-none">
            <div className="bg-gray-900 rounded-lg shadow-2xl border border-gray-700">
              {renderCardContent(false)}
            </div>
          </div>
        )}
      </span>

      {/* Expanded full-screen modal */}
      {isExpanded && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 backdrop-blur-sm p-4"
          onClick={() => setIsExpanded(false)}
        >
          <div
            className="relative bg-gray-900 rounded-lg shadow-2xl max-h-screen overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setIsExpanded(false)}
              className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors z-10"
              aria-label="Close"
            >
              <X size={24} />
            </button>

            <div className="p-6">
              {renderCardContent(true)}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// Convenience wrapper for card names in text
export function CardLink({ cardName }: { cardName: string }) {
  return (
    <CardPreview cardName={cardName}>
      {cardName}
    </CardPreview>
  );
}
