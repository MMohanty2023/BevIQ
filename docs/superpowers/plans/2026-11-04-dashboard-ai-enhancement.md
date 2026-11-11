# Beverage Data Assistant Dashboard and AI Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or superpowers:subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the existing Flask Beverage Data Assistant with live Power BI-style dashboard analytics, reliable Master Brand lookup, useful work/general chatbot behavior, and clearer SQLite/MySQL status while preserving existing features.

**Architecture:** Keep the current Flask single-page application and existing engines. Add focused SQL-engine methods and Flask API endpoints for metrics, Master Brand search, database status, and exports; then enhance the existing HTML/JavaScript UI to consume those APIs with simple cards, donut/bar charts, filters, tables, and clear states.

**Tech Stack:** Python, Flask, SQLite, MySQL/PyMySQL, Pandas, existing SQL/comparison/RAG engines, HTML/CSS/JavaScript, Chart.js loaded in the existing page if not already available.

**Spec:** `docs/superpowers/specs/2026-11-04-dashboard-ai-enhancement-design.md`

## Global Constraints

- Do not rebuild the project from scratch.
- Preserve existing chat, RAG, UPC audit, comparison, document upload, report export, and conversation history features.
- All dashboard numbers and database answers must come from actual database queries.
- Do not invent Master Brand IDs, product fields, UPCs, or sample data.
- Keep UPC values as strings and preserve leading zeroes.
- SQLite remains the safe default unless MySQL connectivity is verified and selected.
- Never expose database passwords or secrets in the frontend or logs.
- Use bounded browser results and parameterized user-input queries.

## Review Focus

- Blank/null/placeholder UPCs: counted as missing consistently; covered by dashboard metric tests.
- Invalid UPC values: reported only when the validator classifies them; covered by UPC-quality tests.
- Master Brand schema variation and non-unique IDs: search uses discovered columns and clearly reports multiple matches; covered by search tests.
- MySQL unavailable or query failure: status remains truthful and SQLite fallback is visible; covered by backend tests.
- Normal greetings/general questions: never execute catalog SQL or return the current unhelpful fallback when a conversational engine is available; covered by routing tests.

### Task 1: Add live analytics and schema-aware SQL services

**Files:**
- Modify: `engines/sql_engine.py`
- Modify: `database/db_manager.py`
- Modify: `data_ingestion/normalizer.py` if the existing validator needs a shared UPC-quality helper
- Test: `tests/test_dashboard_metrics.py`
- Test: `tests/test_master_brand_search.py`
- Test: `tests/test_db_backend.py`

**Interfaces:**
- Produce `SQLEngine.get_dashboard_metrics() -> dict` with category totals, overall UPC quality, category UPC quality, and Master Brand summary.
- Produce `SQLEngine.search_master_brands(query: str = "", master_id: str | None = None, brand: str | None = None, upc: str | None = None, product: str | None = None, limit: int = 100) -> dict` returning `columns`, `records`, `total_matches`, and schema metadata.
- Produce `DBManager.database_status() -> dict` returning SQLite status, MySQL status, active backend, database name, and last checked/connected timestamps without credentials.
- Keep existing method signatures and fallback behavior compatible.

- [ ] **Step 1: Write failing metric tests** for live Beer/Wine/RTD/Spirits totals, overall available/missing UPC counts, category completion percentages, and Master Brand totals using a fake database with known rows.
- [ ] **Step 2: Run `pytest tests/test_dashboard_metrics.py -v` and confirm the new interfaces fail.**
- [ ] **Step 3: Implement the metric methods** using configured table names, normalized UPC columns, explicit missing-value rules, distinct counts only where required, and safe zero-denominator percentages.
- [ ] **Step 4: Write failing Master Brand search tests** for exact ID, brand+UPC, brand-only partial search, multiple matches, dynamic columns, and not-found response.
- [ ] **Step 5: Run `pytest tests/test_master_brand_search.py -v` and confirm failure.**
- [ ] **Step 6: Implement schema discovery and parameterized Master Brand search** against `ai_master`; detect the real ID-like column from actual table columns, prefer exact ID/UPC matching, and return all available fields without inventing names.
- [ ] **Step 7: Write failing database status tests** for SQLite-only, MySQL-connected, and MySQL-failure fallback states.
- [ ] **Step 8: Implement `database_status()` and connection timestamp tracking** without changing password handling or logging secrets.
- [ ] **Step 9: Run the three focused test files and the existing database tests; commit the task.**

### Task 2: Add dashboard, Master Brand, export, and database-status APIs

**Files:**
- Modify: `app.py`
- Modify: `engines/sql_engine.py` only if route-specific adapters are needed
- Test: `tests/test_dashboard_endpoints.py`
- Test: `tests/test_master_brand_endpoints.py`

