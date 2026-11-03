# SDD ledger â€” plan: docs/superpowers/plans/2026-11-03-mysql-primary-dashboard-enhancement.md

Pre-flight: Task 1 produces active backend selection consumed by Tasks 2 and 6; Task 2 produces indexed lookup/search consumed by Tasks 5 and 6; Task 4 produces upload/document search behavior consumed by Task 5; Task 6 produces dashboard APIs consumed by Task 7.

Ruling: Continue in the existing `beverage_db` feature branch â€” native execution was explicitly selected, the branch is not `main/master`, and existing user edits must remain in place â€” cost if wrong: new changes share the current working tree and require careful diff review.

Task 1: complete (tests: pytest tests/test_db_backend.py -q -> 3 passed)
Task 2: complete (tests: pytest tests/test_sql_search.py tests/test_rag_id_lookup.py tests/test_rag_audit.py tests/test_app_endpoints.py -q -> 22 passed)
Task 3: complete (tests: pytest tests/test_optimize_csv.py -q -> 2 passed)
Task 4: complete (tests: pytest tests/test_document_rag.py tests/test_upload_endpoints.py tests/test_rag_audit.py tests/test_app_endpoints.py -q -> 22 passed)
Task 5: complete (tests: pytest tests/test_conversation_context.py tests/test_rag_audit.py tests/test_queries.py tests/test_app_endpoints.py -q -> 20 passed)
Task 6: complete (tests: pytest tests/test_dashboard_endpoints.py tests/test_app_endpoints.py tests/test_rag_audit.py -q -> 21 passed)
Task 7: complete (tests: pytest tests/test_frontend_contract.py tests/test_app_endpoints.py tests/test_dashboard_endpoints.py -q -> 12 passed)
Task 8: complete (tests: explicit non-script suite -> 47 passed; full pytest invocation could not be used because legacy script-style tests execute long-running database work during collection)
Final: fixed legacy-document FTS migration edge case — test_search_falls_back_for_chunks_created_before_fts_index RED?GREEN, document suite 5/5
Final: fixed MySQL query-time fallback — test_query_falls_back_to_sqlite_when_mysql_query_fails RED?GREEN, backend suite 4/4
