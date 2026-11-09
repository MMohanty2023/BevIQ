# Supplier Overview Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the complete supplier experience from the general Dashboard into a dedicated Supplier Overview tab.

**Architecture:** Keep the existing single-page tab architecture and existing AllMasterBrands-backed supplier API. Move the supplier markup into a new `tab-supplier-overview`, add a navigation button, and update the existing tab loader so supplier data loads when the new tab opens.

**Tech Stack:** Flask template, vanilla JavaScript, CSS, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-supplier-overview-tab-design.md`

## Global Constraints

- Supplier data continues to come only from the existing AllMasterBrands-backed endpoint.
- Remove the supplier section from `tab-dashboard`; do not duplicate it.
- Preserve supplier search, filters, counts, categories, expandable cards, and brand details.
- Keep the existing Dashboard metrics and API behavior unchanged.

## Review Focus

- Supplier tab is reachable from the top navigation — covered in Task 1.
- Dashboard no longer contains the supplier directory markup — covered in Task 1.
- Supplier data loads when the new tab opens and does not require opening Dashboard first — covered in Task 2.
- Existing supplier search/detail hooks remain intact after the move — covered in Task 2.

### Task 1: Move the supplier section and add navigation

**Files:**
- Modify: `templates/index.html` navigation and tab markup
- Test: `tests/test_frontend_contract.py`

**Interfaces:**
- Produces: `tab-supplier-overview`, a `Supplier Overview` navigation button, and the existing supplier element IDs under the new tab.

- [ ] **Step 1: Write failing frontend contract assertions**

  Assert the template contains the Supplier Overview navigation/tab hooks and does not place `supplier-directory-card` inside the Dashboard tab section.

- [ ] **Step 2: Run the focused test and verify it fails**

  Run: `PYTHONPATH=. .venv/Scripts/pytest.exe tests/test_frontend_contract.py -k supplier_overview_tab -v`

  Expected: FAIL because the supplier section is currently inside `tab-dashboard` and no Supplier Overview tab exists.

- [ ] **Step 3: Move the existing supplier markup**

  Add the navigation button and `tab-supplier-overview` panel, move the complete existing supplier card/filter/detail markup into that panel, and remove it from Dashboard without changing its element IDs or API references.

- [ ] **Step 4: Run focused frontend tests**

  Run: `PYTHONPATH=. .venv/Scripts/pytest.exe tests/test_frontend_contract.py -k supplier -v`

  Expected: PASS.

### Task 2: Load supplier data from the dedicated tab

**Files:**
- Modify: `templates/index.html` tab-switch/load logic
- Test: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: existing `loadSupplierDirectory()` and `/api/dashboard/suppliers`.
- Produces: supplier data loading when `switchTab('supplier-overview', ...)` is called, while preserving the current Dashboard load behavior for other metrics.

- [ ] **Step 1: Write failing contract assertion**

  Assert the tab-switch logic explicitly recognizes `supplier-overview` and calls `loadSupplierDirectory()` for it.

- [ ] **Step 2: Run the focused test and verify it fails**

  Run: `PYTHONPATH=. .venv/Scripts/pytest.exe tests/test_frontend_contract.py -k supplier_overview_load -v`

  Expected: FAIL because current loading is tied only to `loadDashboard()`.

- [ ] **Step 3: Add the dedicated-tab load hook**

  Update the existing tab switch logic to load suppliers on the new tab, with the existing cache/guard behavior so repeated tab clicks do not create unnecessary requests.

- [ ] **Step 4: Run focused frontend and supplier backend tests**

  Run: `PYTHONPATH=. .venv/Scripts/pytest.exe tests/test_frontend_contract.py -k supplier -v` and `PYTHONPATH=. .venv/Scripts/pytest.exe tests/test_dashboard_endpoints.py -k supplier -v`

  Expected: PASS.

### Task 3: Full verification

**Files:**
- No planned source changes.

- [ ] **Step 1: Run the relevant regression suite**

  Run: `PYTHONPATH=. .venv/Scripts/pytest.exe tests/test_frontend_contract.py tests/test_dashboard_endpoints.py tests/test_dashboard_metrics.py -q`

  Expected: Supplier tests pass; report unrelated pre-existing failures separately.

- [ ] **Step 2: Check the final diff**

  Run: `git diff --check` and inspect that Dashboard no longer contains `supplier-directory-card` while the new tab does.
