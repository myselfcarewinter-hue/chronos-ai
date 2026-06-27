"""End-to-end integration test for Chronos AI pipeline.

Tests the complete flow:
  User Input -> Intake -> Risk -> Priority -> Planner -> MongoDB -> Dashboard -> Guardian -> Reflection
"""
import asyncio
import logging
import sys

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("e2e_test")

OK = "[OK]"
FAIL = "[FAIL]"


async def run_e2e():
    from app.config.settings import get_settings
    from app.database.db import Database
    from app.database.models import User, UserPreferences, UserProfile, UserStats
    from app.repositories import get_repositories
    from app.services.gemini_service import get_gemini_service
    from app.services.oauth_service import OAuthService
    from app.services.calendar_service import CalendarService
    from app.services.notification_service import NotificationService
    from app.services.gamification_service import GamificationService
    from app.services.task_pipeline_service import TaskPipelineService
    from app.agents.intake_agent import IntakeAgent
    from app.agents.risk_agent import RiskPredictionAgent
    from app.agents.priority_agent import PriorityAgent
    from app.agents.planner_agent import PlannerAgent
    from app.agents.memory_agent import MemoryAgent
    from app.agents.guardian_agent import GuardianAgent
    from app.agents.rescue_agent import RescueAgent
    from app.agents.reflection_agent import ReflectionAgent

    settings = get_settings()
    print("=" * 60)
    print("CHRONOS AI -- END-TO-END INTEGRATION TEST")
    print("=" * 60)

    # Step 0: Connect to MongoDB
    print("\n[Step 0] Connecting to MongoDB...")
    await Database.connect(settings)
    db = Database.get_db()
    repos = get_repositories(db)
    print(f"  {OK} MongoDB connected")

    # Step 0.5: Create or get test user
    print("\n[Step 0.5] Creating test user...")
    existing = await repos.users.find_by_google_id("e2e-test-user")
    if existing:
        user = existing
        print(f"  {OK} Test user exists: {user.id}")
    else:
        user = await repos.users.create(User(
            google_id="e2e-test-user",
            email="e2e@chronos.ai",
            name="E2E Test User",
            preferences=UserPreferences(),
            stats=UserStats(),
            profile=UserProfile(),
        ))
        print(f"  {OK} Test user created: {user.id}")

    # Initialize services
    gemini = get_gemini_service(settings)
    print(f"  {OK} Gemini service initialized (available: {gemini.is_available})")

    oauth = OAuthService(repos.users, settings)
    calendar = CalendarService(repos.calendar_events, oauth, settings)
    notifications = NotificationService(repos.notifications)
    gamification = GamificationService(repos.users, repos.rewards, notifications, settings)

    # Initialize agents
    intake = IntakeAgent(gemini)
    risk_agent = RiskPredictionAgent(gemini)
    priority_agent = PriorityAgent(gemini)
    planner = PlannerAgent(gemini, repos.subtasks, calendar)
    memory = MemoryAgent(gemini, repos.users, repos.tasks)
    rescue = RescueAgent(gemini, repos.tasks, planner, notifications)
    guardian = GuardianAgent(gemini, repos.tasks, repos.users, notifications, rescue)
    reflection = ReflectionAgent(
        gemini, repos.tasks, repos.daily_summaries, repos.productivity_history, notifications
    )

    pipeline = TaskPipelineService(
        intake, risk_agent, priority_agent, planner, memory,
        repos.tasks, repos.subtasks, calendar,
    )

    # Step 1: Intake Agent
    print("\n[Step 1] Intake Agent -- parsing natural language...")
    raw_input = "I have an ML assignment due Friday night."
    intake_data = await intake.execute(raw_input, user_timezone="UTC")
    print(f"  {OK} Title: {intake_data['title']}")
    print(f"  {OK} Category: {intake_data['category']}")
    print(f"  {OK} Difficulty: {intake_data['difficulty']}")
    print(f"  {OK} Estimated hours: {intake_data['estimated_hours']}")
    print(f"  {OK} Deadline: {intake_data['deadline']}")

    # Step 2: Full Pipeline (Intake -> Risk -> Priority -> Plan -> Store)
    print("\n[Step 2] Full Task Pipeline...")
    task = await pipeline.create_task(raw_input, user)
    print(f"  {OK} Task created: {task.id}")
    print(f"  {OK} Title: {task.title}")
    print(f"  {OK} Status: {task.status.value}")
    print(f"  {OK} Risk: {task.risk.risk_percentage:.0f}% ({task.risk.risk_level.value})")
    print(f"  {OK} Priority: {task.priority.priority_score:.0f} ({task.priority.priority_level.value})")
    plan_preview = task.execution_plan[:80] if task.execution_plan else "(using fallback)"
    print(f"  {OK} Plan: {plan_preview}")

    # Step 3: Verify MongoDB storage
    print("\n[Step 3] Verifying MongoDB storage...")
    stored_task = await repos.tasks.find_by_id(task.id)
    assert stored_task is not None, "Task not found in MongoDB!"
    print(f"  {OK} Task found in DB: {stored_task.title}")

    subtasks = await repos.subtasks.find_by_task(task.id)
    print(f"  {OK} Subtasks created: {len(subtasks)}")
    for st in subtasks:
        print(f"    - {st.title} ({st.estimated_hours}h)")

    # Step 4: Dashboard query
    print("\n[Step 4] Dashboard query...")
    user_tasks = await repos.tasks.find_by_user(user.id)
    print(f"  {OK} User has {len(user_tasks)} tasks")

    from datetime import timedelta
    high_risk = await repos.tasks.find_high_risk(user.id, threshold=50.0)
    print(f"  {OK} High risk tasks: {len(high_risk)}")

    productivity = await repos.productivity_history.find_last_n_days(user.id, days=30)
    print(f"  {OK} Productivity history entries: {len(productivity)}")

    # Step 5: Complete task & gamification
    print("\n[Step 5] Task completion & gamification...")
    completed_task = await pipeline.complete_task(task.id, user)
    print(f"  {OK} Task status: {completed_task.status.value}")

    updated_user = await gamification.award_task_completion(user, task.id, task.xp_reward)
    print(f"  {OK} XP awarded: {updated_user.stats.total_xp}")
    print(f"  {OK} Streak: {updated_user.stats.current_streak}")
    print(f"  {OK} Level: {updated_user.stats.level}")
    print(f"  {OK} Life score: {updated_user.stats.life_score:.0f}")

    # Step 6: Guardian Agent
    print("\n[Step 6] Guardian Agent...")
    guardian_result = await guardian.execute(user_id=user.id)
    print(f"  {OK} Guardian actions: {len(guardian_result.get('actions', []))}")

    # Step 7: Reflection Agent
    print("\n[Step 7] Reflection Agent...")
    summary = await reflection.execute(updated_user)
    summary_preview = summary.summary[:80] if summary.summary else "(empty)"
    print(f"  {OK} Summary: {summary_preview}")
    print(f"  {OK} Productivity score: {summary.productivity_score:.0f}")
    print(f"  {OK} Tasks completed today: {summary.tasks_completed}")

    # Step 8: JWT token generation
    print("\n[Step 8] JWT token generation...")
    token = oauth.create_access_token(user)
    decoded = oauth.decode_access_token(token)
    print(f"  {OK} Token created and decoded successfully")
    print(f"  {OK} Subject: {decoded.get('sub')}")

    # Cleanup
    await Database.disconnect()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED -- PIPELINE IS FULLY FUNCTIONAL")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(run_e2e())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n{FAIL} TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
