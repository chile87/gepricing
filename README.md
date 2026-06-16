# GePricing — Rule-based Pricing Engine

> An e-commerce pricing system that crawls competitor prices, applies configurable business rules, and surfaces price recommendations through an admin UI with an approval workflow.

---

## Architecture Overview

```
                         LOCAL DEVELOPMENT (No Docker)
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  ┌──────────────┐         REST/JSON     ┌──────────────────────┐  │
│  │   Frontend   │◄──────────────────────►│    FastAPI (API)     │  │
│  │ React + TS   │   http://localhost:    │  :8000               │  │
│  │ TailwindCSS  │   5173                 │  Uvicorn (reload)    │  │
│  │   :5173      │                        │  CORS enabled        │  │
│  └──────────────┘                        │                      │  │
│   (npm run dev)                          │  Routers:            │  │
│                                          │  /skus, /pricing,    │  │
│                                          │  /approvals          │  │
│                                          └──────────┬───────────┘  │
│                                                     │               │
│                        ┌────────────────────────────┼──────────┐   │
│                        │                            │          │   │
│                        ▼                            ▼          │   │
│        ┌────────────────────────┐    ┌──────────────────────┐│   │
│        │  Pricing Engine        │    │  Redis (localhost)   ││   │
│        │  (Python module)       │    │  :6379               ││   │
│        │                        │    │  Cache price_recs    ││   │
│        │  Rules:                │    │  TTL: 5 min          ││   │
│        │  • MarginRule          │    └──────────────────────┘│   │
│        │  • CompetitorRule      │                            │   │
│        │  • InventoryRule       │                            │   │
│        │  • GuardrailsEngine    │                            │   │
│        └────────┬───────────────┘                            │   │
│                 │                                            │   │
│                 ▼                                            │   │
│    ┌────────────────────────┐    ┌────────────────────────┐ │   │
│    │   Crawler              │───►│  PostgreSQL (localhost)│ │   │
│    │  (Python process)      │    │  :5432                 │ │   │
│    │                        │    │  DB: gepricing_db      │ │   │
│    │  Runs every 30 min:    │    │  Tables:               │ │   │
│    │  • TGDD                │    │  • skus                │ │   │
│    │  • CellphoneS          │    │  • competitor_prices   │ │   │
│    │  • HoangHa             │    │  • price_recommendations
│    │  • ERP/POS data        │    │  • approval_log        │ │   │
│    └────────────────────────┘    └────────────────────────┘ │   │
│                                                              │   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Local Development Prerequisites

Before starting, ensure you have installed:

1. **Python 3.11+** → `python --version`
2. **Node.js 20+** → `node --version`
3. **PostgreSQL 16+** → `psql --version`
4. **Redis** → `redis-cli --version`

If using macOS with Homebrew:
```bash
brew install python@3.11
brew install node
brew install postgresql
brew install redis
```

---

## Step-by-Step Setup & Local Development

### 1️⃣ Start PostgreSQL & Redis (In Background)

#### Start PostgreSQL
```bash
# macOS (Homebrew)
brew services start postgresql

# Or manually:
postgres -D /usr/local/var/postgres &
```

#### Start Redis
```bash
# macOS (Homebrew)
brew services start redis

# Or manually:
redis-server &
```

**Verify connections:**
```bash
psql -d postgres -c "SELECT version();"
redis-cli ping  # Should print: PONG
```

---

### 2️⃣ Configure Environment Variables

```bash
# In the project root
cp .env.example .env
```

Edit `.env` and update these for local PostgreSQL/Redis:
```bash
# ── PostgreSQL ─────────────────────────
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres          # or your PostgreSQL password
POSTGRES_DB=gepricing_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/gepricing_db
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres@localhost:5432/gepricing_db

# ── Redis ──────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

# ── API ────────────────────────────────
SECRET_KEY=your-secret-key-change-this-in-production
ENVIRONMENT=development
API_PORT=8000

# ── Frontend ───────────────────────────
VITE_API_URL=http://localhost:8000
```

---

### 3️⃣ Create PostgreSQL Database

```bash
# Connect to PostgreSQL as superuser
psql -U postgres -h localhost

# Inside psql:
CREATE DATABASE gepricing_db;
\q
```

Verify the database was created:
```bash
psql -U postgres -d gepricing_db -c "SELECT 1;"
```

---

### 4️⃣ Backend Setup — Python Virtual Environment

Open **Terminal #1** for the FastAPI server:

```bash
cd backend/api

# Create virtual environment
python3.11 -m venv .venv

# Activate it
source .venv/bin/activate          # macOS / Linux
# OR on Windows:
# .venv\Scripts\activate

# Upgrade pip & install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
pip list | grep -E "fastapi|sqlmodel|alembic"
```

---

### 5️⃣ Run Database Migrations

Still in **Terminal #1**:

```bash
# Make sure you're in backend/api with venv activated
cd ../..  # Back to project root
cd backend

# Run Alembic migrations (creates tables in PostgreSQL)
alembic upgrade head

# Verify tables were created
psql -U postgres -d gepricing_db -c "\dt"
# Should show: skus, competitor_prices, price_recommendations, approval_log
```

---

### 6️⃣ Start FastAPI Server

Still in **Terminal #1**, from `backend/api` with venv activated:

```bash
cd backend/api
source .venv/bin/activate  # if not already activated

