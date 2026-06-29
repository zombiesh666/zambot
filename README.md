# Zambot Documentation

Zambot is a real-time schedule aggregator for ice skating and hockey drop-in sessions across Austin (ATX) ice rinks. It continuously polls rink schedules, processes slot capacities for players and goalies, and presents an optimized, mobile-first unified view for local skaters.

---

## 1. Project Architecture & How It Works

Zambot is built on a highly efficient, non-blocking asynchronous Python stack optimized to run seamlessly on resource-constrained environments (such as a 512MB VPS).

```
                         [ External Rink Feeds ]
                         (DaySmart APIs & Web HTML)
                                    │
                                    ▼ (Every 5 Mins)
┌────────────────────────────────────────────────────────────────────────┐
│ Zambot Backend (FastAPI Engine)                                        │
│                                                                        │
│  ┌───────────────────────┐            ┌─────────────────────────────┐  │
│  │  Async Task Poller    │───────────>│   SyncManager               │  │
│  │  (Lifespan Loop)      │            │  (Unified Feeds Crawler)    │  │
│  └───────────────────────┘            └─────────────────────────────┘  │
│                                                      │                 │
│                                                      ▼                 │
│  ┌───────────────────────┐            ┌─────────────────────────────┐  │
│  │   /sessions Endpoint  │<───────────│   SQLite Database           │  │
│  │  (Aggregated JSON)    │            │  (zambot.db Space-Optimized)│  │
│  └───────────────────────┘            └─────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (JSON Stream)
                        [ Caddy Reverse Proxy ]
                                    │
                                    ▼ (TLS / HTTPS)
                        [ Frontend Client UI ]
                       (Tactile Mobile index.html)

```

### Core Execution Flows:

1. **Asynchronous Background Worker:** Upon application startup, FastAPI's `lifespan` handler spawns an isolated asynchronous tracking task (`schedule_poller_task`) directly inside the main ASGI event loop. Every 5 minutes, this task safely triggers the extraction pipelines without spinning up heavy external system threads.
2. **Consolidated Feed Harvesting:** The `SyncManager` orchestrates the parsers. Rinks sharing the same underlying platform (DaySmart/Dash) are funneled through a single DRY pipeline (`_sync_daysmart_feed`), while unique HTML scrapes (The Pond) utilize custom fallbacks to preserve capacity historical entries if network fetches encounter timeouts.
3. **Unified Data Queries:** When a user opens the page, the client hits `/sessions`. The backend runs a relational `UNION ALL` query across the localized SQLite tables to generate a cron-sorted 14-day chronological schedule matrix.

---

## 2. Project Directory Structure

```text
zambot/
├── .github/workflows/
│   └── deploy.yml          # Automated CI/CD pipeline to production droplet
├── data/
│   ├── feeds.json          # Target URL configuration endpoints for API pollers
│   └── zambot.db           # Local SQLite application database (Git-ignored)
├── src/
│   ├── __init__.py
│   ├── main.py             # FastAPI entrypoint, routing API and lifespan setups
│   ├── sync_manager.py     # Aggregation pipeline manager (DaySmart & Pond routines)
│   ├── parsers/            # Extraction and sanitization engines
│   │   ├── base_parser.py
│   │   ├── chaparral_parser.py
│   │   ├── iceandfield_parser.py
│   │   └── pond_parser.py
│   ├── storage/            # SQLite connection contexts and table write commits
│   │   ├── base_storage.py
│   │   ├── chaparral_storage.py
│   │   ├── iceandfield_storage.py
│   │   └── pond_storage.py
│   └── static/             # Pure static presentation elements
│       ├── index.html      # Responsive mobile UI with tactile touch feedback
│       ├── favicon.svg     # Native vector site brand assets
│       ├── robots.txt      # Search engine indexing directives
│       └── sitemap.xml     # SEO route architecture map
├── tests/
│   └── load/
│       └── load_test.js    # k6 performance script simulating user spikes
├── Caddyfile               # Production gateway configuration (Logs & TLS)
├── Dockerfile              # Python container production compilation setup
├── docker-compose.yml      # Multi-container cluster mapping (Web, Proxy, GoAccess)
├── requirements.txt        # Frozen application dependencies footprint
└── .gitignore              # Workspace boundary protection rules

```

---

## 3. Local Environment Setup

Follow these instructions to stand up a local instance of Zambot for development and testing on a Windows machine.

### Prerequisites

* Python 3.10+ installed on your system.
* Git installed.

### Step 1: Clone and Enter the Repository

Open a PowerShell terminal and navigate to your working development directory:

```powershell
git clone <your-repository-url>
cd zambot

```

### Step 2: Initialize a Virtual Environment

Create an isolated Python virtual environment to house your workspace dependencies cleanly:

```powershell
python -m venv venv

```

Activate the environment inside your PowerShell instance:

```powershell
.\venv\Scripts\Activate.ps1

```

*(Your prompt should now display `(venv)` at the beginning of the path.)*

### Step 3: Install Workspace Dependencies

Upgrade the base package managers and pull down your lock-step runtime definitions:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt

```

### Step 4: Configure Local Application Feeds

Zambot expects a configuration block to know where to find the source data. Ensure that a `data/feeds.json` directory structure exists. For local debugging, you can populate a base JSON skeleton inside it:

```json
{
  "iceandfield_feed": "https://example-api-endpoint.com",
  "chaparral_feed": "https://example-api-endpoint.com",
  "pond_feed": "https://example-api-endpoint.com"
}

```

### Step 5: Start the Development Server

Run the FastAPI application locally using Uvicorn with hot-reload enabled so code changes update instantly:

```powershell
uvicorn src.main:app --reload --port 8000

```

### Step 6: Verify Local Connectivity

* **User Interface:** Open your browser and navigate to `http://127.0.0.1:8000/`. You should see the custom Zambot typography layout.
* **Data Endpoint:** Check `http://127.0.0.1:8000/sessions` to see your local SQLite database payloads.
* **Manual Crawler Check:** You can force-trigger a synchronization cycle at any point by sending an empty `POST` request to `http://127.0.0.1:8000/sync` using Postman or `curl`.