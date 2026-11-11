# Beverage Data Assistant – Dashboard, Master Brand and AI Enhancement

## Intent

Enhance the existing Flask Beverage Data Assistant into a clearer, more professional analytics product without rebuilding it or removing working features. The result should feel like the current application improved: simple, attractive, light-themed, responsive, and easy to understand for a business user.

## Goals

- Replace static dashboard values with live database-derived metrics.
- Add category KPI cards for Beer, Wine, RTD, Spirits, Master Brand records, and Suppliers.
- Add Power BI-style dashboard visualizations: overall UPC quality donut, category comparison, and readable summary tables.
- Add category-level UPC metrics with clickable/detail access and CSV export.
- Add Master Brand overview and dedicated search/detail experience using the real table schema and real ID column.
- Preserve existing chat, RAG, UPC audit, comparison, document upload, report export, and conversation history features.
- Improve AI routing so database questions use database engines, while general questions stay conversational and do not execute catalog SQL.
- Show safe SQLite/MySQL connectivity state, active backend, database name, and refresh/connection timing without exposing secrets.
- Keep UPC values as strings and use parameterized queries wherever supported.

## Non-goals and anti-goals

- Do not rebuild the project from scratch.
- Do not invent KPI values, Master Brand IDs, product data, or schema fields.
- Do not automatically modify Master Brand or UPC data from audits.
- Do not add excessive animations, gradients, oversized cards, or a generic AI-dashboard aesthetic.
- Do not make MySQL the active source unless it is verified reachable and selected safely by configuration.

## Current architecture and constraints

- Flask routes are in `app.py`; the main UI is currently in `templates/index.html`.
- `database/db_manager.py` selects SQLite or MySQL and currently falls back to SQLite if MySQL is unavailable.
- `engines/sql_engine.py`, `comparison_engine.py`, `rag_orchestrator.py`, and `conversation_store.py` already provide core data and chat behavior.
- Existing CSV ingestion creates normalized fields such as `clean_upc`, `clean_alt_upc`, `norm_brand`, and `norm_supplier`.
- The real Master Brand schema and ID column must be discovered from the active database before implementing search/detail rendering.
- The existing single-page interface and endpoint contracts should remain compatible where possible.

## Approaches considered

### Single-page enhancement

Extend the current page and routes directly. This minimizes file changes and keeps the current UI flow, but risks making the existing large template harder to maintain as Master Brand and analytics features grow.

### Modular backend and UI enhancement — selected

Keep the existing single-page experience and technology stack, while adding focused service methods and API endpoints for dashboard metrics, UPC analysis, Master Brand search, database status, and exports. Reorganize the page into a simple sidebar/navigation layout with sections that load live data on demand. This provides reliable boundaries for future changes while preserving current functionality.

### Full frontend rewrite

Would provide maximum visual control, but would add unnecessary risk, dependency changes, and regression surface for a project that already has a working Flask/HTML/JavaScript interface.

## Proposed design

### Dashboard

The dashboard will use a compact light theme with a sidebar or clear navigation rail, a top status strip, KPI cards, and a two-column content area. The first row will show live category and master/supplier totals. The next area will show an overall UPC completion donut and category-wise UPC bars/cards. A lower section will show Master Brand quality and recent/live data summaries.

Chart.js will be used if available through the existing frontend pattern. Charts will be driven only by API responses. Clicking a category or UPC segment will populate a filtered table/detail view rather than showing fake drill-down data.

### Backend metrics

Add database-backed methods that return:

- category totals for Beer, Wine, RTD, and Spirits;
- Master Brand total rows, unique brands, unique IDs, records with UPC, and records without UPC;
- supplier count using the actual supplier source and a defined distinct-count rule;
- total/available/missing UPC counts per category and overall;
- invalid UPC count only if existing validation logic can classify it consistently;
- active backend and connection status for SQLite and MySQL.

All counts will handle blank/null UPCs consistently and avoid duplicate counting across metrics.

### Master Brand search

Inspect the actual `ai_master` table columns and identify the real ID column and its uniqueness. Add a parameterized search endpoint supporting exact ID/UPC matches and partial brand/product searches, with optional combined filters. Results will return all available columns dynamically, bounded by a safe result limit, and the UI will show an empty state when nothing matches.

### AI assistant

Retain the existing conversation store and RAG orchestrator. Strengthen routing rules so greetings and general questions do not reach catalog SQL/vector search, while UPC, Master Brand ID, product, category, supplier, comparison, and report requests use the appropriate existing engines. Replies will match the user's latest language style: English, Devanagari Hindi, or Roman Hindi/Hinglish. Unsupported requests will receive a clear clarification instead of fabricated data.

### Database settings and safety

Expose a simple active-database selector/status panel. SQLite remains the safe default unless MySQL connectivity is verified. MySQL migration stays explicit. Passwords will remain server-side and will not be rendered into HTML, API responses, or logs. Existing fallback behavior will be kept but made visible and testable.

### Reports

Reuse the current report-token/export mechanism. Add exports for missing UPC data, category UPC summaries/details, Master Brand search results, duplicate UPCs, and supplier information where the corresponding API returns records.

## Verification

- Add focused tests for metric correctness, Master Brand schema-aware search, UPC classification, backend status, and chat routing.
- Run the existing test suite and relevant endpoint tests.
- Check frontend diagnostics and manually exercise dashboard load, category drill-down, Master Brand search, chat, export, and database status states.
- Verify no static KPI values remain in live dashboard sections.

## Open implementation calls

- Use existing normalized columns when present and derive safe fallback expressions only when the active schema requires it.
- Treat blank, null, and common placeholder UPC values as missing; classify invalid values only through an explicit validator.
- Use bounded result sizes for browser tables and preserve full CSV exports through the existing download flow.
