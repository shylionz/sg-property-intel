"""
API routes for project data endpoints.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models.database import get_db, Transaction, Rental
from analytics.psf import (
    compute_psf_stats, compute_monthly_psf_trend, 
    compute_monthly_rental_trend, compute_median_rent, get_last_transaction
)
from analytics.yield_engine import compute_yield_by_size_band
from utils.parsers import normalise_project_name, resolve_project_name
from scrapers.project_fetcher import fetch_project_data, refresh_project_transactions

router = APIRouter(prefix="/project", tags=["project"])


@router.get("/{project_name}/transactions")
def get_transactions(project_name: str, page: int = Query(0, ge=0), per_page: int = Query(20, ge=1, le=100), force_refresh: bool = Query(False), db: Session = Depends(get_db)):
    normalized_name = resolve_project_name(project_name, db)
    refresh = refresh_project_transactions(db, normalized_name, force=force_refresh)
    
    query = db.query(Transaction).filter(Transaction.project_name == normalized_name)
    total = query.count()
    transactions = query.order_by(Transaction.sale_date_parsed.desc()).offset(page * per_page).limit(per_page).all()
    data = []
    for t in transactions:
        data.append({
            "project_name": t.project_name,
            "sale_date": t.sale_date,
            "sale_date_parsed": t.sale_date_parsed.isoformat() if t.sale_date_parsed else None,
            "transacted_price": t.transacted_price,
            "price_psf": t.price_psf,
            "area_sqft": t.area_sqft,
            "area_sqft_band": t.area_sqft_band,
            "floor_band": t.floor_band,
            "sale_type": t.sale_type,
            "property_type": t.property_type,
            "tenure": t.tenure,
            "postal_district": t.postal_district,
            "market_segment": t.market_segment,
            "size_band": t.size_band,
        })
    return {"project_name": normalized_name, "total": total, "page": page, "per_page": per_page, "data": data, "refresh": refresh}


@router.get("/{project_name}/rentals")
def get_rentals(project_name: str, page: int = Query(0, ge=0), per_page: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    # Try to fetch project data if not exists
    normalized_name = resolve_project_name(project_name, db)
    count = db.query(Rental).filter(Rental.project_name == normalized_name).count()
    if count == 0:
        # Fetch data on-demand
        fetch_project_data(normalized_name, db)
    
    query = db.query(Rental).filter(Rental.project_name == normalized_name)
    total = query.count()
    rentals = query.order_by(Rental.lease_date_parsed.desc()).offset(page * per_page).limit(per_page).all()
    data = []
    for r in rentals:
        data.append({
            "project_name": r.project_name,
            "lease_date": r.lease_date,
            "lease_date_parsed": r.lease_date_parsed.isoformat() if r.lease_date_parsed else None,
            "monthly_rent": r.monthly_rent,
            "bedrooms": r.bedrooms,
            "area_sqft_band": r.area_sqft_band,
            "area_sqft_midpoint": r.area_sqft_midpoint,
            "property_type": r.property_type,
            "postal_district": r.postal_district,
            "size_band": r.size_band,
        })
    return {"project_name": normalized_name, "total": total, "page": page, "per_page": per_page, "data": data}


@router.get("/{project_name}/analytics")
def get_analytics(project_name: str, force_refresh: bool = Query(False), db: Session = Depends(get_db)):
    normalized_name = resolve_project_name(project_name, db)
    refresh = refresh_project_transactions(db, normalized_name, force=force_refresh)
    
    transactions = db.query(Transaction).filter(Transaction.project_name == normalized_name).all()
    rentals = db.query(Rental).filter(Rental.project_name == normalized_name).all()
    if not transactions and not rentals:
        raise HTTPException(status_code=404, detail="Project not found")
    txn_dicts = [{"price_psf": t.price_psf, "sale_date_parsed": t.sale_date_parsed.isoformat() if t.sale_date_parsed else None, "transacted_price": t.transacted_price} for t in transactions]
    rent_dicts = [{"monthly_rent": r.monthly_rent, "lease_date_parsed": r.lease_date_parsed.isoformat() if r.lease_date_parsed else None} for r in rentals]
    psf_stats = compute_psf_stats(txn_dicts)
    psf_trend = compute_monthly_psf_trend(txn_dicts)
    rental_trend = compute_monthly_rental_trend(rent_dicts)
    median_rent = compute_median_rent(rent_dicts)
    last_txn = get_last_transaction(txn_dicts)
    return {"project_name": normalized_name, "summary": {"median_psf": psf_stats.get("median_psf"), "p25_psf": psf_stats.get("p25_psf"), "p75_psf": psf_stats.get("p75_psf"), "last_transaction_date": last_txn.get("sale_date_parsed") if last_txn else None, "last_transaction_price": last_txn.get("transacted_price") if last_txn else None, "last_transaction_psf": last_txn.get("price_psf") if last_txn else None, "total_transactions": len(transactions), "median_monthly_rent": median_rent, "total_rentals": len(rentals)}, "psf_trend": psf_trend, "rental_trend": rental_trend, "refresh": refresh}


@router.get("/{project_name}/yield")
def get_yield(project_name: str, db: Session = Depends(get_db)):
    normalized_name = resolve_project_name(project_name, db)
    # Check if data exists, if not fetch it
    txn_count = db.query(Transaction).filter(Transaction.project_name == normalized_name).count()
    rent_count = db.query(Rental).filter(Rental.project_name == normalized_name).count()
    if txn_count == 0 and rent_count == 0:
        # Fetch data on-demand
        fetch_project_data(normalized_name, db)
    
    transactions = db.query(Transaction).filter(Transaction.project_name == normalized_name).all()
    rentals = db.query(Rental).filter(Rental.project_name == normalized_name).all()
    # Return empty array (200) instead of 404 — frontend handles gracefully
    if not transactions or not rentals:
        return {"project_name": normalized_name, "yield_by_size_band": [], "note": "Insufficient data for yield calculation"}
    txn_dicts = [{"transacted_price": t.transacted_price, "size_band": t.size_band} for t in transactions]
    rent_dicts = [{"monthly_rent": r.monthly_rent, "size_band": r.size_band} for r in rentals]
    yield_data = compute_yield_by_size_band(txn_dicts, rent_dicts)
    return {"project_name": normalized_name, "yield_by_size_band": yield_data, "note": "Gross yield only. Net yield typically 1-1.5% lower after costs."}
