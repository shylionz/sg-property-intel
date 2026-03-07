# Singapore Property Transaction Intelligence Tool
## Final Implementation Specification — v1.0
**Date:** 7 March 2026
**Status:** Build-Ready
**Prepared for:** Engineering implementation

---

## 1. Product Objective

**Product name:** Singapore Property Transaction Intelligence Tool

**Purpose:**
Allow users to search a Singapore private residential project or postal district and retrieve structured investment intelligence including sale transactions, rental transactions, price analytics, and rental yield estimation.

**Positioning:**
This is an investment intelligence and comps analysis tool, not a property listing portal. Every screen and metric is designed to help users answer:
- What did this property actually sell for?
- What is it renting for?
- What yield does it generate?
- How does that compare across size types?

---

## 2. Version 1 Scope

### Included in v1

**Search inputs**
- Project name (with autocomplete)
- Postal district (D01–D28 dropdown)

**Core analytics outputs**
- Sale transaction table
- Rental transaction table
- Median PSF
- PSF trend chart (monthly)
- P25 / Median / P75 PSF distribution
- Rental trend chart (monthly median rent)
- Gross rental yield by size band
- Confidence indicator per yield row

**Data sources**
- URA Private Residential Transaction Search
- URA Private Residential Rental Search

### Excluded from v1 (design for later)

- Liquidity Score
- User accounts and authentication
- Subscription billing
- Saved searches and watchlists
- Email or push alerts
- Mobile app

The backend must be API-first so all of the above can be added without refactoring the core.

---

## 3. User Flow

```
User opens app
        │
        ▼
Enter project name or select postal district
        │
        ▼
System fetches:
  - All sale transactions (last 60 months, paginated)
  - All rental transactions (last 60 months, paginated)
        │
        ▼
Display: Project Summary Header
  ┌─────────────────────────────────────────────┐
  │  Project Name        Postal District        │
  │  Median PSF          Last transaction date  │
  │  Median Monthly Rent Estimated Gross Yield  │
  └─────────────────────────────────────────────┘
        │
        ▼
Display: Analytics Panels (in order)

  Panel 1: Transaction Table
  Panel 2: PSF Trend Chart
  Panel 3: Rental Table
  Panel 4: Rental Trend Chart
  Panel 5: Yield by Size Band Table
```

### Panel Definitions

**Panel 1 — Transaction Table**
All individual sale transactions for the project.
Columns: Sale Date | Transacted Price ($) | PSF | Floor Band | Area (SQFT) | Type of Sale | Property Type | Tenure

**Panel 2 — PSF Trend Chart**
Monthly median PSF computed from all transactions, plotted as a line chart.
X-axis: Month/Year | Y-axis: $ PSF
Overlay: 3-month rolling average line

**Panel 3 — Rental Table**
All individual rental contracts for the project.
Columns: Lease Date | Monthly Rent ($) | Bedrooms | Area Band (SQFT) | Property Type

**Panel 4 — Rental Trend Chart**
Monthly median rent computed from all rental contracts, plotted as a line chart.
X-axis: Month/Year | Y-axis: $ per month

**Panel 5 — Yield by Size Band Table**
Computed yield per normalised size band.
Columns: Size Band | Median Rent | Median Sale Price | Gross Yield % | Rental n | Sales n | Confidence

---

## 4. UI Components

### Search Bar

```
Component: SearchBar
Props:
  - mode: "project" | "district"
  - onSelect: (value: string) => void

Behaviour:
  - Project mode: text input with autocomplete
    - Autocomplete list seeded from URA project name list
    - Min 2 characters to trigger suggestions
    - Fuzzy match on project name
  - District mode: dropdown of D01–D28 with area labels
```

### Summary Cards (4 cards in a row)

```
Component: SummaryCard
Cards:
  1. Median PSF
     Value: $X,XXX psf
     Sub: Based on N transactions

  2. Median Monthly Rent
     Value: $X,XXX / month
     Sub: Based on N rental contracts

  3. Estimated Gross Yield
     Value: X.X%
     Sub: [Size band label] | Confidence: High/Med/Low
     Note: "Gross — net typically 1–1.5% lower"

  4. Last Transaction
     Value: $X.XXM — Mon-YY
     Sub: Floor XX | XXX sqft | PSF: $X,XXX
```

