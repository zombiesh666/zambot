import sqlite3
from src.storage.base_storage import BaseStorage


class IceAndFieldStorage(BaseStorage):
    def _init_tables(self):
        """
        Creates your single, denormalized flat data table if it doesn't exist.
        """
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS iceandfield (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    open_slots INTEGER,
                    registration_status TEXT,
                    event_type_id TEXT,
                    event_type_code TEXT,
                    event_type_name TEXT,
                    summary_id TEXT,
                    summary_name TEXT,
                    facility_id TEXT,
                    facility_name TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def save_flat_records(self, flat_records: list[dict]):
        """
        Performs high-speed batch synchronization into your flat table.
        """
        if not flat_records:
            print("📭 Storage received empty dataset slice. Skipping write transactions.")
            return

        # Unpack flat dictionaries into database row positional tuples
        data_tuples = [
            (
                r["id"], r["name"], r["start_time"], r["end_time"], r["open_slots"],
                r["registration_status"], r["event_type_id"], r["event_type_code"],
                r["event_type_name"], r["summary_id"], r["summary_name"],
                r["facility_id"], r["facility_name"]
            )
            for r in flat_records
        ]

        print(f"💾 Synchronizing {len(data_tuples)} records into local SQLite storage...")

        # Bulk write everything inside a single transactional block
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO iceandfield (
                    id, name, start_time, end_time, open_slots, registration_status,
                    event_type_id, event_type_code, event_type_name,
                    summary_id, summary_name, facility_id, facility_name, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, data_tuples)

        print("✅ Database synchronization transaction successfully committed.")