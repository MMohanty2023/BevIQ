from engines.rag_orchestrator import RAGOrchestrator


def test_master_brand_id_question_uses_schema_aware_search(monkeypatch):
    class FakeSQL:
        def search_master_brands(self, **kwargs):
            assert kwargs["master_id"] == "64836d6479db3373669996ae"
            return {
                "columns": ["id", "BrandName", "ProductName", "clean_upc"],
                "records": [{"id": kwargs["master_id"], "BrandName": "Kingfisher", "ProductName": "Lager", "clean_upc": "8901234567890"}],
                "total_matches": 1,
            }

    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", FakeSQL())
    result = RAGOrchestrator().route_and_execute("Show Master Brand ID 64836d6479db3373669996ae")

    assert result["record_count"] == 1
    assert "Kingfisher" in result["answer"]
    assert "8901234567890" in result["answer"]


def test_brand_and_upc_question_uses_combined_master_search(monkeypatch):
    class FakeSQL:
        def search_master_brands(self, **kwargs):
            assert kwargs["brand"] == "Kingfisher"
            assert kwargs["upc"] == "8901234567890"
            return {"columns": ["BrandName", "clean_upc"], "records": [{"BrandName": "Kingfisher", "clean_upc": kwargs["upc"]}], "total_matches": 1}

    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", FakeSQL())
    result = RAGOrchestrator().route_and_execute("Find Kingfisher with UPC 8901234567890 in Master Brand")

    assert result["record_count"] == 1
    assert "Kingfisher" in result["answer"]


def test_general_database_question_gets_an_answer_without_catalog_lookup(monkeypatch):
    class ExplodingSQL:
        def __getattr__(self, name):
            raise AssertionError(f"general chat must not call SQL: {name}")

    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", ExplodingSQL())
    result = RAGOrchestrator().route_and_execute("What is a database?")

    assert "organized collection" in result["answer"].lower()
