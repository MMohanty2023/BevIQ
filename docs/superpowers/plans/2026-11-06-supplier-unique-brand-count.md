# Supplier Unique Brand Count Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show every unique supplier from `AllMasterBrands` with its unique brand count, total MasterBrand record count, and actual categories.

**Architecture:** Reuse the existing `/api/dashboard/suppliers` endpoint and Supplier Directory UI. Keep all supplier and supplier-brand aggregation in `SQLEngine.get_supplier_directory()` against the `all_brands` table, then render the returned totals and searchable supplier rows without adding another data source.

**Tech Stack:** Python, SQLite/MySQL query abstraction, Flask, vanilla JavaScript, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-supplier-unique-brand-count-design.md`

## Global Constraints

- Source table: configured `all_brands` table loaded from `$ALLBrand_202610291524.csv` (`AllMasterBrands`).
- Do not use `ai_master` or `trained_brands` for supplier lists or supplier counts.
- Normalize supplier names by trimming and case-folding; display one readable name per normalized supplier.
- Count unique non-empty brand names per normalized supplier, case-insensitively.
- Aggregate non-empty `ProductCategory` values per supplier without duplicates.
- Treat blank/null-like suppliers as `NA`.
- No dummy supplier or brand data and no data mutation.
- Keep the existing supplier search and update the visible count after filtering.

## Review Focus

- Supplier names differing only by case/whitespace aggregate into one supplier — covered in Task 1.
- Brand names differing only by case/whitespace count once for a supplier — covered in Task 1.
- Blank/null-like brands do not inflate brand counts — covered in Task 1.
- Supplier MasterBrand rows and categories come from actual `all_brands` values — covered in Task 1.
- Search can find a supplier and updates the visible supplier total — covered in Task 2.
- Existing endpoint remains available and returns dynamic supplier totals — covered in Task 2.

### Task 1: Make supplier and unique-brand aggregation authoritative

**Files:**
- Modify: `engines/sql_engine.py` in `SQLEngine.get_supplier_directory`
- Test: `tests/test_dashboard_metrics.py`

**Interfaces:**
- Consumes: `self.db.query()` and `CSV_FILES["all_brands"]["table"]` only.
- Produces: `{"total_suppliers": int, "suppliers": [{"supplier": str, "supplier_code": str|None, "brand_count": int, "record_count": int, ...}]}` with case-insensitive deduplicated brand counts.

- [ ] **Step 1: Write failing tests**

  Add a focused fake-database test with case/whitespace variants of one supplier and one brand, a second supplier, blank/null-like brands, and multiple `ProductCategory` values. Assert one normalized supplier entry, the correct unique brand count, exact MasterBrand record count, and deduplicated categories.

- [ ] **Step 2: Run the focused test and verify it fails for the intended reason**

  Run: `pytest tests/test_dashboard_metrics.py -k supplier_directory -v`

  Expected: FAIL if the current query/result does not provide the required deduplicated supplier/brand counts.

- [ ] **Step 3: Implement the minimal SQL/data response change**

  Use the existing `all_brands` table and normalized supplier/brand expressions. Ensure supplier grouping is independent of display-case differences, brand counts exclude null-like brand values, categories come from `ProductCategory`, and each supplier returns its unique brand count and total MasterBrand record count.

- [ ] **Step 4: Run the focused test and verify it passes**

  Run: `pytest tests/test_dashboard_metrics.py -k supplier_directory -v`

  Expected: PASS with no query against `ai_master` or `trained_brands` in this path.

### Task 2: Present the supplier total and per-supplier brand count clearly

**Files:**
- Modify: `templates/index.html` in the Supplier Directory markup and renderer
- Test: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: `total_suppliers`, `suppliers[].supplier`, `suppliers[].supplier_code`, `suppliers[].brand_count`, and `suppliers[].record_count` from `/api/dashboard/suppliers`.
- Produces: a simple supplier overview with total supplier count, supplier search, and visible per-supplier unique brand count.

- [ ] **Step 1: Write failing frontend contract assertions**

  Assert the template contains labels/hooks for total suppliers, supplier name, unique brands, `brand_count`, search, and visible filtered supplier total.

- [ ] **Step 2: Run the focused frontend test and verify the intended failure**

  Run: `pytest tests/test_frontend_contract.py -k supplier -v`

  Expected: FAIL if the current UI does not present the brand count in the requested simple overview format.

- [ ] **Step 3: Implement the minimal rendering change**

  Keep the existing Supplier Directory endpoint and search. Render supplier name, code, unique brand count, total MasterBrand records, and categories in each supplier row/card; keep the total supplier counter and update the visible count after filtering. Avoid adding unrelated brand-detail/image UI.

- [ ] **Step 4: Run focused frontend and endpoint tests**

  Run: `pytest tests/test_frontend_contract.py -k supplier -v` and `pytest tests/test_dashboard_endpoints.py -k supplier -v`

  Expected: PASS.

### Task 3: Full verification

**Files:**
- No planned source changes.

- [ ] **Step 1: Run the complete test suite**

  Run: `pytest -q`

  Expected: exit code 0; report any unrelated pre-existing failures explicitly.

- [ ] **Step 2: Check the final diff**

  Run: `git diff --check` and inspect the diff. Preserve unrelated existing worktree changes.
