import os
import json
import sqlite3
import asyncio
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from src.sync_manager import SyncManager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

IS_DOCKER = os.path.exists('/.dockerenv')
DB_DIR = "/app/data" if IS_DOCKER else "./data"
DB_PATH = os.path.join(DB_DIR, "zambot.db")
CONFIG_PATH = os.path.join(DB_DIR, "feeds.json")

# Initialize the manager properly without the base_url argument
sync_manager = SyncManager(DB_PATH)

def get_feeds():
    """Safely extracts the endpoint from either the old or new feeds.json format."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
            if "feeds" in config_data:
                return config_data["feeds"]
            elif "iceandfield_feed" in config_data:
                return [{"parser_type": "iceandfield", "events_base_url": config_data["iceandfield_feed"]}]
            return []
    except Exception as e:
        print(f"Config error: {e}")
        return []

async def run_scheduled_sync():
    print("CRON: Starting daily 4:00 AM sync...")
    feeds = get_feeds()
    for feed in feeds:
        if feed.get("parser_type") == "iceandfield":
            await sync_manager.sync_iceandfield(feed)

def scheduled_sync_wrapper():
    asyncio.run(run_scheduled_sync())

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler(timezone="America/Chicago")
    scheduler.add_job(scheduled_sync_wrapper, CronTrigger(hour=4, minute=0))
    scheduler.start()
    print("Scheduler started: Sync job set for 04:00 daily (America/Chicago).")
    yield
    scheduler.shutdown()

app = FastAPI(title="Zambot Hockey Parser", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "Zambot is online", "db_location": DB_PATH}

@app.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    feeds = get_feeds()
    for feed in feeds:
        if feed.get("parser_type") == "iceandfield":
            background_tasks.add_task(sync_manager.sync_iceandfield, feed)
    return {"message": "Flat sync pipeline started."}

@app.get("/sessions")
def get_sessions():
    """Returns everything cleanly from the single flat table."""
    if not os.path.exists(DB_PATH):
        return []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM iceandfield ORDER BY start_time ASC")
        return [dict(row) for row in cursor.fetchall()]