"""MEDORA OT — FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from config import settings
from database import init_db
from routes import auth, notes, patients, speech, consultations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medora")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MEDORA OT starting — initialising database…")
    await init_db()
    logger.info("Database ready.")
    yield
    logger.info("MEDORA OT shutting down.")


app = FastAPI(
    title="MEDORA OT Documentation API",
    description=(
        "Speech-assisted, structured and legally defensible operative documentation system. "
        "ASR: Deepgram | LLM: Gemini | TTS: Sarvam"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins() + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(patients.router)
app.include_router(speech.router)
app.include_router(consultations.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "MEDORA OT", "version": "1.0.0"}


# ── Serve Frontend (SPA) ──────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        index = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return {"detail": "Frontend not built yet"}
