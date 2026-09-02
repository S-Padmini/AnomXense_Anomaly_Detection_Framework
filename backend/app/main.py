from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.phase1 import router as phase1_router
from app.api.phase2 import router as phase2_router
from app.api.phase3 import router as phase3_router
from app.api.phase4 import router as phase4_router
from app.api.phase5 import router as phase5_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Intelligent Anomaly Insights",
    version="4.0.0",
    description=(
        "Intelligent anomaly detection framework "
        "with objective understanding and model recommendation."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(phase1_router)
app.include_router(phase2_router)
app.include_router(phase3_router)
app.include_router(phase4_router)
app.include_router(phase5_router)

@app.get("/")
def root():
    return {
        "name": "Intelligent Anomaly Insights",
        "version": "4.0.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }