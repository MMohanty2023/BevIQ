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
