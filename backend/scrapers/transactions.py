"""Transaction scraper for URA Residential Transaction Search."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from scrapers.session import get_ura_session
from utils.parsers import clean_number, safe_int, extract_area_midpoint, parse_ura_date, normalise_size_band, normalise_project_name

TRANSACTION_FIELDS = ["project_name", "transacted_price", "area_sqft", "price_psf", "sale_date", "street_name", "sale_type", "type_of_area", "area_sqm", "price_psm", "nett_price", "property_type", "number_of_units", "tenure", "postal_district", "market_segment", "floor_band"]

def parse_transaction_html(html: str) -> List[Dict[str, Any]]:
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
        record = {field: cells[i] if i < len(cells) else "" for i, field in enumerate(TRANSACTION_FIELDS)}
        # Normalize
        for f in ["transacted_price", "nett_price", "price_psf", "price_psm"]:
            record[f] = clean_number(record.get(f, ""))
        record["area_sqft"] = extract_area_midpoint(record.get("area_sqft", ""))
        record["area_sqft_band"] = record.get("area_sqft", "")
        record["area_sqm"] = extract_area_midpoint(record.get("area_sqm", ""))
        record["sale_date_parsed"] = parse_ura_date(record.get("sale_date", ""))
        record["project_name"] = normalise_project_name(record.get("project_name", ""))
        record["number_of_units"] = safe_int(record.get("number_of_units", ""))
        record["size_band"] = normalise_size_band(record.get("area_sqft")) if record.get("area_sqft") else "unknown"
        records.append(record)
    return records

def fetch_transactions(project_name: str, year_from: int = 2021, month_from: int = 1, year_to: int = 2026, month_to: int = 12, max_pages: int = 50) -> List[Dict[str, Any]]:
    session = get_ura_session()
    url = session.TRANSACTION_URL
    csrf = session.get_csrf(url)
    page, all_records = 0, []
    
    while page < max_pages:
        payload = {
            "resultPerPage": "20", "displayResult": "true", "displayResultHeader": "0",
            "loadAnalysis": "false", "displayAnalysis": "false", "displayChart": "false",
            "displayAnalysisFilters": "false", "dashboardDisplay": "false",
            "locationDetails": f'["projectName","{project_name.upper()}"]',
            "saleYearFrom": str(year_from), "saleMonthFrom": str(month_from),
            "saleYearTo": str(year_to), "saleMonthTo": str(month_to),
            "propertyTypeGroupNo": "", "page": str(page), "sortBy": "5", "sortAsc": "0",
            "downloadType": "", "_csrf": csrf,
        }
        resp = session.post(url, data=payload, timeout=30)
        if resp.status_code != 200:
            break
        records = parse_transaction_html(resp.text)
        if not records:
            break
        all_records.extend(records)
        if len(records) < 20:
            break
        page += 1
        time.sleep(1.0)
    return all_records
