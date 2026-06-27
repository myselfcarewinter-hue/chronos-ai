# Chronos AI

Autonomous AI productivity platform — backend and frontend.

## Structure

- `backend/` — Python FastAPI backend with multi-agent AI architecture
- `frontend/` — React + Vite frontend with CSS Modules

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env         # Add your API keys
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Note:** Requires Python 3.12. Python 3.14 may fail to build pydantic-core from source.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — API requests proxy to http://localhost:8000

### Environment

Copy `backend/.env.example` → `backend/.env` and set:

| Variable | Description |
|----------|-------------|
| `MONGO_URI` | MongoDB connection string |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |

See [backend/README.md](backend/README.md) for full API documentation and architecture details.
