import os
import json
import sqlite3
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from src.sync_manager import SyncManager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# --- Configuration Paths ---
IS_DOCKER = os.path.exists('/.dockerenv')
DB_DIR = "/app/data" if IS_DOCKER else "./data"
DB_PATH = os.path.join(DB_DIR, "zambot.db")
CONFIG_PATH = os.path.join(DB_DIR, "feeds.json")

def get_sync_manager() -> SyncManager:
    """
    Bootstraps the SyncManager instance by extracting the parameter-free URL.
    """
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Missing required configuration file: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r") as config_file:
        feeds_config = json.load(config_file)

    iceandfield_url = feeds_config.get("iceandfield_feed")
    if not iceandfield_url:
        raise KeyError("Target key 'iceandfield_feed' missing from feeds.json.")

    return SyncManager(db_path=DB_PATH, base_url=iceandfield_url)


def scheduled_sync_wrapper():
    """Triggered by the automated background scheduler at 4:00 AM."""
    print("CRON: Triggering automated daily 4:00 AM sync...")
    try:
        manager = get_sync_manager()
        manager.run_sync()
    except Exception as e:
        print(f"CRON Error: Failed executing automated sync pipeline: {e}")


# --- App Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Boot up the background cron task executor
    scheduler = BackgroundScheduler(timezone="America/Chicago")
    scheduler.add_job(
        scheduled_sync_wrapper,
        CronTrigger(hour=4, minute=0)
    )
    scheduler.start()
    print("Scheduler initialized: Automated task registry set for 04:00 AM (America/Chicago).")

    yield

    # 2. Cleanup Hooks on Server Shutdown
    scheduler.shutdown()


# Expose ASGI application instance
app = FastAPI(title="Zambot Hockey Parser Engine", lifespan=lifespan)


# --- Routing Layout ---

@app.get("/")
def read_root():
    return {
        "status": "Zambot is online",
        "lookahead": "+90 days (Pure Python Window)",
        "timezone": "America/Chicago",
        "db_location": DB_PATH
    }

@app.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    """Manual sync endpoint processing via non-blocking background threads."""
    def run_async_wrapper():
        manager = get_sync_manager()
        manager.run_sync()

    background_tasks.add_task(run_async_wrapper)
    return {"message": "Sync pipeline started across rolling 90-day horizon."}

@app.get("/sessions")
def get_sessions():
    """Returns all denormalized records from the flat table sorted chronologically."""
    if not os.path.exists(DB_PATH):
        return []

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM iceandfield ORDER BY start_time ASC")
        return [dict(row) for row in cursor.fetchall()]