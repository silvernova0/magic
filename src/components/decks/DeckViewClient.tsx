/**
 * DeckViewClient - Client component for viewing a deck
 * Displays full deck details with share, edit, and export functionality
 */

'use client';

import { Deck } from '@prisma/client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Share2, Edit, Trash2, Download, Copy, Check } from 'lucide-react';
import { CardPreview } from '../CardPreview';

interface DeckWithUser extends Deck {
  user: {
    id: string;
    name: string | null;
    email: string | null;
  };
}

interface Props {
  deck: DeckWithUser;
  isOwner: boolean;
}

const getStatusBadgeColor = (status: string) => {
  switch (status) {
    case 'GENERATED':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    case 'SAVED':
      return 'bg-green-500/20 text-green-400 border-green-500/50';
    case 'IMPORTED':
      return 'bg-purple-500/20 text-purple-400 border-purple-500/50';
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

export default function DeckViewClient({ deck, isOwner }: Props) {
  const router = useRouter();
  const [copied, setCopied] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const cardCount = getDeckCardCount(deck.decklist);
  const isValidDeck = cardCount === 100;

  const handleShare = () => {
    const url = `${window.location.origin}/decks/${deck.id}`;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${deck.name}"? This action cannot be undone.`)) {
      return;
    }

    setIsDeleting(true);
    try {
      const response = await fetch(`/api/decks/${deck.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete deck');
      }

      router.push('/decks');
    } catch (error) {
      console.error('Error deleting deck:', error);
      alert('Failed to delete deck. Please try again.');
      setIsDeleting(false);
    }
  };

  const exportDeck = () => {
    const deckText = generateDeckText(deck);
    const blob = new Blob([deckText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${deck.name}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const generateDeckText = (deck: Deck): string => {
    const decklist = deck.decklist as any;
    let text = `# ${deck.name}\n`;
    text += `# Theme: ${deck.theme}\n`;
    text += `# Power Level: ${deck.powerLevel}\n`;
    if (deck.description) {
      text += `# Description: ${deck.description}\n`;
    }
    text += `\n`;

    const addSection = (title: string, cards: any[]) => {
      if (cards && cards.length > 0) {
        text += `\n## ${title}\n`;
        cards.forEach((card: any) => {
          const cardName = typeof card === 'string' ? card : card.name;
          text += `1 ${cardName}\n`;
        });
      }
    };

    if (decklist.commander) {
      addSection('Commander', Array.isArray(decklist.commander) ? decklist.commander : [decklist.commander]);
    }
    addSection('Creatures', decklist.creatures);
    addSection('Instants', decklist.instants);
    addSection('Sorceries', decklist.sorceries);
    addSection('Artifacts', decklist.artifacts);
    addSection('Enchantments', decklist.enchantments);
    addSection('Planeswalkers', decklist.planeswalkers);
    addSection('Lands', decklist.lands);

    return text;
  };

  const renderCardList = (title: string, cards: any[]) => {
    if (!cards || cards.length === 0) return null;

    return (
      <div className="mb-6">
        <h3 className="text-xl font-bold text-purple-300 mb-3 flex items-center gap-2">
          {title}
          <span className="text-sm text-purple-400 font-normal">({cards.length})</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
          {cards.map((card: any, index: number) => {
            const cardName = typeof card === 'string' ? card : card.name;
            return (
              <div key={index} className="text-purple-200 hover:text-purple-100 transition-colors">
                <CardPreview cardName={cardName}>
                  <span>{cardName}</span>
                </CardPreview>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const decklist = deck.decklist as any;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-900/40 via-blue-900/40 to-purple-900/40 border-2 border-purple-500/30 rounded-xl p-8 backdrop-blur-xl">
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-4xl font-bold text-purple-300">{deck.name}</h1>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold border ${getStatusBadgeColor(
                    deck.status
                  )}`}
                >
                  {deck.status}
                </span>
              </div>
              <p className="text-purple-200/80 mb-2">
                Created by {deck.user.name || deck.user.email} on{' '}
                {new Date(deck.createdAt).toLocaleDateString()}
              </p>
              {deck.description && (
                <p className="text-purple-200/70 mt-3">{deck.description}</p>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleShare}
                className="p-3 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg transition-colors"
                title="Share deck"
              >
                {copied ? <Check className="w-5 h-5" /> : <Share2 className="w-5 h-5" />}
              </button>
              <button
                onClick={exportDeck}
                className="p-3 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg transition-colors"
                title="Export deck"
              >
                <Download className="w-5 h-5" />
              </button>
              {isOwner && (
                <>
                  <Link
                    href={`/decks/${deck.id}/edit`}
                    className="p-3 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg transition-colors"
                    title="Edit deck"
                  >
                    <Edit className="w-5 h-5" />
                  </Link>
                  <button
                    onClick={handleDelete}
                    disabled={isDeleting}
                    className="p-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors disabled:opacity-50"
                    title="Delete deck"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="text-sm text-purple-400">Cards</div>
              <div className={`text-2xl font-bold ${isValidDeck ? 'text-green-400' : 'text-red-400'}`}>
                {cardCount}/100
              </div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="text-sm text-purple-400">Theme</div>
              <div className="text-xl font-bold text-purple-300">{deck.theme}</div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="text-sm text-purple-400">Power Level</div>
              <div className="text-xl font-bold text-purple-300">{deck.powerLevel}</div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="text-sm text-purple-400">Updated</div>
              <div className="text-xl font-bold text-purple-300">
                {new Date(deck.updatedAt).toLocaleDateString()}
              </div>
            </div>
          </div>
        </div>

        {/* Back Button */}
        <Link
          href="/decks"
          className="inline-block px-4 py-2 bg-purple-600/20 text-purple-300 rounded-lg hover:bg-purple-600/30 transition-colors"
        >
          ← Back to Library
        </Link>

        {/* Decklist */}
        <div className="bg-slate-900/50 backdrop-blur-xl border-2 border-purple-500/30 rounded-xl p-8">
          <h2 className="text-3xl font-bold text-purple-300 mb-6">Decklist</h2>
          
          {decklist.commander && renderCardList(
            'Commander',
            Array.isArray(decklist.commander) ? decklist.commander : [decklist.commander]
          )}
          {renderCardList('Creatures', decklist.creatures)}
          {renderCardList('Instants', decklist.instants)}
          {renderCardList('Sorceries', decklist.sorceries)}
          {renderCardList('Artifacts', decklist.artifacts)}
          {renderCardList('Enchantments', decklist.enchantments)}
          {renderCardList('Planeswalkers', decklist.planeswalkers)}
          {renderCardList('Lands', decklist.lands)}
        </div>
      </div>
    </div>
  );
}
