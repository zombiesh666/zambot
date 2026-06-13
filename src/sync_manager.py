from src.parsers.iceandfield_parser import IceAndFieldParser
from src.storage.iceandfield_storage import IceAndFieldStorage


class SyncManager:
    def __init__(self, db_path: str, base_url: str):
        """
        Coordinates the initialization of the flat storage layout
        and the parameter-driven parser.
        """
        self.db_path = db_path
        self.parser = IceAndFieldParser(base_url=base_url)
        self.storage = IceAndFieldStorage(db_path=db_path)

    def run_sync(self):
        """
        Orchestrates network fetching, data flattening, and persistence operations.
        """
        print("🔄 Running Zambot data collection engine sync pipeline...")

        # 1. Network Fetch Block
        raw_events, raw_included = self.parser.fetch_feed_data()

        # 2. Data Mapping & Flattening Block
        flat_data = self.parser.parse_records(raw_events, raw_included)

        # 3. Database Persistence Block
        self.storage.save_flat_records(flat_data)

        return raw_events, raw_included