"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://sg-property-intel.onrender.com';

interface SearchResult {
  name: string;
  transactions: number;
}

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search as user types
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 2) {
      setResults([]);
      setShowDropdown(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setResults(data.results || []);
        setShowDropdown(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }, [query]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function selectProject(name: string) {
    setQuery(name);
    setShowDropdown(false);
    router.push(`/project/${encodeURIComponent(name)}`);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      setShowDropdown(false);
      router.push(`/project/${encodeURIComponent(query.trim())}`);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-xl">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            SG Property Intelligence
          </h1>
          <p className="text-gray-500">
            Search any residential project for transactions, rentals and yield
          </p>
        </div>

        {/* Search box with dropdown */}
        <div ref={containerRef} className="relative">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onFocus={() => results.length > 0 && setShowDropdown(true)}
                placeholder="e.g. The Interlace, Marina One..."
                className="w-full px-4 py-3 rounded-lg border border-gray-300 bg-white text-gray-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoComplete="off"
              />
              {loading && (
                <div className="absolute right-3 top-3.5">
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                </div>
              )}
            </div>
            <button
              type="submit"
              className="px-5 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              Search
            </button>
          </form>

          {/* Dropdown */}
          {showDropdown && results.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
              {results.map((r) => (
                <button
                  key={r.name}
                  onMouseDown={() => selectProject(r.name)}
                  className="w-full px-4 py-3 text-left hover:bg-blue-50 flex items-center justify-between group transition-colors"
                >
                  <span className="font-medium text-gray-900 group-hover:text-blue-700">
                    {r.name}
                  </span>
                  <span className="text-sm text-gray-400">
                    {r.transactions} txns
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* No results hint */}
          {showDropdown && results.length === 0 && query.length >= 2 && !loading && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg">
              <div className="px-4 py-3 text-gray-500 text-sm">
                No ingested projects match — press Search to try anyway
              </div>
            </div>
          )}
        </div>

        {/* Hint */}
        <p className="text-center text-sm text-gray-400 mt-4">
          Try: The Interlace · The Sail @ Marina Bay
        </p>
      </div>
    </div>
  );
}
