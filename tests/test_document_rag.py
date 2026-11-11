from io import BytesIO
from pathlib import Path
import sys

import pytest
from werkzeug.datastructures import FileStorage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import document_rag


def storage(name, content=b"hello beverage data"):
    return FileStorage(stream=BytesIO(content), filename=name, content_type="text/plain")


def test_validate_upload_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="Supported uploads"):
        document_rag.validate_upload(storage("malware.exe"), max_bytes=1000)


def test_validate_upload_rejects_large_upload():
    with pytest.raises(ValueError, match="too large"):
        document_rag.validate_upload(storage("notes.txt", b"12345"), max_bytes=4)


def test_ingest_searches_text_without_loading_all_chunks(monkeypatch, tmp_path):
    monkeypatch.setattr(document_rag, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(document_rag, "DOC_DB", tmp_path / "documents.sqlite3")

    result = document_rag.ingest(storage("notes.txt", b"Important supplier record for Example Brand"), "session-a")
    hits = document_rag.search("supplier Example Brand", "session-a")

    assert result["chunks"] == 1
    assert hits
    assert hits[0]["filename"] == "notes.txt"


def test_doc_upload_fails_with_clear_message(monkeypatch, tmp_path):
    monkeypatch.setattr(document_rag, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(document_rag, "DOC_DB", tmp_path / "documents.sqlite3")

    with pytest.raises(ValueError, match="DOC files require conversion"):
        document_rag.ingest(storage("legacy.doc"), "session-a")


def test_search_falls_back_for_chunks_created_before_fts_index(monkeypatch, tmp_path):
    monkeypatch.setattr(document_rag, "DOC_DB", tmp_path / "documents.sqlite3")
    conn = document_rag._connection()
    conn.execute("INSERT INTO documents(document_id, session_id, filename, content_hash) VALUES(?,?,?,?)",
                 ("legacy", "session-a", "legacy.txt", "hash"))
    conn.execute("INSERT INTO document_chunks(document_id, session_id, chunk_index, page, content) VALUES(?,?,?,?,?)",
                 ("legacy", "session-a", 0, "1", "Legacy supplier record"))
    conn.commit()
    conn.close()

    hits = document_rag.search("supplier record", "session-a")

    assert hits[0]["filename"] == "legacy.txt"
