import os
import sys
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

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
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
