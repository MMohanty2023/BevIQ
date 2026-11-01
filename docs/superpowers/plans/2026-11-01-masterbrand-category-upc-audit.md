# MasterBrand–Category Product UPC Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a UPC-first, review-only CSV/Excel-compatible audit showing every category UPC's MasterBrand status and full product details, with conservative alternate UPC suggestions only when product identity is confirmed.

**Architecture:** Keep the existing Flask/API and chat flow. Replace the combined fuzzy score in `UPCMatchEngine` with field-aware matching, then expose the same records through the existing `/api/upc-audit`, chat response, and CSV export path without writing to source tables.

**Tech Stack:** Python 3.14, Flask, SQLite-backed `db_manager`, rapidfuzz, CSV export, existing HTML UI.

**Spec:** `docs/superpowers/specs/2026-11-01-masterbrand-category-upc-audit-design.md`

## Global Constraints

- No automatic UPC insertion, replacement, or deletion.
- No inference based on brand alone.
- UPC is the primary identity; brand alone is never sufficient because each brand can have multiple products.
- Every observed UPC, duplicate UPC, and alternate UPC remains visible in the report.
- Preserve leading-zero UPCs as strings.
- Ambiguous or low-confidence matches remain review-only/unmatched.
- Output must include category/source details, MasterBrand details, confidence, suggested UPC, and reason.

## Review Focus

- Exact UPC in MasterBrand → mark as verified and retain the full UPC/product record.
- Category UPC absent from MasterBrand → report the category UPC and its complete source product details.
- Missing category UPC with a strong MasterBrand product match → emit a suggested UPC and full details.
- Existing category UPC absent from MasterBrand but same product found → emit the MasterBrand UPC as a review suggestion.
- Brand-only similarity → reject; no alternate UPC.
- Size/pack conflict → reject or mark ambiguous, never suggest automatically.
- Duplicate/alternate UPCs in MasterBrand → preserve both values and identify the selected/supplemental UPC clearly.

### Task 1: Field-aware conservative matching

**Files:**
- Modify: `engines/upc_match_engine.py`
- Test: `tests/test_upc_match_engine.py`

**Interfaces:**
- Produces `UPCMatchEngine.audit(category: str | None, limit: int) -> list[dict]` records containing `category`, source fields, MasterBrand fields, `suggested_upc`, `alternate_upc`, `confidence`, and `remarks`.

- [ ] **Step 1: Write failing tests** for a strong brand/product/size match, missing category UPC, brand-only rejection, and size conflict rejection. Assert that UPC strings retain leading zeros and no database write occurs.
- [ ] **Step 2: Run `c:/python314/python.exe -m pytest tests/test_upc_match_engine.py -q` and verify the new tests fail for the current combined-score behavior.
- [ ] **Step 3: Implement field-aware normalization and scoring in `engines/upc_match_engine.py`.** Narrow candidates by normalized brand; compare product/flavour and size/pack separately; require product identity plus compatible size/pack before emitting a suggestion; keep the current read-only SQL behavior.
- [ ] **Step 4:** Run the focused test file and verify all tests pass.
- [ ] **Step 5:** Run `c:/python314/python.exe -m py_compile engines/upc_match_engine.py`.

### Task 2: Formal CSV/Excel-compatible audit export

**Files:**
- Modify: `app.py`
- Modify: `engines/rag_orchestrator.py`
- Test: `tests/test_app_endpoints.py`

**Interfaces:**
- `/api/upc-audit` remains read-only and returns JSON records.
- The audit response exposes a downloadable CSV token using the existing export mechanism; the CSV has stable columns suitable for opening in Excel.

- [ ] **Step 1: Write failing endpoint tests** asserting `/api/upc-audit` returns `record_count`, read-only messaging, stable audit columns, and a valid CSV download token when records exist.
- [ ] **Step 2: Run the focused endpoint tests and verify failure where export metadata is missing.
- [ ] **Step 3: Add stable CSV columns and export-token generation without updating any source table. Update chat formatting to explain that suggested UPCs require manual review.
- [ ] **Step 4: Run the focused endpoint tests and verify they pass.

### Task 3: UI audit access and user-facing explanation

**Files:**
- Modify: `templates/index.html`
- Test: `tests/test_app_endpoints.py`

- [ ] **Step 1: Add/adjust a UI regression assertion for the Product Match → Alternate UPC action and its review-only wording.
- [ ] **Step 2: Run the test and verify the assertion fails if the expected wording/action is absent.
- [ ] **Step 3: Ensure the quick action renders the audit records and CSV link with columns for source UPC, MasterBrand UPC, product details, confidence, and review status.
- [ ] **Step 4: Run the endpoint/UI checks and verify they pass.

### Task 4: Full verification and data audit

**Files:**
- Modify: `README.md` if the final export behavior needs documentation.

- [ ] **Step 1: Run the full existing endpoint suite: `c:/python314/python.exe tests/test_app_endpoints.py`.
- [ ] **Step 2: Run focused matching and endpoint tests together.
- [ ] **Step 3: Call `/api/upc-audit` separately for Beer, Wine, Spirits, and RTD with a bounded limit; inspect sample rows for product/size agreement and confirm no source-table row counts change.
- [ ] **Step 4: Verify the exported CSV opens as valid UTF-8 CSV and retains leading-zero UPC values.
- [ ] **Step 5: Report counts by category, sample confidence, and any ambiguous cases without claiming automatic updates.
