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


def test_how_are_you_gets_a_response(monkeypatch):
    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: False)
    result = RAGOrchestrator().route_and_execute("How are you?")
    assert "ready" in result["answer"].lower()


def test_general_chat_prefers_ollama_over_predefined_fallback(monkeypatch):
    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: True)
    monkeypatch.setattr(
        RAGOrchestrator,
        "query_ollama",
        lambda self, prompt, system_prompt=None: "I am doing well and ready to help.",
    )

    result = RAGOrchestrator().route_and_execute("How are you?")

    assert "I am doing well" in result["answer"]


def test_master_brand_brand_only_question_uses_master_search(monkeypatch):
    class FakeSQL:
        def search_master_brands(self, **kwargs):
            assert kwargs["brand"] == "Kingfisher"
            return {"records": [{"BrandName": "Kingfisher"}], "total_matches": 1}

    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", FakeSQL())
    result = RAGOrchestrator().route_and_execute("Show Master Brand Kingfisher")
    assert result["record_count"] == 1


def test_missing_master_audit_is_not_captured_by_brand_count_handler(monkeypatch):
    class FakeComparison:
        def compare_all_missing_in_master(self, limit_per_category=150):
            return {
                "summary": {
                    "categories": [],
                    "total_categorization_upcs": 4,
                    "total_matched_in_master": 1,
                    "total_missing_from_master": 3,
                    "overall_missing_pct": 75.0,
                },
                "records": [{"category": "Beer", "upc": "123"}],
            }

    class ExplodingSQL:
        def count_brands(self, category):
            raise AssertionError("missing-master audit must run before brand count")

    monkeypatch.setattr("engines.rag_orchestrator.comparison_engine", FakeComparison())
    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", ExplodingSQL())

    result = RAGOrchestrator().route_and_execute(
        "beer, wine, rtd or spirits missing upc kon kon se hai check karo master brands me se jo hai nahi vo batao or count bhi"
    )

    assert result["record_count"] == 1
    assert "Missing UPCs" in result["answer"]
