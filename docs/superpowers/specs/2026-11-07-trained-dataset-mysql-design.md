# Trained Dataset MySQL Design

## Intent

Make MySQL the source of truth for the Trained Dataset tab. The existing
`TrainedBrandsData.csv` source contains 15,839 records and image URLs; those
records must be available through MySQL so the summary, table, details, and
image gallery work when MySQL is the active backend.

## Goals

- Create or refresh the MySQL `trained_brands` table from the configured trained CSV.
- Preserve the existing trained-dataset API and frontend contract.
- Keep `ImageUrls` available as source URLs for lazy image previews and details.
- Detect a missing MySQL trained table clearly during startup/status checks.
- Verify record counts, API responses, and image URL parsing.

## Non-goals

- No changes to the source CSV data.
- No replacement of MySQL with SQLite for trained data.
- No changes to unrelated datasets or the existing UI design.

## Approaches

1. MySQL migration plus schema/status safeguard (selected): keeps all application
   queries on the requested MySQL backend and makes the missing-table failure
   explicit and recoverable.
2. SQLite fallback: faster but violates the requirement that MySQL be used.
3. Hybrid backend: avoids migration but creates inconsistent data ownership.

## Implementation

- Extend the existing MySQL migration path to include `trained_brands` using the
  configured delimiter and normalized column names.
- Ensure the startup/setup path can refresh this table when requested and report
  its row count.
- Add focused tests for migration schema, trained API responses, and image URL
  parsing; run the full test suite afterward.

## Success criteria

With MySQL active, `/api/trained-dataset/summary` returns non-zero totals,
`/api/trained-dataset/records` returns trained rows, detail responses include
`image_urls`, and the UI can render the source images from those URLs.
