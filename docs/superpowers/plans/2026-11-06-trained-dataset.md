# Trained Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a server-backed Trained Dataset dashboard and extend the existing AI Assistant to answer trained-brand questions.

**Architecture:** Ingest `TrainedBrandsData.csv` into an indexed `trained_brands` table through the existing loader. Add Flask/SQL endpoints for summary, analytics, filtered pagination, detail, and CSV export; render the dashboard with the existing tab/theme and native SVG/CSS charts. Add trained intent routing to the existing `RAGOrchestrator`.

**Tech Stack:** Flask, SQLite/MySQL query abstraction, pandas loader, vanilla JavaScript, SVG/CSS, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-trained-dataset-design.md`

## Global Constraints

- Use actual `TrainedBrandsData.csv` records only.
- Preserve the existing AI Assistant interface, session history, model configuration, and all existing tabs.
- Use server-side filtering/pagination; do not ship all trained rows or full-size images on initial load.
- Category artwork is separate UI artwork; source image URLs remain record images.
- Missing values must display as unavailable/missing, never guessed.

## Review Focus

- Missing SKU, model, status, and image URL values remain filterable and visibly marked.
- Pipe-delimited image URL values produce a deduplicated lazy-loaded gallery.
- ID, class ID, supplier/brand code, and model ID searches match exact records.
- Category names and source status values are preserved exactly in filters and details.
- Existing AI and Master Brands queries continue to route as before.

---

### Task 1: Ingest and query trained records

**Files:**
- Modify: `config.py`, `data_ingestion/loader.py`, `run.py`, `engines/sql_engine.py`
- Test: `tests/test_trained_dataset.py`

- [ ] Add a failing test for normalized trained-record search, missing-data summary, and image URL parsing.
- [ ] Run it and verify failure because the trained table/API does not exist.
- [ ] Add the `trained_brands` config entry, create the indexed table through the existing loader, and implement SQL methods for summary, analytics, filtered pagination, detail, and export data.
- [ ] Run focused tests and verify pass.

### Task 2: Add Flask endpoints

**Files:**
- Modify: `app.py`
- Test: `tests/test_trained_dataset.py`

- [ ] Add failing endpoint tests for records, analytics, detail, and export parameters.
- [ ] Implement `/api/trained-dataset/summary`, `/api/trained-dataset/records`, `/api/trained-dataset/detail/<id>`, and `/api/trained-dataset/export` with bounded parameters.
- [ ] Run focused endpoint tests.

### Task 3: Add the dashboard tab

**Files:**
- Modify: `templates/index.html`
- Test: `tests/test_frontend_contract.py`

- [ ] Add failing contract assertions for navigation, summary cards, filter controls, charts, table pagination/visibility/export, detail panel, category art, and lazy image gallery hooks.
- [ ] Add the Trained Dataset tab using the existing theme and native SVG/CSS rendering.
- [ ] Run frontend tests.

### Task 4: Extend the existing AI Assistant

**Files:**
- Modify: `engines/rag_orchestrator.py`, `engines/sql_engine.py`
- Test: `tests/test_trained_dataset.py`, `tests/test_chat_routing.py`

- [ ] Add failing tests for trained category, class ID, supplier aggregate, image threshold, missing SKU/image, model ID, and inactive queries.
- [ ] Add trained intent detection and structured responses using the existing `_format_response` path; do not add a second chat route or UI.
- [ ] Run trained chat tests and existing chat tests.

### Task 5: Full verification

- [ ] Run `pytest`.
- [ ] Run `git diff --check` and inspect the final diff for unrelated changes.
