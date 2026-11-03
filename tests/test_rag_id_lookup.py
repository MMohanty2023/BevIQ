from engines.rag_orchestrator import RAGOrchestrator


def test_id_query_uses_complete_identifier_lookup(monkeypatch):
    class FakeSQL:
        def lookup_identifier(self, identifier, limit=200):
            assert identifier == "10245"
            return {
                "normalized_identifier": "10245",
                "total_matches": 1,
                "records": [{
                    "id": "10245",
                    "BrandName": "Example Brand",
                    "ProductName": "Example Product",
                    "source_file": "AIMasterBrandData.csv",
                    "original_row": 12,
                }],
                "related_records": [],
                "source_files": ["AIMasterBrandData.csv"],
            }

    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", FakeSQL())

    result = RAGOrchestrator().route_and_execute("Find details for ID 10245")

    assert result["record_count"] == 1
    assert "10245" in result["answer"]
    assert "Example Product" in result["answer"]


def test_invalid_id_returns_clear_not_found_response(monkeypatch):
    class FakeSQL:
        def lookup_identifier(self, identifier, limit=200):
            return {
                "normalized_identifier": identifier,
                "total_matches": 0,
                "records": [],
                "related_records": [],
                "source_files": [],
            }

    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", FakeSQL())

    result = RAGOrchestrator().route_and_execute("Find details for ID 999999")

    assert result["record_count"] == 0
    assert "not found" in result["answer"].lower()
