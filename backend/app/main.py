from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.phase1 import router as phase1_router
from app.api.phase2 import router as phase2_router
from app.api.phase3 import router as phase3_router

load_dotenv()

app = FastAPI(
    title="Intelligent Anomaly Insights API",
    version="3.0.0",
    description="Dynamic Phase 1–3 dataset analysis, selection, preprocessing and statistical analysis.",
)

origins = [
    x.strip() for x in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:5174"
    ).split(",") if x.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(phase1_router)
app.include_router(phase2_router)
app.include_router(phase3_router)


@app.get("/")
def root():
    return {"service": "Intelligent Anomaly Insights API", "status": "ok",
            "version": app.version, "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}
