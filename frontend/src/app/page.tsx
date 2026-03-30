"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "https://sg-property-intel.onrender.com";

interface SearchResult { name: string; transactions: number; }

const DISTRICTS = [
  {code:"D01",area:"Raffles Place, Cecil, Marina"},{code:"D02",area:"Anson, Tanjong Pagar"},
  {code:"D03",area:"Queenstown, Tiong Bahru"},{code:"D04",area:"Telok Blangah, Harbourfront"},
  {code:"D05",area:"Pasir Panjang, Clementi"},{code:"D09",area:"Orchard, River Valley"},
  {code:"D10",area:"Bukit Timah, Holland"},{code:"D11",area:"Novena, Thomson"},
  {code:"D12",area:"Toa Payoh, Serangoon"},{code:"D14",area:"Geylang, Eunos"},
  {code:"D15",area:"Katong, Joo Chiat"},{code:"D19",area:"Hougang, Punggol"},
  {code:"D20",area:"Bishan, Ang Mo Kio"},{code:"D21",area:"Upper Bukit Timah"},
  {code:"D23",area:"Hillview, Bukit Panjang"},{code:"D27",area:"Yishun, Sembawang"},
];

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 2) { setResults([]); setShowDropdown(false); return; }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setResults(data.results || []);
        setShowDropdown(true);
      } catch { setResults([]); }
      finally { setLoading(false); }
    }, 300);
  }, [query]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setShowDropdown(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function selectProject(name: string) {
    setQuery(name); setShowDropdown(false);
    router.push(`/project/${encodeURIComponent(name)}`);
  }
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) { setShowDropdown(false); router.push(`/project/${encodeURIComponent(query.trim())}`); }
  }

  return (
    <div className="min-h-screen bg-[#0a0a1a]">
      <section className="relative min-h-[480px] flex flex-col items-center justify-center px-5 py-10 overflow-hidden" style={{backgroundImage:"linear-gradient(to bottom, rgba(10,10,26,0.4), rgba(10,10,26,0.7)), url(/images/hero.jpg)", backgroundSize:"cover", backgroundPosition:"center top"}}>
        <div className="relative z-10 text-center w-full max-w-[700px]">
          <div className="inline-flex items-center gap-2 bg-white/[0.08] border border-white/[0.12] rounded-full px-4 py-1.5 mb-6 backdrop-blur-sm">
            <div className="w-2 h-2 rounded-full bg-blue-500"></div>
            <span className="text-white/70 text-xs tracking-wide">SG PROPERTY INTELLIGENCE</span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">Know Your <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">Property Market</span></h1>
          <p className="text-white/50 text-base mb-8">Real-time URA transaction data, rental trends, and yield analytics for every residential project in Singapore.</p>

          <div ref={containerRef} className="relative w-full max-w-[600px] mx-auto">
            <form onSubmit={handleSubmit} className="flex bg-white/10 border border-white/15 rounded-2xl p-1.5 backdrop-blur-xl">
              <div className="relative flex-1">
                <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} onFocus={() => results.length > 0 && setShowDropdown(true)} placeholder="Search project..." className="w-full bg-transparent border-none outline-none text-white text-base px-4 py-3.5 placeholder:text-white/35" autoComplete="off"/>
                {loading && <div className="absolute right-3 top-4"><div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div></div>}
              </div>
              <button type="submit" className="bg-blue-500 hover:bg-blue-600 text-white rounded-xl px-7 py-3.5 text-sm font-semibold transition-colors">Search</button>
            </form>
            {showDropdown && results.length > 0 && (
              <div className="absolute z-20 w-full mt-2 bg-white rounded-xl shadow-2xl overflow-hidden border border-gray-200">
                {results.map((r) => (
                  <button key={r.name} onMouseDown={() => selectProject(r.name)} className="w-full px-4 py-3 text-left hover:bg-blue-50 flex items-center justify-between">
                    <span className="font-medium text-gray-900">{r.name}</span>
                    <span className="text-sm text-gray-400">{r.transactions} txns</span>
                  </button>
                ))}
              </div>
            )}
            {showDropdown && results.length === 0 && query.length >= 2 && !loading && (
              <div className="absolute z-20 w-full mt-2 bg-white rounded-xl shadow-2xl border border-gray-200">
                <div className="px-4 py-3 text-gray-500 text-sm">No matches found - press Search to try anyway</div>
              </div>
            )}
          </div>
          <p className="text-white/30 text-xs mt-4">Try: <Link href="/project/THE%20INTERLACE" className="text-white/50 hover:text-white">The Interlace</Link> | <Link href="/project/PARC%20ESTA" className="text-white/50 hover:text-white">Parc Esta</Link> | <Link href="/project/MARINA%20BAY%20RESIDENCES" className="text-white/50 hover:text-white">Marina Bay Residences</Link></p>

          <div className="flex justify-center gap-10 mt-10">
            <div className="text-center"><div className="text-2xl font-bold text-white">3,021</div><div className="text-[11px] text-white/40 uppercase tracking-wider mt-1">Projects</div></div>
            <div className="text-center"><div className="text-2xl font-bold text-white">28</div><div className="text-[11px] text-white/40 uppercase tracking-wider mt-1">Districts</div></div>
            <div className="text-center"><div className="text-2xl font-bold text-white">5 yrs</div><div className="text-[11px] text-white/40 uppercase tracking-wider mt-1">Data Range</div></div>
          </div>
        </div>
      </section>

      <section className="max-w-[900px] mx-auto -mt-8 px-5 pb-16 relative z-20">
        <div className="bg-[#1a1a2e] rounded-2xl p-8 shadow-lg border border-white/10">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-white">Browse by District</h2>
            <span className="text-sm text-gray-500">28 postal districts</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
            {DISTRICTS.map(d => (
              <Link key={d.code} href={`/district/${d.code}`} className="flex flex-col p-3.5 bg-white/[0.06] border border-white/10 rounded-xl hover:bg-white/[0.12] hover:border-blue-500/40 hover:-translate-y-0.5 hover:shadow-md transition-all">
                <span className="text-sm font-bold text-blue-400">{d.code}</span>
                <span className="text-[11px] text-gray-400 leading-tight">{d.area}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-[900px] mx-auto px-5 pb-16">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div className="bg-[#1a1a2e] rounded-2xl p-7 shadow-sm border border-white/10">
            <div className="w-11 h-11 rounded-xl bg-blue-50 flex items-center justify-center text-xl mb-4">TX</div>
            <h3 className="text-sm font-semibold text-white mb-2">Transaction Analytics</h3>
            <p className="text-xs text-gray-400 leading-relaxed">5 years of URA data with PSF trends, price movements, and market insights.</p>
          </div>
          <div className="bg-[#1a1a2e] rounded-2xl p-7 shadow-sm border border-white/10">
            <div className="w-11 h-11 rounded-xl bg-green-50 flex items-center justify-center text-xl mb-4">RT</div>
            <h3 className="text-sm font-semibold text-white mb-2">Rental Intelligence</h3>
            <p className="text-xs text-gray-400 leading-relaxed">Track rental trends, median rents by unit size, and compare across projects.</p>
          </div>
          <div className="bg-[#1a1a2e] rounded-2xl p-7 shadow-sm border border-white/10">
            <div className="w-11 h-11 rounded-xl bg-purple-50 flex items-center justify-center text-xl mb-4">YD</div>
            <h3 className="text-sm font-semibold text-white mb-2">Yield Calculator</h3>
            <p className="text-xs text-gray-400 leading-relaxed">Gross yield by size band with confidence ratings. Know your returns.</p>
          </div>
        </div>
      </section>

      <footer className="text-center py-8 text-gray-500 text-xs border-t border-gray-800">
        SG Property Intelligence | Data from URA | Built in Singapore
      </footer>
    </div>
  );
}