import httpx
import calendar
import asyncio
from datetime import datetime
from src.parsers.iceandfield_parser import IceAndFieldParser
from src.storage.iceandfield_storage import IceAndFieldStorage


class SyncManager:
    def __init__(self, db_path: str):
        self.storage = IceAndFieldStorage(db_path)
        self.parser = IceAndFieldParser()

    async def sync_iceandfield(self, config: dict):
        custom_timeout = httpx.Timeout(timeout=10.0, read=30.0)

        async with httpx.AsyncClient(timeout=custom_timeout) as client:
            base_url = config.get("events_base_url") or "https://api.daysmartrecreation.com/v1/events"
            now = datetime.now()
            current_year = now.year
            current_month = now.month

            for i in range(7):
                target_month = current_month + i
                target_year = current_year
                if target_month > 12:
                    target_month -= 12
                    target_year += 1

                _, last_day = calendar.monthrange(target_year, target_month)

                start_str = f"{target_year}-{target_month:02d}-01 00:00:00"
                end_str = f"{target_year}-{target_month:02d}-{last_day:02d} 23:59:59"

                print(f"🔄 Processing month batch: {target_year}-{target_month:02d}")

                base_params = {
                    "cache[save]": "false",
                    "page[size]": "100",
                    "sort": "start",
                    "company": "iceandfield",
                    "filter[start__gte]": start_str,
                    "filter[start__lte]": end_str,
                    "include": "eventType,summary,resource.facility"
                }

                # Apply the target hockey codes
                target_codes = ["10", "12", "15", "16", "17", "22", "g", "r"]
                for index, code in enumerate(target_codes):
                    base_params[f"filter[or][{index}][eventType.code]"] = code

                current_page = 1
                has_more_pages = True

                while has_more_pages:
                    params = base_params.copy()
                    params["page[number]"] = str(current_page)

                    print(f"   Fetching Page {current_page}...")
                    try:
                        response = await client.get(base_url, params=params)
                    except httpx.ReadTimeout:
                        print(f"⚠️ Page {current_page} timed out. Retrying once...")
                        await asyncio.sleep(3)
                        response = await client.get(base_url, params=params)

                    if response.status_code != 200:
                        print(f"❌ Error fetching page {current_page}: {response.status_code}")
                        break

                    payload = response.json()
                    data_list = payload.get("data", [])

                    if not data_list:
                        print(f"🛑 Found empty data payload ('data': []) at page {current_page}.")
                        break

                        # 1. Parse flat items safely
                    flat_records = self.parser.parse_page_payload(payload)

                    # 2. Save directly to the single flat table
                    if flat_records:
                        self.storage.save_flat_records(flat_records)
                        print(f"   ✅ Saved {len(flat_records)} sessions from Page {current_page}")

                    meta = payload.get("meta", {})
                    page_info = meta.get("page", {})
                    last_page = page_info.get("last-page", 1)

                    if current_page >= last_page:
                        has_more_pages = False
                    else:
                        current_page += 1
                        await asyncio.sleep(1)