### Transaction Table

```
Component: TransactionTable
Columns:
  - Sale Date        (sortable)
  - Price ($)        (sortable, formatted with commas)
  - PSF ($ psf)      (sortable)
  - Floor Band
  - Area (SQFT)      (sortable)
  - Type of Sale     (filter: New Sale / Resale / Sub Sale)
  - Property Type
  - Tenure

Features:
  - Default sort: Sale Date descending
  - Pagination: 20 rows per page
  - Column filters for Type of Sale and Property Type
  - Export to CSV button
```

### Rental Table

```
Component: RentalTable
Columns:
  - Lease Date       (sortable)
  - Monthly Rent ($) (sortable)
  - Bedrooms         (filter)
  - Area Band (SQFT)
  - Property Type

Features:
  - Default sort: Lease Date descending
  - Pagination: 20 rows per page
  - Filter by bedroom count
```

### PSF Trend Chart

```
Component: PSFTrendChart
Library: Recharts (LineChart)
Data: Monthly median PSF array

Lines:
  - Primary: Median PSF (solid blue)
  - Secondary: 3-month rolling average (dashed grey)
  - Optional bands: P25 and P75 as area fill

X-axis: Month-Year labels, rotate 45°
Y-axis: $ PSF, formatted as $X,XXX
Tooltip: Month | Median PSF | Rolling Avg | Transaction count (n)
```

### Rental Trend Chart

```
Component: RentalTrendChart
Library: Recharts (LineChart)
Data: Monthly median rent array

Lines:
  - Primary: Median monthly rent (solid green)

X-axis: Month-Year
Y-axis: $ per month
Tooltip: Month | Median Rent | n contracts
```

### Yield Table

```
Component: YieldTable
Columns:
  - Size Band        (e.g. "1,200–1,600 sqft")
  - Median Rent      ($X,XXX/mo)
  - Median Price     ($X.XXM)
  - Gross Yield      (X.X%)
  - Rental n         (sample count)
  - Sales n          (sample count)
  - Confidence       (High / Medium / Low / — )

Behaviour:
  - Suppress row entirely if rental n < 5 OR sales n < 5
  - Highlight highest yield row
  - Show footnote: "Gross yield only. Net yield typically 1–1.5% lower after costs."
```

---

## 5. Data Model

### Database: SQLite (v1), PostgreSQL-compatible schema

```sql
-- Transactions table
CREATE TABLE transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name        TEXT NOT NULL,
    street_name         TEXT,
    postal_district     TEXT,
    market_segment      TEXT,
    property_type       TEXT,
    tenure              TEXT,
    sale_type           TEXT,
    sale_date           TEXT,          -- stored as "MMM-YY" e.g. "Feb-26"
    sale_date_parsed    DATE,          -- parsed to YYYY-MM-01 for querying
    transacted_price    INTEGER,
    nett_price          INTEGER,
    area_sqft           REAL,          -- midpoint of band e.g. 1259.39 (exact from URA)
    area_sqft_band      TEXT,          -- original band string if returned as range
    area_sqm            REAL,
    price_psf           INTEGER,
    price_psm           INTEGER,
    floor_band          TEXT,
    number_of_units     INTEGER,
    size_band           TEXT,          -- normalised: "<600"|"600-900"|"900-1200"|"1200-1600"|"1600-2200"|">2200"
    fetched_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_txn_project ON transactions(project_name);
CREATE INDEX idx_txn_district ON transactions(postal_district);
CREATE INDEX idx_txn_date ON transactions(sale_date_parsed);
CREATE INDEX idx_txn_size_band ON transactions(project_name, size_band);

-- Rentals table
CREATE TABLE rentals (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name        TEXT NOT NULL,
    street_name         TEXT,
    postal_district     TEXT,
    property_type       TEXT,
    bedrooms            INTEGER,
    monthly_rent        INTEGER,
    area_sqft_band      TEXT,          -- e.g. "1,400 to 1,500"
    area_sqft_midpoint  REAL,          -- computed midpoint
    area_sqm_band       TEXT,
    lease_date          TEXT,          -- "Jan-26"
    lease_date_parsed   DATE,          -- YYYY-MM-01
    size_band           TEXT,          -- same normalised bands as transactions
    fetched_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rent_project ON rentals(project_name);
CREATE INDEX idx_rent_district ON rentals(postal_district);
CREATE INDEX idx_rent_date ON rentals(lease_date_parsed);
CREATE INDEX idx_rent_size_band ON rentals(project_name, size_band);

-- Ingestion log table (for cache/refresh tracking)
CREATE TABLE ingestion_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type       TEXT NOT NULL,    -- "transactions" | "rentals"
    project_name    TEXT,
    postal_district TEXT,
    fetched_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    record_count    INTEGER,
    status          TEXT              -- "success" | "error"
);
```

