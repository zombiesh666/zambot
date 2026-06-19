import os
import json
import sqlite3
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from src.sync_manager import SyncManager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

IS_DOCKER = os.path.exists('/.dockerenv')
DB_DIR = "/app/data" if IS_DOCKER else "./data"
DB_PATH = os.path.join(DB_DIR, "zambot.db")
CONFIG_PATH = os.path.join(DB_DIR, "feeds.json")

sync_manager = SyncManager(DB_PATH)


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Config error: {e}")
        return {}


async def run_scheduled_sync():
    print("CRON: Running automated 5-minute interval synchronization loop...")
    config = load_config()
    await sync_manager.sync_all_feeds(config)


def scheduled_sync_wrapper():
    asyncio.run(run_scheduled_sync())


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler(timezone="America/Chicago")
    # 👉 Changed cron trigger to a rolling 5-minute interval trigger
    scheduler.add_job(scheduled_sync_wrapper, IntervalTrigger(minutes=5))
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Zambot Hockey Parser", lifespan=lifespan)


@app.get("/")
def read_root():
    static_root_index = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_root_index):
        return FileResponse(static_root_index)
    return {"status": "Zambot Online", "msg": "Static HTML index missing."}


# --- NEW: Robots.txt Endpoint ---
@app.get("/robots.txt", include_in_schema=False)
def serve_robots_txt():
    robots_path = os.path.join(os.path.dirname(__file__), "static", "robots.txt")
    if os.path.exists(robots_path):
        return FileResponse(robots_path, media_type="text/plain")
    raise HTTPException(status_code=404, detail="robots.txt not found")


static_assets_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_assets_path):
    app.mount("/static", StaticFiles(directory=static_assets_path), name="static")


@app.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    config = load_config()
    background_tasks.add_task(sync_manager.sync_all_feeds, config)
    return {"message": "All aggregation pipelines activated."}


@app.get("/sessions")
def get_sessions():
    if not os.path.exists(DB_PATH): return []

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 👉 Updated queries to strictly bound returned records to a +14 day window
        query = """
            SELECT CAST(id AS TEXT) as id, summary_name, start_time, end_time, length, 
                   skaters_registered, skaters_open_slots, skaters_capacity, 
                   goalies_registered, goalies_open_slots, goalies_capacity,
                   registration_status, resource_name, facility_name, event_url, event_type
            FROM iceandfield_v3
            WHERE start_time >= date('now', 'localtime') AND start_time <= date('now', '+14 days', 'localtime')

            UNION ALL

            SELECT CAST(id AS TEXT) as id, summary_name, start_time, end_time, length, 
                   skaters_registered, skaters_open_slots, skaters_capacity, 
                   goalies_registered, goalies_open_slots, goalies_capacity,
                   registration_status, resource_name, facility_name, event_url, event_type
            FROM chaparral_sessions_v3
            WHERE start_time >= date('now', 'localtime') AND start_time <= date('now', '+14 days', 'localtime')

            UNION ALL

            SELECT CAST(id AS TEXT) as id, summary_name, start_time, end_time, length, 
                   skaters_registered, skaters_open_slots, skaters_capacity, 
                   goalies_registered, goalies_open_slots, goalies_capacity,
                   registration_status, resource_name, facility_name, event_url, event_type
            FROM pond_sessions_v3
            WHERE start_time >= date('now', 'localtime') AND start_time <= date('now', '+14 days', 'localtime')

            ORDER BY start_time ASC
        """
        try:
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            print(f"Database read mismatch: {e}")
            return []