"use client";

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

function ImportReviewModal({ deck, onClose, onImport }: any) {
  if (!deck) return null;
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-surface p-6 rounded shadow max-w-2xl w-full">
        <h3 className="text-xl font-semibold mb-4">Import Review - {deck.title}</h3>
        <div className="max-h-64 overflow-auto mb-4">
          {deck.cards && deck.cards.length ? (
            <ul className="list-inside">
              {deck.cards.map((c: any, i: number) => (
                <li key={i}>{c.qty} x {c.name}</li>
              ))}
            </ul>
          ) : (<p>No cards parsed.</p>)}
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={() => onImport(deck)}>Import</Button>
        </div>
      </div>
    </div>
  );
}

export default function CommanderPage() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [importing, setImporting] = useState<string | null>(null);
  const [modalDeck, setModalDeck] = useState<any | null>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [commanderSuggestions, setCommanderSuggestions] = useState<string[]>([]);
  const [showAutocomplete, setShowAutocomplete] = useState(false);

  // Auto-complete commander search using local database
  useEffect(() => {
    const fetchCommanderSuggestions = async () => {
      if (query.length < 2) {
        setCommanderSuggestions([]);
        setShowAutocomplete(false);
        return;
      }

      try {
        // Use local card database with isCommander filter and EDHREC ranking
        const params = new URLSearchParams({
          name: query,
          isCommander: 'true',
          sortBy: 'edhrecRank',
          sortOrder: 'asc',
          limit: '10',
        });
        
        const response = await fetch(`/api/cards/search?${params}`);
        if (response.ok) {
          const data = await response.json();
          const suggestions = data.cards?.map((card: any) => card.name) || [];
          setCommanderSuggestions(suggestions);
          setShowAutocomplete(suggestions.length > 0);
        }
      } catch (error) {
        console.error('Error fetching commander suggestions:', error);
      }
    };

    const debounce = setTimeout(fetchCommanderSuggestions, 300);
    return () => clearTimeout(debounce);
  }, [query]);

  async function searchCommander(e?: React.FormEvent) {
    e?.preventDefault();
    setError(null);
    setResults(null);
    setSuggestions([]);
    if (!query) return setError('Enter a commander name');
    setLoading(true);
    try {
      const res = await fetch('/api/commander/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Failed');
      setResults(json);
      setSuggestions(json.scry || []);
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  async function importDeck(deck: any) {
    setModalDeck(deck);
  }

  async function confirmImport(deck: any) {
    setImporting(deck.url);
    try {
      const res = await fetch('/api/decks/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deck }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Import failed');
      alert('Imported: ' + (json.importedCount || 0) + ' cards');
    } catch (err: any) {
      alert('Import error: ' + (err.message || String(err)));
    } finally {
      setImporting(null);
      setModalDeck(null);
    }
  }

  return (
    <div className="container mx-auto max-w-7xl">
      {/* Hero Header */}
      <div className="mb-8 p-8 rounded-xl bg-gradient-to-br from-purple-500/10 via-indigo-500/10 to-blue-500/10 border border-purple-500/20">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 bg-clip-text text-transparent mb-2">
          Commander Deck Search
        </h1>
        <p className="text-lg text-muted-foreground">
          Discover popular Commander decks from EDHREC and MTGTop8
        </p>
      </div>

      <Card className="mb-6 border-2">
        <CardContent className="pt-6">
          <form onSubmit={searchCommander} className="flex gap-2">
            <div className="flex-1 relative">
              <input
                className="bg-background border-2 border-input hover:border-purple-500/50 focus:border-purple-500 transition-colors rounded-lg px-4 py-3 w-full text-lg"
                placeholder="Enter commander name (e.g. Tatyova, Benthic Druid)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => setShowAutocomplete(commanderSuggestions.length > 0)}
                onBlur={() => setTimeout(() => setShowAutocomplete(false), 200)}
                autoComplete="off"
              />
              {showAutocomplete && commanderSuggestions.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-background border-2 border-purple-500/50 rounded-lg shadow-lg max-h-60 overflow-auto">
                  {commanderSuggestions.map((name, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className="w-full text-left px-4 py-2 hover:bg-purple-500/20 transition-colors border-b border-border last:border-0"
                      onClick={() => {
                        setQuery(name);
                        setCommanderSuggestions([]);
                        setShowAutocomplete(false);
                      }}
                    >
                      {name}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <Button type="submit" size="lg" className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700">
              Search
            </Button>
          </form>
        </CardContent>
      </Card>

      {suggestions.length > 0 && (
        <Card className="mb-6 bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-500/20">
          <CardContent className="pt-6">
            <h4 className="text-sm font-semibold text-muted-foreground mb-3">💡 Card Suggestions</h4>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((s: any) => (
                <button 
                  key={s.name} 
                  className="px-4 py-2 bg-background border-2 border-blue-500/30 hover:border-blue-500 rounded-lg transition-all hover:scale-105 hover:shadow-lg"
                  onClick={() => { setQuery(s.name); setSuggestions([]); searchCommander(); }}
                >
                  <span className="font-medium">{s.name}</span>
                  {s.set_name && <span className="text-muted-foreground text-sm ml-2">({s.set_name})</span>}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {loading && (
        <Card className="border-2 border-purple-500/50">
          <CardContent className="py-12 text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-purple-500 border-t-transparent mb-4"></div>
            <p className="text-lg text-purple-600 font-medium">Searching EDHREC...</p>
          </CardContent>
        </Card>
      )}
      
      {error && (
        <Card className="border-2 border-red-500/50 bg-red-500/10">
          <CardContent className="py-8 text-center">
            <p className="text-red-500 text-lg font-medium">⚠️ {error}</p>
          </CardContent>
        </Card>
      )}

      {results && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="border-2 hover:border-purple-500/50 transition-all">
            <CardHeader>
              <CardTitle className="text-2xl flex items-center gap-2">
                <span>🔗</span>
                Discovered Links
              </CardTitle>
              <CardDescription className="text-base">External deck links found on EDHREC</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {results.links && results.links.length ? (
                  results.links.map((l: string) => (
                    <li key={l} className="truncate">
                      <a href={l} target="_blank" rel="noreferrer" className="text-sky-400 underline">
                        {l}
                      </a>
                    </li>
                  ))
                ) : (
                  <li>No external links found.</li>
                )}
              </ul>
            </CardContent>
          </Card>

          <div className="space-y-4">
            {(results.samples || []).map((deck: any) => (
              <Card key={deck.url}>
                <CardHeader>
                  <CardTitle>{deck.title}</CardTitle>
                  <CardDescription className="truncate">{deck.url}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="mb-2 flex gap-2">
                    <Button onClick={() => importDeck(deck)} disabled={importing !== null}>
                      {importing === deck.url ? 'Importing...' : 'Import to Collection'}
                    </Button>
                    <a href={deck.url} target="_blank" rel="noreferrer">
                      <Button variant="secondary">Open Source</Button>
                    </a>
                  </div>
                  <div className="max-h-48 overflow-auto text-sm">
                    {deck.cards && deck.cards.length ? (
                      <ul className="list-inside">
                        {deck.cards.map((c: any, i: number) => (
                          <li key={i}>
                            {c.qty} x {c.name}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No cards parsed.</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      <ImportReviewModal deck={modalDeck} onClose={() => setModalDeck(null)} onImport={confirmImport} />
    </div>
  );
}
