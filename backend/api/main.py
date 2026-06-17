from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from sqlalchemy import text

# Ensure backend/ is importable when starting from backend/api with:
# uvicorn main:app --reload
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.routers.dashboard import router as dashboard_router
from app.routers.pricing import router as pricing_router
from app.routers.approvals import router as approvals_router
from app.core.db import engine
from app.services.dashboard_service import check_database_connection

app = FastAPI(
    title="GePricing API",
    description="Rule-based Pricing Engine — Admin API",
    version="0.1.0",
)

# ── CORS Configuration ────────────────────────────────────────────────────────
# Allow frontend (React on :5173) to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local Vite dev server
        "http://127.0.0.1:5173",  # Alternative localhost
        "http://localhost:5174",  # Vite auto-fallback when 5173 is occupied
        "http://127.0.0.1:5174",  # Alternative localhost
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)


@app.on_event("startup")
def startup() -> None:
    with Session(engine) as session:
        check_database_connection(session)
        session.exec(text("SELECT 1"))


app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(pricing_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
