"""Rental scraper for URA Residential Rental Search."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from scrapers.session import get_ura_session
from utils.parsers import clean_number, safe_int, extract_area_midpoint, parse_ura_date, normalise_size_band, normalise_project_name

RENTAL_FIELDS = ["project_name", "street_name", "postal_district", "property_type", "bedrooms", "monthly_rent", "area_sqm_band", "area_sqft_band", "lease_date"]

def parse_rental_html(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []
    rows = table.find_all("tr")[1:]
    records = []
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 5:
            continue
        record = {field: cells[i] if i < len(cells) else "" for i, field in enumerate(RENTAL_FIELDS)}
        record["monthly_rent"] = clean_number(record.get("monthly_rent", ""))
        record["bedrooms"] = safe_int(record.get("bedrooms", ""))
        record["area_sqft_midpoint"] = extract_area_midpoint(record.get("area_sqft_band", ""))
        record["lease_date_parsed"] = parse_ura_date(record.get("lease_date", ""))
        record["project_name"] = normalise_project_name(record.get("project_name", ""))
        record["size_band"] = normalise_size_band(record.get("area_sqft_midpoint")) if record.get("area_sqft_midpoint") else "unknown"
        records.append(record)
    return records

def fetch_rentals(project_name: str, year_from: int = 2021, month_from: int = 1, year_to: int = 2026, month_to: int = 1, max_pages: int = 100) -> List[Dict[str, Any]]:
    session = get_ura_session()
    url = session.RENTAL_URL
    csrf = session.get_csrf(url)
    page, all_records = 0, []
    
    while page < max_pages:
        payload = {
            "resultPerPage": "20", "displayResult": "true", "displayResultHeader": "0",
            "loadAnalysis": "false", "displayAnalysis": "false", "displayChart": "false",
            "displayAnalysisFilters": "false", "dashboardDisplay": "false",
            "locationDetails": f'["projectName","{project_name.upper()}"]',
            "contractYearFrom": str(year_from), "contractMonthFrom": str(month_from),
            "contractYearTo": str(year_to), "contractMonthTo": str(month_to),
            "propertyTypeGroupNo": "", "page": str(page), "sortBy": "9", "sortAsc": "0",
            "downloadType": "", "_csrf": csrf,
        }
        resp = session.post(url, data=payload, timeout=30)
        if resp.status_code != 200:
            break
        records = parse_rental_html(resp.text)
        if not records:
            break
        all_records.extend(records)
        if len(records) < 20:
            break
        page += 1
        time.sleep(1.0)
    return all_records
