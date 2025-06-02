'use client';

import { useState } from 'react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  initialQuery: string;
  setQuery: (query: string) => void;
}

export default function SearchBar({ onSearch, initialQuery, setQuery }: SearchBarProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (initialQuery.trim()) {
      onSearch(initialQuery.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
      <div className="relative">
        <input
          type="text"
          value={initialQuery}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for skincare products..."
          className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Search
        </button>
      </div>
    </form>
  );
}