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

# --- Configuration Paths Configuration ---
IS_DOCKER = os.path.exists('/.dockerenv')
DB_DIR = "/app/data" if IS_DOCKER else "./data"
DB_PATH = os.path.join(DB_DIR, "zambot.db")
CONFIG_PATH = os.path.join(DB_DIR, "feeds.json")

# Instantiate tracking manager using baseline data configurations
sync_manager = SyncManager(DB_PATH)

def get_feeds():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f).get("feeds", [])
    except Exception as e:
        print(f"Config mapping exception error: {e}")
        return []

async def run_scheduled_sync():
    print("CRON: Triggering automated 4:00 AM flat pipeline execution run...")
    feeds = get_feeds()
    for feed in feeds:
        if feed.get("parser_type") == "iceandfield":
            await sync_manager.sync_iceandfield(feed)

def scheduled_sync_wrapper():
    asyncio.run(run_scheduled_sync())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize light internal thread scheduling mechanisms
    scheduler = BackgroundScheduler(timezone="America/Chicago")
    scheduler.add_job(scheduled_sync_wrapper, CronTrigger(hour=4, minute=0))
    scheduler.start()
    print("Scheduler initiated: Local America/Chicago chron sync thread launched.")
    yield
    scheduler.shutdown()

app = FastAPI(title="Zambot Hockey Parser", lifespan=lifespan)

# --- THE ZERO-OVERHEAD FRONTEND ROUTES ---

# 1. Resolve root endpoint lookups using highly cached FileResponse assets
@app.get("/")
def read_root():
    static_root_index = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_root_index):
        return FileResponse(static_root_index)
    return {"status": "Zambot Online", "msg": "Static HTML index template missing from src/static/"}

# 2. Mount static directory assets for clean client reference execution paths
static_assets_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_assets_path):
    app.mount("/static", StaticFiles(directory=static_assets_path), name="static")

# --- Pipeline Core API Routings ---

@app.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    feeds = get_feeds()
    for feed in feeds:
        if feed.get("parser_type") == "iceandfield":
            background_tasks.add_task(sync_manager.sync_iceandfield, feed)
    return {"message": "Sync pipeline task initialized successfully."}

@app.get("/sessions")
def get_sessions():
    """Returns everything cleanly from the singular flat table layout architecture."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM iceandfield ORDER BY start_time ASC")
        return [dict(row) for row in cursor.fetchall()]