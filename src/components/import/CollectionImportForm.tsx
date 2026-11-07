'use client';

import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Upload } from 'lucide-react';

interface CollectionImportFormProps {
  onSubmit: (data: { collection: string; enrich: boolean }) => Promise<void>;
}

export default function CollectionImportForm({ onSubmit }: CollectionImportFormProps) {
  const [collection, setCollection] = useState('');
  const [enrich, setEnrich] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['text/csv', 'text/plain', 'application/vnd.ms-excel'];
    const fileExtension = file.name.toLowerCase().split('.').pop();
    
    if (!allowedTypes.includes(file.type) && fileExtension !== 'csv') {
      alert('Invalid file type. Please upload a CSV or TXT file.');
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
      setCollection(text);
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
      await onSubmit({ collection, enrich });
      setCollection('');
      setEnrich(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
      <div className="flex gap-2">
        <Textarea
          name="collection"
          value={collection}
          onChange={(e) => setCollection(e.target.value)}
          placeholder="Count,Name,Edition
1,Sol Ring,Commander 2021
4,Lightning Bolt,Alpha
..."
          className="min-h-[250px] font-mono text-sm flex-1"
        />
      </div>

      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2"
        >
          <Upload className="w-4 h-4" />
          Upload CSV File
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv,.txt,text/plain"
          onChange={handleFileUpload}
          className="hidden"
          aria-label="Upload CSV file"
        />
      </div>

      <label className="flex items-center gap-2 cursor-pointer group/check">
        <input
          type="checkbox"
          checked={enrich}
          onChange={(e) => setEnrich(e.target.checked)}
          className="w-4 h-4 cursor-pointer"
        />
        <span className="group-hover/check:text-purple-600 transition-colors">
          ✨ Enrich with Scryfall data (slower, but more complete)
        </span>
      </label>

      <Button
        type="submit"
        size="lg"
        disabled={!collection.trim() || isSubmitting}
        className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700"
      >
        {isSubmitting ? 'Importing...' : 'Import Collection'}
      </Button>
    </form>
  );
}
