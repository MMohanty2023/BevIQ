from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import base64
import sys

import pytest
import requests
from PIL import Image
from werkzeug.datastructures import FileStorage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engines.image_chat import ImageChatEngine, VisionUnavailableError


def photo(name="scene.png", size=(400, 200)):
    stream = BytesIO()
    Image.new("RGB", size, (50, 120, 180)).save(stream, format="PNG")
    stream.seek(0)
    return FileStorage(stream=stream, filename=name, content_type="image/png")


@pytest.fixture
def engine(tmp_path):
    return ImageChatEngine(tmp_path / "images.sqlite3", tmp_path / "uploads")


def test_photo_without_text_is_saved_and_scoped_to_session(engine):
    uploaded = engine.ingest(photo(size=(1600, 900)), "session-a")
    assert uploaded["type"] == "image"
    assert uploaded["filename"] == "scene.png"
    saved = engine.get_image("session-a", uploaded["image_id"])
    with Image.open(saved["path"]) as image:
        assert image.format == "JPEG"
        assert max(image.size) <= 768
    assert engine.get_image("session-b") is None
    assert engine.get_image("session-b", uploaded["image_id"]) is None


def test_corrupt_image_is_rejected_without_orphan_file(engine):
    with pytest.raises(ValueError, match="valid image"):
        engine.ingest(FileStorage(stream=BytesIO(b"not a photo"), filename="fake.jpg"), "a")
    assert not list(engine.upload_dir.glob("*.jpg"))
    assert engine.get_image("a") is None


def test_large_dimensions_rejected_before_decoding(engine):
    with pytest.raises(ValueError, match="pixels"):
        engine.ingest(photo(size=(5100, 5000)), "a")
    assert not list(engine.upload_dir.glob("*.jpg"))


def test_cpu_vision_receives_pixels_prompt_and_conversation(engine, monkeypatch):
    uploaded = engine.ingest(photo(), "a")
    calls = []
    def post(url, **kwargs):
        calls.append((url, kwargs))
        return SimpleNamespace(status_code=200, json=lambda: {"message": {"content": "A blue scene.\n\nA little poem."}})
    monkeypatch.setattr("engines.image_chat.requests.post", post)
    answer = engine.answer(
        "Describe this picture and write poetry.", "a",
        history=[{"role": "assistant", "content": "Previous description"}],
        image_id=uploaded["image_id"], language_instruction="Reply in English.",
    )
    url, kwargs = calls[0]
    assert url == engine.host.rstrip("/") + "/api/chat"
    payload = kwargs["json"]
    assert payload["options"]["num_gpu"] == 0
    assert payload["model"] == engine.model
    assert payload["stream"] is False
    assert payload["messages"][-1]["content"] == "Describe this picture and write poetry."
    assert "Reply in English." in payload["messages"][0]["content"]
    assert payload["messages"][1]["content"] == "Previous description"
    pixels = base64.b64decode(payload["messages"][-1]["images"][0])
    assert Image.open(BytesIO(pixels)).format == "JPEG"
    assert "poem" in answer


def test_foreign_image_id_cannot_be_used_for_answer(engine):
    uploaded = engine.ingest(photo(), "a")
    with pytest.raises(ValueError, match="Attach"):
        engine.answer("Describe image", "b", image_id=uploaded["image_id"])


@pytest.mark.parametrize("status", [404, 500])
def test_model_failures_are_actionable(engine, monkeypatch, status):
    engine.ingest(photo(), "a")
    monkeypatch.setattr("engines.image_chat.requests.post", lambda *a, **k: SimpleNamespace(status_code=status))
    with pytest.raises(VisionUnavailableError):
        engine.answer("Describe image", "a")


def test_ollama_timeout_is_reported(engine, monkeypatch):
    engine.ingest(photo(), "a")
    def timeout(*args, **kwargs):
        raise requests.Timeout()
    monkeypatch.setattr("engines.image_chat.requests.post", timeout)
    with pytest.raises(VisionUnavailableError, match="CPU|time"):
        engine.answer("Describe image", "a")


def test_empty_model_response_is_not_a_success(engine, monkeypatch):
    engine.ingest(photo(), "a")
    monkeypatch.setattr("engines.image_chat.requests.post", lambda *a, **k: SimpleNamespace(
        status_code=200, json=lambda: {"message": {"content": ""}}))
    with pytest.raises(VisionUnavailableError, match="empty"):
        engine.answer("Describe image", "a")


def test_followups_do_not_capture_ordinary_catalog_or_general_requests():
    assert ImageChatEngine.is_followup("Write a poem about this image")
    assert ImageChatEngine.is_followup("Make it shorter")
    assert ImageChatEngine.is_followup("Tell me more about the picture")
    assert not ImageChatEngine.is_followup("What is Python?")
    assert not ImageChatEngine.is_followup("Show brands with missing images")
    assert not ImageChatEngine.is_followup("Write a poem about winter")



