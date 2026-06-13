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
        """
        Calculates a dynamic rolling 6-month date range, handles inner-page
        pagination, and intelligently halts early if a month returns no events.
        """
        custom_timeout = httpx.Timeout(timeout=10.0, read=30.0)

        async with httpx.AsyncClient(timeout=custom_timeout) as client:
            # 1. Sync Facility Metadata
            info_res = await client.get(config["info_url"])
            if info_res.status_code == 200:
                facility = self.parser.parse_facility_info(info_res.json())
                self.storage.save_facility_info(facility)

            # 2. Sync Event Types Reference Lookup
            types_res = await client.get(config["event_types_url"])
            if types_res.status_code == 200:
                event_types = self.parser.parse_event_types(types_res.json())
                self.storage.save_event_types(event_types)

            # 3. Dynamic Rolling Month + Paginated Loop with Early Exit Guard
            base_url = config["events_base_url"]
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

                print(f"🔄 Processing month batch: {target_year}-{target_month:02d} ({start_str} to {end_str})")

                base_params = {
                    "cache[save]": "false",
                    "page[size]": "100",
                    "sort": "start",
                    "company": "iceandfield",
                    "filter[start__gte]": start_str,
                    "filter[start__lte]": end_str,
                    "filter[resource.facility.my_sam_visible]": "true",
                    "filter[eventType.code__not]": "L",
                    "filter[resource.facility.id]": config.get("facility_id", "1"),
                    "filterRelations[comments.comment_type]": "public",
                    "include": "homeTeam.league.programType,visitingTeam.league.programType,summary,resource.facility,resourceArea,comments,eventType"
                }

                current_page = 1
                has_more_pages = True
                month_has_data = True

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

                    # 🛑 EARLY EXIT CHECK: If the page returns an empty data array
                    if not data_list:
                        print(f"🛑 Found empty data payload ('data': []) at page {current_page}.")
                        print(f"   No further schedules are published yet. Halting monthly iteration.")
                        month_has_data = False
                        break  # Breaks out of the inner pagination 'while' loop

                    sessions = self.parser.parse_sessions(payload, facility_id=config.get("facility_id", "1"))
                    if sessions:
                        self.storage.save_sessions(sessions)
                        print(f"   ✅ Saved {len(sessions)} sessions from Page {current_page}")

                    meta = payload.get("meta", {})
                    page_info = meta.get("page", {})
                    last_page = page_info.get("last-page", 1)

                    if current_page >= last_page:
                        has_more_pages = False
                    else:
                        current_page += 1
                        await asyncio.sleep(1)