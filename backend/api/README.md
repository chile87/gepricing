# Backend API Run Guide

## Run Backend (Recommended)

From repository root:

```bash
cd backend/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

If you do not want to activate the virtual environment manually:

```bash
cd backend/api && .venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Quick Check

- Swagger UI: `http://127.0.0.1:8000/docs`
- Example endpoint check:

```bash
curl http://127.0.0.1:8000/api/v1/dashboard/summary
```

## Why Previous Command Failed

- `python api/main.py` is not the correct way to run a FastAPI app.
- FastAPI app should be served by Uvicorn (ASGI server).
- Your system Python may not have `uvicorn`; use `.venv` in `backend/api`.
