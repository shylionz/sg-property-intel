"""
Analytics engine for computing PSF statistics.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any, Optional
from statistics import median, quantiles
from collections import defaultdict


def compute_psf_stats(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    psf_values = [t["price_psf"] for t in transactions if t.get("price_psf") and t["price_psf"] > 0]
    if not psf_values:
        return {"median_psf": None, "p25_psf": None, "p75_psf": None, "count": 0}
    if len(psf_values) < 4:
        med = median(psf_values)
        return {"median_psf": round(med), "p25_psf": round(min(psf_values)), "p75_psf": round(max(psf_values)), "count": len(psf_values)}
    q = quantiles(psf_values, n=4)
    return {"median_psf": round(median(psf_values)), "p25_psf": round(q[0]), "p75_psf": round(q[2]), "count": len(psf_values)}


def compute_monthly_psf_trend(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    monthly_data = defaultdict(list)
    for t in transactions:
        sale_date = t.get("sale_date_parsed")
        psf = t.get("price_psf")
        if sale_date and psf and psf > 0:
            month_key = sale_date[:7]
            monthly_data[month_key].append(psf)
    trend = []
    for month in sorted(monthly_data.keys()):
        values = monthly_data[month]
        trend.append({"month": month, "median_psf": round(median(values)), "n": len(values)})
    return trend


def compute_monthly_rental_trend(rentals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    monthly_data = defaultdict(list)
    for r in rentals:
        lease_date = r.get("lease_date_parsed")
        rent = r.get("monthly_rent")
        if lease_date and rent and rent > 0:
            month_key = lease_date[:7]
            monthly_data[month_key].append(rent)
    trend = []
    for month in sorted(monthly_data.keys()):
        values = monthly_data[month]
        trend.append({"month": month, "median_rent": round(median(values)), "n": len(values)})
    return trend


def compute_median_rent(rentals: List[Dict[str, Any]]) -> Optional[int]:
    rent_values = [r["monthly_rent"] for r in rentals if r.get("monthly_rent") and r["monthly_rent"] > 0]
    if not rent_values:
        return None
    return round(median(rent_values))


def get_last_transaction(transactions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    sorted_txns = sorted([t for t in transactions if t.get("sale_date_parsed")], key=lambda x: x["sale_date_parsed"], reverse=True)
    return sorted_txns[0] if sorted_txns else None
