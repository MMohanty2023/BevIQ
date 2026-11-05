import pytest

from engines.rag_orchestrator import RAGOrchestrator


@pytest.fixture(autouse=True)
def disable_live_ollama_by_default(monkeypatch):
    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: False)


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
    seen = {}

    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: True)
    monkeypatch.setattr(
        RAGOrchestrator,
        "query_ollama",
        lambda self, prompt, system_prompt=None: (
            seen.setdefault("system_prompt", system_prompt),
            "I am doing well and ready to help.",
        )[-1],
    )

    result = RAGOrchestrator().route_and_execute("How are you?")

    assert "English only" in seen["system_prompt"]
    assert "I am doing well" in result["answer"]


def test_hinglish_chat_explicitly_requires_roman_hinglish_reply(monkeypatch):
    seen = {}

    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: True)
    monkeypatch.setattr(
        RAGOrchestrator,
        "query_ollama",
        lambda self, prompt, system_prompt=None: (
            seen.setdefault("system_prompt", system_prompt),
            "Main Hinglish mein baat kar sakta hoon.",
        )[-1],
    )

    result = RAGOrchestrator().route_and_execute("Hinglish mein baat kar sakte ho?")

    assert "natural conversational Hinglish" in seen["system_prompt"]
    assert "Roman script" in seen["system_prompt"]
    assert "Devanagari" in seen["system_prompt"]
    assert "Main Hinglish" in result["answer"]


def test_open_ended_chat_explains_how_to_start_local_ollama(monkeypatch):
    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: False)

    result = RAGOrchestrator().route_and_execute("Can you explain how rainbows form?")

    assert "ollama run llama3.2" in result["answer"]
    assert "stays on this computer" in result["answer"]


def test_beverage_knowledge_question_is_treated_as_normal_chat(monkeypatch):
    class ExplodingSQL:
        def __getattr__(self, name):
            raise AssertionError(f"knowledge questions must not query catalog data: {name}")

    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", ExplodingSQL())
    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: True)
    monkeypatch.setattr(
        RAGOrchestrator,
        "query_ollama",
        lambda self, prompt, system_prompt=None: "Beer is brewed by fermenting grains.",
    )

    result = RAGOrchestrator().route_and_execute("What is beer?")

    assert "brewed by fermenting grains" in result["answer"]


def test_data_results_are_summarized_naturally_with_verified_records(monkeypatch):
    prompts = []
    system_prompts = []

    class FakeSQL:
        def search_master_brands(self, **kwargs):
            return {
                "records": [{"BrandName": "Kingfisher", "ProductName": "Lager"}],
                "total_matches": 1,
            }

    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", FakeSQL())
    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: True)
    monkeypatch.setattr(
        RAGOrchestrator,
        "query_ollama",
        lambda self, prompt, system_prompt=None: (
            prompts.append(prompt),
            system_prompts.append(system_prompt),
            "I found Kingfisher Lager in the Master Brand data.",
        )[-1],
    )

    result = RAGOrchestrator().route_and_execute("Show Master Brand Kingfisher")

    assert result["record_count"] == 1
    assert "I found Kingfisher Lager" in result["answer"]
    assert '"BrandName": "Kingfisher"' in prompts[0]
    assert "English only" in system_prompts[-1]


def test_uploaded_pdf_question_keeps_document_retrieval_route(monkeypatch):
    monkeypatch.setattr(
        "engines.rag_orchestrator.search_documents",
        lambda query, session_id: [{
            "filename": "notes.pdf",
            "page": "1",
            "content": "The product launch is scheduled for June.",
        }],
    )
    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: False)

    result = RAGOrchestrator().route_and_execute("Tell me about this PDF")

    assert result["record_count"] == 1
    assert "product launch" in result["answer"].lower()
    assert "notes.pdf" in result["source_files"]


def test_hinglish_uploaded_document_answer_keeps_hinglish_language(monkeypatch):
    system_prompts = []
    monkeypatch.setattr(
        "engines.rag_orchestrator.search_documents",
        lambda query, session_id: [{
            "filename": "notes.pdf",
            "page": "1",
            "content": "The launch is scheduled for June.",
        }],
    )
    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: True)
    monkeypatch.setattr(
        RAGOrchestrator,
        "query_ollama",
        lambda self, prompt, system_prompt=None: (
            system_prompts.append(system_prompt),
            "Launch June ke liye scheduled hai.",
        )[-1],
    )

    result = RAGOrchestrator().route_and_execute("Is PDF mein launch kab hai?", session_id="hinglish-document")

    assert "natural conversational Hinglish" in system_prompts[0]
    assert "Launch June" in result["answer"]


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
