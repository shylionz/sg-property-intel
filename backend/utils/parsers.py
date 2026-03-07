"""Utility functions for data normalization and parsing."""
import re
from datetime import datetime, date
from typing import Optional


def clean_number(value: str) -> Optional[int]:
    if not value or value == "-":
        return None
    try:
        return int(value.replace(",", "").replace("$", "").strip())
    except (ValueError, AttributeError):
        return None


def safe_int(value: str) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def extract_area_midpoint(band_str: str) -> Optional[float]:
    if not band_str:
        return None
    band_str = band_str.replace(",", "").strip()
    if "to" in band_str.lower():
        parts = re.findall(r"[\d.]+", band_str)
        if len(parts) == 2:
            return (float(parts[0]) + float(parts[1])) / 2
    try:
        match = re.findall(r"[\d.]+", band_str)
        if match:
            return float(match[0])
    except (ValueError, IndexError):
        pass
    return None


def parse_ura_date(date_str: str) -> Optional[date]:
    """Convert URA date format to Python date object."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%b-%y")
        return dt.date()
    except ValueError:
        return None


def normalise_size_band(area_sqft: float) -> str:
    if area_sqft is None:
        return "unknown"
    if area_sqft < 600:
        return "<600"
    elif area_sqft < 900:
        return "600-900"
    elif area_sqft < 1200:
        return "900-1200"
    elif area_sqft < 1600:
        return "1200-1600"
    elif area_sqft < 2200:
        return "1600-2200"
    else:
        return ">2200"


SIZE_BAND_LABELS = {
    "<600": "Under 600 sqft",
    "600-900": "600–900 sqft",
    "900-1200": "900–1,200 sqft",
    "1200-1600": "1,200–1,600 sqft",
    "1600-2200": "1,600–2,200 sqft",
    ">2200": "Above 2,200 sqft",
    "unknown": "Unknown",
}


def normalise_project_name(name: str) -> str:
    if not name:
        return ""
    return name.strip().upper()


def resolve_project_name(name: str, db) -> str:
    """
    Resolve a partial or full project name to the exact name stored in the DB.
    Tries exact match first, then LIKE contains, returns best match.
    """
    from models.database import Transaction
    upper = name.strip().upper()

    # 1. Exact match
    exact = db.query(Transaction.project_name).filter(
        Transaction.project_name == upper
    ).first()
    if exact:
        return exact[0]

    # 2. Contains match (e.g. "interlace" → "THE INTERLACE")
    like = db.query(Transaction.project_name).filter(
        Transaction.project_name.ilike(f"%{upper}%")
    ).first()
    if like:
        return like[0]

    # 3. No match — return normalised name (will trigger ingest path)
    return upper


def parse_floor_band(floor_str: str) -> str:
    if not floor_str:
        return "unknown"
    return floor_str.strip()
