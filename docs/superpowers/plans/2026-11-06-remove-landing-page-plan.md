# Remove Landing Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing dashboard appear immediately at `/` by removing the separate BevIQ landing screen.

**Architecture:** Keep the existing Flask route and single-page template. Remove landing-only markup, styles, and transition code; make `#beviq-app` visible by default so all existing dashboard tabs and API behavior remain unchanged.

**Tech Stack:** Flask, Jinja template, vanilla HTML/CSS/JavaScript, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-remove-landing-page-design.md`

## Global Constraints

- Preserve the existing `/` Flask route and `templates/index.html` response.
- Preserve dashboard markup, navigation, tabs, API calls, and styling outside landing-only code.
- Do not add a new route or duplicate the dashboard template.

## Review Focus

- Root page must contain the dashboard and must not contain the landing container: covered by the frontend contract test.
- Dashboard must no longer depend on clicking `enterBevIQ()`: covered by the absence of the transition hook and default visible app container.
- Existing dashboard navigation and live endpoint hooks must remain: covered by the existing frontend contract tests.

### Task 1: Remove landing presentation and default to dashboard

**Files:**
- Modify: `templates/index.html` — remove landing-only CSS/HTML/JavaScript and change the dashboard container to default visible.
- Modify: `tests/test_frontend_contract.py` — replace the landing-hook contract with direct-dashboard assertions.

**Interfaces:**
- Consumes: Existing `#beviq-app` dashboard container and existing frontend contract test fixture.
- Produces: Root template with no `#beviq-landing`, no `enterBevIQ()` transition, and a visible dashboard container.

- [ ] **Step 1: Write the failing test**

  Replace the landing-hook test with assertions that `#beviq-landing` and `enterBevIQ()` are absent, while `#beviq-app` exists without `display: none` and the dashboard tab remains present.

- [ ] **Step 2: Run the focused test to verify it fails**

  Run: `pytest tests/test_frontend_contract.py -q`

  Expected: FAIL because the current template still contains the landing markup and hides `#beviq-app`.

- [ ] **Step 3: Implement the minimal template change**

  Remove only the landing-specific CSS block, landing HTML block, and `beviqEntered`/`enterBevIQ()` JavaScript. Change `#beviq-app` to be visible by default. Do not change dashboard handlers or API URLs.

- [ ] **Step 4: Run the focused test to verify it passes**

  Run: `pytest tests/test_frontend_contract.py -q`

  Expected: PASS.

- [ ] **Step 5: Run the full test suite**

  Run: `pytest -q`

  Expected: all tests pass.

- [ ] **Step 6: Review the diff**

  Run: `git diff -- templates/index.html tests/test_frontend_contract.py`

  Confirm only landing presentation/transition code and its contract assertions changed.
