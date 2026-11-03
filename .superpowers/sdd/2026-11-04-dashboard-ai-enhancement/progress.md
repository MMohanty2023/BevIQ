# SDD ledger — plan: docs/superpowers/plans/2026-11-04-dashboard-ai-enhancement.md

Pre-flight: Tasks 1→2 share the metrics/search interfaces produced by `SQLEngine`; Tasks 2→4 share the API response contracts; Task 3→4 share the chat response shape. Existing routes and response keys remain compatibility constraints.

Baseline: `pytest -q` could not start because `pytest` was not on PATH; `.venv/Scripts/python.exe -m pytest -q` started but produced no output for more than 45 seconds and was interrupted. Focused tests will be used to isolate the baseline/import wait.

Task 1: complete (tests: `.venv/Scripts/python.exe -m pytest tests/test_db_backend.py tests/test_master_brand_search.py tests/test_dashboard_metrics.py -q` → 7 passed)

Task 2: complete (tests: `.venv/Scripts/python.exe -m pytest tests/test_master_brand_endpoints.py tests/test_dashboard_endpoints.py tests/test_db_backend.py -q` → 12 passed)

Task 3: complete (tests: `.venv/Scripts/python.exe -m pytest tests/test_chat_routing.py tests/test_rag_id_lookup.py tests/test_rag_audit.py -q` → 16 passed)

Task 4: complete (tests: `.venv/Scripts/python.exe -m pytest tests/test_frontend_contract.py tests/test_dashboard_endpoints.py tests/test_master_brand_endpoints.py tests/test_chat_routing.py -q` → 13 passed; JavaScript syntax check passed)
