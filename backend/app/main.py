from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.services.session_service import SessionService
from app.services.stt_service import STTService
from app.routes import audio, interpret, execute, session


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = settings
    app.state.session_service = SessionService(ttl_minutes=settings.session_ttl_minutes)
    app.state.stt_service = STTService(
        model_size=settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
    yield
    # Cleanup
    if hasattr(app.state, "stt_service"):
        del app.state.stt_service


app = FastAPI(title="ClickUp Voice Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audio.router, prefix="/api")
app.include_router(interpret.router, prefix="/api")
app.include_router(execute.router, prefix="/api")
app.include_router(session.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
