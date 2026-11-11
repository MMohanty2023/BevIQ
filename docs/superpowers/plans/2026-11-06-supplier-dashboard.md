# Supplier Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add dynamic supplier and brand-level summaries to the existing dashboard Supplier Directory.

**Architecture:** Extend `SQLEngine.get_supplier_directory()` so the live Master Brand table produces one normalized supplier summary with nested brand record counts. Update the existing dashboard card to display those summaries and search across supplier and brand names; keep the existing bounded product preview and Master Brands tab intact.

**Tech Stack:** Flask, SQLite/MySQL query abstraction, vanilla JavaScript, inline dashboard CSS, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-supplier-dashboard-design.md`

## Global Constraints

- Use the existing Master Brand table as the only data source.
- Do not hardcode supplier, brand, or record totals.
- Do not modify Master Brands search behavior.
- Treat null-like supplier values as `NA` and exclude null-like brand values from unique brand counts.

## Review Focus

- Case/whitespace variants of the same supplier or brand must aggregate together; cover in the SQL engine test.
- Suppliers with multiple brands must report each brand's exact record count; cover in the SQL engine test.
- Search must match brand names as well as supplier names; cover in the frontend contract test.
- Empty search must restore all suppliers; cover in the frontend contract test.
- Missing suppliers/brands must not create misleading brand entries; cover in the SQL engine test.

---

### Task 1: Add dynamic brand detail aggregation

**Files:**
- Modify: `engines/sql_engine.py:486-540`
- Test: `tests/test_dashboard_endpoints.py`

**Interfaces:**
- Produces `brand_details: [{"brand_name": str, "record_count": int}]` for every supplier returned by `get_supplier_directory()`.

- [ ] **Step 1: Write the failing test**

Add a focused test using a fake database query result or a small SQLite fixture that asserts supplier summaries normalize supplier/brand case and whitespace, exclude null-like brands, and return exact nested brand record counts.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pytest tests/test_dashboard_endpoints.py -k brand_detail -v`

Expected: FAIL because `brand_details` is not present or counts are not returned.

- [ ] **Step 3: Implement the minimal aggregation**

In `get_supplier_directory()`, query grouped brand counts per normalized supplier using the existing `supplier_key` and `brand_key`, preserve a display label with the first/minimum source spelling, and add the sorted `brand_details` list to each supplier payload. Keep current supplier-level totals and bounded records unchanged.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `pytest tests/test_dashboard_endpoints.py -k brand_detail -v`

Expected: PASS.

### Task 2: Render and search supplier/brand details

**Files:**
- Modify: `templates/index.html:896-914, 1308-1315, 1771-1816`
- Test: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes `supplier.brand_details` from `/api/dashboard/suppliers`.
- `filterSupplierCards(query)` filters on supplier name or any nested brand name.

- [ ] **Step 1: Write the failing frontend contract assertions**

Assert the template contains brand-detail rendering, a brand-aware search placeholder/label, and a filter expression that checks nested brand names.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pytest tests/test_frontend_contract.py -k supplier -v`

Expected: FAIL because the current template only renders `brand_names` and filters supplier names.

- [ ] **Step 3: Implement the minimal UI change**

Render each supplier’s brand name and per-brand record count inside the expandable body, retain the supplier-level records/brands/UPCs stats, and update search to match supplier or brand text. Add responsive styling for the brand count rows without changing the existing Master Brands markup.

- [ ] **Step 4: Run the focused frontend tests**

Run: `pytest tests/test_frontend_contract.py -k supplier -v`

Expected: PASS.

### Task 3: Run regression verification

**Files:**
- Test: `tests/test_dashboard_endpoints.py`, `tests/test_frontend_contract.py`

- [ ] **Step 1: Run the complete test suite**

Run: `pytest`

Expected: exit code 0 with no failures.

- [ ] **Step 2: Review the final diff**

Run: `git diff --check` and `git diff --stat`

Expected: no whitespace errors; only the supplier dashboard implementation, tests, and planning documents are changed.
