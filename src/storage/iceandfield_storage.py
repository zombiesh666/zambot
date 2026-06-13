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
                    summary_name TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    length INTEGER,
                    registered_count INTEGER,
                    remaining_slots INTEGER,
                    registration_status TEXT,
                    composite_capacity INTEGER,
                    resource_name TEXT,
                    facility_name TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def save_flat_records(self, flat_records: list[dict]):
        """
        Performs high-speed batch synchronization into your flat table structure.
        """
        if not flat_records:
            return

        # Map flat dictionary records into database row positional tuples
        data_tuples = [
            (
                r["id"], r["summary_name"], r["start_time"], r["end_time"], r["length"],
                r["registered_count"], r["remaining_slots"], r["registration_status"],
                r["composite_capacity"], r["resource_name"], r["facility_name"]
            )
            for r in flat_records
        ]

        print(f"💾 Synchronizing {len(data_tuples)} flat records into local SQLite storage...")

        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO iceandfield (
                    id, summary_name, start_time, end_time, length,
                    registered_count, remaining_slots, registration_status,
                    composite_capacity, resource_name, facility_name, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, data_tuples)

        print("   ✅ Database synchronization transaction committed.")