"""
Yield estimation engine.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any, Optional
from statistics import median

SIZE_BAND_LABELS = {
    "<600": "Under 600 sqft",
    "600-900": "600–900 sqft",
    "900-1200": "900–1,200 sqft",
    "1200-1600": "1,200–1,600 sqft",
    "1600-2200": "1,600–2,200 sqft",
    ">2200": "Above 2,200 sqft",
    "unknown": "Unknown",
}

MIN_SAMPLES = 5


def compute_yield_by_size_band(transactions: List[Dict[str, Any]], rentals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    txn_by_band = _group_by_size_band(transactions)
    rent_by_band = _group_by_size_band(rentals)
    all_bands = set(txn_by_band.keys()) | set(rent_by_band.keys())
    results = []
    for band in sorted(all_bands):
        txn_prices = txn_by_band.get(band, [])
        rent_prices = rent_by_band.get(band, [])
        n_rentals = len(rent_prices)
        n_sales = len(txn_prices)
        if n_rentals < MIN_SAMPLES or n_sales < MIN_SAMPLES:
            continue
        median_rent = median(rent_prices)
        median_price = median(txn_prices)
        if median_price <= 0:
            continue
        gross_yield = (median_rent * 12) / median_price
        if n_rentals >= 10 and n_sales >= 10:
            confidence = "High"
        elif n_rentals >= 5 and n_sales >= 5:
            confidence = "Medium"
        else:
            confidence = "Low"
        results.append({
            "size_band": band,
            "size_band_label": SIZE_BAND_LABELS.get(band, band),
            "median_rent": round(median_rent),
            "median_price": round(median_price),
            "gross_yield": round(gross_yield * 100, 2),
            "n_rentals": n_rentals,
            "n_sales": n_sales,
            "confidence": confidence,
        })
    results.sort(key=lambda x: x["gross_yield"], reverse=True)
    return results


def _group_by_size_band(records: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    grouped = {}
    for record in records:
        band = record.get("size_band", "unknown")
        if band == "unknown":
            continue
        if "transacted_price" in record and record.get("transacted_price"):
            if band not in grouped:
                grouped[band] = []
            grouped[band].append(record["transacted_price"])
        elif "monthly_rent" in record and record.get("monthly_rent"):
            if band not in grouped:
                grouped[band] = []
            grouped[band].append(record["monthly_rent"])
    return grouped


def compute_overall_yield(transactions: List[Dict[str, Any]], rentals: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    prices = [t["transacted_price"] for t in transactions if t.get("transacted_price")]
    rents = [r["monthly_rent"] for r in rentals if r.get("monthly_rent")]
    if len(prices) < MIN_SAMPLES or len(rents) < MIN_SAMPLES:
        return None
    median_price = median(prices)
    median_rent = median(rents)
    return {"gross_yield": round((median_rent * 12) / median_price * 100, 2), "median_price": round(median_price), "median_rent": round(median_rent)}
