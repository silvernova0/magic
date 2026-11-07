
import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

const Header: React.FC = () => {
  return (
    <header className="flex justify-between items-center">
      <h1 className="text-4xl sm:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-600">
        MTG AI Commander Deck Builder
      </h1>
      <Button asChild>
        <Link href="/decks">My Decks</Link>
      </Button>
    </header>
  );
};

export default Header;
