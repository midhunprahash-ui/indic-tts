from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.models import router as model_router
from app.api.routes.tts import router as tts_router
from app.infrastructure.config.settings import settings
from app.infrastructure.logging import configure_logging

configure_logging(settings.log_level)

app = FastAPI(title="Tanglish TTS Playground API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(model_router)
app.include_router(tts_router)
