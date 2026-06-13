import sqlite3
import os

class BaseStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        """Each storage sub-class must implement its own table creation script."""
        raise NotImplementedError
