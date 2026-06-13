import os
import json
import sqlite3
import asyncio
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from src.sync_manager import SyncManager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# --- Configuration ---
IS_DOCKER = os.path.exists('/.dockerenv')
DB_DIR = "/app/data" if IS_DOCKER else "./data"
DB_PATH = os.path.join(DB_DIR, "zambot.db")
CONFIG_PATH = os.path.join(DB_DIR, "feeds.json")

# Instantiating SyncManager automatically runs BaseStorage/IceAndFieldStorage initialization,
# which sets up all tables using the 'iceandfield_' prefix on a zero-ops deployment.
sync_manager = SyncManager(DB_PATH)


# --- Helper Logic ---
def get_feeds():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f).get("feeds", [])
    except Exception as e:
        print(f"Config error: {e}")
        return []


async def run_scheduled_sync():
    print("CRON: Starting daily 4:00 AM sync...")
    feeds = get_feeds()
    for feed in feeds:
        if feed.get("parser_type") == "iceandfield":
            await sync_manager.sync_iceandfield(feed)
        else:
            if hasattr(sync_manager, "sync_all"):
                await sync_manager.sync_all(feeds)
                break


def scheduled_sync_wrapper():
    """Safe sync runner to isolate the async loop execution thread within APScheduler."""
    asyncio.run(run_scheduled_sync())


# --- App Lifespan (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Start Background Scheduler (Local time zone aware)
    scheduler = BackgroundScheduler(timezone="America/Chicago")

    # Run the hash-guarded sync process automatically every day at 4:00 AM local time
    scheduler.add_job(
        scheduled_sync_wrapper,
        CronTrigger(hour=4, minute=0)
    )
    scheduler.start()
    print("Scheduler started: Sync job set for 04:00 daily (America/Chicago).")

    yield

    # 2. Shutdown Hooks
    scheduler.shutdown()


# Explicitly global definition for ASGI loader visibility
app = FastAPI(title="Zambot Hockey Parser", lifespan=lifespan)


# --- Routes ---

@app.get("/")
def read_root():
    return {
        "status": "Zambot is online",
        "lookahead": "+6 months",
        "timezone": "America/Chicago",
        "db_location": DB_PATH
    }


@app.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    """Manual sync trigger endpoint for immediate local or droplet validation updates."""
    feeds = get_feeds()

    # Re-use background tasks worker to process without freezing API response times
    for feed in feeds:
        if feed.get("parser_type") == "iceandfield":
            background_tasks.add_task(sync_manager.sync_iceandfield, feed)
        else:
            if hasattr(sync_manager, "sync_all"):
                background_tasks.add_task(sync_manager.sync_all, feeds)
                break

    return {"message": "Sync started across current and +6 upcoming months."}


@app.get("/sessions")
def get_sessions():
    """Returns all aggregated hockey sessions sorted chronologically by date and time."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM iceandfield_sessions 
            ORDER BY session_date ASC, session_start_time ASC
        """)
        return [dict(row) for row in cursor.fetchall()]
