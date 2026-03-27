"""
Project fetcher for on-demand data fetching.
"""
import time
from typing import Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .session import URASession
from .transactions import fetch_transactions
from .rentals import fetch_rentals
from models.database import Transaction, Rental, SessionLocal
from utils.parsers import clean_number, parse_ura_date, extract_area_midpoint, normalise_size_band

def fetch_project_data(project_name: str, db: Session) -> Dict:
    """
    Fetch and store data for a project on-demand.
    Returns a dict with fetch status and counts.
    """
    try:
        # Check if project data already exists
        existing_txns = db.query(Transaction).filter(Transaction.project_name == project_name).count()
        existing_rents = db.query(Rental).filter(Rental.project_name == project_name).count()
        
        if existing_txns > 0 or existing_rents > 0:
            # Data already exists, return counts
            return {
                "project": project_name,
                "transactions": existing_txns,
                "rentals": existing_rents,
                "status": "cached"
            }
        
        # Fetch new data
        txns = fetch_transactions(
            project_name, year_from=2024, month_from=1, year_to=2026, month_to=12, max_pages=15
        )
        rents = fetch_rentals(
            project_name, year_from=2024, month_from=1, year_to=2026, month_to=12, max_pages=15
        )
        
        # Clear existing data for this project before re-inserting
        db.query(Transaction).filter(Transaction.project_name == project_name).delete()
        db.query(Rental).filter(Rental.project_name == project_name).delete()
        
        # Insert transactions
        for rec in txns:
            db.add(Transaction(
                project_name=rec.get("project_name"), street_name=rec.get("street_name"),
                postal_district=rec.get("postal_district"), market_segment=rec.get("market_segment"),
                property_type=rec.get("property_type"), tenure=rec.get("tenure"),
                sale_type=rec.get("sale_type"), sale_date=rec.get("sale_date"),
                sale_date_parsed=rec.get("sale_date_parsed"), transacted_price=rec.get("transacted_price"),
                nett_price=rec.get("nett_price"), area_sqft=rec.get("area_sqft"),
                area_sqft_band=rec.get("area_sqft_band"), area_sqm=rec.get("area_sqm"),
                price_psf=rec.get("price_psf"), price_psm=rec.get("price_psm"),
                floor_band=rec.get("floor_band"), number_of_units=rec.get("number_of_units"),
                size_band=rec.get("size_band"),
            ))
        
        # Insert rentals
        for rec in rents:
            db.add(Rental(
                project_name=rec.get("project_name"), street_name=rec.get("street_name"),
                postal_district=rec.get("postal_district"), property_type=rec.get("property_type"),
                bedrooms=rec.get("bedrooms"), monthly_rent=rec.get("monthly_rent"),
                area_sqft_band=rec.get("area_sqft_band"), area_sqm_band=rec.get("area_sqm_band"),
                area_sqft_midpoint=rec.get("area_sqft_midpoint"), lease_date=rec.get("lease_date"),
                lease_date_parsed=rec.get("lease_date_parsed"), size_band=rec.get("size_band"),
            ))
        
        db.commit()
        
        # Return counts
        new_txns = db.query(Transaction).filter(Transaction.project_name == project_name).count()
        new_rents = db.query(Rental).filter(Rental.project_name == project_name).count()
        
        return {
            "project": project_name,
            "transactions": new_txns,
            "rentals": new_rents,
            "status": "success"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to fetch project data: {str(e)}")