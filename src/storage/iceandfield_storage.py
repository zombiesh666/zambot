import sqlite3
from src.storage.base_storage import BaseStorage


class IceAndFieldStorage(BaseStorage):

    def _init_tables(self):
        with self._get_connection() as conn:
            # 1. Facilities Table (Prefix applied)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS iceandfield_facilities (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    phone TEXT,
                    email TEXT,
                    timezone TEXT
                )
            """)

            # 2. Event Types Table (Prefix applied)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS iceandfield_event_types (
                    id TEXT PRIMARY KEY,
                    code TEXT,
                    name TEXT
                )
            """)

            # 3. Aggregated Sessions Table (Prefix applied)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS iceandfield_sessions (
                    id TEXT PRIMARY KEY,
                    facility_id TEXT,
                    rink_name TEXT,
                    event_type_id TEXT,
                    session_name TEXT,
                    session_date TEXT,
                    session_start_time TEXT,
                    session_end_time TEXT,
                    open_slots INTEGER,
                    status TEXT,
                    FOREIGN KEY(facility_id) REFERENCES iceandfield_facilities(id),
                    FOREIGN KEY(event_type_id) REFERENCES iceandfield_event_types(id)
                )
            """)

    def save_facility_info(self, facility_data: dict):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO iceandfield_facilities (id, name, phone, email, timezone)
                VALUES (:id, :name, :phone, :email, :timezone)
            """, facility_data)

    def save_event_types(self, event_types: list[dict]):
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO iceandfield_event_types (id, code, name)
                VALUES (:id, :code, :name)
            """, event_types)

    def save_sessions(self, sessions: list[dict]):
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO iceandfield_sessions (
                    id, facility_id, rink_name, event_type_id, session_name,
                    session_date, session_start_time, session_end_time, open_slots, status
                ) VALUES (
                    :id, :facility_id, :rink_name, :event_type_id, :session_name,
                    :session_date, :session_start_time, :session_end_time, :open_slots, :status
                )
            """, sessions)
