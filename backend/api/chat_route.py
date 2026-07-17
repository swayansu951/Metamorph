from fastapi import APIRouter, Form
from fastapi.responses import StreamingResponse

from backend.api.shared import (
    asks_about_uploaded_document,
    latest_indexed_doc_id,
    session_doc_path,
)
from backend.llm_services.query_router import async_final_answer_stream

router = APIRouter()


@router.post("/chat")
async def chat(
    query: str = Form(...),
    doc_id: str = Form(""),
    session_id: str = Form(""),
    session_summary: str = Form(""),
):
    async def stream_response():
        resolved_doc_id = doc_id.strip()
        if not resolved_doc_id and session_id.strip():
            doc_file = session_doc_path(session_id)
            if doc_file.exists():
                resolved_doc_id = doc_file.read_text(encoding="utf-8").strip()
        if not resolved_doc_id and asks_about_uploaded_document(query):
            resolved_doc_id = latest_indexed_doc_id()

        async for token in async_final_answer_stream(
            query,
            resolved_doc_id or None,
            session_summary.strip() or None,
        ):
            yield token

    return StreamingResponse(
        stream_response(),
        media_type="text/plain",
    )
