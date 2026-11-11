# Untrained Brand Process Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the untrained-brand audit follow the approved staged process and present the current total untrained-brand count clearly.

**Architecture:** Keep the existing read-only `/api/compare` endpoint and CSV export. Refactor `ComparisonEngine.find_untrained_brands()` into explicit stages: trained UPC set, ordered reference UPC collection, missing UPC calculation, and unique brand grouping; return concise stage summaries plus final records.

**Tech Stack:** Python, pandas-compatible SQLite query interface, Flask, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-untrained-brand-process-design.md`

## Global Constraints

- `TrainedBrandsData.csv` is the correct/reference dataset.
- Reference order is All Master Brand, Beer, Wine, Spirits, RTD.
- The audit is read-only and must not modify source files or database records.
- Missing UPCs are the global reference UPC union minus trained UPCs.
- Final brand records are grouped by normalized brand text; empty brands are excluded from the unique-brand list.
- Search and limit apply to final brand records; CSV export uses the untruncated final records.
- User-facing output must show the total unique untrained-brand count first and avoid unnecessary technical detail.

## Review Focus

- Duplicate UPC across multiple sheets: one missing UPC and one final UPC entry, with source rows retained for grouping — covered in Task 1.
- Duplicate brand spellings/casing: one normalized brand record with a readable display name — covered in Task 1.
- Empty brand name: missing UPC remains counted but no blank brand record is emitted — covered in Task 1.
- Search and limit: summary count remains the total, while returned records are filtered/limited and export remains complete — covered in Task 2.
- Existing endpoint contract: `/api/compare` stays read-only and still returns a download token — covered in Task 2.

### Task 1: Implement the staged comparison pipeline

**Files:**
- Modify: `engines/comparison_engine.py` in `ComparisonEngine.find_untrained_brands`
- Test: `tests/test_untrained_brands.py`

**Interfaces:**
- Consumes: `self.db.query()`, `CSV_FILES['trained_brands']`, `CSV_FILES['ai_master']`, and the four categorization table configurations.
- Produces: `find_untrained_brands(limit=None, search=None)` with `process`, `summary`, `records`, and `export_records`; summary includes `trained_upcs`, `reference_upcs`, `missing_upcs`, `unique_untrained_brands`, and per-sheet UPC counts.

- [ ] **Step 1: Write failing unit tests**

  Add a fake database fixture that returns overlapping UPCs and repeated brand spellings across the five configured sheets. Assert the process order is exactly `Trained Brand DataSheet`, `All Master Brand DataSheet`, `Beer`, `Wine`, `Spirits`, `RTD`, `Missing UPCs`, `Unique Brand Names`, `Untrained Brand Names`; assert totals and grouped UPC/supplier lists.

- [ ] **Step 2: Run the focused tests and verify the expected failure**

  Run: `pytest tests/test_untrained_brands.py -q`

  Expected: FAIL because the current method uses undefined summary variables and does not return the approved stage names/counts.

- [ ] **Step 3: Implement the minimum staged pipeline**

  In `engines/comparison_engine.py`, collect trained UPCs first, then iterate reference sheets in the exact configured order. Build a global missing UPC set, retain source rows for missing UPCs, group non-empty brands with a stable normalized key, calculate total counts before search/limit, and return a concise process list plus a `summary` whose first useful metric is `total_untrained_brands`.

- [ ] **Step 4: Run the focused tests and verify they pass**

  Run: `pytest tests/test_untrained_brands.py -q`

  Expected: all focused tests PASS with no undefined-variable errors.

- [ ] **Step 5: Commit the task**

  ```bash
  git add engines/comparison_engine.py tests/test_untrained_brands.py
  git commit -m "fix: follow staged untrained brand audit process"
  ```

### Task 2: Make the API response easy to understand and preserve export behavior

**Files:**
- Modify: `app.py` only if the existing response needs a user-facing summary field
- Modify: `tests/test_untrained_brands.py`

**Interfaces:**
- Consumes: `comparison_engine.find_untrained_brands()` from Task 1.
- Produces: `/api/compare` response with `summary.total_untrained_brands`, stage summaries, final records, and `download_token`.

- [ ] **Step 1: Write failing endpoint assertions**

  Assert that posting `{"type": "untrained_brands"}` returns HTTP 200, includes `summary.total_untrained_brands`, includes the short process, returns final brand records, and still returns a CSV download token.

- [ ] **Step 2: Run the focused endpoint test and verify the expected failure**

  Run: `pytest tests/test_untrained_brands.py::test_untrained_comparison_endpoint_returns_read_only_report -q`

  Expected: FAIL if the response does not expose the new total-count field.

- [ ] **Step 3: Implement only the necessary response wiring**

  Preserve the existing generic export path. If required, add a concise `headline`/`message` field derived from `total_untrained_brands`; do not add a second data-processing path in `app.py`.

- [ ] **Step 4: Run focused tests and verify export behavior**

  Run: `pytest tests/test_untrained_brands.py -q`

  Expected: all tests PASS, including read-only response and download token assertions.

### Task 3: Full verification and regression check

**Files:**
- No planned source changes; inspect the diff and existing user modifications before running tests.

- [ ] **Step 1: Run the complete test suite**

  Run: `pytest -q`

  Expected: exit code 0; report any pre-existing failures separately rather than hiding them.

- [ ] **Step 2: Run static/problem validation**

  Inspect `git diff --check` and run the focused endpoint tests again if the full suite reveals unrelated failures.

- [ ] **Step 3: Review the final diff**

  Confirm only the approved design/plan, comparison logic, and focused tests are part of this task; preserve unrelated existing worktree changes.
