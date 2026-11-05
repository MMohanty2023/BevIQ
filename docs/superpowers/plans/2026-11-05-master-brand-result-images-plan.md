# Master Brand Result Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show Master Brand image URLs as thumbnails beside matching search results on the existing Master Brands page.

**Architecture:** Keep the existing search API and returned columns unchanged. Add small frontend helpers that identify common image URL fields, validate HTTP(S) URLs, and render a thumbnail panel beside the existing result table; rows without images continue to render normally.

**Tech Stack:** Flask API, HTML/CSS/JavaScript, pytest frontend contract tests.

**Spec:** `docs/superpowers/specs/2026-11-05-master-brand-result-images-design.md`

## Global Constraints

- The image option must appear on the existing Master Brands search page, alongside the current search form/results; no new page or tab is introduced.
- Keep the existing `/api/master-brands/search` response and table data unchanged.
- Render only valid HTTP(S) image URLs and handle broken images without breaking results.
- Keep all existing columns and values visible.
- Do not download, cache, proxy, or upload images through Flask.

## Review Focus

- Image fields with different casing/names such as `image_url`, `ImageURL`, or `image` must be detected — covered in Task 1.
- Missing or empty image URLs must leave the result table usable — covered in Task 1.
- Invalid schemes such as `javascript:` must never become image sources — covered in Task 1.
- Broken remote images must hide/remove their preview without breaking the result table — covered in Task 1.
- Multiple result rows with mixed image availability must preserve every row and its columns — covered in Task 1.

### Task 1: Render Master Brand images on the existing search page

**Files:**
- Modify: `templates/index.html`
- Test: `tests/test_frontend_contract.py`

**Interfaces:**
- Consumes: `data.columns` and `data.records` from `/api/master-brands/search`.
- Produces: frontend helpers `getMasterBrandImageUrl(row, columns)` and `renderMasterBrandResults(data)` used by `searchMasterBrands()`.

- [ ] **Step 1: Write failing frontend contract tests** asserting the image helper/render hooks, existing Master Brands page placement, HTTP(S) validation, and broken-image handling.
- [ ] **Step 2: Run the focused tests** with `pytest tests/test_frontend_contract.py -q`; confirm failure is due to the missing image-rendering contract.
- [ ] **Step 3: Implement the minimal CSS/JavaScript** in `templates/index.html`. Keep the current search form and table on the same page; add a side thumbnail area only when a valid URL exists.
- [ ] **Step 4: Re-run focused tests** and confirm they pass.
- [ ] **Step 5: Run the full suite** with `pytest -q` and record any unrelated failures.
- [ ] **Step 6: Commit** with `git commit -m "feat: show master brand result images"`.

### Task 2: Final verification

**Files:**
- Verify: `templates/index.html`, `tests/test_frontend_contract.py`

- [ ] **Step 1:** Run `git diff --check` and confirm no conflict markers remain.
- [ ] **Step 2:** Confirm the Master Brands page still contains the existing search form, result container, and API endpoint.
- [ ] **Step 3:** Check `git status` and report only the intended changes; do not push to GitHub.