### Size Band Normalisation

```python
def normalise_size_band(area_sqft: float) -> str:
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
    "<600":      "Under 600 sqft",
    "600-900":   "600–900 sqft",
    "900-1200":  "900–1,200 sqft",
    "1200-1600": "1,200–1,600 sqft",
    "1600-2200": "1,600–2,200 sqft",
    ">2200":     "Above 2,200 sqft",
}
```

### Area Midpoint Extraction

```python
import re

def extract_area_midpoint(band_str: str) -> float:
    """
    Input examples:
      "1,259.39"           → 1259.39  (exact value)
      "1,400 to 1,500"     → 1450.0   (midpoint of band)
    """
    band_str = band_str.replace(",", "").strip()
    if "to" in band_str:
        parts = re.findall(r"[\d.]+", band_str)
        if len(parts) == 2:
            return (float(parts[0]) + float(parts[1])) / 2
    try:
        return float(re.findall(r"[\d.]+", band_str)[0])
    except:
        return None
```

---

## 6. Yield Estimation Logic

```python
from statistics import median

MIN_SAMPLES = 5

def compute_yield_by_size_band(project_name: str, db) -> list[dict]:
    """
    Join rental and sale records by project + size_band.
    Compute gross yield per band.
    """
    size_bands = ["<600", "600-900", "900-1200", "1200-1600", "1600-2200", ">2200"]
    results = []

    for band in size_bands:
        rental_rows = db.query(
            "SELECT monthly_rent FROM rentals WHERE project_name=? AND size_band=?",
            (project_name, band)
        )
        sale_rows = db.query(
            "SELECT transacted_price FROM transactions WHERE project_name=? AND size_band=?",
            (project_name, band)
        )

        rents  = [r["monthly_rent"] for r in rental_rows if r["monthly_rent"]]
        prices = [s["transacted_price"] for s in sale_rows if s["transacted_price"]]

        n_rent  = len(rents)
        n_sales = len(prices)

        # Suppress if insufficient data
        if n_rent < MIN_SAMPLES or n_sales < MIN_SAMPLES:
            continue

        median_rent  = median(rents)
        median_price = median(prices)
        gross_yield  = (median_rent * 12) / median_price

        # Confidence
        if n_rent >= 10 and n_sales >= 10:
            confidence = "High"
        elif n_rent >= 5 and n_sales >= 5:
            confidence = "Medium"
        else:
            confidence = "Low"

        results.append({
            "size_band":     band,
            "size_band_label": SIZE_BAND_LABELS[band],
            "median_rent":   round(median_rent),
            "median_price":  round(median_price),
            "gross_yield":   round(gross_yield * 100, 2),
            "n_rentals":     n_rent,
            "n_sales":       n_sales,
            "confidence":    confidence,
        })

    return sorted(results, key=lambda x: x["gross_yield"], reverse=True)
```

---

## 7. Data Ingestion Architecture

### URA Endpoints

| Endpoint | URL | Data type |
|----------|-----|-----------|
| Transaction search | `https://eservice.ura.gov.sg/property-market-information/pmiResidentialTransactionSearch` | POST |
| Rental search | `https://eservice.ura.gov.sg/property-market-information/pmiResidentialRentalSearch` | POST |

### CSRF Token Extraction

Both endpoints require:
1. A valid session cookie (obtained by loading the page with a GET request)
2. A `_csrf` token embedded in the HTML response

