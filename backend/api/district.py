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

@router.get("/districts/{district_code}/search")
def search_district(district_code: str, property_type: str = "", sale_type: str = "", year_from: int = None, month_from: int = 1, year_to: int = None, month_to: int = 12):
 """Search URA for transactions in a district with filters."""
 from scrapers.district_search import search_by_district
 records = search_by_district(district_code, property_type, sale_type, year_from, month_from, year_to, month_to, max_pages=10)
 # Group by project name
 projects = {}
 for r in records:
  name = r["project_name"]
  if name not in projects:
   projects[name] = {"name": name, "transactions": 0, "last_sale": None, "sale_types": set(), "property_type": r.get("property_type", "")}
  projects[name]["transactions"] += 1
  projects[name]["sale_types"].add(r.get("sale_type", ""))
  if r.get("sale_date_parsed") and (not projects[name]["last_sale"] or str(r["sale_date_parsed"]) > str(projects[name]["last_sale"])):
   projects[name]["last_sale"] = str(r["sale_date_parsed"])
 result = sorted([{"name": p["name"], "transactions": p["transactions"], "last_sale": p["last_sale"], "sale_types": list(p["sale_types"]), "property_type": p["property_type"]} for p in projects.values()], key=lambda x: x["transactions"], reverse=True)
 districts_data = load_districts()
 area = districts_data.get(district_code.upper(), "")
 return {"district": district_code, "area": area, "total_records": len(records), "projects": result}