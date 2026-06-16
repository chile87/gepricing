from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend/ is importable when starting from backend/api with:
# uvicorn main:app --reload
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.routers.dashboard import router as dashboard_router

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

app.include_router(dashboard_router, prefix="/api/v1")
