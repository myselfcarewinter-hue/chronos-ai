"""Verification script for Chronos AI backend."""
import sys
import asyncio

def check_settings():
    from app.config.settings import get_settings
    s = get_settings()
    print(f"[Settings] {s.app_name} v{s.app_version}")
    print(f"  Mongo: {s.mongo_uri}/{s.mongo_db_name}")
    print(f"  Gemini model: {s.gemini_model}")
    print(f"  Gemini key set: {bool(s.gemini_api_key and s.gemini_api_key != 'your-gemini-api-key-here')}")
    print(f"  OAuth client_id set: {bool(s.google_client_id and s.google_client_id != 'your-google-client-id')}")
    print(f"  JWT secret: {'custom' if s.jwt_secret_key != 'change-me-in-production' else 'DEFAULT (ok for dev)'}")
    print(f"  Environment: {s.environment}")
    print(f"  CORS: {s.cors_origin_list}")
    return s

def check_app():
    from app.main import app
    routes = list(app.openapi()["paths"].keys())
    print(f"\n[FastAPI] {len(routes)} routes registered:")
    for r in sorted(routes):
        print(f"  {r}")
    return app

def check_gemini(settings):
    from app.services.gemini_service import GeminiService
    svc = GeminiService(settings)
    print(f"\n[Gemini] Available: {svc.is_available}")
    print(f"  Model: {settings.gemini_model}")
    return svc

def check_scheduler():
    from app.scheduler import scheduler, setup_scheduler
    setup_scheduler()
    jobs = scheduler.get_jobs()
    print(f"\n[Scheduler] {len(jobs)} jobs configured:")
    for j in jobs:
        print(f"  {j.id}: {j.name}")
    return scheduler

async def check_mongo(settings):
    from app.database.db import Database
    try:
        await Database.connect(settings)
        db = Database.get_db()
        collections = await db.list_collection_names()
        print(f"\n[MongoDB] Connected to '{settings.mongo_db_name}'")
        print(f"  Collections: {collections or '(empty - will be created on first use)'}")
        await Database.disconnect()
        return True
    except Exception as e:
        print(f"\n[MongoDB] Connection FAILED: {e}")
        return False

def check_imports():
    print("\n[Imports] Checking all modules...")
    modules = [
        "app.agents",
        "app.agents.intake_agent",
        "app.agents.risk_agent",
        "app.agents.priority_agent",
        "app.agents.planner_agent",
        "app.agents.memory_agent",
        "app.agents.guardian_agent",
        "app.agents.rescue_agent",
        "app.agents.reflection_agent",
        "app.services",
        "app.services.gemini_service",
        "app.services.oauth_service",
        "app.services.calendar_service",
        "app.services.notification_service",
        "app.services.gamification_service",
        "app.services.task_pipeline_service",
        "app.repositories",
        "app.routes",
        "app.routes.schemas",
        "app.middleware.dependencies",
        "app.middleware.error_handler",
        "app.database.db",
        "app.database.models",
        "app.utils.helpers",
        "app.utils.exceptions",
    ]
    failed = []
    for mod in modules:
        try:
            __import__(mod)
        except Exception as e:
            failed.append((mod, str(e)))
    if failed:
        for mod, err in failed:
            print(f"  FAIL: {mod} -> {err}")
    else:
        print(f"  All {len(modules)} modules import successfully")
    return len(failed) == 0

async def main():
    print("=" * 60)
    print("CHRONOS AI — BACKEND VERIFICATION")
    print("=" * 60)

    s = check_settings()
    check_app()
    check_gemini(s)
    check_scheduler()
    imports_ok = check_imports()
    mongo_ok = await check_mongo(s)

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"  Settings:   OK")
    print(f"  FastAPI:    OK")
    print(f"  Gemini:     {'OK' if s.gemini_api_key and s.gemini_api_key != 'your-gemini-api-key-here' else 'NO KEY (fallback mode)'}")
    print(f"  Scheduler:  OK")
    print(f"  Imports:    {'OK' if imports_ok else 'FAILED'}")
    print(f"  MongoDB:    {'OK' if mongo_ok else 'FAILED (is mongod running?)'}")

if __name__ == "__main__":
    asyncio.run(main())