def test_chat_image_upload_bypasses_ocr(engine, monkeypatch):
    import importlib
    app_module = importlib.import_module("app")
    monkeypatch.setattr(app_module, "image_chat", engine, raising=False)
    def no_ocr(*args, **kwargs):
        raise AssertionError("A photo must not go through document OCR")
    monkeypatch.setattr(app_module, "ingest_document", no_ocr)
    calls = []
    def route(query, session_id="default-session", uploaded_image=None):
        calls.append(uploaded_image)
        return {"answer": "A blue picture and a poem.", "record_count": 0}
    monkeypatch.setattr(app_module.rag_orchestrator, "route_and_execute", route)
    upload = photo()
    response = app_module.app.test_client().post(
        "/api/chat", data={"message": "Describe this picture and write poetry", "session_id": "photo-chat",
                           "file": (upload.stream, upload.filename)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert calls[0]["type"] == "image"
    assert response.get_json()["uploaded_document"]["image_id"] == calls[0]["image_id"]


def test_image_turns_and_followups_use_vision_but_topic_changes_do_not(engine, monkeypatch, tmp_path):
    import engines.rag_orchestrator as routing
    from engines.conversation_store import ConversationStore
    monkeypatch.setattr(routing, "image_chat", engine, raising=False)
    assistant = routing.RAGOrchestrator()
    assistant.conversation_store = ConversationStore(tmp_path / "conversation.sqlite3")
    calls = []
    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return SimpleNamespace(status_code=200, json=lambda: {"message": {"content": "Blue scene. A poem."}})
    monkeypatch.setattr("engines.image_chat.requests.post", post)
    uploaded = engine.ingest(photo(), "a")
    first = assistant.route_and_execute("Describe this and add a poem", "a", uploaded_image=uploaded)
    second = assistant.route_and_execute("Make it shorter", "a")
    assert first["source_files"] == ["scene.png"]
    assert second["conversation_context_used"] is True
    assert len(calls) == 2
    assert calls[-1]["messages"][-1]["images"]
    monkeypatch.setattr(assistant, "_route_and_execute", lambda *a, **k: {
        "answer": "Python is a language.", "record_count": 0,
    })
    assistant.route_and_execute("What is Python?", "a")
    assistant.route_and_execute("Explain it", "a")
    assert len(calls) == 2
    assistant.route_and_execute("Describe this picture again", "a")
    assert len(calls) == 3


def test_conversation_store_upgrades_existing_database_for_image_context(tmp_path):
    import sqlite3
    from engines.conversation_store import ConversationStore
    db = tmp_path / "old.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE conversation_turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
        role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("INSERT INTO conversation_turns(session_id,role,content) VALUES('a','user','hello')")
    conn.commit()
    conn.close()
    store = ConversationStore(db)
    store.append("a", "assistant", "A photo", image_id="picture-1")
    recent = store.recent("a")
    assert recent[0]["content"] == "hello"
    assert recent[0]["image_id"] is None
    assert recent[1]["image_id"] == "picture-1"



def test_cpu_model_defaults_to_direct_answer_variant():
    from config import OLLAMA_VISION_MODEL
    assert OLLAMA_VISION_MODEL == "qwen3-vl:2b-instruct"


@pytest.mark.parametrize("query", ["What color is it?", "Where was this taken?", "Tell me more"])
def test_natural_image_followups_are_recognized(query):
    assert ImageChatEngine.is_followup(query)


@pytest.mark.parametrize("query", [
    "Show products with image count over 5",
    "How many products have an image?",
    "kitne products ke image hain?",
    "List products and their image",
    "Show brands with missing images",
])
def test_catalog_questions_do_not_switch_to_photo_vision(query):
    assert not ImageChatEngine.is_followup(query)


def test_explicit_scene_question_can_include_products():
    assert ImageChatEngine.is_followup("Show the products visible in this picture")


def test_new_document_attachment_does_not_reuse_old_photo(engine, monkeypatch, tmp_path):
    import engines.rag_orchestrator as routing
    from engines.conversation_store import ConversationStore
    monkeypatch.setattr(routing, "image_chat", engine)
    assistant = routing.RAGOrchestrator()
    assistant.conversation_store = ConversationStore(tmp_path / "conversation.sqlite3")
    photo_info = engine.ingest(photo(), "a")
    assistant.conversation_store.append("a", "assistant", "Photo description", image_id=photo_info["image_id"])
    def no_vision(*args, **kwargs):
        raise AssertionError("New document must not use previous image")
    monkeypatch.setattr(engine, "answer", no_vision)
    seen = []
    def document_route(query, **kwargs):
        seen.append(query)
        return {"answer": "Document summary", "record_count": 0}
    monkeypatch.setattr(assistant, "_route_and_execute", document_route)
    result = assistant.route_and_execute("Describe this", "a", uploaded_document={"filename": "notes.txt"})
    assert result["answer"] == "Document summary"
    assert "document" in seen[0].lower()
    assert assistant.conversation_store.recent("a")[-1]["image_id"] is None


def test_endpoint_passes_new_document_context(monkeypatch):
    import importlib
    app_module = importlib.import_module("app")
    uploaded = {"document_id": "doc-1", "filename": "notes.txt", "chunks": 1}
    monkeypatch.setattr(app_module, "ingest_document", lambda *a, **k: uploaded)
    captured = []
    def route(query, session_id="default-session", uploaded_document=None):
        captured.append(uploaded_document)
        return {"answer": "Document summary", "record_count": 0}
    monkeypatch.setattr(app_module.rag_orchestrator, "route_and_execute", route)
    response = app_module.app.test_client().post("/api/chat", data={
        "message": "Describe this", "session_id": "a", "file": (BytesIO(b"notes"), "notes.txt"),
    }, content_type="multipart/form-data")
    assert response.status_code == 200
    assert captured == [uploaded]
