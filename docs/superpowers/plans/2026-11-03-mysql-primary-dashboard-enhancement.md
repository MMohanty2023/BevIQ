# MySQL-Primary Assistant and Dashboard Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make BevIQ MySQL-first with SQLite fallback, deliver complete indexed ID/search results, improve grounded document chat and uploads, and add a simple Power BI-ready business dashboard.

**Architecture:** Keep Flask routes, engines, and the existing frontend. Introduce explicit backend selection in `DBManager`, indexed search methods in `SQLEngine`, bounded session history in the document/RAG layer, and additive dashboard APIs. The original CSV files remain unchanged; optional optimized copies are generated separately and database queries remain the runtime search path.

**Tech Stack:** Python 3, Flask, MySQL/PyMySQL, SQLite fallback, pandas, pypdf, python-docx, openpyxl, pytesseract/Pillow when available, HTML/CSS/JavaScript.

**Spec:** `docs/superpowers/specs/2026-11-03-mysql-primary-dashboard-design.md`

## Global Constraints

- MySQL is the preferred backend; SQLite is selected only when MySQL is not configured or unavailable.
- Preserve original CSV files and source filenames/original row references.
- Existing APIs remain compatible; new request fields and response fields are additive.
- No automatic modification of master UPC or product data.
- Search responses are bounded and paginated.
- Answers must be based on retrieved source data and must not invent records.

## Review Focus

- MySQL configuration succeeds but the application continues using SQLite; covered by Task 1 backend-selection tests.
- MySQL becomes unavailable after startup; covered by Task 1 fallback test.
- An ID exists in multiple files or only as an alternate UPC; covered by Task 2 complete lookup tests.
- Search terms contain SQL wildcard characters or empty/very long input; covered by Task 2 validation tests.
- Empty, unsupported, oversized, or OCR-unreadable uploads; covered by Task 4 upload tests.

### Task 1: Make MySQL the active backend with safe SQLite fallback

**Files:**
- Modify: `database/db_manager.py`
- Modify: `app.py` (`/api/configure-db`, `/api/db-status`)
- Modify: `config.py` only if backend-selection configuration needs an explicit environment value
- Test: `tests/test_db_backend.py`

**Interfaces:**
- Produce `DBManager.set_mysql_backend(enabled: bool) -> None`.
- Produce `DBManager.backend_name() -> str` returning `"mysql"` or `"sqlite"`.
- Preserve `query(sql, params=None)` and `query_df(sql, params=None)` signatures.

- [ ] Step 1: Write failing tests for successful MySQL configuration setting the active backend to MySQL, failed configuration leaving SQLite active, and `/api/db-status` reporting the active backend.
- [ ] Step 2: Run `pytest tests/test_db_backend.py -v`; confirm the tests fail because backend state is not switched/reported.
- [ ] Step 3: Implement explicit backend state, connection probing, and controlled fallback in `DBManager`; update configure/status routes without breaking current response keys.
- [ ] Step 4: Run the focused tests and existing endpoint tests; confirm all pass.
- [ ] Step 5: Commit `feat: make mysql the primary database backend`.

### Task 2: Add complete indexed ID lookup and fast paginated search

**Files:**
- Modify: `engines/sql_engine.py`
- Modify: `data_ingestion/loader.py`
- Modify: `database/mysql_migrator.py`
- Modify: `engines/rag_orchestrator.py`
- Test: `tests/test_sql_search.py`
- Test: `tests/test_rag_id_lookup.py`

**Interfaces:**
- Produce `SQLEngine.lookup_identifier(identifier: str, limit: int = 200) -> dict` with `records`, `related_records`, `total_matches`, `source_files`, and normalized identifier fields.
- Produce `SQLEngine.search_catalog(query: str, limit: int = 100, offset: int = 0) -> dict` while preserving old callers.
- Produce `SQLEngine.get_dashboard_metrics() -> dict` for later dashboard routes.

