"""District browsing endpoints."""
import json
import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import distinct, func
from models.database import Transaction, Rental, get_db

router = APIRouter()

DISTRICTS_FILE = "data/districts.json"

def load_districts():
    if os.path.exists(DISTRICTS_FILE):
        with open(DISTRICTS_FILE) as f:
            return json.load(f)
    return {}

@router.get("/districts")
def list_districts():
 """List all 28 postal districts."""
 return {"districts": load_districts()}

@router.get("/districts/{district_code}/projects")
def get_district_projects(district_code: str, db: Session = Depends(get_db)):
 """Get all projects in a district from ingested data."""
 code = district_code.replace("D", "").zfill(2)
 rows = (
 db.query(
 Transaction.project_name,
 func.count(Transaction.id).label("n"),
 func.max(Transaction.sale_date_parsed).label("last_sale")
 )
 .filter(Transaction.postal_district == code)
 .group_by(Transaction.project_name)
 .order_by(func.count(Transaction.id).desc())
 .all()
 )
 projects = [{"name": r[0], "transactions": r[1], "last_sale": str(r[2]) if r[2] else None} for r in rows]
 districts = load_districts()
 area_name = districts.get(f"D{code}", districts.get(district_code, ""))
 return {"district": f"D{code}", "area": area_name, "projects": projects}