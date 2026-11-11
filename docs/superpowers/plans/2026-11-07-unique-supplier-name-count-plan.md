# Unique Supplier Name Count Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Count the same trained-dataset supplier once by normalized supplier name, even when it has multiple supplier codes.

**Architecture:** Keep the existing summary API and frontend contract unchanged. Replace only the `total_suppliers` SQL distinct key in `SQLEngine.get_trained_dataset_summary`; supplier-level brand and record metrics remain unchanged.

**Tech Stack:** Python, pytest, SQL generated for SQLite/MySQL backends.

**Spec:** `docs/superpowers/specs/2026-11-07-unique-supplier-name-count-design.md`

## Global Constraints

- Count supplier identity by trimmed, case-insensitive `SupplierName`.
- Preserve all other trained summary metrics.
- Exclude blank and placeholder supplier names from the total.
- Add a regression test before changing production code.

## Review Focus

- Same supplier name with different supplier codes must count once; test in `tests/test_trained_dataset.py`.
- Case and whitespace variants of one supplier name must count once; test in `tests/test_trained_dataset.py`.
- Blank/placeholder supplier names must not inflate the count; test in `tests/test_trained_dataset.py`.

### Task 1: Update trained supplier identity counting

**Files:**
- Modify: `tests/test_trained_dataset.py`
- Modify: `engines/sql_engine.py` in `SQLEngine.get_trained_dataset_summary`

**Interfaces:**
- Consumes: existing `get_trained_dataset_summary(filters=None)` API.
- Produces: unchanged summary response with name-based `total_suppliers`.

- [ ] **Step 1: Write the failing test**

  Add a focused fake database test whose summary query result demonstrates duplicate supplier codes for one normalized supplier name and assert `total_suppliers == 1`; also assert the SQL uses `SupplierName` for the supplier distinct expression.

- [ ] **Step 2: Run the focused test to verify it fails**

  Run: `pytest tests/test_trained_dataset.py -k supplier -v`

  Expected: FAIL because the current SQL uses `SupplierCode`.

- [ ] **Step 3: Implement the minimal SQL change**

  In `engines/sql_engine.py`, define a normalized supplier-name expression using `TRIM` and `LOWER`, map blank/placeholder values to `NULL`, and use `COUNT(DISTINCT <expression>) AS total_suppliers` in the existing summary query. Keep the existing backend-compatible SQL style.

- [ ] **Step 4: Run the focused tests to verify they pass**

  Run: `pytest tests/test_trained_dataset.py -k supplier -v`

  Expected: PASS.

- [ ] **Step 5: Run the complete test suite**

  Run: `pytest`

  Expected: all tests pass.

- [ ] **Step 6: Review the diff**

  Run: `git diff -- docs/superpowers/specs/2026-11-07-unique-supplier-name-count-design.md docs/superpowers/plans/2026-11-07-unique-supplier-name-count-plan.md engines/sql_engine.py tests/test_trained_dataset.py`

  Confirm only the intended metric and regression coverage changed.