```python
import requests
from bs4 import BeautifulSoup

class URASession:
    TRANSACTION_URL = "https://eservice.ura.gov.sg/property-market-information/pmiResidentialTransactionSearch"
    RENTAL_URL      = "https://eservice.ura.gov.sg/property-market-information/pmiResidentialRentalSearch"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

    def get_csrf(self, url: str) -> str:
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        token = soup.find("input", {"name": "_csrf"})
        if token:
            return token["value"]
        # Fallback: extract from meta tag
        meta = soup.find("meta", {"name": "_csrf"})
        if meta:
            return meta["content"]
        raise ValueError("CSRF token not found")
```

### Transaction Scraper

```python
def fetch_transactions(session: URASession, project_name: str) -> list[dict]:
    """
    Fetches all paginated transaction records for a given project.
    """
    url   = URASession.TRANSACTION_URL
    csrf  = session.get_csrf(url)
    page  = 0
    all_records = []

    while True:
        payload = {
            "resultPerPage":         "20",
            "displayResult":         "true",
            "displayResultHeader":   "0",
            "loadAnalysis":          "true",
            "displayAnalysis":       "1",
            "displayChart":          "true",
            "displayAnalysisFilters":"true",
            "dashboardDisplay":      "false",
            "locationDetails":       f'["projectName","{project_name.upper()}"]',
            "saleYearFrom":          "2021",
            "saleMonthFrom":         "1",
            "saleYearTo":            "2026",
            "saleMonthTo":           "12",
            "sortBy":                "5",
            "sortAsc":               "0",
            "page":                  str(page),
            "_csrf":                 csrf,
        }

        resp = session.session.post(url, data=payload, timeout=15)
        resp.raise_for_status()

        records = parse_transaction_html(resp.text)
        if not records:
            break

        all_records.extend(records)

        # Check if more pages exist
        if len(records) < 20:
            break
        page += 1

    return all_records
```

### HTML Parser — Transactions

```python
from bs4 import BeautifulSoup

TRANSACTION_FIELDS = [
    "project_name", "transacted_price", "area_sqft", "price_psf",
    "sale_date", "street_name", "sale_type", "type_of_area",
    "area_sqm", "price_psm", "nett_price", "property_type",
    "number_of_units", "tenure", "postal_district", "market_segment", "floor_band"
]

def parse_transaction_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    rows = table.find_all("tr")[1:]  # Skip header
    records = []

    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 5:
            continue

        record = dict(zip(TRANSACTION_FIELDS, cells))

        # Clean price fields
        for field in ["transacted_price", "nett_price", "price_psf", "price_psm"]:
            if field in record:
                record[field] = clean_number(record[field])

        # Parse area
        record["area_sqft"]      = extract_area_midpoint(record.get("area_sqft", ""))
        record["area_sqft_band"] = record.get("area_sqft", "")
        record["area_sqft_midpoint"] = record["area_sqft"]

        # Parse date
        record["sale_date_parsed"] = parse_ura_date(record.get("sale_date", ""))

        # Assign size band
        if record["area_sqft"]:
            record["size_band"] = normalise_size_band(record["area_sqft"])

        records.append(record)

    return records
```

### HTML Parser — Rentals

```python
RENTAL_FIELDS = [
    "project_name", "street_name", "postal_district", "property_type",
    "bedrooms", "monthly_rent", "area_sqm_band", "area_sqft_band", "lease_date"
]

def parse_rental_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    rows = table.find_all("tr")[1:]
    records = []

    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 5:
            continue

        record = dict(zip(RENTAL_FIELDS, cells))
        record["monthly_rent"]      = clean_number(record.get("monthly_rent", ""))
        record["bedrooms"]          = safe_int(record.get("bedrooms", ""))
        record["area_sqft_midpoint"] = extract_area_midpoint(record.get("area_sqft_band", ""))
        record["lease_date_parsed"] = parse_ura_date(record.get("lease_date", ""))

        if record["area_sqft_midpoint"]:
            record["size_band"] = normalise_size_band(record["area_sqft_midpoint"])

        records.append(record)

    return records
```

### Helper Utilities

```python
from datetime import datetime

def clean_number(value: str) -> int | None:
    try:
        return int(value.replace(",", "").replace("$", "").replace("-", "").strip())
    except:
        return None

def safe_int(value: str) -> int | None:
    try:
        return int(value.strip())
    except:
        return None

def parse_ura_date(date_str: str) -> str | None:
    """Convert 'Feb-26' or 'Jan-26' to '2026-02-01'"""
    try:
        dt = datetime.strptime(date_str.strip(), "%b-%y")
        return dt.strftime("%Y-%m-01")
    except:
        return None
```