- [ ] Step 1: Write failing tests for exact ID lookup across all configured datasets, alternate UPC matching, invalid IDs, complete row fields, and paginated catalog search.
- [ ] Step 2: Run the focused tests and confirm failures are caused by missing identifier behavior rather than test setup.
- [ ] Step 3: Add safe identifier normalization and parameterized exact-match queries for UPC/alternate UPC and dataset-specific ID columns; return all selected source columns and related UPC-linked rows.
- [ ] Step 4: Add MySQL indexes/full-text-compatible search indexes and equivalent SQLite indexes during ingestion/migration; keep leading-zero UPC values as strings.
- [ ] Step 5: Update orchestrator routing so numeric IDs and explicit “ID/details/find” requests use the complete lookup path before generic search; remove hardcoded record counts from generated answers.
- [ ] Step 6: Run focused tests and all existing query/orchestrator tests; confirm pass.
- [ ] Step 7: Commit `feat: add indexed complete identifier search`.

### Task 3: Generate safe optimized CSV copies without changing source data

**Files:**
- Create: `tools/optimize_csv.py`
- Modify: `config.py` to register an optional optimized-data directory only if needed
- Test: `tests/test_optimize_csv.py`
- Documentation: `README.md`

**Interfaces:**
- Produce `optimize_csv_file(source: Path, destination: Path, delimiter: str, columns: list[str] | None = None) -> dict`.
- Produce a CLI that accepts an input directory, output directory, and optional deduplication key.

- [ ] Step 1: Write failing tests that verify originals are unchanged, selected columns are retained, duplicate rows are removed deterministically, and row/source metadata is preserved.
- [ ] Step 2: Run the focused tests and confirm failure because the utility does not yet exist.
- [ ] Step 3: Implement streaming chunked optimization with string preservation for identifiers, stable deduplication, and atomic output replacement inside the requested output directory.
- [ ] Step 4: Run the utility in dry-run/report mode against the real CSV directory; record row counts and size comparisons without replacing application inputs.
- [ ] Step 5: Add usage documentation and run the full test suite.
- [ ] Step 6: Commit `feat: add safe optimized csv generation utility`.

### Task 4: Strengthen document and image upload/search

**Files:**
- Modify: `document_rag.py`
- Modify: `app.py` (`/api/chat`, new upload validation/status route if required)
- Modify: `requirements.txt` only for packages already used by supported formats and missing from the manifest
- Test: `tests/test_document_rag.py`
- Test: `tests/test_upload_endpoints.py`

**Interfaces:**
- Produce `validate_upload(file_storage, max_bytes: int) -> None`.
- Preserve `ingest(file_storage, session_id)` and extend supported extraction safely.
- Add indexed document search without loading every session chunk into Python for each query.

- [ ] Step 1: Write failing tests for PDF, DOCX, CSV, XLSX, image OCR success/failure, unsupported extension, oversized upload, and no-readable-text errors.
- [ ] Step 2: Run focused tests and confirm expected failures.
- [ ] Step 3: Add upload size/type validation, safe cleanup on extraction failure, optional `.doc` handling with a clear dependency/error message, and bounded CSV/Excel extraction.
- [ ] Step 4: Add SQLite FTS5 document content indexing and a MySQL-compatible fallback path where document storage is configured; preserve session scoping and source page/sheet metadata.
- [ ] Step 5: Run document and endpoint tests, then the full suite.
- [ ] Step 6: Commit `feat: harden document and image retrieval`.

### Task 5: Persist bounded conversation context and improve grounded answers

**Files:**
- Modify: `document_rag.py` or create `engines/conversation_store.py`
- Modify: `engines/rag_orchestrator.py`
- Modify: `app.py`
- Test: `tests/test_conversation_context.py`
- Test: `tests/test_rag_grounding.py`

