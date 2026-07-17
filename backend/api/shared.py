import os
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "Frontend"
UPLOAD_FOLDER = ROOT_DIR / "uploads"
REVIEW_FOLDER = ROOT_DIR / "reviews"
SESSION_MEMORY_FOLDER = ROOT_DIR / "memory"

os.chdir(ROOT_DIR)

for import_path in (ROOT_DIR, BACKEND_DIR):
    import_path_string = str(import_path)
    if import_path_string not in sys.path:
        sys.path.insert(0, import_path_string)

for folder in (UPLOAD_FOLDER, REVIEW_FOLDER, SESSION_MEMORY_FOLDER):
    folder.mkdir(exist_ok=True)

REVIEW_OPTIONS = {
    "accurate answer",
    "first response",
    "followed query correctly",
}


def sanitize_reviewer_name(reviewer_name: str) -> str:
    sanitized_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", reviewer_name.strip().lower())
    return sanitized_name.strip("_") or "reviewer"


def sanitize_session_id(session_id: str) -> str:
    sanitized_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", session_id.strip())
    return sanitized_id.strip("_") or "session"


def session_memory_path(session_id: str) -> Path:
    return SESSION_MEMORY_FOLDER / f"{sanitize_session_id(session_id)}.txt"


def session_doc_path(session_id: str) -> Path:
    return SESSION_MEMORY_FOLDER / f"{sanitize_session_id(session_id)}.doc.txt"


def latest_indexed_doc_id() -> str:
    documents_path = ROOT_DIR / "rag_db" / "documents"
    if not documents_path.exists():
        return ""

    indexed_docs = [
        doc_path
        for doc_path in documents_path.iterdir()
        if doc_path.is_dir()
        and (doc_path / "metadata.pkl").exists()
        and (doc_path / "chunk_index.faiss").exists()
    ]
    if not indexed_docs:
        return ""

    latest_doc = max(indexed_docs, key=lambda path: path.stat().st_mtime)
    return latest_doc.name


def asks_about_uploaded_document(query: str) -> bool:
    normalized_query = query.lower()
    document_words = ["pdf", "document", "doc", "uploaded", "provided", "from the file"]
    return any(word in normalized_query for word in document_words)