---

## 8. Backend API

### Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** SQLite (MVP); SQLAlchemy ORM for future PostgreSQL migration
- **Cache:** TTLCache (in-memory, `cachetools` library)
- **HTTP client:** `requests` with session persistence

### Cache Configuration

```python
from cachetools import TTLCache

transaction_cache = TTLCache(maxsize=200, ttl=43200)  # 12 hours
rental_cache      = TTLCache(maxsize=200, ttl=86400)  # 24 hours
analytics_cache   = TTLCache(maxsize=200, ttl=86400)  # 24 hours
```

### API Endpoints

#### GET /project/{project_name}/transactions

```json
Response:
{
  "project_name": "THE INTERLACE",
  "total": 239,
  "page": 0,
  "per_page": 20,
  "data": [
    {
      "project_name": "THE INTERLACE",
      "sale_date": "Feb-26",
      "sale_date_parsed": "2026-02-01",
      "transacted_price": 2230000,
      "price_psf": 1771,
      "area_sqft": 1259.39,
      "area_sqft_band": "1,259.39",
      "floor_band": "06 to 10",
      "sale_type": "Resale",
      "property_type": "Condominium",
      "tenure": "99 yrs lease commencing from 2009",
      "postal_district": "04",
      "market_segment": "Rest of Central Region",
      "size_band": "1200-1600"
    }
  ]
}
```

#### GET /project/{project_name}/rentals

```json
Response:
{
  "project_name": "THE INTERLACE",
  "total": 1196,
  "page": 0,
  "per_page": 20,
  "data": [
    {
      "project_name": "THE INTERLACE",
      "lease_date": "Jan-26",
      "lease_date_parsed": "2026-01-01",
      "monthly_rent": 8000,
      "bedrooms": 3,
      "area_sqft_band": "1,400 to 1,500",
      "area_sqft_midpoint": 1450.0,
      "property_type": "Non-Landed Properties",
      "postal_district": "04",
      "size_band": "1200-1600"
    }
  ]
}
```

#### GET /project/{project_name}/analytics

```json
Response:
{
  "project_name": "THE INTERLACE",
  "summary": {
    "median_psf": 1724,
    "p25_psf": 1628,
    "p75_psf": 1844,
    "last_transaction_date": "2026-02-01",
    "last_transaction_price": 2230000,
    "last_transaction_psf": 1771,
    "total_transactions": 239,
    "median_monthly_rent": 7500,
    "total_rentals": 1196
  },
  "psf_trend": [
    { "month": "2024-03", "median_psf": 1650, "n": 4 },
    { "month": "2024-04", "median_psf": 1680, "n": 7 }
  ],
  "rental_trend": [
    { "month": "2024-03", "median_rent": 7200, "n": 18 },
    { "month": "2024-04", "median_rent": 7400, "n": 22 }
  ]
}
```

#### GET /project/{project_name}/yield

```json
Response:
{
  "project_name": "THE INTERLACE",
  "yield_by_size_band": [
    {
      "size_band": "1200-1600",
      "size_band_label": "1,200–1,600 sqft",
      "median_rent": 8000,
      "median_price": 2673800,
      "gross_yield": 3.59,
      "n_rentals": 47,
      "n_sales": 23,
      "confidence": "High"
    }
  ],
  "note": "Gross yield only. Net yield typically 1–1.5% lower after costs."
}
```

#### GET /district/{district_code}/projects

```json
Response:
{
  "district": "04",
  "projects": [
    {
      "project_name": "THE INTERLACE",
      "transaction_count": 239,
      "median_psf": 1724,
      "latest_sale_date": "2026-02-01"
    }
  ]
}
```

#### POST /ingest/project

```json
Request body:
{ "project_name": "THE INTERLACE" }

Response:
{
  "status": "success",
  "transactions_fetched": 239,
  "rentals_fetched": 1196,
  "duration_seconds": 12.4
}
```

### Analytics Computation

