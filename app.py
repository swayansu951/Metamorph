import sys
import asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )

import os
import re
import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from query_router import async_final_answer
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi import FastAPI, UploadFile, File, Form, HTTPException

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "Frontend"
SIMPLE_RAG_DIR = PROJECT_ROOT / "simple_rag"

os.chdir(PROJECT_ROOT)

if str(SIMPLE_RAG_DIR) not in sys.path:
    sys.path.insert(0, str(SIMPLE_RAG_DIR))

from simple_rag.database.ingest_db import ingest_pdf
from simple_rag.main import GENERATE
from query_router import async_final_answer

app = FastAPI()


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    # In production we have to replace "*" with specific frontend url
)

rag = GENERATE()

UPLOAD_FOLDER = PROJECT_ROOT / "uploads"
REVIEW_FOLDER = PROJECT_ROOT / "reviews"
SESSION_MEMORY_FOLDER = PROJECT_ROOT / "memory"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REVIEW_FOLDER, exist_ok=True)
os.makedirs(SESSION_MEMORY_FOLDER, exist_ok=True)

REVIEW_OPTIONS = {
    "accurate answer",
    "first response",
    "followed query correctly",
}


class ReviewPayload(BaseModel):
    reviewer_name: str = "none"
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    selected_options: List[str] = Field(default_factory=list)
    feedback: str = "none"
    doc_id: str = "none"
    query: str = "none"
    answer: str = "none"
    review_action: str = "submitted"


class SessionMemoryPayload(BaseModel):
    session_id: str
    summary: str = "No conversation yet."


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
    documents_path = PROJECT_ROOT / "rag_db" / "documents"
    if not documents_path.exists():
        return ""

    indexed_docs = [
        doc_path for doc_path in documents_path.iterdir()
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

@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/style.css")
async def serve_stylesheet():
    return FileResponse(
        FRONTEND_DIR / "style.css",
        headers={"Cache-Control": "no-store"},
    )

@app.get("/script.js")
async def serve_script():
    return FileResponse(
        FRONTEND_DIR / "script.js",
        headers={"Cache-Control": "no-store"},
    )

@app.post("/upload")
async def upload_pdf(
    file:UploadFile = File(...),
    session_id: str = Form("")
):
    safe_filename = Path(file.filename).name
    file_path = UPLOAD_FOLDER / safe_filename

    with open(file_path, 'wb') as f:
        f.write(await file.read())

    doc_id = file_path.stem

    ingest_pdf(file_path, doc_id)

    doc_folder = PROJECT_ROOT / "rag_db" / "documents" / doc_id
    if not (doc_folder / "metadata.pkl").exists() or not (doc_folder / "chunk_index.faiss").exists():
        raise HTTPException(status_code=500, detail="PDF upload succeeded, but indexing failed.")

    if session_id.strip():
        session_doc_path(session_id).write_text(doc_id, encoding="utf-8")

    return{
        "message" : "PDF indexed successfully",
        "doc_id" : doc_id
    }


@app.post("/review")
async def save_review(review: ReviewPayload):
    reviewer_name = review.reviewer_name.strip() or "none"

    if review.review_action not in {"submitted", "skipped"}:
        raise HTTPException(status_code=400, detail="Invalid review action.")

    invalid_options = [
        option for option in review.selected_options
        if option not in REVIEW_OPTIONS
    ]
    if invalid_options:
        raise HTTPException(status_code=400, detail="Invalid review option selected.")

    review_record = {
        "reviewer_name": reviewer_name,
        "rating": review.rating if review.rating is not None else "none",
        "selected_options": review.selected_options or ["none"],
        "feedback": review.feedback.strip() or "none",
        "doc_id": review.doc_id.strip() or "none",
        "query": review.query.strip() or "none",
        "answer": review.answer.strip() or "none",
        "review_action": review.review_action,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    reviewer_file = REVIEW_FOLDER / f"{sanitize_reviewer_name(reviewer_name)}.jsonl"
    with reviewer_file.open("a", encoding="utf-8") as review_file:
        review_file.write(json.dumps(review_record, ensure_ascii=True) + "\n")

    return {
        "message": "Review saved successfully",
        "reviewer_name": reviewer_name,
    }


@app.get("/session-memory/{session_id}")
async def get_session_memory(session_id: str):
    memory_file = session_memory_path(session_id)
    doc_file = session_doc_path(session_id)
    summary = "No conversation yet."
    doc_id = ""
    if memory_file.exists():
        summary = memory_file.read_text(encoding="utf-8").strip() or summary
    if doc_file.exists():
        doc_id = doc_file.read_text(encoding="utf-8").strip()
    return {
        "session_id": session_id,
        "summary": summary,
        "doc_id": doc_id,
    }


@app.post("/session-memory")
async def save_session_memory(memory: SessionMemoryPayload):
    memory_file = session_memory_path(memory.session_id)
    summary = memory.summary.strip() or "No conversation yet."
    memory_file.write_text(summary[:1000], encoding="utf-8")
    return {
        "message": "Session memory saved successfully",
        "session_id": memory.session_id,
    }


@app.delete("/session-memory/{session_id}")
async def delete_session_memory(session_id: str):
    memory_file = session_memory_path(session_id)
    doc_file = session_doc_path(session_id)
    if memory_file.exists():
        memory_file.unlink()
    if doc_file.exists():
        doc_file.unlink()
    return {
        "message": "Session memory deleted successfully",
        "session_id": session_id,
    }


@app.post("/chat")
async def chat(
    query : str = Form(...),
    doc_id: str = Form(""),
    session_id: str = Form(""),
    session_summary: str = Form("")
):
    async def stream_response():
        resolved_doc_id = doc_id.strip()
        if not resolved_doc_id and session_id.strip():
            doc_file = session_doc_path(session_id)
            if doc_file.exists():
                resolved_doc_id = doc_file.read_text(encoding="utf-8").strip()
        if not resolved_doc_id and asks_about_uploaded_document(query):
            resolved_doc_id = latest_indexed_doc_id()

        async for token in async_final_answer(
            query,
            resolved_doc_id or None,
            session_summary.strip() or None
        ):
            yield token
    
    return StreamingResponse(
        stream_response(),
        media_type="text/plain"
    )
