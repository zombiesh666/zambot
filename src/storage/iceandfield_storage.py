import sqlite3
from src.storage.base_storage import BaseStorage

class IceAndFieldStorage(BaseStorage):
    def _init_tables(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS iceandfield_v2 (
                    id TEXT PRIMARY KEY,
                    summary_name TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    length INTEGER,
                    skaters_registered INTEGER,
                    skaters_open_slots INTEGER,
                    skaters_capacity INTEGER,
                    goalies_registered INTEGER,
                    goalies_open_slots INTEGER,
                    goalies_capacity INTEGER,
                    registration_status TEXT,
                    resource_name TEXT,
                    facility_name TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def save_flat_records(self, flat_records: list[dict]):
        if not flat_records:
            return
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO iceandfield_v2 (
                    id, summary_name, start_time, end_time, length,
                    skaters_registered, skaters_open_slots, skaters_capacity,
                    goalies_registered, goalies_open_slots, goalies_capacity,
                    registration_status, resource_name, facility_name, updated_at
                ) VALUES (
                    :id, :summary_name, :start_time, :end_time, :length,
                    :skaters_registered, :skaters_open_slots, :skaters_capacity,
                    :goalies_registered, :goalies_open_slots, :goalies_capacity,
                    :registration_status, :resource_name, :facility_name, CURRENT_TIMESTAMP
                )
            """, flat_records)