```python
from statistics import median, quantiles

def compute_psf_analytics(transactions: list[dict]) -> dict:
    psf_values = [t["price_psf"] for t in transactions if t.get("price_psf")]
    if not psf_values:
        return {}

    q = quantiles(psf_values, n=4)
    return {
        "median_psf": round(median(psf_values)),
        "p25_psf":    round(q[0]),
        "p75_psf":    round(q[2]),
    }

def compute_monthly_trend(records: list[dict], value_field: str, date_field: str) -> list[dict]:
    from collections import defaultdict
    monthly = defaultdict(list)
    for r in records:
        month = r.get(date_field, "")[:7]  # "YYYY-MM"
        val   = r.get(value_field)
        if month and val:
            monthly[month].append(val)

    return [
        {"month": m, "median": round(median(vals)), "n": len(vals)}
        for m, vals in sorted(monthly.items())
        if vals
    ]
```

---

## 9. Frontend Architecture

### Stack
- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS
- **Charts:** Recharts
- **HTTP:** fetch / axios to backend API
- **State:** React useState / useEffect (no Redux for v1)

### Pages

```
/                  → Home (search bar only)
/project/[name]    → Project analytics page
/district/[code]   → District project list page
```

### Component Tree

```
app/
├── page.tsx                        # Home — SearchBar only
├── project/
│   └── [name]/
│       └── page.tsx                # Project analytics page
│           ├── SummaryCards        # 4 summary metric cards
│           ├── TransactionTable    # Paginated, sortable
│           ├── PSFTrendChart       # Recharts LineChart
│           ├── RentalTable         # Paginated, sortable
│           ├── RentalTrendChart    # Recharts LineChart
│           └── YieldTable          # Static table with confidence indicator
└── district/
    └── [code]/
        └── page.tsx                # Project list for district
```

### Environment Variables

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Frontend Data Fetching Pattern

```typescript
// Example: fetch analytics on page load
const [analytics, setAnalytics] = useState(null)
const [loading, setLoading]     = useState(true)

useEffect(() => {
  fetch(`${API_BASE}/project/${encodeURIComponent(projectName)}/analytics`)
    .then(r => r.json())
    .then(data => { setAnalytics(data); setLoading(false); })
}, [projectName])
```

---

## 10. Data Refresh Strategy

| Data type | Refresh interval | Trigger |
|-----------|-----------------|---------|
| Sale transactions | 12 hours | Background job or on-demand if cache miss |
| Rental contracts | 24 hours | Background job or on-demand if cache miss |
| Analytics (PSF trend, yield) | 24 hours | Recomputed after data refresh |

### Refresh Logic

```python
from datetime import datetime, timedelta

def needs_refresh(project_name: str, data_type: str, db) -> bool:
    row = db.query(
        "SELECT fetched_at FROM ingestion_log WHERE project_name=? AND data_type=? ORDER BY fetched_at DESC LIMIT 1",
        (project_name, data_type)
    )
    if not row:
        return True

    ttl = timedelta(hours=12 if data_type == "transactions" else 24)
    last_fetch = datetime.fromisoformat(row[0]["fetched_at"])
    return datetime.utcnow() - last_fetch > ttl
```

---

## 11. Future Expansion Design

The system is designed API-first for the following extensions without core refactoring:

| Feature | Required additions |
|---------|--------------------|
| User accounts | Add `users` table + JWT auth middleware to FastAPI |
| Saved searches | Add `saved_searches` table keyed to `user_id` |
| Subscription billing | Add Stripe webhook handler; gate analytics endpoints by plan |
| Alerts | Add `alert_rules` table; background job checks thresholds |
| Liquidity Score | Add `project_metadata` table with unit counts; add `GET /project/{name}/liquidity` endpoint |
| Mobile app | Mobile app calls same FastAPI endpoints — no backend changes needed |

---

## 12. Future Dataset: URA Private Residential Price Index (PPI)

**Dataset:** URA Private Residential Property Price Index (Quarterly)
**Source:** data.gov.sg dataset `d_7c69c943d5f0d89d6a9a773d2b51f337`
**Access:** Public API — `https://data.gov.sg/api/action/datastore_search?resource_id=d_7c69c943d5f0d89d6a9a773d2b51f337`

**When added, enables:**
- National price cycle chart (quarterly index)
- Benchmark project PSF trend against CCR / RCR / OCR index

