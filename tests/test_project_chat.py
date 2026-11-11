from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engines.project_knowledge import is_project_question, get_project_context


@pytest.mark.parametrize("query", [
    "Explain my project architecture",
    "How does PD Comparison Studio work?",
    "What database does this app use?",
    "mere project ki working batao",
    "How can I deploy BevIQ offline on a CPU?",
    "Explain how missing UPC auditing works in this project",
])
def test_project_explanations_are_recognized(query):
    assert is_project_question(query)


@pytest.mark.parametrize("query", [
    "What is a database?",
    "What is beer?",
    "Write a poem about winter",
    "How many brands are in my project?",
    "Show Master Brand Kingfisher",
    "Find UPC 0852955008021 in BevIQ",
    "Compare master with beer in my project",
])
def test_general_and_record_queries_keep_existing_routes(query):
    assert not is_project_question(query)


def test_project_context_uses_real_guide_and_safe_runtime_facts(monkeypatch):
    monkeypatch.setenv("MYSQL_PASSWORD", "DO_NOT_EXPOSE_THIS_VALUE")
    result = get_project_context("Explain my project architecture")
    assert "Flask" in result["text"]
    assert "SQLite" in result["text"]
    assert "Ollama" in result["text"]
    assert "PD Comparison Studio" in result["text"]
    assert "DO_NOT_EXPOSE_THIS_VALUE" not in result["text"]
    assert "MYSQL_PASSWORD=" not in result["text"]
    assert "docs/assistant-project-guide.md" in result["source_files"]
    assert "config.py" in result["source_files"]
    assert len(result["text"]) < 9000


@pytest.fixture
def assistant(tmp_path):
    from engines.rag_orchestrator import RAGOrchestrator
    from engines.conversation_store import ConversationStore
    instance = RAGOrchestrator()
    instance.conversation_store = ConversationStore(tmp_path / "conversation.sqlite3")
    return instance


def test_project_explanation_uses_grounded_context_not_catalog(assistant, monkeypatch):
    class NoCatalog:
        def __getattr__(self, name):
            raise AssertionError("Project explanation must not query product records")
    monkeypatch.setattr("engines.rag_orchestrator.sql_engine", NoCatalog())
    monkeypatch.setattr("engines.rag_orchestrator.vector_engine", NoCatalog())
    monkeypatch.setattr(assistant, "is_ollama_available", lambda: True)
    calls = []
    def answer(prompt, system_prompt=None):
        calls.append((prompt, system_prompt))
        return "BevIQ uses Flask and local Ollama; UPC auditing checks the database."
    monkeypatch.setattr(assistant, "query_ollama", answer)
    result = assistant.route_and_execute("Explain how missing UPC auditing works in this project", "project")
    assert "docs/assistant-project-guide.md" in result["source_files"]
    assert result["record_count"] == 0
    assert "Verified project context" in calls[0][0]
    assert "Ollama" in calls[0][0]
    assert "English only" in calls[0][1]


def test_project_facts_remain_available_when_model_is_stopped(assistant, monkeypatch):
    monkeypatch.setattr(assistant, "is_ollama_available", lambda: False)
    result = assistant.route_and_execute("Explain my project architecture", "project-offline")
    assert "Flask" in result["answer"]
    assert "SQLite" in result["answer"]
    assert result["source_files"]
    assert result["record_count"] == 0


def test_project_followup_keeps_context_but_unrelated_topic_does_not(assistant, monkeypatch):
    monkeypatch.setattr(assistant, "is_ollama_available", lambda: True)
    calls = []
    def answer(prompt, system_prompt=None):
        calls.append((prompt, system_prompt))
        return "Project answer" if "Verified project context" in prompt else "General answer"
    monkeypatch.setattr(assistant, "query_ollama", answer)
    assistant.route_and_execute("Explain my project architecture", "project")
    followup = assistant.route_and_execute("What database does it use?", "project")
    general = assistant.route_and_execute("What is a database?", "project")
    assert "Verified project context" in calls[1][0]
    assert followup["source_files"]
    assert "Verified project context" not in calls[2][0]
    assert general["source_files"] == []


def test_english_hinglish_project_answers_keep_language(assistant, monkeypatch):
    monkeypatch.setattr(assistant, "is_ollama_available", lambda: True)
    systems = []
    monkeypatch.setattr(assistant, "query_ollama", lambda prompt, system_prompt=None: systems.append(system_prompt) or "Yeh Flask project hai.")
    result = assistant.route_and_execute("mere project ki working batao", "hinglish-project")
    assert "natural conversational Hinglish" in systems[0]
    assert result["source_files"]



def test_project_explanation_after_photo_is_not_an_image_followup(assistant, monkeypatch):
    assistant.conversation_store.append("topic", "assistant", "Photo description", image_id="old-picture")
    def no_image(*args, **kwargs):
        raise AssertionError("An app explanation must not reuse photo pixels")
    monkeypatch.setattr("engines.rag_orchestrator.image_chat.get_image", no_image)
    monkeypatch.setattr(assistant, "is_ollama_available", lambda: False)
    result = assistant.route_and_execute("How does this app work?", "topic")
    assert "Flask" in result["answer"]
    assert "docs/assistant-project-guide.md" in result["source_files"]


def test_user_pdf_about_project_keeps_upload_route(assistant, monkeypatch):
    monkeypatch.setattr(assistant, "is_ollama_available", lambda: False)
    monkeypatch.setattr("engines.rag_orchestrator.search_documents", lambda *a, **k: [{
        "filename": "project.pdf", "page": "1", "content": "This uploaded project brief is about a bakery.",
    }])
    result = assistant.route_and_execute("Explain my project according to this PDF", "project-doc")
    assert "bakery" in result["answer"]
    assert result["source_files"] == ["project.pdf"]



@pytest.mark.parametrize("query", [
    "Can you show brands in my project?",
    "Could you compare master with beer in my project?",
    "mere project mein brands dikhao",
])
def test_polite_and_hinglish_data_requests_are_not_project_guide_queries(query):
    assert not is_project_question(query)


@pytest.mark.parametrize("query", [
    "Explain my project according to the document I uploaded",
    "Explain my project based on the PDF I attached",
])
def test_uploaded_document_paraphrases_keep_their_own_source(assistant, monkeypatch, query):
    monkeypatch.setattr(assistant, "is_ollama_available", lambda: False)
    monkeypatch.setattr("engines.rag_orchestrator.search_documents", lambda *a, **k: [{
        "filename": "my-brief.pdf", "page": "1", "content": "My brief describes a gardening project.",
    }])
    result = assistant.route_and_execute(query, "uploaded-project")
    assert result["source_files"] == ["my-brief.pdf"]
    assert "gardening" in result["answer"]