**Interfaces:**
- Add `GET /api/dashboard/metrics` returning the complete live metric payload.
- Extend `GET /api/db-status` with SQLite/MySQL status, active database, database name, and refresh timestamp while preserving current keys.
- Add `GET /api/master-brands/search` with validated query parameters `id`, `brand`, `upc`, `product`, and `limit`.
- Add `GET /api/master-brands/export` using the existing report-token CSV export flow.
- Add `GET /api/dashboard/export/<dataset>` support for allowed analytical datasets without weakening its allow-list.

- [ ] **Step 1: Write failing Flask client tests** for metric response shape, Master Brand search parameters, not-found response, export token, and no-secret status payload.
- [ ] **Step 2: Run the focused endpoint tests and confirm failure.**
- [ ] **Step 3: Implement the routes** with strict limits, safe numeric parsing, clear 400 errors, and existing error-response conventions.
- [ ] **Step 4: Verify current `/api/chat`, `/api/compare`, `/api/upc-audit`, and existing dashboard routes remain compatible.**
- [ ] **Step 5: Run `pytest tests/test_dashboard_endpoints.py tests/test_master_brand_endpoints.py tests/test_app_endpoints.py -v` and commit.**

### Task 3: Make chatbot routing and answers useful for work and general chat

**Files:**
- Modify: `engines/rag_orchestrator.py`
- Modify: `engines/sql_engine.py` if Master Brand ID/brand+UPC routing needs a dedicated adapter
- Test: `tests/test_rag_audit.py`
- Test: `tests/test_rag_id_lookup.py`
- Test: `tests/test_chat_routing.py`

**Interfaces:**
- Preserve `RAGOrchestrator.route_and_execute(user_query, session_id='default-session')` response shape.
- Route Master Brand ID, brand+UPC, and brand-only questions to the exact Master Brand search before fuzzy/general catalog search.
- Keep normal greetings and general questions away from SQL/vector catalog search.

- [ ] **Step 1: Write failing routing tests** for exact Master Brand ID, brand+UPC, brand-only Master Brand search, English general questions, Devanagari Hindi, Roman Hinglish, greetings, and unsupported requests.
- [ ] **Step 2: Run focused routing tests and confirm failure or current incorrect fallback behavior.**
- [ ] **Step 3: Implement explicit intent precedence**: Master Brand exact lookup, UPC/product/database operations, uploaded-document context, then general conversation; never run catalog SQL for a plain greeting/general question.
- [ ] **Step 4: Improve response prompts and deterministic fallbacks** so the answer is direct, language-matched, and explains what was found, including all available Master Brand fields and multiple matches.
- [ ] **Step 5: Preserve conversation context and existing comparison/audit/report behavior.**
- [ ] **Step 6: Run all RAG and conversation tests plus the chat endpoint tests; commit.**

### Task 4: Enhance the UI/UX with live cards, donut charts, category details, and Master Brand search

**Files:**
- Modify: `templates/index.html`
- Create or modify: `static/app.css` only if separating the current inline styles is low-risk
- Test: `tests/test_frontend_contract.py`

**Interfaces:**
- Dashboard client consumes `/api/dashboard/metrics` and renders live values only.
- Master Brand panel consumes `/api/master-brands/search` and renders dynamic columns safely escaped.
- Existing chat/comparison/upload controls continue using their current functions and endpoints.

- [ ] **Step 1: Add frontend contract tests** for live KPI element IDs, UPC donut/chart hooks, category cards, Master Brand section/search controls, database status fields, and no hardcoded record totals in dashboard copy.
- [ ] **Step 2: Implement a restrained light dashboard layout** with clear navigation, compact KPI cards, a UPC quality donut, category UPC cards/bar chart, Master Brand overview card, and database status card.
- [ ] **Step 3: Add category click/filter behavior** that opens bounded records/details and links to the existing export endpoint.
- [ ] **Step 4: Add the Master Brand search experience** for ID, brand, UPC, product, and combined filters, with loading, empty, error, multi-match, and dynamic-detail states.
- [ ] **Step 5: Improve chat presentation** with readable response typography, proper Markdown/newline rendering, language-preserving responses, loading state, and clearer work-result tables/download actions.
- [ ] **Step 6: Run frontend contract tests and inspect the rendered page for responsive layout, escaped values, and accessible labels; commit.**

### Task 5: Full verification and regression cleanup

**Files:**
- Modify: any files required by verified regressions only
- Test: existing `tests/` suite

- [ ] **Step 1: Run `pytest -q` for the full suite.**
- [ ] **Step 2: Fix only evidence-backed regressions**, especially MySQL placeholder compatibility, static dashboard text, encoding/newline rendering, and route response compatibility.
- [ ] **Step 3: Run focused tests again, then the full suite again.**
- [ ] **Step 4: Run `problems` on modified files and confirm no diagnostics remain.**
- [ ] **Step 5: Manually verify dashboard metrics, donut/category interactions, Master Brand ID/brand+UPC search, general chat, work queries, CSV export, and MySQL/SQLite status.**
- [ ] **Step 6: Commit the completed enhancement with a focused message.**

