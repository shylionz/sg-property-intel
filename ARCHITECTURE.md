# Architecture Notes — SG Property Intelligence

---

## Current State (Prototype)

- Projects must be manually ingested via `POST /admin/ingest/{project_name}`
- Search dropdown only returns projects already in the local SQLite DB
- DB is ephemeral on Render free tier — wiped on restart
- Requires periodic re-ingestion to keep data fresh

**This is acceptable for prototype speed. It is not the target design.**

---

## Target Architecture

### 1. Dynamic Project Discovery

Search should not be limited to pre-ingested projects.

- Maintain a **project name index** — a lightweight list of all valid Singapore condo/project names
- Source: scrape or cache the full URA project list on first run, refresh periodically
- Search endpoint queries this index, not the transactions table
- User can find any valid project, whether or not it has been fetched yet

### 2. On-Demand Data Fetch

When a user selects a project that is not yet in the DB:

```
User selects project
       ↓
Backend checks local cache (DB)
       ↓
Cache HIT → return immediately
Cache MISS → fetch from URA on the fly → store in DB → return to user
```

- First load for an uncached project: ~5–15s (URA scrape time)
- Subsequent loads: instant (served from DB cache)
- Show a loading indicator on the frontend during live fetch

### 3. Result Caching

- After first fetch, cache transactions + rentals in DB as normal
- Add `fetched_at` timestamp to project records
- Treat cache as stale after 7 days → re-fetch on next request
- Popular projects can still be pre-warmed at startup as an optimisation, not a requirement

### 4. Persistence

- Migrate from SQLite (ephemeral on Render) to **PostgreSQL**
- Render offers a managed Postgres add-on, or use Supabase/Neon free tier
- DB persists across deploys and restarts — no more re-ingestion on every cold start

---

## Implementation Phases

| Phase | Scope |
|-------|-------|
| **Phase A** | Migrate SQLite → Postgres. DB survives restarts. No UX change. |
| **Phase B** | Build project name index. Search queries index, not DB. |
| **Phase C** | On-demand fetch on project select. Loading state on frontend. |
| **Phase D** | Stale cache refresh (7-day TTL). Remove manual ingest dependency. |

---

## What Does NOT Change

- API contract stays the same (`/project/{name}/transactions` etc.)
- Frontend is unchanged until Phase C loading state
- Pre-ingest remains available as an optional warm-cache tool for popular projects

---

## Notes

- Do not implement until explicitly requested
- Phase A (Postgres) is the highest-leverage first step — fixes the ephemeral DB problem immediately
- Phase B + C are the UX win — makes the app feel like a real product

Last updated: 2026-03-07
