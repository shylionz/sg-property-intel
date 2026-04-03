"use client";

import { useEffect, useState, useMemo } from "react";
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
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedBand, setSelectedBand] = useState(0);

  useEffect(() => {
    if (psfTrend.length > 0 || rentalTrend.length > 0) {
      const allMonths = [...psfTrend.map(p => p.month), ...rentalTrend.map(r => r.month)].sort();
      if (allMonths.length > 0 && !dateFrom) setDateFrom(allMonths[0]);
      if (allMonths.length > 0 && !dateTo) setDateTo(allMonths[allMonths.length - 1]);
    }
  }, [psfTrend, rentalTrend]);

  const monthOptions = useMemo(() => {
    const allMonths = new Set([...psfTrend.map(p => p.month), ...rentalTrend.map(r => r.month)]);
    return Array.from(allMonths).sort();
  }, [psfTrend, rentalTrend]);

  const filteredPsfTrend = useMemo(() => {
    return psfTrend.filter(p => (!dateFrom || p.month >= dateFrom) && (!dateTo || p.month <= dateTo));
  }, [psfTrend, dateFrom, dateTo]);

  const filteredRentalTrend = useMemo(() => {
    return rentalTrend.filter(r => (!dateFrom || r.month >= dateFrom) && (!dateTo || r.month <= dateTo));
  }, [rentalTrend, dateFrom, dateTo]);

  const filteredTransactions = useMemo(() => {
    return transactions.filter(t => {
      const m = (t.sale_date_parsed || t.sale_date || "").slice(0, 7);
      return (!dateFrom || m >= dateFrom) && (!dateTo || m <= dateTo);
    });
  }, [transactions, dateFrom, dateTo]);

  const filteredRentals = useMemo(() => {
    return rentals.filter(r => {
      const m = (r.lease_date_parsed || r.lease_date || "").slice(0, 7);
      return (!dateFrom || m >= dateFrom) && (!dateTo || m <= dateTo);
    });
  }, [rentals, dateFrom, dateTo]);

  const filteredSummary = useMemo(() => {
    if (!analytics) return null;
    const psfValues = filteredTransactions.map(t => t.price_psf).filter(v => v > 0).sort((a,b) => a - b);
    const rentValues = filteredRentals.map(r => r.monthly_rent).filter(v => v > 0).sort((a,b) => a - b);
    const median = (arr: number[]) => {
      if (arr.length === 0) return null;
      const mid = Math.floor(arr.length / 2);
      return arr.length % 2 ? arr[mid] : Math.round((arr[mid-1] + arr[mid]) / 2);
    };
    const lastTx = filteredTransactions.length > 0 ? filteredTransactions[0] : null;
    return {
      ...analytics,
      median_psf: median(psfValues),
      total_transactions: filteredTransactions.length,
      median_monthly_rent: median(rentValues),
      total_rentals: filteredRentals.length,
      last_transaction_price: lastTx ? lastTx.transacted_price : null,
      last_transaction_date: lastTx ? (lastTx.sale_date_parsed || lastTx.sale_date || null) : null,
    };
  }, [analytics, filteredTransactions, filteredRentals]);

  const filteredYields = useMemo(() => {
    const bands: Record<string, {rents: number[], prices: number[]}> = {};
    filteredTransactions.forEach(t => {
      const band = t.area_sqft_band || t.size_band || "unknown";
      if (!bands[band]) bands[band] = {rents: [], prices: []};
      if (t.transacted_price > 0) bands[band].prices.push(t.transacted_price);
    });
    filteredRentals.forEach(r => {
      const band = r.area_sqft_band || r.size_band || "unknown";
      if (!bands[band]) bands[band] = {rents: [], prices: []};
      if (r.monthly_rent > 0) bands[band].rents.push(r.monthly_rent);
    });
    const median = (arr: number[]) => {
      if (arr.length === 0) return 0;
      const s = [...arr].sort((a,b) => a - b);
      const m = Math.floor(s.length / 2);
      return s.length % 2 ? s[m] : (s[m-1] + s[m]) / 2;
    };
    return Object.entries(bands).filter(([_,v]) => v.rents.length > 0 && v.prices.length > 0).map(([band, v]) => {
      const medRent = median(v.rents);
      const medPrice = median(v.prices);
      const grossYield = medPrice > 0 ? ((medRent * 12) / medPrice * 100).toFixed(2) : "0";
      return {size_band: band, size_band_label: band, median_rent: medRent, median_price: medPrice, gross_yield: parseFloat(grossYield), n_rentals: v.rents.length, n_sales: v.prices.length, confidence: v.rents.length >= 10 && v.prices.length >= 5 ? "High" : v.rents.length >= 3 ? "Medium" : "Low"};
    }).sort((a,b) => b.n_rentals - a.n_rentals);
  }, [filteredTransactions, filteredRentals]);

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
          // Auto-trigger ingest and retry with loading spinner
          await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'https://sg-property-intel.onrender.com'}/admin/ingest/${encodeURIComponent(decodedName)}`, { method: 'POST' });
          // Wait 30 seconds then retry automatically
          await new Promise(resolve => setTimeout(resolve, 30000));
          const retryResult = await fetchAnalytics(decodedName).catch(() => null);
          if (!retryResult) {
            // Second retry after another 30 seconds
            await new Promise(resolve => setTimeout(resolve, 30000));
            const retryResult2 = await fetchAnalytics(decodedName).catch(() => null);
            if (!retryResult2) {
              setError(`Could not load data for "${decodedName}" after ingestion. Please try again later.`);
              setLoading(false);
              return;
            }
            setAnalytics(retryResult2.summary);
            setPsfTrend(retryResult2.psf_trend || []);
            setRentalTrend(retryResult2.rental_trend || []);
          } else {
            setAnalytics(retryResult.summary);
            setPsfTrend(retryResult.psf_trend || []);
            setRentalTrend(retryResult.rental_trend || []);
          }
          // Re-fetch transactions, rentals, yield after successful ingestion
          const [txn2, rent2, yield2] = await Promise.allSettled([
            fetchTransactions(decodedName),
            fetchRentals(decodedName),
            fetchYield(decodedName),
          ]);
          if (txn2.status === "fulfilled") setTransactions(txn2.value.data || []);
          if (rent2.status === "fulfilled") setRentals(rent2.value.data || []);
          if (yield2.status === "fulfilled") setYields(yield2.value.yield_by_size_band || []);
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
            <div className="flex items-center gap-2"><h1 className="text-xl font-bold text-gray-900">{decodeURIComponent(projectName)}</h1><button onClick={async () => { setLoading(true); await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "https://sg-property-intel.onrender.com"}/admin/ingest/${encodeURIComponent(decodeURIComponent(projectName))}`, { method: "POST" }); window.location.reload(); }} className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200">↻ Refresh</button></div>
            <div className="text-sm text-gray-500">{filteredSummary?.postal_district ? `District ${filteredSummary.postal_district}` : ""}</div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Date Range Picker */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="flex items-center gap-4 flex-wrap">
            <span className="text-sm font-medium text-gray-700">Date Range:</span>
            <select value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-md text-sm bg-white">
              {monthOptions.map(m => (<option key={m} value={m}>{m}</option>))}
            </select>
            <span className="text-gray-400">to</span>
            <select value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-md text-sm bg-white">
              {monthOptions.map(m => (<option key={m} value={m}>{m}</option>))}
            </select>
            <button onClick={() => { if (monthOptions.length > 0) { setDateFrom(monthOptions[0]); setDateTo(monthOptions[monthOptions.length - 1]); }}} className="px-3 py-2 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200">Reset</button>
            <span className="text-xs text-gray-400">{filteredTransactions.length} txns · {filteredRentals.length} rentals in range</span>
          </div>
        </div>
        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <SummaryCard label="Median PSF" value={filteredSummary?.median_psf ? `$${filteredSummary.median_psf}` : "—"} subtext={`${filteredSummary?.total_transactions || 0} transactions`} />
          <SummaryCard label="Median Rent" value={filteredSummary?.median_monthly_rent ? `$${filteredSummary.median_monthly_rent}` : "—"} subtext={`${filteredSummary?.total_rentals || 0} rentals`} />
          <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
              <div className="text-sm text-gray-500 mb-1">Est. Yield</div>
              <div className="text-2xl font-bold text-gray-900">{filteredYields[selectedBand] ? `${filteredYields[selectedBand].gross_yield}%` : "—"}</div>
              <select value={selectedBand} onChange={e => setSelectedBand(Number(e.target.value))} className="text-xs text-gray-400 mt-1 bg-transparent border-none outline-none cursor-pointer">
                {filteredYields.length === 0 ? <option value={0}>No data</option> : filteredYields.map((y, i) => <option key={i} value={i}>{y.size_band_label} ({y.n_rentals}r/{y.n_sales}s)</option>)}
              </select>
            </div>
          <SummaryCard label="Last Sale" value={filteredSummary?.last_transaction_price ? `$${(filteredSummary.last_transaction_price / 1000000).toFixed(2)}M` : "—"} subtext={filteredSummary?.last_transaction_date?.slice(0, 7) || ""} />
        </div>

        {/* Charts */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <h2 className="text-lg font-semibold mb-4">PSF Trend</h2>
            {psfTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={filteredPsfTrend}>
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
                <LineChart data={filteredRentalTrend}>
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
        {filteredYields.length > 0 && (
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
                  {filteredYields.map((y) => (
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
          <h2 className="text-lg font-semibold mb-4">Transactions ({filteredTransactions.length})</h2>
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
                {filteredTransactions.slice(0, 50).map((t, i) => (
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
          <h2 className="text-lg font-semibold mb-4">Rentals ({filteredRentals.length})</h2>
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
                {filteredRentals.slice(0, 50).map((r, i) => (
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
