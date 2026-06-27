# Chronos AI

**Autonomous AI productivity companion** that understands tasks, predicts deadline risks, intelligently plans work, continuously monitors progress, adapts schedules, and motivates users through gamification.

## Architecture

```
User Input (Natural Language)
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                   Task Pipeline Service                  │
│                                                         │
│  Intake → Risk → Priority → Planner → Memory → Store   │
└─────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
   MongoDB Store              Google Calendar Sync
        │
        ▼
┌──────────────────┐    ┌──────────────────┐
│  Guardian Agent  │    │ Reflection Agent │
│  (Every Hour)    │    │  (Every Night)   │
│       │          │    └──────────────────┘
│       ▼          │
│  Rescue Agent    │
└──────────────────┘
```

### Design Principles

- **Layered Architecture**: Routes → Services/Agents → Repositories → Database
- **Multi-Agent System**: 8 independent agent classes, each with a single responsibility
- **Single Gemini Client**: All AI requests flow through `services/gemini_service.py`
- **Dependency Injection**: FastAPI `Depends()` wires all components
- **Repository Pattern**: MongoDB access isolated from business logic
- **Async Everywhere**: Motor for MongoDB, async agents and services
- **Graceful Degradation**: Rule-based fallbacks when Gemini API is unavailable

### Agent Pipeline

| Agent | Responsibility | Trigger |
|-------|---------------|---------|
| **Intake** | Parse natural language → structured task | Task creation |
| **Risk** | Predict failure probability | Task creation |
| **Priority** | Calculate urgency/importance score | Task creation |
| **Planner** | Break into subtasks, schedule sessions, create calendar events | Task creation |
| **Guardian** | Monitor deadlines, overdue work, high-risk tasks | Hourly (APScheduler) |
| **Rescue** | Rebuild schedule, suggest recovery strategy | Triggered by Guardian |
| **Memory** | Learn user patterns, update profile | Task creation/completion |
| **Reflection** | Daily/weekly summaries, productivity insights | Nightly (APScheduler) |

## Tech Stack

- **Python 3.12** + **FastAPI** (async)
- **MongoDB** via **Motor**
- **Google Gemini** for AI
- **Google Calendar API** + **Google OAuth**
- **APScheduler** for background jobs
- **Pydantic** for validation

## Quick Start

### Prerequisites

- Python 3.12+
- MongoDB running locally (or a remote URI)
- Google Cloud project with Gemini API, Calendar API, and OAuth credentials

### Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
# Edit .env with your API keys
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `MONGO_URI` | MongoDB connection string |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `JWT_SECRET_KEY` | Secret for JWT session tokens |

### Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

### Run Tests

```bash
pytest tests/ -v
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/login` | Get Google OAuth URL |
| `GET` | `/auth/callback` | OAuth callback → JWT token |
| `POST` | `/tasks/create` | Create task via AI pipeline |
| `GET` | `/tasks` | List user tasks |
| `GET` | `/tasks/{id}` | Get single task |
| `PUT` | `/tasks/{id}/complete` | Complete task, award XP |
| `GET` | `/dashboard` | Full productivity dashboard |
| `POST` | `/chat` | Chat with AI assistant |
| `GET` | `/health` | Health check |

### Example: Create a Task

```bash
curl -X POST http://localhost:8000/tasks/create \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": "I have an ML assignment due Friday night."}'
```

The pipeline will automatically:
1. Extract title, deadline, category, difficulty, estimated hours
2. Predict failure risk based on calendar availability
3. Calculate priority score
4. Generate subtasks and work sessions
5. Create Google Calendar events
6. Store everything in MongoDB

## Project Structure

```
backend/
├── app/
│   ├── agents/           # 8 independent AI agents
│   │   ├── intake_agent.py
│   │   ├── risk_agent.py
│   │   ├── priority_agent.py
│   │   ├── planner_agent.py
│   │   ├── guardian_agent.py
│   │   ├── rescue_agent.py
│   │   ├── memory_agent.py
│   │   └── reflection_agent.py
│   ├── services/         # Shared services
│   │   ├── gemini_service.py    # Single Gemini client
│   │   ├── calendar_service.py
│   │   ├── oauth_service.py
│   │   ├── notification_service.py
│   │   ├── gamification_service.py
│   │   └── task_pipeline_service.py
│   ├── database/
│   │   ├── db.py         # Motor connection
│   │   └── models.py     # Pydantic document models
│   ├── repositories/     # MongoDB repositories
│   ├── routes/           # FastAPI route handlers
│   ├── middleware/       # Auth + error handling
│   ├── config/           # Settings from .env
│   ├── utils/            # Helpers + exceptions
│   ├── scheduler.py      # APScheduler jobs
│   └── main.py           # Application entry point
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT
