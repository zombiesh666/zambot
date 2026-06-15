import sqlite3
from src.storage.base_storage import BaseStorage


class PondStorage(BaseStorage):
    def _init_tables(self):
        """Creates a flat table with autoincrement IDs specifically designed for scraping."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pond_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary_name TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    length INTEGER,
                    registered_count INTEGER,
                    remaining_slots INTEGER,
                    composite_capacity INTEGER,
                    registration_status TEXT,
                    resource_name TEXT,
                    facility_name TEXT,
                    event_url TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def save_flat_records(self, flat_records: list[dict]):
        if not flat_records:
            return

        with self._get_connection() as conn:
            # Drop older records to prevent boundless duplication from autoincrement looping
            conn.execute("DELETE FROM pond_sessions")
            conn.executemany("""
                INSERT INTO pond_sessions (
                    summary_name, start_time, end_time, length,
                    registered_count, remaining_slots, composite_capacity,
                    registration_status, resource_name, facility_name, event_url, updated_at
                ) VALUES (
                    :summary_name, :start_time, :end_time, :length,
                    :registered_count, :remaining_slots, :composite_capacity,
                    :registration_status, :resource_name, :facility_name, :event_url, CURRENT_TIMESTAMP
                )
            """, flat_records)