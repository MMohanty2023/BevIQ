from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.conversation_store import ConversationStore


def test_conversation_store_keeps_recent_bounded_turns(tmp_path):
    store = ConversationStore(tmp_path / "conversation.sqlite3")

    for index in range(10):
        store.append("session-a", "user", f"question {index}")

    recent = store.recent("session-a", limit=3)

    assert len(recent) == 3
    assert recent[0]["content"] == "question 7"
    assert recent[-1]["content"] == "question 9"


def test_conversation_store_is_session_scoped(tmp_path):
    store = ConversationStore(tmp_path / "conversation.sqlite3")
    store.append("session-a", "user", "private question")

    assert store.recent("session-b") == []


def test_follow_up_context_is_added_only_for_contextual_short_questions():
    from engines.rag_orchestrator import RAGOrchestrator

    assistant = RAGOrchestrator()
    history = [{"role": "user", "content": "Find details for ID 10245"}]

    assert "Find details for ID 10245" in assistant._with_conversation_context("what about it?", history)
    assert assistant._with_conversation_context("Find UPC 1234567890123", history) == "Find UPC 1234567890123"


def test_general_chat_sends_recent_turns_to_ollama(monkeypatch, tmp_path):
    from engines.rag_orchestrator import RAGOrchestrator

    assistant = RAGOrchestrator()
    assistant.conversation_store = ConversationStore(tmp_path / "conversation.sqlite3")
    assistant.conversation_store.append("chat", "user", "Tell me about renewable energy")
    assistant.conversation_store.append("chat", "assistant", "It comes from naturally replenished sources.")
    prompts = []

    monkeypatch.setattr(RAGOrchestrator, "is_ollama_available", lambda self: True)
    monkeypatch.setattr(
        RAGOrchestrator,
        "query_ollama",
        lambda self, prompt, system_prompt=None: prompts.append(prompt) or "It helps reduce reliance on fossil fuels.",
    )

    result = assistant.route_and_execute("Why does that matter?", session_id="chat")

    assert "It helps reduce reliance on fossil fuels" in result["answer"]
    assert "User: Tell me about renewable energy" in prompts[0]
    assert "Assistant: It comes from naturally replenished sources." in prompts[0]
    assert "Current user message: Why does that matter?" in prompts[0]


def test_response_language_detection_distinguishes_english_hinglish_and_hindi():
    from engines.rag_orchestrator import RAGOrchestrator

    assistant = RAGOrchestrator()

    assert assistant._detect_response_language("Can you explain how rainbows form?") == "English"
    assert assistant._detect_response_language("kaise ho") == "Hinglish"
    assert assistant._detect_response_language("आप कैसे हैं?") == "Hindi"
