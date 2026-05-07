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

sync_manager = SyncManager(DB_PATH)


# --- Database Schema Setup ---
def init_db(db_path):
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    with sqlite3.connect(db_path) as conn:
        # Create Sessions table (matches your preferred column order)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rink_name TEXT,
                event_name TEXT,
                session_name TEXT,
                program_name TEXT,
                session_date TEXT,
                session_start_time TEXT,
                session_end_time TEXT,
                timezone TEXT,
                status TEXT,
                UNIQUE(rink_name, session_date, session_start_time)
            )
        """)
        # Create Feed Hashes table for the caching logic
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feed_hashes (
                feed_id TEXT PRIMARY KEY,
                last_hash TEXT
            )
        """)
    print(f"Database initialized at {db_path}")


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
    # Using run_in_executor if sync_all wasn't fully async,
    # but since it uses httpx.AsyncClient, we can just await it.
    await sync_manager.sync_all(feeds)


# --- App Lifespan (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Tables
    init_db(DB_PATH)

    # 2. Start Scheduler
    scheduler = BackgroundScheduler(timezone="America/Chicago")
    # hour=4 triggers at 4:00 AM Georgetown time
    scheduler.add_job(
        lambda: asyncio.run(run_scheduled_sync()),
        CronTrigger(hour=4, minute=0)
    )
    scheduler.start()
    print("Scheduler started: Sync job set for 04:00 daily (America/Chicago).")

    yield

    # 3. Shutdown
    scheduler.shutdown()


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
    """Manual sync trigger for testing or forced updates."""
    feeds = get_feeds()
    background_tasks.add_task(sync_manager.sync_all, feeds)
    return {"message": "Sync started across current and +6 upcoming months."}


@app.get("/sessions")
def get_sessions():
    """Returns all upcoming hockey sessions sorted by date and time."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM sessions 
            ORDER BY session_date ASC, session_start_time ASC
        """)
        return [dict(row) for row in cursor.fetchall()]