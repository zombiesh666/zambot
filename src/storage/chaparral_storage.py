import sqlite3
from src.storage.base_storage import BaseStorage

class ChaparralStorage(BaseStorage):
    def _init_tables(self):
        """Creates a single, flat table for Chaparral Ice schedule records."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chaparral_sessions (
                    id TEXT PRIMARY KEY,
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
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def save_flat_records(self, flat_records: list[dict]):
        if not flat_records:
            return
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO chaparral_sessions (
                    id, summary_name, start_time, end_time, length,
                    registered_count, remaining_slots, composite_capacity,
                    registration_status, resource_name, facility_name, updated_at
                ) VALUES (
                    :id, :summary_name, :start_time, :end_time, :length,
                    :registered_count, :remaining_slots, :composite_capacity,
                    :registration_status, :resource_name, :facility_name, CURRENT_TIMESTAMP
                )
            """, flat_records)