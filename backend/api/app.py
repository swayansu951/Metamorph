import asyncio
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.chat_route import router as chat_router
from backend.api.shared import FRONTEND_DIR
from backend.api.upload_route import router as upload_router

app = FastAPI()

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


app.include_router(upload_router)
app.include_router(chat_router)
