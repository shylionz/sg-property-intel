const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://sg-property-intel.onrender.com';

export interface Transaction {
  project_name: string;
  sale_date: string;
  sale_date_parsed: string | null;
  transacted_price: number;
  price_psf: number;
  area_sqft: number | null;
  area_sqft_band: string;
  floor_band: string;
  sale_type: string;
  property_type: string;
  tenure: string;
  postal_district: string;
  market_segment: string;
  size_band: string;
}

export interface Rental {
  project_name: string;
  lease_date: string;
  lease_date_parsed: string | null;
  monthly_rent: number;
  bedrooms: number | null;
  area_sqft_band: string;
  area_sqft_midpoint: number | null;
  property_type: string;
  postal_district: string;
  size_band: string;
}

export interface AnalyticsSummary {
  median_psf: number | null;
  p25_psf: number | null;
  p75_psf: number | null;
  last_transaction_date: string | null;
  last_transaction_price: number | null;
  last_transaction_psf: number | null;
  total_transactions: number;
  median_monthly_rent: number | null;
  total_rentals: number;
  postal_district?: string;
}

export interface TrendPoint {
  month: string;
  median_psf?: number;
  median_rent?: number;
  n: number;
}

export interface YieldBand {
  size_band: string;
  size_band_label: string;
  median_rent: number;
  median_price: number;
  gross_yield: number;
  n_rentals: number;
  n_sales: number;
  confidence: string;
}

export async function fetchTransactions(projectName: string, page = 0, perPage = 100) {
  const res = await fetch(`${API_BASE}/project/${encodeURIComponent(projectName)}/transactions?page=${page}&per_page=${perPage}`);
  if (!res.ok) throw new Error('Failed to fetch transactions');
  return res.json();
}

export async function fetchRentals(projectName: string, page = 0, perPage = 100) {
  const res = await fetch(`${API_BASE}/project/${encodeURIComponent(projectName)}/rentals?page=${page}&per_page=${perPage}`);
  if (!res.ok) throw new Error('Failed to fetch rentals');
  return res.json();
}

export async function fetchAnalytics(projectName: string) {
  const res = await fetch(`${API_BASE}/project/${encodeURIComponent(projectName)}/analytics`);
  if (!res.ok) throw new Error('Failed to fetch analytics');
  return res.json();
}

export async function fetchYield(projectName: string) {
  const res = await fetch(`${API_BASE}/project/${encodeURIComponent(projectName)}/yield`);
  if (!res.ok) throw new Error('Failed to fetch yield');
  return res.json();
}