**Interfaces:**
- Produce `ConversationStore.append(session_id: str, role: str, content: str) -> None`.
- Produce `ConversationStore.recent(session_id: str, limit: int = 8) -> list[dict]`.
- Keep `route_and_execute(user_query, session_id='default-session')` compatible.

- [ ] Step 1: Write failing tests for follow-up questions, bounded history, grounded unknown responses, and no hallucinated record details.
- [ ] Step 2: Run focused tests and verify failure.
- [ ] Step 3: Persist user/assistant turns, use recent context for intent resolution, and require retrieved evidence for catalog/document claims.
- [ ] Step 4: Refactor response formatting so complete retrieved records are available to the frontend while answer summaries remain concise and live.
- [ ] Step 5: Run focused and full tests.
- [ ] Step 6: Commit `feat: add grounded conversation context`.

### Task 6: Add dashboard and Power BI-ready APIs

**Files:**
- Modify: `app.py`
- Modify: `engines/sql_engine.py`
- Create: `engines/dashboard_engine.py` if dashboard aggregation exceeds the SQL engine responsibility
- Test: `tests/test_dashboard_endpoints.py`

**Interfaces:**
- Add `GET /api/dashboard/overview` returning live KPIs and dataset summaries.
- Add `GET /api/dashboard/categories` returning category aggregates.
- Add `GET /api/dashboard/missing-upc` returning bounded missing-UPC metrics/records.
- Add `GET /api/dashboard/export/<dataset>` returning Power BI-friendly CSV data with validated dataset names.

- [ ] Step 1: Write failing endpoint tests with fake DB results and verify stable JSON keys, no hardcoded counts, bounded results, and invalid dataset rejection.
- [ ] Step 2: Run focused tests and confirm failure.
- [ ] Step 3: Implement read-only dashboard aggregation using the active backend and safe allowlisted dataset mappings.
- [ ] Step 4: Verify results against actual local database counts without modifying source data.
- [ ] Step 5: Run dashboard and full test suites.
- [ ] Step 6: Commit `feat: add powerbi-ready dashboard APIs`.

### Task 7: Simplify and enhance the frontend UX

**Files:**
- Modify: `templates/index.html`
- Modify: `static/*` only if an existing static asset structure is present and useful
- Test: `tests/test_frontend_contract.py` or endpoint-level assertions for required frontend data contracts

**Interfaces:**
- Add a Dashboard tab consuming the dashboard endpoints.
- Add clear MySQL/SQLite active-backend status.
- Add upload preview for images and selected-file metadata for documents.
- Add loading, empty, error, pagination, and source display states.

- [ ] Step 1: Add frontend contract checks for dashboard endpoint names, backend status rendering, upload preview hooks, and download links.
- [ ] Step 2: Implement a restrained business dashboard with KPI cards, category/missing-UPC summaries, and responsive tables using existing CSS conventions.
- [ ] Step 3: Improve chat rendering for complete record details, pagination controls, upload errors, and image previews without removing existing comparison UI.
- [ ] Step 4: Manually exercise desktop and mobile layouts and all existing navigation tabs.
- [ ] Step 5: Run full backend tests and a Flask smoke test.
- [ ] Step 6: Commit `feat: improve assistant dashboard and chat ux`.

### Task 8: Final verification and handoff

**Files:**
- Modify: `README.md` with setup, MySQL-primary behavior, dashboard/Power BI usage, and test commands
- Modify: any affected configuration documentation

- [ ] Run focused tests for backend selection, identifier search, uploads, conversations, dashboard APIs, and frontend contracts.
- [ ] Run the complete project test command and record unrelated pre-existing failures separately.
- [ ] Verify valid/invalid IDs, complete records, optimized CSV dry-run, document/image upload paths, follow-ups, and dashboard exports.
- [ ] Run static/problem diagnostics on modified Python and HTML files.
- [ ] Provide final modified-file list, dependencies, API/database changes, test results, and remaining issues.
