"use client";

import { useState } from 'react';
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
    <main className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">Commander Deck Search</h1>

      <form onSubmit={searchCommander} className="flex gap-2 mb-6">
        <input
          className="bg-white/5 rounded px-3 py-2 flex-1"
          placeholder="Enter commander name (e.g. Tatyova, Benthic Druid)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Button type="submit">Search</Button>
      </form>

      {suggestions.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm text-muted-foreground mb-2">Suggestions</h4>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((s: any) => (
              <button key={s.name} className="px-2 py-1 bg-white/5 rounded" onClick={() => { setQuery(s.name); setSuggestions([]); searchCommander(); }}>
                {s.name} {s.set_name ? `(${s.set_name})` : ''}
              </button>
            ))}
          </div>
        </div>
      )}

      {loading && <p>Searching EDHREC...</p>}
      {error && <p className="text-red-400">{error}</p>}

      {results && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Discovered Links</CardTitle>
              <CardDescription>External deck links found on EDHREC</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="list-disc pl-6 space-y-2">
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
    </main>
  );
}
