#!/usr/bin/env python3
"""Ingestion script - limited to 12 months for reliability."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ingest_project.py \"PROJECT NAME\"")
        sys.exit(1)
    
    project_name = sys.argv[1]
    if not project_name:
        print("Error: Project name required")
        sys.exit(1)
    
    # Use last 12 months only for faster ingestion
    from scrapers.transactions import fetch_transactions
    from scrapers.rentals import fetch_rentals
    from models.database import SessionLocal, Transaction, Rental, init_db
    
    init_db()
    db = SessionLocal()
    
    try:
        print(f"Ingesting: {project_name}")
        
        # Use 2025-2026 data only (faster)
        txns = fetch_transactions(project_name, year_from=2025, month_from=1, year_to=2026, month_to=3, max_pages=10)
        print(f"  Transactions: {len(txns)}")
        
        rents = fetch_rentals(project_name, year_from=2025, month_from=1, year_to=2026, month_to=3, max_pages=10)
        print(f"  Rentals: {len(rents)}")
        
        # Add transactions
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
        
        # Add rentals
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
        print(f"SUCCESS: {len(txns)} txns, {len(rents)} rentals")
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
