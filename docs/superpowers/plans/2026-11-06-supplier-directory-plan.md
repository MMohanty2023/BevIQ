# Supplier Directory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live Master Brand supplier directory with one expandable div/card per supplier, including supplier totals, brand counts, brand names, UPC counts, and related product details.

**Architecture:** Add a read-only aggregation method to `SQLEngine`, expose it through `/api/dashboard/suppliers`, then render the result in the existing dashboard template with client-side search and expand/collapse cards. Missing supplier values are normalized into the `NA` bucket.

**Tech Stack:** Flask, SQLite/MySQL abstraction already used by the project, SQL aggregation, vanilla JavaScript, existing dashboard CSS, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-supplier-directory-design.md`

## Global Constraints

- Use the active database's Master Brand table (`CSV_FILES['ai_master']['table']`).
- Keep the endpoint read-only.
- Group blank/null supplier values into `NA`.
- Preserve existing dashboard and Master Brand search behavior.
- Follow test-first development: each production behavior gets a failing test before implementation.

## Review Focus

- Blank, null, whitespace, and literal placeholder supplier values must not create separate supplier cards; test in the aggregation task.
- Supplier names and brand names with mixed casing must be grouped case-insensitively while displaying a stable readable value; test in the aggregation task.
- Suppliers with no usable brand name or UPC must still appear with zero counts; test in the aggregation task.
- Large brand/detail lists must be bounded by the endpoint response contract so the dashboard remains usable; test in the API task.
- Search must match supplier names and collapse non-matching cards without corrupting rendered text; test in the frontend contract task.

### Task 1: Aggregate supplier summaries from Master Brand data

**Files:**
- Modify: `engines/sql_engine.py` near `get_dashboard_metrics`
- Test: `tests/test_dashboard_metrics.py`

**Interfaces:**
- Produces: `sql_engine.get_supplier_directory(limit=500)` returning `{total_suppliers: int, suppliers: list[dict]}`.
- Each supplier dict contains `supplier`, `record_count`, `brand_count`, `brand_names`, `upc_count`, and `records`.

- [ ] **Step 1: Write the failing tests**

Add tests covering a fake active Master Brand table with normal suppliers, mixed-case duplicate supplier/brand values, blank/whitespace/null supplier values grouped as `NA`, and missing brand/UPC values producing zero-safe counts. Assert the exact supplier summary fields and deterministic ordering.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dashboard_metrics.py -k supplier_directory -v`

Expected: FAIL because `get_supplier_directory` does not exist.

- [ ] **Step 3: Implement `SQLEngine.get_supplier_directory(limit: int = 500) -> dict`**

Use the existing table-column lookup/database abstraction. Normalize supplier values with SQL expressions into `NA`, group supplier and brand values case-insensitively, count records and usable UPCs, collect sorted unique brand names, and fetch a bounded list of related Master Brand detail rows per supplier. Return suppliers sorted with `NA` last and `total_suppliers` equal to the number of supplier buckets.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dashboard_metrics.py -k supplier_directory -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_dashboard_metrics.py engines/sql_engine.py
git commit -m "feat: aggregate master brand suppliers"
```

### Task 2: Expose the supplier directory API

**Files:**
- Modify: `app.py` near the dashboard routes
- Test: `tests/test_dashboard_endpoints.py`

**Interfaces:**
- Consumes: `sql_engine.get_supplier_directory(limit=500)`.
- Produces: `GET /api/dashboard/suppliers` JSON with `backend`, `total_suppliers`, and `suppliers`.

- [ ] **Step 1: Write the failing endpoint test**

Add a Flask test-client test that calls `/api/dashboard/suppliers`, verifies HTTP 200, and asserts the response has the required top-level fields plus supplier card fields. Add a limit validation test for invalid and bounded limits if the endpoint accepts a query limit.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dashboard_endpoints.py -k suppliers -v`

Expected: FAIL with 404 because the route does not exist.

- [ ] **Step 3: Implement `api_dashboard_suppliers()`**

Add a read-only Flask route that validates an optional limit, calls the SQL engine, includes the active backend name, and returns a JSON error with status 500 on database failure consistent with existing dashboard routes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dashboard_endpoints.py -k suppliers -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_dashboard_endpoints.py app.py
git commit -m "feat: add supplier directory endpoint"
```

### Task 3: Render searchable expandable supplier cards

**Files:**
- Modify: `templates/index.html` in dashboard styles, dashboard markup, and dashboard JavaScript
- Test: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: `/api/dashboard/suppliers` response from Task 2.
- Produces: dashboard hooks `dashboard-supplier-total`, `dashboard-supplier-search`, and `dashboard-supplier-directory`.

- [ ] **Step 1: Write the failing frontend contract test**

Assert the template contains the supplier directory container, total-supplier element, search input, and JavaScript references to `/api/dashboard/suppliers`, `NA`, brand count, brand names, and expand/collapse behavior.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_frontend_contract.py -k supplier -v`

Expected: FAIL because the supplier directory hooks are absent.

- [ ] **Step 3: Implement the supplier directory UI**

Add a dedicated dashboard card with total supplier count, search field, loading/empty/error states, and a responsive card grid. Implement HTML escaping, supplier search filtering, accessible expand/collapse buttons, summary metrics, brand-name rendering, and a bounded related-record detail list. Use the existing dashboard data-loading flow so the directory loads when the dashboard opens and refreshes with dashboard metrics.

- [ ] **Step 4: Run frontend contract tests**

Run: `pytest tests/test_frontend_contract.py -k supplier -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_frontend_contract.py templates/index.html
git commit -m "feat: render supplier directory cards"
```

### Task 4: Run focused and full verification

**Files:**
- Test: existing test suite

- [ ] **Step 1: Run focused supplier tests**

Run: `pytest tests/test_dashboard_metrics.py -k supplier_directory -v; pytest tests/test_dashboard_endpoints.py -k suppliers -v; pytest tests/test_frontend_contract.py -k supplier -v`

Expected: all focused tests pass.

- [ ] **Step 2: Run the complete suite**

Run: `pytest -q`

Expected: all existing and new tests pass with no regressions.

- [ ] **Step 3: Inspect the final diff**

Run: `git diff --check; git status --short`

Expected: no whitespace errors; only the intended supplier directory files are changed.
