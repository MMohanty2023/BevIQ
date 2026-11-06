# BevIQ Single-Page Landing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the BevIQ artwork first when `app.py` runs, then reveal the existing application in the same page when the artwork is clicked.

**Architecture:** Keep Flask serving one root template. Add a landing container before the current application container and switch the two containers with a small client-side state transition. Delay existing app initialization until the transition so the current dashboard/chat behavior remains unchanged.

**Tech Stack:** Flask, one existing HTML/CSS/JavaScript template, local static image asset, pytest frontend contract tests.

**Spec:** `docs/superpowers/specs/2026-11-06-beviq-single-page-landing-design.md`

## Global Constraints

- Keep the current Flask root entry point and existing APIs unchanged.
- Use the supplied BevIQ artwork as a local asset; do not load it from an external URL.
- The landing-to-app transition must stay in the same browser tab and page.
- Existing dashboard, AI Assistant, Master Brands, Comparison Studio, and Datasets behavior must continue to work.

## Review Focus

- Initial load: only the landing screen is visible before entry.
- Artwork click: the existing app becomes visible in the same page and initializes once.
- Refresh: the page returns to the landing screen without corrupting the app state.
- Responsive viewport: the artwork remains contained and usable on narrow screens.
- Existing frontend contract: current navigation and app hooks remain present.

### Task 1: Add the single-page landing shell and transition

**Files:**
- Create: `static/images/beviq-landing.jpg` from the supplied artwork.
- Modify: `templates/index.html` near the body start, app root wrapper, CSS section, and existing initialization script.

**Interfaces:**
- Produces `#beviq-landing` for the initial state.
- Produces `#beviq-app` for the existing application state.
- Produces `enterBevIQ()` to switch states and initialize the current app once.

- [ ] **Step 1: Add failing frontend contract assertions**

  Assert the template contains the landing id, app id, local landing image path, click handler, and `enterBevIQ` function.

- [ ] **Step 2: Run the focused frontend test and confirm it fails**

  Run: `\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py -q`

  Expected: fail because the landing hooks are not present yet.

- [ ] **Step 3: Add the supplied artwork as the local landing asset**

  Store it at `static/images/beviq-landing.jpg`; do not alter the artwork pixels.

- [ ] **Step 4: Implement the landing/app state switch in `templates/index.html`**

  Add a full-screen landing container with the local image as a button-like click target. Wrap the existing page content in `#beviq-app`, hidden initially. Add responsive `object-fit: contain` styling and `enterBevIQ()` that hides the landing, shows the app, and invokes the existing initialization exactly once.

- [ ] **Step 5: Run focused tests and confirm they pass**

  Run: `\.venv\Scripts\python.exe -m pytest tests/test_frontend_contract.py tests/test_dashboard_endpoints.py tests/test_dashboard_metrics.py -q`

  Expected: all tests pass.

### Task 2: Verify the browser flow and regression behavior

**Files:**
- Modify: `tests/test_frontend_contract.py` only if an assertion needs to pin the final landing contract.

**Interfaces:**
- Consumes `#beviq-landing`, `#beviq-app`, and `enterBevIQ()` from Task 1.

- [ ] **Step 1: Restart the local Flask server and open the root URL**

  Confirm the landing artwork is the only visible primary view.

- [ ] **Step 2: Click the BevIQ artwork**

  Confirm the same page reveals the existing navigation and dashboard/chat UI without opening another tab.

- [ ] **Step 3: Exercise existing app navigation**

  Confirm Dashboard, AI Assistant, and Master Brands still switch normally after entry.

- [ ] **Step 4: Run `git diff --check` and the focused test suite**

  Expected: no whitespace errors and all focused tests pass.
