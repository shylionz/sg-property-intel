# Rental freshness repair

Prepared 7 November 2026. Production deployment is pending account access.

## Behavior

Project analytics now refresh sales and rentals independently. Rental downloads use URA's one-based pagination and fetch all advertised rows (100 per page), rejecting incomplete, repeated, changed, invalid or older snapshots. A 15-minute successful-refresh cooldown and one-minute failed-refresh cooldown limit source requests.

Before changing rentals, a consistent SQLite backup is created at `<database directory>/.backups/<database stem>-before-rental-refresh-v1.db`. Backup errors fail the rental refresh and retain cached data. The backup is created once and never overwritten. The replacement and refresh status update commit atomically; identical visible contracts retain their multiplicity. Cached history older than the earliest published source month is preserved because URA can apply a narrower retention window than the requested dates.

The page displays sales and rental freshness separately, waits for refresh before reading all stored table pages, and calculates date-filtered summaries/yields over all loaded records. Both tables offer 50-row pagination. Loading a table page does not re-scrape URA. The old automatic destructive admin ingestion fallback is removed; admin ingest now delegates to the validated refresh path.

The production API default and tracked production environment file now point to Railway instead of the retired Render/Tailscale backends.

## Validation completed

- 14 backend regression tests: source pagination past 1,000 rows, one-based source pages, failure/empty/invalid/older snapshot preservation, rollback, idempotence, identical contracts, history retention, independent metadata, endpoint pagination and backup integrity/failure handling.
- 4 frontend API tests: complete pagination, changing/partial result rejection, HTTP errors and no repeated source refreshes for table pages.
- ESLint passes for both modified frontend source files.
- Production build and TypeScript checks pass.
- Complete live URA source downloads: THE ANCHORAGE 884 rows, RIVIERE 501 rows, THE INTERLACE 1,189 rows; latest month September 2026 for all three. These are source snapshot counts, not expected total stored counts: retained archival history can make database totals larger.
- Local browser preview uses the real downloaded Anchorage rental snapshot and synthetic sales. Confirmed 884 rental rows loaded, next page displays 51–100, and an older date filter still returns 46 rentals. Production has not been modified by these preview checks.
- Local SQLite integration confirms the pre-refresh backup retains the original rental row while the active database receives the source snapshot.

Run checks from repository root:

```sh
python -m pytest backend/tests -q
cd frontend
node --test tests/api.test.mjs
npx eslint 'src/app/project/[name]/page.tsx' src/lib/api.ts
npm run build
```

Backend tests need pytest and httpx 0.27.x in addition to runtime dependencies. Frontend tests directly import TypeScript and require Node 22.18+ or a newer Node release with type stripping (validated on Node 26).

## Production rollout

1. Confirm the deployed branch and current head. Retain current deployment IDs for rollback. Verify Railway `DATABASE_URL=sqlite:////data/sg_property_intel.db` and persistent volume at `/data`.
2. Back up the live SQLite database with SQLite's online backup API and verify `PRAGMA integrity_check` and table counts. Keep an export off the Railway volume if available. The application backup is an additional safeguard before rental replacement, not an off-service disaster recovery backup.
3. Deploy the backend first. Startup creates only the additive `rental_refresh_status` table; existing columns are unchanged. Verify `/health` and API metadata.
4. Load/refresh the three known projects. Confirm rental source/database latest months are September 2026 (or newer if URA has published more). Compare monthly counts within the refreshed source window and check that the backup exists and passes integrity check. Do not compare total database counts directly with source counts when older cached history is retained.
5. Confirm a second refresh does not add duplicate rows; throttled normal requests do not re-download. Confirm a source error continues to display cached data with a rental-specific warning.
6. Deploy Vercel frontend with `NEXT_PUBLIC_API_BASE_URL=https://sg-property-intel-backend-production.up.railway.app`. Verify the deployed bundle's API base, independent freshness banners, pagination, and older-date filters.
7. Verify through the public URL. Until backend and frontend are deployed and these checks pass, the repair is not complete.

GitHub integration allowed repository reads but branch creation returned HTTP 403 "Resource not accessible by integration". Publishing requires an authenticated GitHub write path. Railway and Vercel connections were requested but not confirmed. Vercel sign-in additionally encountered a user-reported recovery-code prompt.

## Rollback and limits

Revert application deployments to the saved versions first. The additive metadata table can remain. A validated rental replacement corrects duplicated first-page records from the old scraper, so rental counts may fall despite adding newer months. Restore the database backup only if data verification establishes a bad replacement; stop writes and make a fresh backup before restoration. The automatic backup reflects the database immediately before the first rental replacement, which may be after a sales refresh.

Source changes that omit the result-count/range markers are treated as failures rather than accepted silently. Empty source results retain cached rentals and show unverified freshness. Process-local project locks and a file lock for the backup suit the existing single-service SQLite deployment; multiple independent replicas sharing a database need a distributed refresh lock. Older archival cached records are retained and are not claimed to have been reverified by URA. Sales scraper behavior beyond its existing refresh mechanism is outside this repair.
