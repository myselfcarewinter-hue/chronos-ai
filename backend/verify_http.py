import httpx
import json
import sys

URL_BASE = "http://localhost:8000"

def log_step(name, success, info=""):
    status = "[OK]" if success else "[FAIL]"
    print(f"{status} {name} {f'— {info}' if info else ''}")

async def test_http_pipeline():
    print("=" * 60)
    print("CHRONOS AI — HTTP API END-TO-END PIPELINE TEST")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Step 1: Demo Login
        try:
            r = await client.post(f"{URL_BASE}/auth/demo")
            if r.status_code != 200:
                log_step("Demo Login", False, f"HTTP {r.status_code}: {r.text}")
                return False
            res = r.json()
            token = res["access_token"]
            user_id = res["user"]["id"]
            user_name = res["user"]["name"]
            log_step("Demo Login", True, f"Logged in as {user_name} ({user_id})")
        except Exception as e:
            log_step("Demo Login", False, f"Exception: {e}")
            return False

        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Create Task via AI Pipeline
        try:
            task_input = "I have an ML assignment due Friday night."
            r = await client.post(
                f"{URL_BASE}/tasks/create",
                headers=headers,
                json={"input": task_input}
            )
            if r.status_code != 200:
                log_step("Create Task", False, f"HTTP {r.status_code}: {r.text}")
                return False
            res = r.json()
            task = res["task"]
            task_id = task["id"]
            title = task["title"]
            priority = task["priority"]["priority_level"]
            risk = task["risk"]["risk_percentage"]
            subtasks_count = len(task["subtasks"])
            log_step("Create Task", True, f"Created task '{title}' (ID: {task_id}). Priority: {priority}, Risk: {risk:.0f}%, Subtasks: {subtasks_count}")
        except Exception as e:
            log_step("Create Task", False, f"Exception: {e}")
            return False

        # Step 3: Query Dashboard
        try:
            r = await client.get(f"{URL_BASE}/dashboard", headers=headers)
            if r.status_code != 200:
                log_step("Query Dashboard", False, f"HTTP {r.status_code}: {r.text}")
                return False
            res = r.json()
            xp_before = res["xp"]
            level_before = res["level"]
            life_score_before = res["life_score"]
            log_step("Query Dashboard", True, f"XP: {xp_before}, Level: {level_before}, Life Score: {life_score_before}")
        except Exception as e:
            log_step("Query Dashboard", False, f"Exception: {e}")
            return False

        # Step 4: Complete Task & Award XP
        try:
            r = await client.put(f"{URL_BASE}/tasks/{task_id}/complete", headers=headers)
            if r.status_code != 200:
                log_step("Complete Task", False, f"HTTP {r.status_code}: {r.text}")
                return False
            res = r.json()
            xp_earned = res["xp_earned"]
            msg = res["message"]
            log_step("Complete Task", True, f"XP Earned: {xp_earned}. Msg: {msg}")
        except Exception as e:
            log_step("Complete Task", False, f"Exception: {e}")
            return False

        # Step 5: Verify Updated Dashboard Stats
        try:
            r = await client.get(f"{URL_BASE}/dashboard", headers=headers)
            if r.status_code != 200:
                log_step("Verify Stats", False, f"HTTP {r.status_code}: {r.text}")
                return False
            res = r.json()
            xp_after = res["xp"]
            level_after = res["level"]
            life_score_after = res["life_score"]
            success = xp_after > xp_before
            log_step("Verify Stats", success, f"XP went from {xp_before} -> {xp_after}. Level: {level_before} -> {level_after}. Life Score: {life_score_before} -> {life_score_after}")
            if not success:
                return False
        except Exception as e:
            log_step("Verify Stats", False, f"Exception: {e}")
            return False

    print("=" * 60)
    print("ALL HTTP END-TO-END PIPELINE CHECKS PASSED SUCCESSFULLY")
    print("=" * 60)
    return True

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_http_pipeline())
    sys.exit(0 if success else 1)
