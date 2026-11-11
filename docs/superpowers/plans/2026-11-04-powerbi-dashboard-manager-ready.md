# Power BI Dashboard Manager-Ready Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the Power BI dashboard metrics unambiguous for manager review while keeping the existing dashboard scope.

**Architecture:** Keep the existing Flask dashboard APIs and SQL engine, but expose consistent distinct-UPC metrics and category-level reconciliation gaps. Update only the dashboard UI labels and visual summaries.

**Tech Stack:** Flask, SQLite/MySQL, SQL, inline dashboard JavaScript, pytest.

**Spec:** Manager review of the Power BI dashboard; Master Brand source is `AIMasterBrandData`.

## Global Constraints

- Dashboard scope only; do not change chat, Master Brand search, or unrelated tabs.
- “Master Brand UPC” means distinct usable UPCs from the AI Master table.
- Keep UPC-field completeness separate from category UPCs missing from the AI Master catalog.
- Make overlap/additive-count behavior explicit in labels.

## Review Focus

- Distinct UPC counts must match between pie chart and dataset table.
- Dataset UPC sums must not be labeled as globally unique UPCs.
- Missing UPC field counts must not be confused with UPCs absent from AI Master.
- Category reconciliation must show Beer, RTD, Wine, and Spirits separately.
- Dashboard export must make the selected/source dataset clear.

### Task 1: Normalize dashboard metric definitions

**Files:**
- Modify: `engines/sql_engine.py`
- Test: `tests/test_dashboard_metrics.py`

- [ ] Add failing tests for distinct AI Master UPC count and category missing-from-master breakdown.
- [ ] Implement the smallest SQL/API response change preserving existing response keys.
- [ ] Verify focused dashboard metrics tests pass.

### Task 2: Clarify dashboard presentation

**Files:**
- Modify: `templates/index.html`
- Test: `tests/test_frontend_contract.py`

- [ ] Add failing contract assertions for unambiguous labels, refresh/source context, and category reconciliation values.
- [ ] Update the pie title/legend, KPI labels, missing-overview copy, and dataset export context.
- [ ] Verify frontend contract tests pass.

### Task 3: Verify the Power BI dashboard end-to-end

**Files:**
- Test: `tests/test_dashboard_endpoints.py tests/test_dashboard_metrics.py tests/test_frontend_contract.py`

- [ ] Run focused dashboard/API/UI tests.
- [ ] Run the full configured pytest suite.
- [ ] Verify the live Flask page contains the updated dashboard markers.

