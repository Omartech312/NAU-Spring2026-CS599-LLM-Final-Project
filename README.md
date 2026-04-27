# Citation-Grounded LLM System

Upload academic PDFs and get AI-powered summaries and Q&A with exact citation grounding from multiple LLM models.

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| npm | 9+ | Frontend dependencies |
| PostgreSQL 16 | with pgvector | Vector search database (must be installed locally) |

---

## Environment Setup

### 1. Clone and Enter Project

```bash
git clone https://github.com/hienngt/NAU-Spring2026-CS599-LLM-Final-Project
cd NAU-Spring2026-CS599-LLM-Final-Project/
```

### 2. Create and Configure Environment Files

You need to configure **two** environment files — one for the backend and one for the frontend.

#### File 1: `backend/.env`

This file holds all backend configuration. Copy the example first:

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and fill in every value:

```env
# Database — change user/password/host if your local Postgres is different
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/citation_llm

# JWT secrets — generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<paste-generated-key>
JWT_SECRET_KEY=<paste-generated-key>

# LLM API Keys — required for Q&A and summarization to work
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
GOOGLE_API_KEY=your-google-key

# Model names (optional — defaults shown)
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-3-5-sonnet-20240620
GOOGLE_MODEL=gemini-1.5-flash

# Embedding (optional)
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# Chunking config in tokens (optional)
CHUNK_SIZE=800
CHUNK_OVERLAP=200

# Number of chunks to retrieve per query (optional)
TOP_K=5
```

#### File 2: `frontend/.env` (optional)

If your backend runs on a host/port other than `localhost:5001`, create this file:

```bash
cp frontend/.env.example frontend/.env 2>/dev/null || touch frontend/.env
```

Then edit `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:5001
```

### 3. Set Up the Database

You must have PostgreSQL 16 with the `pgvector` extension installed locally.

Create the database and enable the vector extension:

```bash
createdb citation_llm
psql -d citation_llm -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

If you prefer a different database name, user, or password, update `DATABASE_URL` in `backend/.env` accordingly.

---

## Installation

### Option A: Automated (Makefile)

```bash
make setup
```

This will:
- Create `backend/venv` and install Python packages
- Install frontend `node_modules`
- Copy `backend/.env.example` to `backend/.env` if it doesn't exist

### Option B: Manual

**Backend:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows
pip install --upgrade pip
pip install -r requirements.txt
```

**Frontend:**

```bash
cd frontend
npm install
```

---

## Running the Application

### Initialize the Database Tables

```bash
make db-init
```

### Start Both Services

```bash
make dev
```

- Backend API: http://localhost:5001
- Frontend UI: http://localhost:3000

### Start Individually

```bash
# Backend only
make dev-backend

# Frontend only
make dev-frontend
```

---

## Makefile Quick Reference

| Target | Description |
|--------|-------------|
| `make setup` | Install all dependencies |
| `make dev` | Start backend + frontend |
| `make dev-backend` | Start Flask backend only |
| `make dev-frontend` | Start Vite frontend only |
| `make db-init` | Create database tables |
| `make db-reset` | Drop and recreate tables (deletes data) |
| `make test` | Run all tests |
| `make test-backend` | Run backend tests |
| `make status` | Check if services are running |
| `make info` | Print environment info and package versions |
| `make clean` | Remove build artifacts |
| `make clean-deep` | Remove node_modules, venv, caches |

---

## Project Structure

```
citation-llm/
├── backend/
│   ├── app/                  # Flask application (routes, models, services)
│   ├── uploads/              # Uploaded PDF files
│   ├── tests/                # pytest integration tests
│   ├── venv/                 # Python virtual environment
│   ├── requirements.txt      # Python dependencies
│   ├── run.py                # Backend entry point
│   ├── .env.example           # Template — copy to .env and fill in
│   └── .env                   # YOUR BACKEND CONFIG — edit this file
├── frontend/
│   ├── src/                  # React components and pages
│   ├── dist/                 # Production build output
│   ├── node_modules/          # Node dependencies
│   ├── package.json          # Node dependencies
│   ├── .env                   # YOUR FRONTEND CONFIG — edit this file (optional)
│   └── .env.example           # Template (optional)
├── docker-compose.test.yml   # Docker setup (not used in this guide)
├── setup.sh                  # Legacy setup script
└── Makefile                  # Project task runner
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.x, SQLAlchemy 2.x |
| Database | PostgreSQL 16 + pgvector |
| Frontend | React 18, Vite 5, Tailwind CSS 3 |
| State | Zustand |
| LLMs | OpenAI GPT-4o, Anthropic Claude, Google Gemini |
| Embeddings | OpenAI text-embedding-3-small |

---

## Troubleshooting

### `ModuleNotFoundError` when starting backend

Your virtual environment is not activated:

```bash
cd backend && source venv/bin/activate
```

### PostgreSQL connection refused

Make sure your local PostgreSQL server is running and that `DATABASE_URL` in `backend/.env` matches your setup.

### Q&A and summarization return errors

The LLM API keys in `backend/.env` are missing or invalid. Add `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GOOGLE_API_KEY`.

### Frontend API requests fail

Check that the backend is running on the port specified in `frontend/.env` (default: `http://localhost:5001`).
