# Singapore Property Transaction Intelligence Tool

## Overview
Full-stack application for analyzing Singapore private residential property transactions and rental yields using URA data.

## Project Structure
```
sg-property-intel/
├── backend/           # FastAPI backend
│   ├── main.py       # API entry point
│   ├── ingest_project.py  # CLI for scraping URA data
│   ├── models/       # SQLAlchemy models
│   ├── scrapers/     # URA web scrapers
│   ├── analytics/    # PSF & yield calculations
│   └── api/          # REST endpoints
│
├── frontend/         # Next.js frontend
│   └── src/app/      # Pages & components
│
└── SPEC.md           # Technical specification
```

## Quick Start

### 1. Backend
```bash
cd backend

# Install dependencies
pip3 install -r requirements.txt

# Start server
python3 -m uvicorn main:app --reload --port 8000
```

### 2. Ingest Data
```bash
# Ingest a project's data (last 12 months for speed)
python3 ingest_project.py "THE INTERLACE"
```

### 3. Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Then open http://localhost:3000

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /project/{name}/transactions` | Sale transactions |
| `GET /project/{name}/rentals` | Rental contracts |
| `GET /project/{name}/analytics` | PSF stats, trends |
| `GET /project/{name}/yield` | Yield by size band |

## Tech Stack

- **Backend**: FastAPI, SQLite, SQLAlchemy
- **Frontend**: Next.js 16, Tailwind CSS, Recharts
- **Data**: URA (Urban Redevelopment Authority) Singapore
