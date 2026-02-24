'use client';

import { useState, type KeyboardEvent } from 'react';

interface MemorySearchProps {
  onSearch: (query: string) => void;
  onClear: () => void;
  isSearchMode: boolean;
  searchQuery: string;
}

export default function MemorySearch({ onSearch, onClear, isSearchMode, searchQuery }: MemorySearchProps) {
  const [inputValue, setInputValue] = useState('');

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      const trimmed = inputValue.trim();
      if (trimmed) {
        onSearch(trimmed);
      }
    }
  }

  function handleClear() {
    setInputValue('');
    onClear();
  }

  return (
    <div className="space-y-2">
      {/* Search input */}
      <div className="relative">
        {/* Magnifying glass icon */}
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
          <svg
            className="h-4 w-4 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 1116.65 16.65z"
            />
          </svg>
        </div>
        <input
          type="text"
          value={inputValue}
          onChange={e => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search memories..."
          className="w-full px-4 py-3 pl-10 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 outline-none"
          aria-label="Search memories — press Enter to search"
        />
      </div>

      {/* Search mode banner */}
      {isSearchMode && (
        <div className="flex items-center justify-between rounded-md bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 px-3 py-2 text-sm">
          <span className="text-blue-800 dark:text-blue-200">
            Showing results for &ldquo;<span className="font-medium">{searchQuery}</span>&rdquo;
          </span>
          <button
            type="button"
            onClick={handleClear}
            className="ml-2 flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 text-xs font-medium"
            aria-label="Clear search and return to browse mode"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Clear
          </button>
        </div>
      )}
    </div>
  );
}