# Start the development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Output should show:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started server process [XXXX]
# INFO:     Waiting for application startup.
```

**Test the API is running:**
- Open browser: `http://localhost:8000/docs` (Swagger UI)
- Or: `http://localhost:8000/redoc` (ReDoc)

---

### 7️⃣ Frontend Setup — Node.js

Open **Terminal #2** for the frontend:

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev

# Output should show:
# Local:   http://localhost:5173/
# press h + enter to show help
```

**Open in browser:** `http://localhost:5173`

---

### 8️⃣ Crawler Setup — Background Python Process

Open **Terminal #3** for the crawler:

```bash
cd backend/crawler

# Create/activate virtual environment (same as API)
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the crawler
python main.py

# Crawler will run and fetch competitor prices every 30 minutes
```

---

## Summary: Terminal Layout

When everything is running, you should have **3 terminals open**:

| Terminal | Command                              | Port | Status Indicator                  |
|----------|--------------------------------------|------|-----------------------------------|
| #1       | `cd backend/api && source .venv/bin/activate && uvicorn main:app --reload` | 8000 | `http://0.0.0.0:8000 (Press CTRL+C to quit)` |
| #2       | `cd frontend && npm run dev`         | 5173 | `Local: http://localhost:5173/`   |
| #3       | `cd backend/crawler && source .venv/bin/activate && python main.py` | —    | `Crawler running, next sync: XX:XX` |

---

## Useful Commands

### Stop All Processes
```bash
# Terminal #1, #2, #3: Press CTRL+C

# Stop background PostgreSQL & Redis
brew services stop postgresql
brew services stop redis
```

### Reset Database
```bash
# Stop all services first
brew services stop postgresql

# Drop and recreate database
psql -U postgres -c "DROP DATABASE IF EXISTS gepricing_db;"
psql -U postgres -c "CREATE DATABASE gepricing_db;"

# Run migrations again
cd backend
alembic upgrade head

# Restart PostgreSQL
brew services start postgresql
```

### Access PostgreSQL Directly
```bash
psql -U postgres -d gepricing_db

# Useful queries:
\dt                      # List all tables
SELECT COUNT(*) FROM skus;
SELECT * FROM price_recommendations LIMIT 5;
\q                       # Exit
```

### Check Redis
```bash
redis-cli
> PING
> KEYS *
> GET gepricing:recommendation:sku123
> FLUSHDB              # Clear cache
> EXIT
```

### View API Logs
```bash
# Terminal #1 shows Uvicorn logs in real-time
# Look for: INFO, WARNING, ERROR messages
```

---

## File Structure

```
gepricing/
├── .env                          ← Your local config (git-ignored)
├── .env.example                  ← Template for .env
├── backend/
│   ├── api/
│   │   ├── .venv/                ← Python venv (git-ignored)
│   │   ├── main.py               ← FastAPI entry point
│   │   ├── requirements.txt
│   │   └── app/                  ← Router & service modules
│   ├── crawler/
│   │   ├── .venv/                ← Crawler venv (git-ignored)
│   │   ├── main.py               ← Crawler entry point
│   │   ├── requirements.txt
│   │   └── scrapers/             ← TGDD, CellphoneS, HoangHa
│   ├── engine/                   ← Pricing rules
│   ├── models/                   ← SQLModel schemas
│   └── alembic/                  ← Database migrations
├── frontend/                     ← React + TypeScript
│   ├── node_modules/             ← npm dependencies (git-ignored)
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
└── README.md                     ← This file
```

---

## Troubleshooting

### PostgreSQL Connection Error
```
Error: could not connect to server: Connection refused
```
**Fix:**
```bash
# Ensure PostgreSQL is running
brew services list
brew services start postgresql

# Or check if it's already running on port 5432
lsof -i :5432
```

### Redis Connection Error
```
Error: Error 111 connecting to localhost:6379
```
**Fix:**
```bash
# Start Redis
brew services start redis

# Or manually:
redis-server
```

### Port Already in Use
```
Address already in use: ('127.0.0.1', 8000)
```
**Fix:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill it (replace PID with actual process ID)
kill -9 PID

# Or use a different port:
uvicorn main:app --reload --port 8001
```

### ModuleNotFoundError in Crawler
```
ModuleNotFoundError: No module named 'models'
```
**Fix:**
```bash
# Ensure the shared models are installed
cd backend/crawler
pip install -e ../models
```

---

## Next Steps

1. ✅ **Local Dev Setup** — Complete (you're here)
2. 🎯 **Implement Backend** — Fill in API routers, services, and pricing engine
3. 🎯 **Implement Frontend** — Bind React components to API endpoints
4. 🎯 **Integration Testing** — Test all three services communicate
5. 🎯 **Docker Deployment** — Use `docker-compose.yml` for production

---

## Tech Stack

| Layer     | Technology                                         |
|-----------|----------------------------------------------------|
| Frontend  | React 18, TypeScript, Vite, TailwindCSS            |
| API       | FastAPI, SQLModel, Alembic, asyncpg, Pydantic v2   |
| Crawler   | httpx, BeautifulSoup4, APScheduler                 |
| Database  | PostgreSQL 16 (localhost)                          |
| Cache     | Redis 7 (localhost)                                |
| Package Manager | pip (Python), npm (Node.js)                    |
