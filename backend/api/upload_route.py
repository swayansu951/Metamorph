import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.api.shared import (
    REVIEW_FOLDER,
    REVIEW_OPTIONS,
    ROOT_DIR,
    UPLOAD_FOLDER,
    sanitize_reviewer_name,
    session_doc_path,
    session_memory_path,
)
from backend.retrievals.simple_rag.database.ingest_db import ingest_pdf

router = APIRouter()


class SessionMemoryPayload(BaseModel):
    session_id: str
    summary: str = "No conversation yet."


class ReviewPayload(BaseModel):
    reviewer_name: str = "none"
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    selected_options: List[str] = Field(default_factory=list)
    feedback: str = "none"
    doc_id: str = "none"
    query: str = "none"
    answer: str = "none"
    review_action: str = "submitted"


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    session_id: str = Form(""),
):
    safe_filename = Path(file.filename).name
    file_path = UPLOAD_FOLDER / safe_filename

    with file_path.open("wb") as uploaded_file:
        uploaded_file.write(await file.read())

    doc_id = file_path.stem
    ingest_pdf(file_path, doc_id)

    doc_folder = ROOT_DIR / "rag_db" / "documents" / doc_id
    if not (doc_folder / "metadata.pkl").exists() or not (doc_folder / "chunk_index.faiss").exists():
        raise HTTPException(status_code=500, detail="PDF upload succeeded, but indexing failed.")

    if session_id.strip():
        session_doc_path(session_id).write_text(doc_id, encoding="utf-8")

    return {
        "message": "PDF indexed successfully",
        "doc_id": doc_id,
    }


@router.post("/review")
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


@router.get("/session-memory/{session_id}")
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


@router.post("/session-memory")
async def save_session_memory(memory: SessionMemoryPayload):
    memory_file = session_memory_path(memory.session_id)
    summary = memory.summary.strip() or "No conversation yet."
    memory_file.write_text(summary[:1000], encoding="utf-8")
    return {
        "message": "Session memory saved successfully",
        "session_id": memory.session_id,
    }


@router.delete("/session-memory/{session_id}")
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
