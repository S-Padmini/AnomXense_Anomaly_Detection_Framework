import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH, override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.phase1 import router as phase1_router
from app.api.phase2 import router as phase2_router
from app.api.phase3 import router as phase3_router
from app.api.phase4 import router as phase4_router
from app.api.phase5 import router as phase5_router
from app.api.phase6 import router as phase6_router
from app.api.statistical import router as statistical_router
from app.api.automatic_discovery import router as automatic_discovery_router

app = FastAPI(
    title="ANOMALY",
    description="Intelligent and conversational anomaly detection platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://huge-cargo-michel-variation.trycloudflare.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(phase1_router)
app.include_router(phase2_router)
app.include_router(phase3_router)
app.include_router(phase4_router)
app.include_router(phase5_router)
app.include_router(phase6_router)
app.include_router(statistical_router)
app.include_router(automatic_discovery_router)


@app.get("/")
async def root():
    return {
        "application": "ANOMALY",
        "status": "running",
        "version": "1.0.0",
        "message": "Intelligent anomaly detection platform is running.",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}

