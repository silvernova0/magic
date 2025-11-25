'use client';

import { Deck, DeckStatus } from '@prisma/client';
import Link from 'next/link';
import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Library, Sparkles, Save, Zap, Trash2, DollarSign, Filter, ArrowUpDown, BarChart3, CheckSquare, Square, Download, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DeckStats } from './DeckStats';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import JSZip from 'jszip';
import { saveAs } from 'file-saver';

type DeckWithPrice = Deck & {
  price?: number;
  currency?: string;
  missingPrice?: number;
};

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

import { getDeckCardCount } from '@/lib/deck-utils';

interface DecksClientProps {
  initialDecks: DeckWithPrice[];
}

export default function DecksClient({ initialDecks }: DecksClientProps) {
  const [decks, setDecks] = useState<DeckWithPrice[]>(initialDecks);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'date' | 'price-asc' | 'price-desc' | 'name'>('date');
  const [filterTheme, setFilterTheme] = useState<string>('all');
  const [expandedStatsId, setExpandedStatsId] = useState<string | null>(null);

  // Multi-select state
  const [selectedDeckIds, setSelectedDeckIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [isBulkExporting, setIsBulkExporting] = useState(false);

  const router = useRouter();

  const stats = {
    total: decks.length,
    generated: decks.filter((d) => d.status === 'GENERATED').length,
    saved: decks.filter((d) => d.status === 'SAVED').length,
    imported: 0,
    totalValue: decks.reduce((sum, d) => sum + (d.price || 0), 0)
  };

  const uniqueThemes = useMemo(() => {
    const themes = new Set(decks.map(d => d.theme));
    return Array.from(themes).sort();
  }, [decks]);

  const filteredAndSortedDecks = useMemo(() => {
    let result = [...decks];

    // Filter by search
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(d =>
        d.name.toLowerCase().includes(q) ||
        d.theme.toLowerCase().includes(q) ||
        (d.description && d.description.toLowerCase().includes(q))
      );
    }

    // Filter by theme
    if (filterTheme !== 'all') {
      result = result.filter(d => d.theme === filterTheme);
    }

    // Sort
    switch (sortBy) {
      case 'date':
        result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
        break;
      case 'price-asc':
        result.sort((a, b) => (a.price || 0) - (b.price || 0));
        break;
      case 'price-desc':
        result.sort((a, b) => (b.price || 0) - (a.price || 0));
        break;
      case 'name':
        result.sort((a, b) => a.name.localeCompare(b.name));
        break;
    }

    return result;
  }, [decks, searchQuery, sortBy, filterTheme]);

  // Selection handlers
  const toggleSelection = (id: string) => {
    const newSelection = new Set(selectedDeckIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedDeckIds(newSelection);
  };

  const selectAll = () => {
    if (selectedDeckIds.size === filteredAndSortedDecks.length) {
      setSelectedDeckIds(new Set());
    } else {
      setSelectedDeckIds(new Set(filteredAndSortedDecks.map(d => d.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (!confirm(`Are you sure you want to delete ${selectedDeckIds.size} decks? This action cannot be undone.`)) {
      return;
    }

    setIsBulkDeleting(true);
    try {
      // Delete sequentially to avoid overwhelming server (or use Promise.all if API handles it)
      // Ideally we'd have a bulk delete endpoint, but loop is fine for now.
      for (const id of Array.from(selectedDeckIds)) {
        await fetch(`/api/decks/${id}`, { method: 'DELETE' });
      }

      // Update local state
      setDecks(decks.filter(d => !selectedDeckIds.has(d.id)));
      setSelectedDeckIds(new Set());
      router.refresh();
    } catch (error) {
      console.error('Error bulk deleting:', error);
      alert('Failed to delete some decks.');
    } finally {
      setIsBulkDeleting(false);
    }
  };

  const handleBulkExport = async () => {
    setIsBulkExporting(true);
    try {
      const zip = new JSZip();
      const selectedDecks = decks.filter(d => selectedDeckIds.has(d.id));

      for (const deck of selectedDecks) {
        // Format decklist as text
        const decklist = deck.decklist as any;
        let content = `// ${deck.name}\n// Commander: ${Array.isArray(decklist.commander) ? decklist.commander.join(' + ') : decklist.commander}\n\n`;

        // Helper to add section
        const addSection = (title: string, cards: string[]) => {
          if (cards && cards.length > 0) {
            content += `${title}\n`;
            cards.forEach(c => content += `1 ${c}\n`);
            content += '\n';
          }
        };

        addSection('Creatures', decklist.creatures);
        addSection('Instants', decklist.instants);
        addSection('Sorceries', decklist.sorceries);
        addSection('Artifacts', decklist.artifacts);
        addSection('Enchantments', decklist.enchantments);
        addSection('Planeswalkers', decklist.planeswalkers);
        addSection('Lands', decklist.lands);

        // Sanitize filename
        const filename = `${deck.name.replace(/[^a-z0-9]/gi, '_')}.txt`;
        zip.file(filename, content);
      }

      const content = await zip.generateAsync({ type: 'blob' });
      saveAs(content, `magic_decks_export_${new Date().toISOString().split('T')[0]}.zip`);

      // Optional: clear selection after export? No, keep it.
    } catch (error) {
      console.error('Error exporting decks:', error);
      alert('Failed to export decks.');
    } finally {
      setIsBulkExporting(false);
    }
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
      if (selectedDeckIds.has(deckId)) {
        const newSelection = new Set(selectedDeckIds);
        newSelection.delete(deckId);
        setSelectedDeckIds(newSelection);
      }

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
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 p-6 pb-24">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-purple-500/10 via-indigo-500/10 to-blue-500/10 border border-purple-500/20 p-8 backdrop-blur-xl">
          <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div className="flex items-center gap-3">
              <Library className="h-10 w-10 text-purple-400" />
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 bg-clip-text text-transparent mb-2">
                  My Deck Library
                </h1>
                <p className="text-lg text-muted-foreground">
                  View and manage all your Commander decks
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <Link
                href="/deckbuilder"
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-lg font-medium hover:scale-105 transition-transform"
              >
                <Sparkles className="h-5 w-5" />
                Generate Deck
              </Link>
            </div>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20 rounded-xl p-6 hover:scale-105 transition-transform">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Decks</p>
                <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">{stats.total}</p>
              </div>
              <Zap className="h-12 w-12 text-purple-600/50 dark:text-purple-400/50" />
            </div>
          </div>
          <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-500/20 rounded-xl p-6 hover:scale-105 transition-transform">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">AI Generated</p>
                <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">{stats.generated}</p>
              </div>
              <Sparkles className="h-12 w-12 text-blue-600/50 dark:text-blue-400/50" />
            </div>
          </div>
          <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-500/20 rounded-xl p-6 hover:scale-105 transition-transform">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Value</p>
                <p className="text-3xl font-bold text-green-600 dark:text-green-400">
                  ${stats.totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <DollarSign className="h-12 w-12 text-green-600/50 dark:text-green-400/50" />
            </div>
          </div>
          <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 rounded-xl p-6 hover:scale-105 transition-transform">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Saved</p>
                <p className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">{stats.saved}</p>
              </div>
              <Save className="h-12 w-12 text-indigo-600/50 dark:text-indigo-400/50" />
            </div>
          </div>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col md:flex-row gap-4 items-center bg-slate-900/50 p-4 rounded-xl border border-purple-500/20">
          <div className="relative w-full md:w-96">
            <Input
              placeholder="Search decks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-slate-950/50 border-purple-500/30"
            />
            <Filter className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          </div>

          <div className="flex gap-2 w-full md:w-auto ml-auto">
            <Button
              variant="outline"
              onClick={selectAll}
              className="border-purple-500/30 bg-slate-950/50 hover:bg-purple-500/10"
            >
              {selectedDeckIds.size === filteredAndSortedDecks.length && filteredAndSortedDecks.length > 0 ? (
                <><CheckSquare className="w-4 h-4 mr-2" /> Deselect All</>
              ) : (
                <><Square className="w-4 h-4 mr-2" /> Select All</>
              )}
            </Button>

            <Select value={filterTheme} onValueChange={setFilterTheme}>
              <SelectTrigger className="w-[180px] border-purple-500/30 bg-slate-950/50">
                <SelectValue placeholder="Theme" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Themes</SelectItem>
                {uniqueThemes.map(t => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={(val: any) => setSortBy(val)}>
              <SelectTrigger className="w-[180px] border-purple-500/30 bg-slate-950/50">
                <SelectValue placeholder="Sort By" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="date">Newest First</SelectItem>
                <SelectItem value="price-desc">Price: High to Low</SelectItem>
                <SelectItem value="price-asc">Price: Low to High</SelectItem>
                <SelectItem value="name">Name (A-Z)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Decks Grid */}
        {filteredAndSortedDecks.length === 0 ? (
          <div className="bg-slate-900/50 backdrop-blur-xl border-2 border-purple-500/30 rounded-xl p-12 text-center">
            <div className="text-6xl mb-4">🃏</div>
            <h3 className="text-2xl font-semibold text-purple-300 mb-2">No Decks Found</h3>
            <p className="text-purple-200/60 mb-6">
              {decks.length === 0 ? "Start building your first Commander deck!" : "Try adjusting your filters."}
            </p>
            {decks.length === 0 && (
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
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredAndSortedDecks.map((deck) => {
              const cardCount = getDeckCardCount(deck);
              const isValidDeck = cardCount === 100;
              const isDeleting = deletingId === deck.id;
              const isSelected = selectedDeckIds.has(deck.id);

              return (
                <div
                  key={deck.id}
                  className={`group bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-xl border-2 rounded-xl p-6 transition-all relative ${isSelected
                    ? 'border-purple-500 shadow-[0_0_15px_-5px_rgba(168,85,247,0.5)] scale-[1.02]'
                    : 'border-purple-500/30 hover:border-purple-400/50 hover:scale-[1.02]'
                    }`}
                >
                  {/* Selection Checkbox */}
                  <div className="absolute top-4 left-4 z-20">
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        toggleSelection(deck.id);
                      }}
                      className={`w-6 h-6 rounded border flex items-center justify-center transition-colors ${isSelected
                        ? 'bg-purple-600 border-purple-600 text-white'
                        : 'bg-slate-950/50 border-purple-500/30 text-transparent hover:border-purple-400'
                        }`}
                    >
                      <CheckSquare className="w-4 h-4" />
                    </button>
                  </div>

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
                    {isDeleting ? <span className="animate-spin">⏳</span> : <Trash2 className="h-4 w-4" />}
                  </button>

                  <Link href={`/decks/${deck.id}`} className="block pl-8">
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
                        className={`text-sm font-medium ${isValidDeck ? 'text-green-400' : 'text-red-400'
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
                        <span className="text-purple-400">💰 Price:</span>
                        <span className="text-green-400 font-semibold">
                          ${(deck.price || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                        {deck.missingPrice && deck.missingPrice > 0 && (
                          <span className="text-xs text-muted-foreground" title={`${deck.missingPrice} cards missing price data`}>
                            (est.)
                          </span>
                        )}
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

                  {/* Stats Toggle */}
                  <div className="mt-2 pl-8">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full text-xs text-purple-400 hover:text-purple-300 hover:bg-purple-500/10"
                      onClick={(e) => {
                        e.preventDefault();
                        setExpandedStatsId(expandedStatsId === deck.id ? null : deck.id);
                      }}
                    >
                      {expandedStatsId === deck.id ? 'Hide Stats' : 'Show Stats'} <BarChart3 className="ml-2 h-3 w-3" />
                    </Button>
                  </div>

                  {/* Expanded Stats */}
                  {expandedStatsId === deck.id && (
                    <div className="mt-4 pt-4 border-t border-purple-500/20 animate-in slide-in-from-top-2 fade-in duration-200 pl-8">
                      <DeckStats decklist={deck.decklist} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Bulk Actions Bar */}
      {selectedDeckIds.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl px-4 animate-in slide-in-from-bottom-10 fade-in duration-300">
          <div className="bg-slate-900/90 backdrop-blur-xl border border-purple-500/50 rounded-xl shadow-2xl p-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="bg-purple-600 text-white rounded-full w-8 h-8 flex items-center justify-center font-bold">
                {selectedDeckIds.size}
              </div>
              <span className="text-purple-200 font-medium">Selected</span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedDeckIds(new Set())}
                className="border-purple-500/30 hover:bg-purple-500/10 text-purple-300"
              >
                <X className="w-4 h-4 mr-2" /> Cancel
              </Button>

              <Button
                variant="default"
                size="sm"
                onClick={handleBulkExport}
                disabled={isBulkExporting}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {isBulkExporting ? <span className="animate-spin mr-2">⏳</span> : <Download className="w-4 h-4 mr-2" />}
                Export ZIP
              </Button>

              <Button
                variant="destructive"
                size="sm"
                onClick={handleBulkDelete}
                disabled={isBulkDeleting}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                {isBulkDeleting ? <span className="animate-spin mr-2">⏳</span> : <Trash2 className="w-4 h-4 mr-2" />}
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
