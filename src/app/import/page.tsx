'use client';

import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import CollectionImportForm from '@/components/import/CollectionImportForm';
import DeckImportForm from '@/components/import/DeckImportForm';
import { useRouter } from 'next/navigation';

export default function ImportPage() {
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const router = useRouter();

  const handleCollectionImport = async (data: { collection: string; enrich: boolean }) => {
    try {
      const response = await fetch('/api/import/collection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: result.message || 'Collection imported successfully!' });
        setTimeout(() => {
          router.push('/collection');
        }, 2000);
      } else {
        setMessage({ type: 'error', text: result.error || 'Failed to import collection' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'An error occurred during import' });
    }
  };

  const handleDeckImport = async (data: { deck: string; enrich: boolean }) => {
    try {
      const response = await fetch('/api/import/deck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: result.message || 'Deck imported successfully!' });
        setTimeout(() => {
          router.push('/collection');
        }, 2000);
      } else {
        setMessage({ type: 'error', text: result.error || 'Failed to import deck' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'An error occurred during import' });
    }
  };

  return (
    <div className="container mx-auto max-w-7xl">
      <div className="mb-8 p-8 rounded-xl bg-gradient-to-br from-purple-500/10 via-indigo-500/10 to-blue-500/10 border border-purple-500/20">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 bg-clip-text text-transparent mb-2">
          Import / Export
        </h1>
        <p className="text-lg text-muted-foreground">
          Quickly import your collection and decklists
        </p>
      </div>

      {message && (
        <div
          className={`mb-6 p-4 rounded-lg border-2 ${
            message.type === 'success'
              ? 'bg-green-50 dark:bg-green-950 border-green-500 text-green-700 dark:text-green-300'
              : 'bg-red-50 dark:bg-red-950 border-red-500 text-red-700 dark:text-red-300'
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card className="group hover:shadow-xl transition-all duration-300 border-2 hover:border-purple-500/50">
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-2 group-hover:text-purple-600 transition-colors">
              <span className="text-3xl">📚</span>
              Import Collection
            </CardTitle>
            <CardDescription className="text-base">
              Upload a CSV file or paste your collection data. Format: Count, Name, Edition (optional).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CollectionImportForm onSubmit={handleCollectionImport} />
          </CardContent>
        </Card>

        <Card className="group hover:shadow-xl transition-all duration-300 border-2 hover:border-indigo-500/50">
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-2 group-hover:text-indigo-600 transition-colors">
              <span className="text-3xl">🎴</span>
              Import Deck
            </CardTitle>
            <CardDescription className="text-base">
              Upload a deck file or paste your decklist. Format: "quantity cardname (SET) number".
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DeckImportForm onSubmit={handleDeckImport} />
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-500/20">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-lg mb-2">💡 CSV Format</h3>
            <p className="text-sm text-muted-foreground">
              Collection imports support CSV with Count, Name, and optional Edition columns. Upload .csv or .txt files (max 2MB).
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-purple-500/20">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-lg mb-2">⚡ Deck Format</h3>
            <p className="text-sm text-muted-foreground">
              Deck imports support standard format: "quantity cardname (SET) number". Upload .txt, .dec, or .dck files (max 2MB).
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/20">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-lg mb-2">🔒 Security</h3>
            <p className="text-sm text-muted-foreground">
              Files are validated for type and size. Only CSV and text files under 2MB are accepted for your protection.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
