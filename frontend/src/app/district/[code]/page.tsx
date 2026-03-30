"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://sg-property-intel.onrender.com';

interface DistrictProject {
 name: string;
 transactions: number;
 last_sale: string | null;
}

export default function DistrictPage() {
 const params = useParams();
 const code = params.code as string;
 const [projects, setProjects] = useState<DistrictProject[]>([]);
 const [area, setArea] = useState("");
 const [loading, setLoading] = useState(true);

 useEffect(() => {
 async function load() {
 setLoading(true);
 try {
 const res = await fetch(`${API_BASE}/districts/${code}/projects`);
 const data = await res.json();
 setProjects(data.projects || []);
 setArea(data.area || "");
 } catch (e) {
 console.error(e);
 } finally {
 setLoading(false);
 }
 }
 load();
 }, [code]);

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
 {loading ? (
 <div className="text-center py-12">
 <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
 <p className="text-gray-600">Loading {code} projects...</p>
 </div>
 ) : projects.length === 0 ? (
 <p className="text-center text-gray-500 py-12">No ingested projects in {code} yet. Search for a project in this district to add data.</p>
 ) : (
 <div className="grid gap-3">
 {projects.map(p => (
 <Link key={p.name} href={`/project/${encodeURIComponent(p.name)}`} className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 hover:border-blue-300 flex items-center justify-between">
 <div>
 <div className="font-medium text-gray-900">{p.name}</div>
 <div className="text-xs text-gray-400 mt-1">{p.transactions} transactions · Last sale: {p.last_sale?.slice(0,7) || "—"}</div>
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