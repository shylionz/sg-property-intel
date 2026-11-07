# Rental freshness repair

Prepared 7 November 2026. Production deployment is pending account access.

## Behavior

Project analytics now refresh sales and rentals independently. Rental downloads use URA's one-based pagination and fetch all advertised rows (100 per page), rejecting incomplete, repeated, changed, invalid or older snapshots. A 15-minute successful-refresh cooldown and one-minute failed-refresh cooldown limit source requests.

Before changing rentals, a consistent SQLite backup is created at `<database directory>/.backups/<database stem>-before-rental-refresh-v1.db`. Backup errors fail the rental refresh and retain cached data. The backup is created once and never overwritten. The replacement and refresh status update commit atomically; identical visible contracts retain their multiplicity. Cached history older than the earliest published source month is preserved because URA can apply a narrower retention window than the requested dates.

The page displays sales and rental freshness separately, waits for refresh before reading all stored table pages, and calculates date-filtered summaries/yields over all loaded records. Both tables offer 50-row pagination. Loading a table page does not re-scrape URA. The old automatic destructive admin ingestion fallback is removed; admin ingest now delegates to the validated refresh path.

The production API default and tracked production environment file now point to Railway instead of the retired Render/Tailscale backends.

## Validation completed

- 16 backend regression tests: source pagination past 1,000 rows, one-based source pages, failure/empty/invalid/older snapshot preservation, rollback, idempotence, identical contracts, history retention, independent metadata, endpoint pagination and backup integrity/failure handling.
- 4 frontend API tests: complete pagination, changing/partial result rejection, HTTP errors and no repeated source refreshes for table pages.
- ESLint passes for both modified frontend source files.
- Production build and TypeScript checks pass.
- Complete live URA source downloads: THE ANCHORAGE 884 rows, RIVIERE 501 rows, THE INTERLACE 1,189 rows; latest month September 2026 for all three. These are source snapshot counts, not expected total stored counts: retained archival history can make database totals larger.
- Local browser preview uses the real downloaded Anchorage rental snapshot and synthetic sales. Confirmed 884 rental rows loaded, next page displays 51–100, and an older date filter still returns 46 rentals. Production has not been modified by these preview checks.
- Startup now creates/verifies the backup before adding metadata tables or serving requests; new installations without a database are supported.
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
2. The new backend verifies a consistent online SQLite backup before schema initialization or serving requests. Confirm the startup log contains the pre-repair backup path and `integrity_check=ok`. Keep an off-volume export or volume snapshot if available; an on-volume backup is not off-service disaster recovery.
3. Deploy the backend first. Startup creates only the additive `rental_refresh_status` table; existing columns are unchanged. Verify `/health` and API metadata.
4. Load/refresh the three known projects. Confirm rental source/database latest months are September 2026 (or newer if URA has published more). Compare monthly counts within the refreshed source window and check that the backup exists and passes integrity check. Do not compare total database counts directly with source counts when older cached history is retained.
5. Confirm a second refresh does not add duplicate rows; throttled normal requests do not re-download. Confirm a source error continues to display cached data with a rental-specific warning.
6. Deploy Vercel frontend with `NEXT_PUBLIC_API_BASE_URL=https://sg-property-intel-backend-production.up.railway.app`. Verify the deployed bundle's API base, independent freshness banners, pagination, and older-date filters.
7. Verify through the public URL. Until backend and frontend are deployed and these checks pass, the repair is not complete.

GitHub integration allowed repository reads but branch creation returned HTTP 403 "Resource not accessible by integration". Publishing requires an authenticated GitHub write path. Railway is connected: project e04059ee-97b4-4558-be11-d43df1c94b63, production environment 5dde231f-ff76-411d-84ae-32de87bc0231, backend service 68289c88-544d-44b7-9b1e-b3493147e97e, volume 55b1e537-677f-4e79-b24d-074ec6ad8c31 mounted at /data. The current healthy deployment 84b30b49-63dd-48d0-9fb6-f713836624c4 is available for rollback. No staged changes were present. Vercel is connected at account level, but project access requires the pending team grant for team_5AvxtRlm8HrukkaZNOV1ozQ8; project prj_PTcL46DSX7NDjR6rWur3oV0s7UD4. A temporary GitHub CLI device sign-in is awaiting user authorization.

## Rollback and limits

Revert application deployments to the saved versions first. The additive metadata table can remain. A validated rental replacement corrects duplicated first-page records from the old scraper, so rental counts may fall despite adding newer months. Restore the database backup only if data verification establishes a bad replacement; stop writes and make a fresh backup before restoration. The automatic backup reflects the database immediately before the first rental replacement, which is now created during startup before schema initialization and refresh requests.

Source changes that omit the result-count/range markers are treated as failures rather than accepted silently. Empty source results retain cached rentals and show unverified freshness. Process-local project locks and a file lock for the backup suit the existing single-service SQLite deployment; multiple independent replicas sharing a database need a distributed refresh lock. Older archival cached records are retained and are not claimed to have been reverified by URA. Sales scraper behavior beyond its existing refresh mechanism is outside this repair.
