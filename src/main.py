import os
import json
import sqlite3
import asyncio
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from src.sync_manager import SyncManager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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
    print("CRON: Triggering automated 4:00 AM flat pipeline execution run...")
    config = load_config()
    await sync_manager.sync_all_feeds(config)


def scheduled_sync_wrapper():
    asyncio.run(run_scheduled_sync())


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler(timezone="America/Chicago")
    scheduler.add_job(scheduled_sync_wrapper, CronTrigger(hour=4, minute=0))
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

        query = """
            SELECT CAST(id AS TEXT) as id, summary_name, start_time, end_time, length, 
                   skaters_registered, skaters_open_slots, skaters_capacity, 
                   goalies_registered, goalies_open_slots, goalies_capacity,
                   registration_status, resource_name, facility_name, NULL as event_url 
            FROM iceandfield_v2
            WHERE start_time >= date('now', 'localtime')

            UNION ALL

            SELECT CAST(id AS TEXT) as id, summary_name, start_time, end_time, length, 
                   skaters_registered, skaters_open_slots, skaters_capacity, 
                   goalies_registered, goalies_open_slots, goalies_capacity,
                   registration_status, resource_name, facility_name, NULL as event_url 
            FROM chaparral_sessions_v2
            WHERE start_time >= date('now', 'localtime')

            UNION ALL

            SELECT CAST(id AS TEXT) as id, summary_name, start_time, end_time, length, 
                   skaters_registered, skaters_open_slots, skaters_capacity, 
                   goalies_registered, goalies_open_slots, goalies_capacity,
                   registration_status, resource_name, facility_name, event_url
            FROM pond_sessions_v2
            WHERE start_time >= date('now', 'localtime')

            ORDER BY start_time ASC
        """
        try:
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            print(f"Database read mismatch: {e}")
            return []