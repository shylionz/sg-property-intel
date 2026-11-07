"""Rental scraper for URA Residential Rental Search."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import re
import json
from datetime import datetime, date
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from scrapers.session import URASession
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
        if not cells:
            continue
        if len(cells) != len(RENTAL_FIELDS):
            raise ValueError("URA rental table has unexpected columns")
        record = {field: cells[i] if i < len(cells) else "" for i, field in enumerate(RENTAL_FIELDS)}
        record["monthly_rent"] = clean_number(record.get("monthly_rent", ""))
        record["bedrooms"] = safe_int(record.get("bedrooms", ""))
        record["area_sqft_midpoint"] = extract_area_midpoint(record.get("area_sqft_band", ""))
        record["lease_date_parsed"] = parse_ura_date(record.get("lease_date", ""))
        record["project_name"] = normalise_project_name(record.get("project_name", ""))
        record["size_band"] = normalise_size_band(record.get("area_sqft_midpoint")) if record.get("area_sqft_midpoint") else "unknown"
        if not record["lease_date_parsed"] or not record["monthly_rent"] or record["monthly_rent"] <= 0:
            raise ValueError("URA returned an invalid rental date or rent")
        records.append(record)
    return records

def fetch_rentals(project_name: str, year_from: int = None, month_from: int = 1,
                  year_to: int = None, month_to: int = None, max_pages: int = 100) -> List[Dict[str, Any]]:
    """Return a complete, validated snapshot or raise; never return partial pages."""
    today = datetime.now()
    year_from = year_from if year_from is not None else today.year - 5
    year_to = year_to if year_to is not None else today.year
    month_to = month_to if month_to is not None else today.month
    # Separate sessions keep simultaneous sales/rental CSRF tokens isolated.
    session = URASession()
    url = session.RENTAL_URL
    csrf = session.get_csrf(url)
    all_records = []
    expected_total = None
    page_size = 100
    # URA uses one-based pages; page=0 and page=1 both return the first page.
    for page in range(max_pages):
        payload = {
            "resultPerPage": str(page_size), "displayResult": "true", "displayResultHeader": "0",
            "loadAnalysis": "false", "displayAnalysis": "false", "displayChart": "false",
            "displayAnalysisFilters": "false", "dashboardDisplay": "false",
            "locationDetails": json.dumps(["projectName", project_name.upper()], separators=(",", ":")),
            "contractYearFrom": str(year_from), "contractMonthFrom": str(month_from),
            "contractYearTo": str(year_to), "contractMonthTo": str(month_to),
            "propertyTypeGroupNo": "", "page": str(page + 1), "sortBy": "9", "sortAsc": "0",
            "downloadType": "", "_csrf": csrf,
        }
        resp = session.post(url, data=payload, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        # Require URA's result count and range, rather than treating an error/login
        # page or missing table as an empty, successful download.
        match = re.search(r"Showing\s+([\d,]+)\s+to\s+([\d,]+)\s+of\s+([\d,]+)\s+results",
                          soup.get_text(" ", strip=True), re.I)
        if not match:
            raise ValueError("URA rental result count is missing; keeping cached records")
        first, last, total = (int(v.replace(",", "")) for v in match.groups())
        if expected_total is None:
            expected_total = total
        if total != expected_total:
            raise ValueError("URA rental count changed during pagination; retry later")
        records = parse_rental_html(resp.text)
        if total == 0:
            raise ValueError("URA returned no rentals; keeping cached records")
        if first != len(all_records) + 1 or last != len(all_records) + len(records) or not records:
            raise ValueError("URA rental page is incomplete or repeated")
        for record in records:
            if normalise_project_name(record["project_name"]) != normalise_project_name(project_name):
                raise ValueError("URA returned rentals for a different project")
            lease = record["lease_date_parsed"]
            if not (date(year_from, month_from, 1) <= lease <= date(year_to, month_to, 1)):
                raise ValueError("URA returned rentals outside the requested dates")
        all_records.extend(records)
        if len(all_records) == expected_total:
            return all_records
        if len(all_records) > expected_total:
            raise ValueError("URA rental count exceeds the advertised total")
        time.sleep(0.5)
    raise ValueError("URA rental pagination limit reached; keeping cached records")
