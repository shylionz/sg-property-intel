"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { fetchAnalytics, fetchTransactions, fetchRentals, fetchYield, AnalyticsSummary, Transaction, Rental, YieldBand, TrendPoint } from "@/lib/api";

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const projectName = params.name as string;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [rentals, setRentals] = useState<Rental[]>([]);
  const [yields, setYields] = useState<YieldBand[]>([]);
  const [psfTrend, setPsfTrend] = useState<TrendPoint[]>([]);
  const [rentalTrend, setRentalTrend] = useState<TrendPoint[]>([]);

  useEffect(() => {
    if (!projectName) return;
    
    async function loadData() {
      setLoading(true);
      setError("");

      const decodedName = decodeURIComponent(projectName);

      try {
        // Use allSettled so a single failing endpoint (e.g. yield with no data)
        // doesn't crash the entire page
        const [analyticsResult, txnResult, rentResult, yieldResult] = await Promise.allSettled([
          fetchAnalytics(decodedName),
          fetchTransactions(decodedName),
          fetchRentals(decodedName),
          fetchYield(decodedName),
        ]);

        // Analytics is required — if it fails, project doesn't exist or DB is empty
        if (analyticsResult.status === "rejected") {
          // Auto-trigger ingest and retry once after delay
          await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'https://sg-property-intel.onrender.com'}/admin/ingest/${encodeURIComponent(decodedName)}`, { method: 'POST' });
          setError(`No data found for "${decodedName}". Ingestion triggered — please try again in 60 seconds.`);
          setLoading(false);
          return;
        }

        const analyticsData = analyticsResult.value;
        setAnalytics(analyticsData.summary);
        setPsfTrend(analyticsData.psf_trend || []);
        setRentalTrend(analyticsData.rental_trend || []);

        if (txnResult.status === "fulfilled") setTransactions(txnResult.value.data || []);
        if (rentResult.status === "fulfilled") setRentals(rentResult.value.data || []);
        if (yieldResult.status === "fulfilled") setYields(yieldResult.value.yield_by_size_band || []);

      } catch (e: any) {
        setError(e.message || "Failed to load data");
      } finally {
        setLoading(false);
      }
    }
    
    loadData();
  }, [projectName]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading {decodeURIComponent(projectName)}...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <Link href="/" className="text-blue-600 hover:underline">← Back to search</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="text-gray-600 hover:text-gray-900">← Search</Link>
            <h1 className="text-xl font-bold text-gray-900">{decodeURIComponent(projectName)}</h1>
            <div className="text-sm text-gray-500">{analytics?.postal_district ? `District ${analytics.postal_district}` : ""}</div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <SummaryCard label="Median PSF" value={analytics?.median_psf ? `$${analytics.median_psf}` : "—"} subtext={`${analytics?.total_transactions || 0} transactions`} />
          <SummaryCard label="Median Rent" value={analytics?.median_monthly_rent ? `$${analytics.median_monthly_rent}` : "—"} subtext={`${analytics?.total_rentals || 0} rentals`} />
          <SummaryCard label="Est. Yield" value={yields[0] ? `${yields[0].gross_yield}%` : "—"} subtext={yields[0]?.size_band_label || ""} />
          <SummaryCard label="Last Sale" value={analytics?.last_transaction_price ? `$${(analytics.last_transaction_price / 1000000).toFixed(2)}M` : "—"} subtext={analytics?.last_transaction_date?.slice(0, 7) || ""} />
        </div>

        {/* Charts */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h2 className="text-lg font-semibold mb-4">PSF Trend</h2>
            {psfTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={psfTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="median_psf" stroke="#2563eb" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400 text-center py-12">No data</p>
            )}
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h2 className="text-lg font-semibold mb-4">Rental Trend</h2>
            {rentalTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={rentalTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="median_rent" stroke="#16a34a" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-400 text-center py-12">No data</p>
            )}
          </div>
        </div>

        {/* Yield Table */}
        {yields.length > 0 && (
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-8">
            <h2 className="text-lg font-semibold mb-4">Yield by Size Band</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Size Band</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Median Rent</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Median Price</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Gross Yield</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-600">Samples</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-600">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {yields.map((y) => (
                    <tr key={y.size_band} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">{y.size_band_label}</td>
                      <td className="py-3 px-4 text-right">${y.median_rent.toLocaleString()}/mo</td>
                      <td className="py-3 px-4 text-right">${(y.median_price / 1000000).toFixed(2)}M</td>
                      <td className="py-3 px-4 text-right font-semibold text-green-600">{y.gross_yield}%</td>
                      <td className="py-3 px-4 text-center text-gray-500">{y.n_rentals}r / {y.n_sales}s</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          y.confidence === "High" ? "bg-green-100 text-green-700" : 
                          y.confidence === "Medium" ? "bg-yellow-100 text-yellow-700" : 
                          "bg-gray-100 text-gray-700"
                        }`}>{y.confidence}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-sm text-gray-500 mt-4">* Gross yield only. Net yield typically 1-1.5% lower after costs.</p>
          </div>
        )}

        {/* Transaction Table */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-8">
          <h2 className="text-lg font-semibold mb-4">Recent Transactions ({transactions.length})</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-3 font-medium text-gray-600">Date</th>
                  <th className="text-right py-3 px-3 font-medium text-gray-600">Price</th>
                  <th className="text-right py-3 px-3 font-medium text-gray-600">PSF</th>
                  <th className="text-right py-3 px-3 font-medium text-gray-600">Area</th>
                  <th className="text-center py-3 px-3 font-medium text-gray-600">Floor</th>
                  <th className="text-center py-3 px-3 font-medium text-gray-600">Type</th>
                </tr>
              </thead>
              <tbody>
                {transactions.slice(0, 20).map((t, i) => (
                  <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-3">{t.sale_date}</td>
                    <td className="py-2 px-3 text-right">${t.transacted_price.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right">${t.price_psf}</td>
                    <td className="py-2 px-3 text-right">{t.area_sqft?.toFixed(0) || "—"} sqft</td>
                    <td className="py-2 px-3 text-center">{t.floor_band}</td>
                    <td className="py-2 px-3 text-center">{t.sale_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Rental Table */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h2 className="text-lg font-semibold mb-4">Recent Rentals ({rentals.length})</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-3 font-medium text-gray-600">Date</th>
                  <th className="text-right py-3 px-3 font-medium text-gray-600">Rent</th>
                  <th className="text-center py-3 px-3 font-medium text-gray-600">Bedrooms</th>
                  <th className="text-right py-3 px-3 font-medium text-gray-600">Area</th>
                </tr>
              </thead>
              <tbody>
                {rentals.slice(0, 20).map((r, i) => (
                  <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-3">{r.lease_date}</td>
                    <td className="py-2 px-3 text-right">${r.monthly_rent.toLocaleString()}/mo</td>
                    <td className="py-2 px-3 text-center">{r.bedrooms}BR</td>
                    <td className="py-2 px-3 text-right">{r.area_sqft_midpoint?.toFixed(0) || "—"} sqft</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}

function SummaryCard({ label, value, subtext }: { label: string; value: string; subtext: string }) {
  return (
    <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-400 mt-1">{subtext}</div>
    </div>
  );
}