**Schema addition (v2):**
```sql
CREATE TABLE ppi_index (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    quarter     TEXT,          -- "2024-Q1"
    segment     TEXT,          -- "CCR" | "RCR" | "OCR" | "All"
    index_value REAL,
    fetched_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 13. Implementation Phases

### Phase 1 — Backend Core (Week 1)
- [ ] Project setup: FastAPI + SQLite + folder structure
- [ ] URA session manager (CSRF extraction, cookie persistence)
- [ ] Transaction scraper (POST + pagination + HTML parser)
- [ ] Rental scraper (POST + pagination + HTML parser)
- [ ] Database schema creation and migrations
- [ ] Data normalisation (size bands, date parsing, area midpoints)
- [ ] Analytics computation (PSF stats, monthly trends)
- [ ] Yield estimation engine
- [ ] Cache layer (TTLCache)
- [ ] REST API endpoints (all 5 confirmed endpoints)

### Phase 2 — Frontend Core (Week 2)
- [ ] Next.js project setup with Tailwind + Recharts
- [ ] Home page with SearchBar
- [ ] Project analytics page layout
- [ ] SummaryCards component
- [ ] TransactionTable (paginated, sortable)
- [ ] PSFTrendChart (Recharts LineChart)
- [ ] RentalTable (paginated, sortable)
- [ ] RentalTrendChart
- [ ] YieldTable with confidence indicators
- [ ] District project list page

### Phase 3 — Integration & Polish (Week 3)
- [ ] Connect frontend to backend APIs
- [ ] Loading states and error handling
- [ ] Empty state handling (no data / low n warnings)
- [ ] Mobile responsive layout
- [ ] CSV export on transaction and rental tables
- [ ] End-to-end test: The Interlace, Orchard area, D04

### Phase 4 — Hardening (Week 4)
- [ ] Background refresh scheduler (APScheduler or cron)
- [ ] Rate limiting / delay between URA requests
- [ ] Error monitoring and retry logic for scraper
- [ ] Deployment configuration
- [ ] Documentation

---

## 14. Engineering Constraints and Notes

| Constraint | Details |
|-----------|---------|
| CSRF dependency | Must GET page before each POST; handle token rotation gracefully |
| Session expiry | Re-initialise session on 403 or redirect response |
| URA rate limiting | Add 1–2 second delay between paginated requests |
| 60-month data cap | URA only returns last 60 months; store locally to extend history over time |
| Area as band | Rental areas are ranges ("1,400 to 1,500") — always use midpoint for size band matching |
| Date format | URA returns "Feb-26" — must parse to YYYY-MM-01 for SQL date operations |
| Terms of use | Internal use tool only; do not republish raw URA data commercially |
| Max 5 projects per URA query | For district queries, collect projects first, then query in batches of 5 |

---

## 15. Folder Structure

```
sg-property-intel/
├── backend/
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # Settings, constants
│   ├── database.py              # SQLite connection + schema init
│   ├── scraper/
│   │   ├── session.py           # URASession class
│   │   ├── transactions.py      # Transaction scraper + parser
│   │   └── rentals.py           # Rental scraper + parser
│   ├── analytics/
│   │   ├── psf.py               # PSF stats computation
│   │   ├── trends.py            # Monthly trend computation
│   │   └── yield_engine.py      # Yield estimation
│   ├── routes/
│   │   ├── project.py           # /project/* endpoints
│   │   └── district.py          # /district/* endpoints
│   ├── models/
│   │   └── schemas.py           # Pydantic response models
│   └── utils/
│       └── parsers.py           # clean_number, parse_ura_date, etc.
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Home
│   │   ├── project/[name]/
│   │   │   └── page.tsx         # Project analytics
│   │   └── district/[code]/
│   │       └── page.tsx         # District list
│   ├── components/
│   │   ├── SearchBar.tsx
│   │   ├── SummaryCards.tsx
│   │   ├── TransactionTable.tsx
│   │   ├── RentalTable.tsx
│   │   ├── PSFTrendChart.tsx
│   │   ├── RentalTrendChart.tsx
│   │   └── YieldTable.tsx
│   └── lib/
│       └── api.ts               # API client functions
│
├── SPEC.md                      # This document
└── README.md
```

---

*This specification is complete and build-ready. Pass to engineering model to begin Phase 1 implementation.*
