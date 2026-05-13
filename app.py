import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "Frontend"
SIMPLE_RAG_DIR = PROJECT_ROOT / "simple_rag"

os.chdir(PROJECT_ROOT)

if str(SIMPLE_RAG_DIR) not in sys.path:
    sys.path.insert(0, str(SIMPLE_RAG_DIR))

from simple_rag.database.ingest_db import ingest_pdf
from simple_rag.main import GENERATE

app = FastAPI()

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    #in production we have to replace "*" with specific frontend url
)

rag = GENERATE()

UPLOAD_FOLDER = PROJECT_ROOT / "uploads"
REVIEW_FOLDER = PROJECT_ROOT / "reviews"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REVIEW_FOLDER, exist_ok=True)

REVIEW_OPTIONS = {
    "accurate answer",
    "first response",
    "followed query correctly",
}


class ReviewPayload(BaseModel):
    reviewer_name: str
    rating: int = Field(ge=1, le=5)
    selected_options: List[str] = Field(default_factory=list)
    feedback: str = ""
    doc_id: str
    query: str
    answer: str


def sanitize_reviewer_name(reviewer_name: str) -> str:
    sanitized_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", reviewer_name.strip().lower())
    return sanitized_name.strip("_") or "reviewer"

@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.post("/upload")
async def upload_pdf(file:UploadFile = File(...)):
    safe_filename = Path(file.filename).name
    file_path = UPLOAD_FOLDER / safe_filename

    with open(file_path, 'wb') as f:
        f.write(await file.read())

    doc_id = file_path.stem

    ingest_pdf(file_path, doc_id)

    return{
        "message" : "PDF indexed successfully",
        "doc_id" : doc_id
    }


@app.post("/review")
async def save_review(review: ReviewPayload):
    reviewer_name = review.reviewer_name.strip()
    if not reviewer_name:
        raise HTTPException(status_code=400, detail="Reviewer name is required.")

    invalid_options = [
        option for option in review.selected_options
        if option not in REVIEW_OPTIONS
    ]
    if invalid_options:
        raise HTTPException(status_code=400, detail="Invalid review option selected.")

    review_record = {
        "reviewer_name": reviewer_name,
        "rating": review.rating,
        "selected_options": review.selected_options,
        "feedback": review.feedback.strip(),
        "doc_id": review.doc_id.strip(),
        "query": review.query.strip(),
        "answer": review.answer.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if not review_record["query"] or not review_record["answer"]:
        raise HTTPException(status_code=400, detail="Query and answer are required for reviews.")

    reviewer_file = REVIEW_FOLDER / f"{sanitize_reviewer_name(reviewer_name)}.jsonl"
    with reviewer_file.open("a", encoding="utf-8") as review_file:
        review_file.write(json.dumps(review_record, ensure_ascii=True) + "\n")

    return {
        "message": "Review saved successfully",
        "reviewer_name": reviewer_name,
    }

@app.post("/chat")

async def chat(
    query : str = Form(...),
    doc_id: str = Form(...)
):
    def stream_response():
        for token in rag.generate(query, doc_id):
            yield token
    
    return StreamingResponse(
        stream_response(),
        media_type="text/plain"
    )
