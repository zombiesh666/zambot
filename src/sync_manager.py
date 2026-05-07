import httpx
import hashlib
import calendar
import re
import sqlite3
from datetime import datetime
from src.parser_manager import get_parser


class SyncManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def should_process(self, feed_id, current_hash):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT last_hash FROM feed_hashes WHERE feed_id = ?", (feed_id,))
            row = cursor.fetchone()
            return row is None or row[0] != current_hash

    def update_feed_hash(self, feed_id, current_hash):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO feed_hashes (feed_id, last_hash) VALUES (?, ?)",
                         (feed_id, current_hash))

    async def sync_all(self, feeds):
        now = datetime.now()

        # Calculate months to fetch: Current month + 6 months ahead (Total 7 months)
        months_to_fetch = []
        for i in range(7):
            month = (now.month + i - 1) % 12 + 1
            year = now.year + (now.month + i - 1) // 12
            months_to_fetch.append((year, month))

        async with httpx.AsyncClient() as client:
            for feed in feeds:
                parser = get_parser(feed['parser_type'])
                if not parser:
                    print(f"Skipping {feed['name']}: No parser found for {feed['parser_type']}")
                    continue

                for year, month in months_to_fetch:
                    last_day = calendar.monthrange(year, month)[1]
                    start_str = f"{year}-{month:02d}-01"
                    end_str = f"{year}-{month:02d}-{last_day:02d}"

                    # Inject placeholders into the URL from feeds.json
                    url = feed['url'].format(start=start_str, end=end_str)

                    try:
                        print(f"Syncing {feed['name']} for {year}-{month:02d}...")
                        response = await client.get(url, timeout=20.0)  # Slightly longer timeout for 6 months of data
                        response.raise_for_status()

                        content_hash = hashlib.md5(response.text.encode()).hexdigest()
                        feed_id = f"{feed['parser_type']}_{year}_{month}"

                        if not self.should_process(feed_id, content_hash):
                            print(f"  -> No changes for {feed_id}. Skipping.")
                            continue

                        data = parser.parse(response.json())
                        self.save_to_db(data)
                        self.update_feed_hash(feed_id, content_hash)
                        print(f"  -> Success: {len(data)} sessions processed.")

                    except Exception as e:
                        print(f"  -> Failed to sync {feed['name']} for {year}-{month}: {e}")

    def save_to_db(self, data):
        with sqlite3.connect(self.db_path) as conn:
            for s in data:
                try:
                    conn.execute("""
                        INSERT INTO sessions (
                            rink_name, event_name, session_name, program_name,
                            session_date, session_start_time, session_end_time,
                            timezone, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (s['rink'], s['event_name'], s['session_name'], s['program_name'],
                          s['date'], s['start'], s['end'], s['timezone'], s['status']))
                except sqlite3.IntegrityError:
                    # Update existing record (e.g., if status changed from available to full)
                    conn.execute("""
                        UPDATE sessions SET 
                            session_end_time = ?, status = ?, event_name = ?, 
                            session_name = ?, program_name = ?
                        WHERE rink_name = ? AND session_date = ? AND session_start_time = ?
                    """, (s['end'], s['status'], s['event_name'], s['session_name'],
                          s['program_name'], s['rink'], s['date'], s['start']))