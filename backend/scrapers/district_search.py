"""Search URA transactions by district with filters."""
import time
from datetime import datetime
from typing import List, Dict
from bs4 import BeautifulSoup
from scrapers.session import get_ura_session
from utils.parsers import clean_number, parse_ura_date, normalise_project_name

DISTRICTS = {
 "D01": "D01 / Raffles Place, Cecil, Marina, People's Park",
 "D02": "D02 / Anson, Tanjong Pagar",
 "D03": "D03 / Queenstown, Tiong Bahru",
 "D04": "D04 / Telok Blangah, Harbourfront",
 "D05": "D05 / Pasir Panjang, Hong Leong Garden, Clementi New Town",
 "D06": "D06 / High Street, Beach Road (part)",
 "D07": "D07 / Middle Road, Golden Mile",
 "D08": "D08 / Little India",
 "D09": "D09 / Orchard, Cairnhill, River Valley",
 "D10": "D10 / Ardmore, Bukit Timah, Holland Road, Tanglin",
 "D11": "D11 / Watten Estate, Novena, Thomson",
 "D12": "D12 / Balestier, Toa Payoh, Serangoon",
 "D13": "D13 / Macpherson, Braddell",
 "D14": "D14 / Geylang, Eunos",
 "D15": "D15 / Katong, Joo Chiat, Amber Road",
 "D16": "D16 / Bedok, Upper East Coast, Eastwood, Kew Drive",
 "D17": "D17 / Loyang, Changi",
 "D18": "D18 / Tampines, Pasir Ris",
 "D19": "D19 / Serangoon Garden, Hougang, Punggol",
 "D20": "D20 / Bishan, Ang Mo Kio",
 "D21": "D21 / Upper Bukit Timah, Clementi Park, Ulu Pandan",
 "D22": "D22 / Jurong",
 "D23": "D23 / Hillview, Dairy Farm, Bukit Panjang, Choa Chu Kang",
 "D24": "D24 / Lim Chu Kang, Tengah",
 "D25": "D25 / Kranji, Woodgrove",
 "D26": "D26 / Upper Thomson, Springleaf",
 "D27": "D27 / Yishun, Sembawang",
 "D28": "D28 / Seletar",
}

def search_by_district(district_code: str, property_type: str = "", sale_type: str = "", year_from: int = None, month_from: int = 1, year_to: int = None, month_to: int = 12, max_pages: int = 50) -> List[Dict]:
 if year_from is None:
  year_from = datetime.now().year - 5
 if year_to is None:
  year_to = datetime.now().year
 
 district_label = DISTRICTS.get(district_code.upper(), "")
 if not district_label:
  return []
 
 session = get_ura_session()
 url = session.TRANSACTION_URL
 csrf = session.get_csrf(url)
 
 prop_type_map = {"landed": "1", "strata_landed": "2", "apartment": "3", "ec": "4"}
 prop_type_no = prop_type_map.get(property_type, "")
 
 all_records = []
 page = 0
 
 while page < max_pages:
  payload = {
  "resultPerPage": "20", "displayResult": "true", "displayResultHeader": "0",
  "loadAnalysis": "false", "displayAnalysis": "false", "displayChart": "false",
  "displayAnalysisFilters": "false", "dashboardDisplay": "false",
  "locationDetails": f'["postalDistrict","{district_label}"]',
  "propertyTypeGroupNo": prop_type_no,
  "saleYearFrom": str(year_from), "saleMonthFrom": str(month_from),
  "saleYearTo": str(year_to), "saleMonthTo": str(month_to),
  "page": str(page), "sortBy": "5", "sortAsc": "0",
  "downloadType": "", "_csrf": csrf,
  }
  resp = session.post(url, data=payload, timeout=30)
  if resp.status_code != 200:
   break
  soup = BeautifulSoup(resp.text, "lxml")
  table = soup.find("table")
  if not table:
   break
  rows = table.find_all("tr")[1:]
  if not rows:
   break
  for row in rows:
   cells = [td.get_text(strip=True) for td in row.find_all("td")]
   if len(cells) >= 7:
    record = {
    "project_name": cells[0],
    "transacted_price": clean_number(cells[1]),
    "area_sqft": cells[2],
    "price_psf": clean_number(cells[3]),
    "sale_date": cells[4],
    "sale_date_parsed": parse_ura_date(cells[4]),
    "street_name": cells[5],
    "sale_type": cells[6] if len(cells) > 6 else "",
    "property_type": cells[7] if len(cells) > 7 else "",
    "area_sqm": cells[8] if len(cells) > 8 else "",
    "price_psm": cells[9] if len(cells) > 9 else "",
    "nett_price": cells[10] if len(cells) > 10 else "",
    "number_of_units": cells[11] if len(cells) > 11 else "",
    "tenure": cells[12] if len(cells) > 12 else "",
    "postal_district": cells[13] if len(cells) > 13 else "",
    "market_segment": cells[14] if len(cells) > 14 else "",
    "floor_band": cells[15] if len(cells) > 15 else "",
    }
    all_records.append(record)
  page += 1
 return all_records