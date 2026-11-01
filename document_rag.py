"""Local document ingestion and retrieval for chat-scoped RAG conversations."""

from __future__ import annotations

import csv
import hashlib
import re
import sqlite3
import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

from config import DB_DIR, REPORTS_DIR

UPLOAD_DIR = REPORTS_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DOC_DB = DB_DIR / "document_rag.sqlite3"


def _connection():
    conn = sqlite3.connect(str(DOC_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, filename TEXT NOT NULL,
        content_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS document_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL,
        session_id TEXT NOT NULL, chunk_index INTEGER NOT NULL, page TEXT,
        content TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_chunks_session ON document_chunks(session_id)")
    conn.commit()
    return conn


def _clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _extract(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        pages = []
        for number, page in enumerate(PdfReader(str(path)).pages, 1):
            text = _clean(page.extract_text())
            if text:
                pages.append((str(number), text))
        return pages
    if suffix == ".docx":
        from docx import Document
        text = _clean("\n".join(p.text for p in Document(str(path)).paragraphs))
        return [("1", text)] if text else []
    if suffix in {".txt", ".md", ".log", ".json", ".xml"}:
        return [("1", _clean(path.read_text(encoding="utf-8", errors="ignore")))]
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
            rows = list(csv.reader(handle))[:5000]
        return [("1", _clean("\n".join(" | ".join(row) for row in rows)))]
    if suffix in {".xlsx", ".xls"}:
        import pandas as pd
        sheets = pd.read_excel(path, sheet_name=None, nrows=5000)
        return [(str(name), _clean(df.fillna("").to_csv(index=False))) for name, df in sheets.items()]
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}:
        try:
            import pytesseract
            from PIL import Image
            text = _clean(pytesseract.image_to_string(Image.open(path)))
            return [("image", text)] if text else []
        except Exception as exc:
            raise RuntimeError("Image OCR needs Tesseract installed and available on PATH.") from exc
    raise ValueError("Supported uploads: PDF, DOCX, TXT, MD, CSV, XLSX, and common image formats.")


def _chunks(text, size=1200, overlap=180):
    words = text.split()
    if not words:
        return []
    result = []
    start = 0
    while start < len(words):
        result.append(" ".join(words[start:start + size]))
        start += max(1, size - overlap)
    return result


def ingest(file_storage, session_id):
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("Uploaded file has no valid filename.")
    document_id = uuid.uuid4().hex[:12]
    path = UPLOAD_DIR / f"{document_id}_{filename}"
    file_storage.save(path)
    pages = _extract(path)
    chunks = [(page, chunk) for page, text in pages for chunk in _chunks(text)]
    if not chunks:
        path.unlink(missing_ok=True)
        raise ValueError("No readable text was found in the uploaded document.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    conn = _connection()
    conn.execute("INSERT INTO documents(document_id,session_id,filename,content_hash) VALUES(?,?,?,?)",
                 (document_id, session_id, filename, digest))
    conn.executemany("INSERT INTO document_chunks(document_id,session_id,chunk_index,page,content) VALUES(?,?,?,?,?)",
                     [(document_id, session_id, index, page, content) for index, (page, content) in enumerate(chunks)])
    conn.commit()
    conn.close()
    return {"document_id": document_id, "filename": filename, "chunks": len(chunks)}


def _tokens(text):
    return set(re.findall(r"[a-z0-9]{2,}", text.lower()))


def search(query, session_id, top_k=6):
    wanted = _tokens(query)
    if not wanted:
        return []
    conn = _connection()
    rows = conn.execute("""SELECT c.*, d.filename FROM document_chunks c
        JOIN documents d ON d.document_id=c.document_id WHERE c.session_id=?""", (session_id,)).fetchall()
    conn.close()
    scored = []
    for row in rows:
        tokens = _tokens(row["content"])
        score = len(wanted & tokens) / max(1, len(wanted))
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [{"document_id": r["document_id"], "filename": r["filename"], "page": r["page"],
             "content": r["content"], "score": round(score, 4)} for score, r in scored[:top_k]]


def list_documents(session_id):
    conn = _connection()
    rows = conn.execute("SELECT document_id, filename, created_at FROM documents WHERE session_id=? ORDER BY created_at DESC", (session_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]
