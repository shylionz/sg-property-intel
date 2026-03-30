"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://sg-property-intel.onrender.com';

interface DistrictProject {
 name: string;
 transactions: number;
 last_sale: string | null;
 sale_types: string[];
 property_type: string;
}

export default function DistrictPage() {
 const params = useParams();
 const code = params.code as string;
 const [projects, setProjects] = useState<DistrictProject[]>([]);
 const [area, setArea] = useState("");
 const [totalRecords, setTotalRecords] = useState(0);
 const [loading, setLoading] = useState(false);
 const [propertyType, setPropertyType] = useState("");
 const [saleType, setSaleType] = useState("");
 const [yearFrom, setYearFrom] = useState(String(new Date().getFullYear() - 5));
 const [yearTo, setYearTo] = useState(String(new Date().getFullYear()));

 async function doSearch() {
 setLoading(true);
 try {
 const params = new URLSearchParams();
 if (propertyType) params.set("property_type", propertyType);
 if (saleType) params.set("sale_type", saleType);
 params.set("year_from", yearFrom);
 params.set("year_to", yearTo);
 const res = await fetch(`${API_BASE}/districts/${code}/search?${params}`);
 const data = await res.json();
 setProjects(data.projects || []);
 setArea(data.area || "");
 setTotalRecords(data.total_records || 0);
 } catch (e) { console.error(e); }
 finally { setLoading(false); }
 }

 useEffect(() => { doSearch(); }, [code]);

 const currentYear = new Date().getFullYear();
 const years = Array.from({length: 6}, (_, i) => String(currentYear - 5 + i));

 return (
 <div className="min-h-screen bg-gray-50">
 <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
 <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
 <Link href="/" className="text-gray-600 hover:text-gray-900">← Search</Link>
 <h1 className="text-xl font-bold text-gray-900">{code} — {area}</h1>
 <div></div>
 </div>
 </header>
 <main className="max-w-7xl mx-auto px-6 py-8">
 <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
 <div className="flex items-center gap-3 flex-wrap">
 <select value={propertyType} onChange={e => setPropertyType(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-md text-sm bg-white">
 <option value="">All Property Types</option>
 <option value="apartment">Apartments & Condos</option>
 <option value="ec">Executive Condo</option>
 <option value="landed">Landed</option>
 <option value="strata_landed">Strata Landed</option>
 </select>
 <select value={saleType} onChange={e => setSaleType(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-md text-sm bg-white">
 <option value="">All Sale Types</option>
 <option value="New Sale">New Sale</option>
 <option value="Sub Sale">Sub Sale</option>
 <option value="Resale">Resale</option>
 </select>
 <select value={yearFrom} onChange={e => setYearFrom(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-md text-sm bg-white">
 {years.map(y => <option key={y} value={y}>{y}</option>)}
 </select>
 <span className="text-gray-400">to</span>
 <select value={yearTo} onChange={e => setYearTo(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-md text-sm bg-white">
 {years.map(y => <option key={y} value={y}>{y}</option>)}
 </select>
 <button onClick={doSearch} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700">Search</button><span className="text-xs text-gray-400">{totalRecords} transactions · {projects.length} projects</span>
 </div>
 </div>
 {loading ? (
 <div className="text-center py-12">
 <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
 <p className="text-gray-600">Searching {code}...</p>
 </div>
 ) : projects.length === 0 ? (
 <p className="text-center text-gray-500 py-12">No projects found with these filters.</p>
 ) : (
 <div className="grid gap-3">
 {projects.map(p => (
 <Link key={p.name} href={`/project/${encodeURIComponent(p.name)}`} className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 hover:border-blue-300 flex items-center justify-between">
 <div>
 <div className="font-medium text-gray-900">{p.name}</div>
 <div className="text-xs text-gray-400 mt-1">{p.transactions} transactions · {p.sale_types?.join(", ") || ""} · Last: {p.last_sale?.slice(0,7) || "—"}</div>
 </div>
 <span className="text-gray-300">→</span>
 </Link>
 ))}
 </div>
 )}
 </main>
 </div>
 );
}