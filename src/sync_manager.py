import time
import requests
from src.parsers.iceandfield_parser import IceAndFieldParser
from src.storage.iceandfield_storage import IceAndFieldStorage


class SyncManager:
    def __init__(self, db_path: str, base_url: str):
        self.db_path = db_path
        self.parser = IceAndFieldParser(base_url=base_url)
        self.storage = IceAndFieldStorage(db_path=db_path)

    def run_sync(self):
        """
        Coordinates network fetching by appending explicit GET param page index adjustments.
        """
        print("🔄 Initiating parameter-driven multi-page sync pipeline...")

        # Pull static filtering parameters initialized across the 90-day time scope
        base_params = self.parser._build_params()
        headers = {"Accept": "application/vnd.api+json"}

        current_page = 1
        has_more_pages = True

        while has_more_pages:
            print(f"📡 Fetching data matrix index: Page {current_page}...")

            # Make a localized parameter copy and inject the clean incremental page index
            request_params = base_params.copy()
            request_params["page[number]"] = str(current_page)

            # Keep the target endpoint anchored cleanly to base_url on every run
            response = requests.get(self.parser.base_url, params=request_params, headers=headers)

            if response.status_code != 200:
                print(f"❌ HTTP Error encountered on Page {current_page}: {response.status_code}")
                break

            payload = response.json()
            data_list = payload.get("data", [])

            # Early Exit Guard: Terminate synchronization if an empty data bucket is hit
            if not data_list:
                print(f"🛑 Found empty data payload at page {current_page}. Halting synchronization.")
                break

            # Parse and write records directly to storage slice by slice
            flat_page_records = self.parser.parse_page_payload(payload)
            self.storage.save_flat_records(flat_page_records)
            print(f"   ✅ Saved {len(flat_page_records)} flat items from Page {current_page}.")

            # Compute pagination boundaries using the response metadata nodes
            meta_page = payload.get("meta", {}).get("page", {})
            last_page = meta_page.get("last-page", 1)

            if current_page >= last_page:
                has_more_pages = False
                print("✨ Reached maximum page boundaries. Synchronization loop closed.")
            else:
                current_page += 1
                time.sleep(1)  # Courteous rate-limiting interval between requests