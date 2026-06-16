import httpx
import calendar
import asyncio
from datetime import datetime
from src.parsers.iceandfield_parser import IceAndFieldParser
from src.storage.iceandfield_storage import IceAndFieldStorage
from src.parsers.chaparral_parser import ChaparralParser
from src.storage.chaparral_storage import ChaparralStorage
from src.parsers.pond_parser import PondParser
from src.storage.pond_storage import PondStorage


class SyncManager:
    def __init__(self, db_path: str):
        self.iaf_storage = IceAndFieldStorage(db_path)
        self.iaf_parser = IceAndFieldParser()

        self.chap_storage = ChaparralStorage(db_path)
        self.chap_parser = ChaparralParser()

        self.pond_storage = PondStorage(db_path)
        self.pond_parser = PondParser()

    async def sync_all_feeds(self, config: dict):
        print("🚀 Starting all aggregation pipelines...")

        iaf_url = config.get("iceandfield_feed")
        if iaf_url: await self.sync_iceandfield(iaf_url)

        chap_url = config.get("chaparral_feed")
        if chap_url: await self.sync_chaparral(chap_url)

        pond_url = config.get("pond_feed")
        if pond_url: await self.sync_pond(pond_url)

        print("✨ All aggregation pipelines finished successfully.")

    async def sync_iceandfield(self, base_url: str):
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
                    "cache[save]": "false", "page[size]": "100", "sort": "start",
                    "company": "iceandfield", "filter[start__gte]": start_str,
                    "filter[start__lte]": end_str, "include": "eventType,summary,resource.facility"
                }

                target_codes = ["10", "12", "15", "16", "17", "22", "g", "r"]
                for index, code in enumerate(target_codes):
                    base_params[f"filter[or][{index}][eventType.code]"] = code

                current_page = 1
                has_more_pages = True

                while has_more_pages:
                    params = base_params.copy()
                    params["page[number]"] = str(current_page)

                    response = None
                    # Robust 3-Attempt Retry Loop for pagination
                    for attempt in range(3):
                        try:
                            response = await client.get(base_url, params=params)
                            if response.status_code == 200:
                                break
                            elif response.status_code == 429:
                                await asyncio.sleep(2)
                            else:
                                break
                        except httpx.ReadTimeout:
                            print(f"   ⚠️ Page {current_page} timed out. Retrying (attempt {attempt + 1}/3)...")
                            await asyncio.sleep(2)
                        except Exception as e:
                            print(f"   ⚠️ Request error on page {current_page}: {e}")
                            await asyncio.sleep(2)

                    # Hard break if the server remains unresponsive after 3 attempts
                    if not response or response.status_code != 200:
                        print(f"❌ Failed to fetch page {current_page}. Skipping remaining pages for this month.")
                        break

                    payload = response.json()
                    data_list = payload.get("data", [])

                    if not data_list: break

                    flat_records = self.iaf_parser.parse_page_payload(payload)

                    if flat_records:
                        self.iaf_storage.save_flat_records(flat_records)
                        print(f"   ✅ Saved {len(flat_records)} sessions from Page {current_page}")

                    meta = payload.get("meta", {})
                    last_page = meta.get("page", {}).get("last-page", 1)

                    if current_page >= last_page:
                        has_more_pages = False
                    else:
                        current_page += 1
                        await asyncio.sleep(1)

    async def sync_chaparral(self, base_url: str):
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
                    "cache[save]": "false", "page[size]": "100", "sort": "start",
                    "company": "chaparralice", "filter[start__gte]": start_str,
                    "filter[start__lte]": end_str, "include": "eventType,summary,resource.facility"
                }

                chap_codes = ["13", "g", "9", "12", "6", "r"]
                for index, code in enumerate(chap_codes):
                    base_params[f"filter[or][{index}][eventType.code]"] = code

                current_page = 1
                has_more_pages = True

                while has_more_pages:
                    params = base_params.copy()
                    params["page[number]"] = str(current_page)

                    response = None
                    # Robust 3-Attempt Retry Loop
                    for attempt in range(3):
                        try:
                            response = await client.get(base_url, params=params)
                            if response.status_code == 200:
                                break
                            elif response.status_code == 429:
                                await asyncio.sleep(2)
                            else:
                                break
                        except httpx.ReadTimeout:
                            print(f"   ⚠️ Page {current_page} timed out. Retrying (attempt {attempt + 1}/3)...")
                            await asyncio.sleep(2)
                        except Exception as e:
                            print(f"   ⚠️ Request error on page {current_page}: {e}")
                            await asyncio.sleep(2)

                    if not response or response.status_code != 200:
                        print(f"❌ Failed to fetch page {current_page}. Skipping remaining pages for this month.")
                        break

                    payload = response.json()
                    data_list = payload.get("data", [])

                    if not data_list: break

                    flat_records = self.chap_parser.parse_page_payload(payload)

                    if flat_records:
                        self.chap_storage.save_flat_records(flat_records)
                        print(f"   ✅ Chaparral: Saved {len(flat_records)} sessions from Page {current_page}")

                    meta = payload.get("meta", {})
                    last_page = meta.get("page", {}).get("last-page", 1)

                    if current_page >= last_page:
                        has_more_pages = False
                    else:
                        current_page += 1
                        await asyncio.sleep(1)

    async def sync_pond(self, base_url: str):
        custom_timeout = httpx.Timeout(timeout=10.0, read=30.0)
        async with httpx.AsyncClient(timeout=custom_timeout, follow_redirects=True) as client:
            print(f"🔄 Pond: Fetching HTML target -> {base_url}")
            try:
                response = await client.get(base_url)
                if response.status_code == 200:
                    current_year = datetime.now().year
                    flat_records = self.pond_parser.parse_html_payload(response.text, current_year)

                    if flat_records:
                        print(f"   🔄 Pond: Fetching capacity JSON for {len(flat_records)} sessions...")
                        for record in flat_records:
                            event_url = record.get("event_url")
                            if event_url:
                                json_url = f"{event_url}.json"
                                fetched = False

                                for attempt in range(3):
                                    try:
                                        j_res = await client.get(json_url)
                                        if j_res.status_code == 200:
                                            self.pond_parser.enrich_with_json(record, j_res.json())
                                            fetched = True
                                            break
                                        elif j_res.status_code == 429:
                                            await asyncio.sleep(2)
                                        else:
                                            break
                                    except httpx.ReadTimeout:
                                        await asyncio.sleep(1)
                                    except Exception as e:
                                        if attempt == 2:
                                            print(f"   ⚠️ Pond JSON Network Error ({json_url}): {e}")
                                        await asyncio.sleep(1)

                                if not fetched:
                                    print(f"   ⚠️ Could not fetch capacity data for {json_url}")

                                await asyncio.sleep(0.5)

                        self.pond_storage.save_flat_records(flat_records)
                        print(f"   ✅ Pond: Saved {len(flat_records)} sessions")
                    else:
                        print(f"   ⚠️ Pond: Parsed payload contained zero current-year sessions.")
                else:
                    print(f"❌ Error fetching Pond HTML: {response.status_code}")
            except Exception as e:
                print(f"❌ Critical exception parsing Pond feed: {e}")