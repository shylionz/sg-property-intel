"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) {
      router.push(`/project/${encodeURIComponent(search.trim())}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Singapore Property Intelligence
          </h1>
          <p className="text-lg text-gray-600">
            Transaction analytics, rental yields, and market insights
          </p>
        </div>

        <form onSubmit={handleSearch} className="mb-12">
          <div className="flex gap-3">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Enter project name (e.g., THE INTERLACE)"
              className="flex-1 px-5 py-4 text-lg border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
            <button
              type="submit"
              className="px-8 py-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors"
            >
              Search
            </button>
          </div>
        </form>

        <div className="grid md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <div className="text-3xl font-bold text-blue-600">5 years</div>
            <div className="text-gray-600 mt-1">Transaction history</div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <div className="text-3xl font-bold text-green-600">Real-time</div>
            <div className="text-gray-600 mt-1">URA data source</div>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <div className="text-3xl font-bold text-purple-600">Yield</div>
            <div className="text-gray-600 mt-1">Rental analytics</div>
          </div>
        </div>
      </div>
    </div>
  );
}
