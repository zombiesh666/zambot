import httpx
import calendar
import asyncio
from datetime import datetime
from src.parsers.iceandfield_parser import IceAndFieldParser
from src.storage.iceandfield_storage import IceAndFieldStorage
from src.parsers.chaparral_parser import ChaparralParser
from src.storage.chaparral_storage import ChaparralStorage


class SyncManager:
    def __init__(self, db_path: str):
        # Ice & Field Instances
        self.iaf_storage = IceAndFieldStorage(db_path)
        self.iaf_parser = IceAndFieldParser()

        # Chaparral Ice Instances
        self.chap_storage = ChaparralStorage(db_path)
        self.chap_parser = ChaparralParser()

    async def sync_all_feeds(self, config: dict):
        """
        Orchestrates sequential execution loops to completely refresh
        schedules across all configured arena platforms.
        """
        print("🚀 Starting all aggregation pipelines...")

        # 1. Run Ice & Field Pipeline
        iaf_url = config.get("iceandfield_feed") or "https://api.daysmartrecreation.com/v1/events"
        await self.sync_iceandfield(iaf_url)

        # 2. Run Chaparral Ice Pipeline
        chap_url = config.get("chaparral_feed") or "https://api.daysmartrecreation.com/v1/events"
        await self.sync_chaparral(chap_url)

        print("✨ All aggregation pipelines finished successfully.")

    async def sync_iceandfield(self, base_url: str):
        """
        Calculates a dynamic rolling 7-month date range, handles inner-page
        pagination, and flattens Ice & Field sessions into a single table.
        """
        custom_timeout = httpx.Timeout(timeout=10.0, read=30.0)

        async with httpx.AsyncClient(timeout=custom_timeout) as client:
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

                print(f"🔄 IceAndField: Processing month batch: {target_year}-{target_month:02d}")

                base_params = {
                    "cache[save]": "false",
                    "page[size]": "100",
                    "sort": "start",
                    "company": "iceandfield",
                    "filter[start__gte]": start_str,
                    "filter[start__lte]": end_str,
                    "include": "eventType,summary,resource.facility"
                }

                # Apply the target hockey codes for Ice & Field
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
                        print(f"🛑 Found empty data payload at page {current_page}.")
                        break

                    flat_records = self.iaf_parser.parse_page_payload(payload)

                    if flat_records:
                        self.iaf_storage.save_flat_records(flat_records)
                        print(f"   ✅ Saved {len(flat_records)} sessions from Page {current_page}")

                    meta = payload.get("meta", {})
                    page_info = meta.get("page", {})
                    last_page = page_info.get("last-page", 1)

                    if current_page >= last_page:
                        has_more_pages = False
                    else:
                        current_page += 1
                        await asyncio.sleep(1)

    async def sync_chaparral(self, base_url: str):
        """
        Calculates a dynamic rolling 7-month date range, handles inner-page
        pagination, and flattens Chaparral Ice sessions into a prefixed flat table.
        """
        custom_timeout = httpx.Timeout(timeout=10.0, read=30.0)

        async with httpx.AsyncClient(timeout=custom_timeout) as client:
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

                print(f"🔄 Chaparral: Processing month batch: {target_year}-{target_month:02d}")

                base_params = {
                    "cache[save]": "false",
                    "page[size]": "100",
                    "sort": "start",
                    "company": "chaparralice",
                    "filter[start__gte]": start_str,
                    "filter[start__lte]": end_str,
                    "include": "eventType,summary,resource.facility"
                }

                # Apply the target hockey codes specific to Chaparral Ice
                chap_codes = ["13", "g", "9", "12", "6", "r"]
                for index, code in enumerate(chap_codes):
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
                        print(f"🛑 Found empty data payload at page {current_page}.")
                        break

                    flat_records = self.chap_parser.parse_page_payload(payload)

                    if flat_records:
                        self.chap_storage.save_flat_records(flat_records)
                        print(f"   ✅ Chaparral: Saved {len(flat_records)} sessions from Page {current_page}")

                    meta = payload.get("meta", {})
                    page_info = meta.get("page", {})
                    last_page = page_info.get("last-page", 1)

                    if current_page >= last_page:
                        has_more_pages = False
                    else:
                        current_page += 1
                        await asyncio.sleep(1)