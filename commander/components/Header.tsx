
import React from 'react';

const Header: React.FC = () => {
  return (
    <header className="text-center">
      <h1 className="text-4xl sm:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-600">
        MTG AI Commander Deck Builder
      </h1>
      <p className="mt-2 text-lg text-gray-300">
        Unleash the power of your collection. Let AI craft your next masterpiece.
      </p>
    </header>
  );
};

export default Header;
