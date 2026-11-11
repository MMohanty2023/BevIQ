# MySQL-Primary Assistant and Dashboard Design

## Intent

Make BevIQ use MySQL as its primary data store, retain SQLite as a reliable
fallback, improve search and record retrieval, and present the existing
functionality through a simpler business-oriented interface with a
Power BI-ready dashboard layer.

## Goals

- Switch to MySQL after a successful configuration and use it for all catalog,
  comparison, and dashboard queries.
- Keep SQLite available when MySQL is unavailable, without changing source CSVs.
- Add indexed exact-ID/UPC lookup and efficient text search with pagination.
- Return complete source-backed records and related records without invented data.
- Improve document/image upload validation, extraction, and search behavior.
- Persist enough conversation context for follow-up questions in a session.
- Replace hardcoded dashboard/query summaries with live database values.
- Make the UI clean, responsive, readable, and business-focused.
- Expose dashboard metrics and export endpoints suitable for Power BI import.

## Non-goals

- No destructive replacement, deletion, or overwriting of original CSV files.
- No mandatory cloud AI or external search service.
- No direct Power BI embedding until the user supplies a Power BI report/workspace
  URL and the required authentication/embedding configuration.
- No automatic modification of master UPC or product data.

## Constraints

- Preserve the current Flask, MySQL, SQLite, pandas, and local Ollama stack.
- MySQL is the preferred backend; SQLite is selected only when MySQL is not
  configured or unavailable.
- Existing APIs should remain compatible while accepting additive parameters.
- Source filenames and original CSV row references must remain available.
- Search responses must be bounded and paginated to avoid large payloads.

## Approaches

### Selected: database-first MySQL search with SQLite parity

Use MySQL as the active backend after successful configuration, add indexes for
exact identifiers, normalized brands, suppliers, and searchable text, and use
parameterized paginated queries. Keep the existing SQLite schema and add the
same logical query behavior for fallback mode. Create optional optimized CSV
copies only as a safe offline artifact; the application continues to use the
database rather than loading CSVs for every search.

This fits the current architecture, preserves all data, and supports Power BI
through stable SQL-backed API endpoints.

### Rejected: replace source CSVs with reduced CSVs

This can reduce disk usage but risks losing columns, duplicate evidence, and
original row traceability. It also does not solve repeated full-file searches
as reliably as indexed database queries.

### Rejected: introduce an external search platform

This would add deployment and data-synchronization complexity and conflict with
the existing offline/fallback design.

## Design decisions

### Backend selection

`DBManager` will expose an explicit active-backend state. Successful MySQL
configuration will enable MySQL for subsequent requests; failed connection
checks will safely leave SQLite active. Connections will not perform a health
check on every query when the selected backend is already known; a controlled
fallback path will handle connection failures.

### Search and IDs

The assistant will detect numeric and textual IDs, search exact identifier
columns across configured datasets, and return all matching rows with dataset,
source file, source row, and available fields. Related records will be linked by
normalized UPC/alternate UPC when present. Text search will be paginated and
bounded, with indexes/full-text search where supported.

### Documents and images

Uploads will be validated by extension and size, stored with safe filenames,
extracted into session-scoped chunks, and searched through an indexed document
store. PDF, DOC/DOCX, CSV, Excel, text, and common image formats will report
clear extraction errors. The frontend will show selected-image previews.

### Conversations

Session-scoped turns will be stored with bounded history. Follow-up questions
will use recent context while keeping database and uploaded-document answers
grounded in retrieved source data.

### Dashboard and Power BI

The dashboard will show live KPIs for records, unique UPCs, dataset sizes,
missing-master counts, and category distribution. New read-only JSON endpoints
will expose KPI, dataset, comparison, and trend data. CSV export endpoints will
provide Power BI-friendly tabular data.

### UI/UX

Retain the existing dark visual foundation but simplify navigation, reduce
decorative badges, improve spacing and typography, add clear status/loading/error
states, and make record tables usable on mobile. The dashboard will be a first
class view rather than a decorative chart area.

## Verification

- Test MySQL selection, MySQL failure fallback, and existing SQLite behavior.
- Test exact valid/invalid ID lookup and related-record retrieval.
- Test paginated text search against the indexed database.
- Test PDF, DOCX, CSV, Excel, and image upload/error paths.
- Test conversation follow-ups and source-grounded answers.
- Test dashboard APIs and Power BI-oriented exports.
- Run the existing test suite and focused endpoint/search tests.
