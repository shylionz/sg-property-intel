"""
Singapore Property Transaction Intelligence Tool - Backend
FastAPI application entry point.
"""
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from models.database import init_db, SessionLocal, Transaction, Rental
from api import project, district
from utils.project_index import search_projects as search_project_index, is_project_valid
from scrapers.project_fetcher import fetch_project_data

# Create database on startup
init_db()

app = FastAPI(
    title="Singapore Property Intelligence API",
    description="URA transaction and rental data with yield analytics",
    version="1.0.0"
)

# CORS - allow all for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(project.router)
app.include_router(district.router)


@app.get("/")
def root():
    return {
        "message": "Singapore Property Intelligence API",
        "version": "1.0.0",
        "endpoints": {
            "transactions": "/project/{project_name}/transactions",
            "rentals": "/project/{project_name}/rentals",
            "analytics": "/project/{project_name}/analytics",
            "yield": "/project/{project_name}/yield",
            "district_projects": "/district/{district_code}/projects",
            "search": "/search?q={query}",
            "project_valid": "/project/{project_name}/valid"
        }
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/search")
def search_projects(q: str = ""):
    """Search projects by partial name. Returns matching project names from index."""
    if len(q.strip()) < 2:
        return {"results": []}
    
    # First try searching in the database
    from sqlalchemy import func
    db = SessionLocal()
    try:
        rows = (
            db.query(Transaction.project_name, func.count(Transaction.id).label("n"))
            .filter(Transaction.project_name.ilike(f"%{q.strip().upper()}%"))
            .group_by(Transaction.project_name)
            .order_by(func.count(Transaction.id).desc())
            .limit(10)
            .all()
        )
        db_results = [{"name": r[0], "transactions": r[1]} for r in rows]
        
        # If we found results in DB, return those
        if db_results:
            return {"results": db_results}
            
        # Otherwise, search in project index
        index_results = search_project_index(q, limit=10)
        return {"results": [{"name": name, "transactions": 0} for name in index_results]}
    finally:
        db.close()


@app.get("/project/{project_name}/valid")
def validate_project(project_name: str):
    """Check if a project name is valid."""
    db = SessionLocal()
    try:
        # First check if project exists in database
        count = db.query(Transaction).filter(Transaction.project_name == project_name).count()
        if count > 0:
            return {"valid": True, "in_database": True}
            
        # Then check in project index
        valid = is_project_valid(project_name)
        if valid:
            return {"valid": True, "in_database": False}
        
        # If not in index, check if we can fetch it (try a quick fetch)
        try:
            # Try to fetch just enough to validate it exists
            temp_db = SessionLocal()
            result = fetch_project_data(project_name, temp_db)
            temp_db.close()
            return {"valid": True, "in_database": False}
        except:
            return {"valid": False, "in_database": False}
    finally:
        db.close()


def _run_ingest(project_name: str):
    """Background ingest task - fetches URA data and stores in DB."""
    from scrapers.transactions import fetch_transactions
    from scrapers.rentals import fetch_rentals

    db = SessionLocal()
    try:
        txns = fetch_transactions(
            project_name, year_from=2024, month_from=1, year_to=2026, month_to=12, max_pages=15
        )
        rents = fetch_rentals(
            project_name, year_from=2024, month_from=1, year_to=2026, month_to=12, max_pages=15
        )

        # Clear existing data for this project before re-inserting
        db.query(Transaction).filter(Transaction.project_name == project_name).delete()
        db.query(Rental).filter(Rental.project_name == project_name).delete()

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
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@app.post("/admin/ingest/{project_name}")
def ingest_project(project_name: str):
    """Trigger data ingestion for a project. Runs synchronously."""
    try:
        _run_ingest(project_name)
        db = SessionLocal()
        from sqlalchemy import func
        txn_count = db.query(func.count(Transaction.id)).filter(
            Transaction.project_name == project_name
        ).scalar()
        db.close()
        return {"status": "success", "project": project_name, "transactions": txn_count}
    except Exception as e:
        return {"status": "error", "project": project_name, "error": str(e)}


@app.post("/admin/ingest-sync/{project_name}")
def ingest_project_sync(project_name: str):
    """Synchronous ingest — returns result or error directly. For debugging."""
    try:
        _run_ingest(project_name)
        db = SessionLocal()
        from sqlalchemy import func
        txn_count = db.query(func.count()).filter(
            Transaction.project_name == project_name
        ).scalar()
        db.close()
        return {"status": "success", "project": project_name, "transactions": txn_count}
    except Exception as e:
        return {"status": "error", "project": project_name, "error": str(e)}


@app.get("/admin/projects")
def list_projects():
    """List all projects currently in the database."""
    db = SessionLocal()
    try:
        from sqlalchemy import func
        rows = (
            db.query(Transaction.project_name, func.count(Transaction.id).label("txns"))
            .group_by(Transaction.project_name)
            .all()
        )
        return {"projects": [{"name": r[0], "transactions": r[1]} for r in rows]}
    finally:
        db.close()


@app.get("/project/{project_name}/data")
def get_project_data(project_name: str):
    """Get project data, fetching it on-demand if not in database."""
    db = SessionLocal()
    try:
        # Check if project data exists
        transaction_count = db.query(Transaction).filter(Transaction.project_name == project_name).count()
        rental_count = db.query(Rental).filter(Rental.project_name == project_name).count()
        
        if transaction_count > 0 or rental_count > 0:
            # Data exists, return it
            return {
                "project": project_name,
                "data_exists": True,
                "transactions": transaction_count,
                "rentals": rental_count
            }
        else:
            # Data doesn't exist, fetch it on-demand
            result = fetch_project_data(project_name, db)
            return {
                "project": project_name,
                "data_exists": True,
                "transactions": result["transactions"],
                "rentals": result["rentals"],
                "message": "Data fetched on-demand"
            }
    finally:
        db.close()
