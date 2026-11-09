# Trained Dataset MySQL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or superpowers:subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load only `TrainedBrandsData.csv` into MySQL table `trained_brands` and make the existing trained-dataset APIs read the migrated records and image URLs.

**Architecture:** Extend the existing MySQL migrator with an explicit dataset-key allowlist so a single CSV can be migrated without touching other tables. Add a CLI path for the trained table, then verify the active MySQL API against the migrated row count and source image URLs.

**Tech Stack:** Python, pandas, mysql-connector-python, Flask, pytest, MySQL 8.

**Spec:** `docs/superpowers/specs/2026-11-07-trained-dataset-mysql-design.md`

## Global Constraints

- Only `TrainedBrandsData.csv` is migrated in this operation.
- Other CSV files and MySQL tables remain untouched.
- Existing trained API field names and image URL parsing remain unchanged.
- Replacement of an existing `trained_brands` table requires an explicit flag.

## Review Focus

- Dataset selection must not accidentally migrate all configured CSVs.
- Existing-table protection must stop a migration unless replacement is explicit.
- The trained CSV's pipe delimiter and normalized column names must be preserved.
- `ImageUrls` must remain available as source URLs after migration.
- MySQL API responses must be non-empty when MySQL is active.

### Task 1: Add single-dataset migration contract

**Files:**
- Modify: `database/mysql_migrator.py`
- Test: `tests/test_mysql_migrator.py`

**Interfaces:**
- `migrate_data_to_mysql(..., dataset_keys=None)` keeps `None` as the existing all-datasets behavior and accepts `['trained_brands']` for a single dataset.
- CLI accepts `--dataset trained_brands` and may combine it with `--replace-existing`.

- [ ] Write a failing test that `_prepare_sources(['trained_brands'])` returns only the trained source and rejects an unknown key.
- [ ] Write a failing test that migration selection passes only the trained table to the migration path.
- [ ] Run the focused tests and confirm they fail for the missing dataset-selection interface.
- [ ] Implement the allowlist parameter, validation, and CLI option without changing default all-dataset behavior.
- [ ] Run focused migrator tests and confirm they pass.

### Task 2: Verify MySQL trained table and API

**Files:**
- Modify: `tests/test_trained_dataset.py` only if an integration assertion is needed.
- Test: existing trained dataset endpoint tests.

- [ ] Run the single-dataset migration with `--dataset trained_brands --replace-existing` against configured MySQL.
- [ ] Query MySQL for the `trained_brands` table row count and presence of `ImageUrls`.
- [ ] Run `/api/db-status`, `/api/trained-dataset/summary`, `/api/trained-dataset/records`, and a detail endpoint using the active MySQL backend.
- [ ] Confirm the API returns non-zero trained totals and source image URLs.

### Task 3: Regression verification

**Files:**
- No production changes expected.

- [ ] Run `pytest tests/test_mysql_migrator.py tests/test_trained_dataset.py tests/test_frontend_contract.py -q`.
- [ ] Run the complete `pytest` suite.
- [ ] Run `git diff --check` and inspect that only the planned files changed.
