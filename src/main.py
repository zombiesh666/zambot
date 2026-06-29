import os
import json
import time
import sqlite3
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from src.sync_manager import SyncManager

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


# 👉 Pure Async Background Poller Task loop (Replaces APScheduler)
async def schedule_poller_task():
    # Delay initial check slightly to give the main Uvicorn web server time to stand up
    await asyncio.sleep(5)
    while True:
        try:
            print("CRON: Running automated 5-minute interval synchronization loop...")
            config = load_config()
            await sync_manager.sync_all_feeds(config)
        except Exception as e:
            print(f"CRON Error: Loop encountered error: {e}")

        # Sleep non-blockingly for 5 minutes (300 seconds)
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 👉 Spawn the async background loop directly into the running application event loop
    poller_task = asyncio.create_task(schedule_poller_task())
    yield
    # Safely cancel the task loop when the application winds down
    poller_task.cancel()


app = FastAPI(title="Zambot Hockey Parser", lifespan=lifespan)


@app.get("/")
def read_root():
    static_root_index = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_root_index):
        return FileResponse(static_root_index)
    return {"status": "Zambot Online", "msg": "Static HTML index missing."}


# --- SEO & Analytics Endpoints ---
@app.get("/robots.txt", include_in_schema=False)
def serve_robots_txt():
    path = os.path.join(os.path.dirname(__file__), "static", "robots.txt")
    if os.path.exists(path):
        return FileResponse(path, media_type="text/plain")
    raise HTTPException(status_code=404, detail="robots.txt not found")


@app.get("/sitemap.xml", include_in_schema=False)
def serve_sitemap():
    path = os.path.join(os.path.dirname(__file__), "static", "sitemap.xml")
    if os.path.exists(path):
        return FileResponse(path, media_type="application/xml")
    raise HTTPException(status_code=404, detail="sitemap.xml not found")


@app.get("/metrics", include_in_schema=False)
def serve_metrics():
    path = os.path.join(os.path.dirname(__file__), "static", "metrics.html")
    if os.path.exists(path):
        return FileResponse(path, media_type="text/html")
    raise HTTPException(status_code=404, detail="metrics.html not found (GoAccess may still be generating it)")


static_assets_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_assets_path):
    app.mount("/static", StaticFiles(directory=static_assets_path), name="static")


@app.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    config = load_config()
    background_tasks.add_task(sync_manager.sync_all_feeds, config)
    return {"message": "All aggregation pipelines activated."}


# 👉 Define a simple cache state
route_cache = {
    "sessions_data": [],
    "last_fetched": 0
}
CACHE_TTL = 30  # Serve from RAM for 30 seconds before re-querying the DB


@app.get("/sessions")
def get_sessions():
    if not os.path.exists(DB_PATH):
        return []

    current_time = time.time()

    # 👉 1. Return instantly from RAM if the cache is still fresh
    if current_time - route_cache["last_fetched"] < CACHE_TTL:
        return route_cache["sessions_data"]

    # 👉 2. Otherwise, hit the database
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
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
            results = [dict(row) for row in cursor.fetchall()]

            # 👉 3. Update the cache with the new data
            route_cache["sessions_data"] = results
            route_cache["last_fetched"] = current_time

            return results
        except sqlite3.OperationalError as e:
            print(f"Database read mismatch: {e}")
            return []
