"""
API routes for district data.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.database import get_db, Transaction

router = APIRouter(prefix="/district", tags=["district"])


@router.get("/{district_code}/projects")
def get_district_projects(district_code: str, db: Session = Depends(get_db)):
    projects = (
        db.query(
            Transaction.project_name,
            func.count(Transaction.id).label("transaction_count"),
            func.min(Transaction.sale_date_parsed).label("latest_sale_date"),
            func.avg(Transaction.price_psf).label("avg_psf")
        )
        .filter(Transaction.postal_district == district_code)
        .group_by(Transaction.project_name)
        .order_by(func.count(Transaction.id).desc())
        .limit(50)
        .all()
    )
    data = []
    for p in projects:
        data.append({
            "project_name": p.project_name,
            "transaction_count": p.transaction_count,
            "latest_sale_date": p.latest_sale_date.isoformat() if p.latest_sale_date else None,
            "median_psf": round(p.avg_psf) if p.avg_psf else None
        })
    return {"district": district_code, "projects": data}
