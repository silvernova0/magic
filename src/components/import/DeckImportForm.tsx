'use client';

import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Upload } from 'lucide-react';

interface DeckImportFormProps {
  onSubmit: (data: { deck: string; enrich: boolean }) => Promise<void>;
}

export default function DeckImportForm({ onSubmit }: DeckImportFormProps) {
  const [deck, setDeck] = useState('');
  const [enrich, setEnrich] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['text/plain'];
    const fileExtension = file.name.toLowerCase().split('.').pop();
    const allowedExtensions = ['txt', 'dec', 'dck'];
    
    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension || '')) {
      alert('Invalid file type. Please upload a TXT, DEC, or DCK file.');
      event.target.value = ''; // Reset file input
      return;
    }

    // Validate file size (2MB limit)
    const maxSize = 2 * 1024 * 1024; // 2MB in bytes
    if (file.size > maxSize) {
      alert(`File is too large (${(file.size / 1024 / 1024).toFixed(2)}MB). Maximum size is 2MB.`);
      event.target.value = ''; // Reset file input
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setDeck(text);
    };
    reader.onerror = () => {
      alert('Error reading file. Please try again.');
    };
    reader.readAsText(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit({ deck, enrich });
      setDeck('');
      setEnrich(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
      <Textarea
        name="deck"
        value={deck}
        onChange={(e) => setDeck(e.target.value)}
        placeholder="1 Sol Ring (C21) 314
1 Command Tower
4 Lightning Bolt (LEA) 161
..."
        className="min-h-[250px] font-mono text-sm"
      />

      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2"
        >
          <Upload className="w-4 h-4" />
          Upload Deck File
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,text/plain,.dec,.dck"
          onChange={handleFileUpload}
          className="hidden"
          aria-label="Upload deck file"
        />
      </div>

      <label className="flex items-center gap-2 cursor-pointer group/check">
        <input
          type="checkbox"
          checked={enrich}
          onChange={(e) => setEnrich(e.target.checked)}
          className="w-4 h-4 cursor-pointer"
        />
        <span className="group-hover/check:text-indigo-600 transition-colors">
          ✨ Enrich with Scryfall data (slower, but more complete)
        </span>
      </label>

      <Button
        type="submit"
        size="lg"
        disabled={!deck.trim() || isSubmitting}
        className="bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700"
      >
        {isSubmitting ? 'Importing...' : 'Import Deck'}
      </Button>
    </form>
  );
}
