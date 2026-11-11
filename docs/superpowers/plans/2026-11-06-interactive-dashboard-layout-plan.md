# Interactive Dashboard Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Rework the existing dashboard into an interactive native SVG/CSS visualization surface with chart selectors, Count/Percentage display mode, and a floating AI Assistant shortcut while preserving all existing behavior.

**Architecture:** Keep the existing Flask template and dashboard API responses. Add a dashboard visualization state in `templates/index.html`, render Pie/Bar/Heatmap/Overview views from the existing metrics data, and keep navigation through the existing `switchTab()` function. Add frontend contract tests in `tests/test_frontend_contract.py`.

**Tech Stack:** Flask, Jinja template, existing browser JavaScript, HTML/CSS/SVG, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-interactive-dashboard-layout-design.md`

## Global Constraints

- Dashboard must be the first top navigation item and AI Assistant the second.
- Reuse existing dashboard API responses and existing AI Assistant implementation.
- Do not auto-navigate to AI Assistant.
- Do not remove existing KPI, table, theme, or dashboard data functionality.
- Add frontend contract tests for navigation order, chart controls, count/percentage state, and floating assistant hooks.

## Review Focus

- Empty or zero-valued datasets must render without invalid SVG geometry or divide-by-zero percentages.
- Switching chart type and display mode must reuse the latest loaded data without a second dashboard fetch.
- Dashboard loading/error states must remain visible when visualization rendering cannot proceed.
- The floating assistant must only navigate on click and must not interfere with existing tab selection.
- Responsive layouts must keep controls usable at narrow viewport widths.

### Task 1: Add failing dashboard interaction contracts

**Files:**
- Modify: `tests/test_frontend_contract.py`

- [ ] Add assertions for Dashboard-before-AI navigation order, chart selector IDs/labels, Count/Percentage controls, visualization state/render functions, and floating assistant click/animation hooks.
- [ ] Run the focused frontend test file and confirm the new assertions fail because the hooks do not yet exist.

### Task 2: Add dashboard controls and visualization shell

**Files:**
- Modify: `templates/index.html` near the dashboard tab and dashboard styles.

- [ ] Add dashboard chart selector buttons for Overview, Pie, Bar, and Heatmap plus Count/Percentage toggle controls.
- [ ] Add a visualization container with accessible labels and a floating AI Assistant button inside the dashboard panel.
- [ ] Add responsive styles, active states, gentle vertical assistant animation, and reduced-motion handling.
- [ ] Reorder top navigation so Dashboard is first and AI Assistant is second while retaining existing tab IDs and handlers.

### Task 3: Render interactive native visualizations

**Files:**
- Modify: `templates/index.html` dashboard JavaScript.

- [ ] Add a dashboard visualization state containing `chartType` and `displayMode`.
- [ ] Add render functions for native SVG Pie, Bar, and Heatmap views plus an Overview fallback.
- [ ] Calculate percentages from the same metrics data with safe zero-total handling.
- [ ] Ensure chart buttons and Count/Percentage controls rerender from cached dashboard data without refetching.

### Task 4: Connect floating assistant and preserve existing dashboard flow

**Files:**
- Modify: `templates/index.html` dashboard JavaScript.

- [ ] Make the floating button call `switchTab('chat', ...)` only on click.
- [ ] Keep the existing AI Assistant form, chat API, upload flow, and tab behavior unchanged.
- [ ] Ensure dashboard load/error states continue to update the existing status elements.

### Task 5: Verify and commit

**Files:**
- Modify: `docs/superpowers/specs/2026-11-06-interactive-dashboard-layout-design.md` only if implementation decisions need recording.

- [ ] Run `pytest tests/test_frontend_contract.py tests/test_master_brand_search.py tests/test_master_brand_endpoints.py -q`.
- [ ] Run `git diff --check`.
- [ ] Verify live browser behavior for navigation order, each chart selector, Count/Percentage switching, responsive dashboard controls, and floating assistant click navigation.
- [ ] Commit the implementation with a focused feature commit message.
