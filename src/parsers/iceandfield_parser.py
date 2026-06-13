import datetime
import requests
from src.parsers.base_parser import BaseParser

class IceAndFieldParser(BaseParser):
    def __init__(self, base_url):
        self.base_url = base_url

    def _build_params(self):
        """
        Gathers baseline static and dynamic parameters across the 90-day window.
        """
        today = datetime.datetime.now()
        start_date = today.strftime("%Y-%m-%d 00:00:00")
        three_months_out = today + datetime.timedelta(days=90)
        end_date = three_months_out.strftime("%Y-%m-%d 23:59:59")

        params = {
            "company": "iceandfield",
            "cache[save]": "false",
            "page[size]": "100",
            "sort": "start",
            "filter[start__gte]": start_date,
            "filter[start__lte]": end_date,
            "include": "eventType,summary,resource.facility"
        }

        # Programmatically append specific target game and session type codes
        target_codes = ["10", "12", "15", "16", "17", "22", "g", "r"]
        for index, code in enumerate(target_codes):
            params[f"filter[or][{index}][eventType.code]"] = code

        return params

    def parse_page_payload(self, payload: dict) -> list[dict]:
        """
        Maps, cross-references, and flattens JSON:API nodes and sideloaded relationships.
        """
        events = payload.get("data", [])
        included = payload.get("included", [])

        # 1. Map sideloaded metadata by unique (type, id) pairs for fast extraction
        included_map = {}
        for item in included:
            included_map[(item.get("type"), item.get("id"))] = item

        flat_records = []

        # 2. Extract and link raw properties item by item
        for event in events:
            event_id = event.get("id")
            attrs = event.get("attributes", {})
            rels = event.get("relationships", {})

            # Traverse Summary Node (event-summary attributes)
            sum_ref = rels.get("summary", {}).get("data", {})
            sum_id = sum_ref.get("id") if sum_ref else None
            sum_obj = included_map.get(("summaries", sum_id), {}) if sum_id else {}
            sum_attrs = sum_obj.get("attributes", {})

            # Traverse Resource Node (rink descriptors)
            res_ref = rels.get("resource", {}).get("data", {})
            res_id = res_ref.get("id") if res_ref else None
            res_obj = included_map.get(("resources", res_id), {}) if res_id else {}
            res_attrs = res_obj.get("attributes", {})

            # Traverse Facility Node (nested inside resource relationship layer)
            fac_ref = res_obj.get("relationships", {}).get("facility", {}).get("data", {}) if res_obj else {}
            fac_id = fac_ref.get("id") if fac_ref else None
            fac_obj = included_map.get(("facilities", fac_id), {}) if fac_id else {}
            fac_attrs = fac_obj.get("attributes", {})

            # 3. Assemble denormalized dictionary layout mapping your target parameters
            flat_record = {
                "id": event_id,
                "summary_name": sum_attrs.get("name") or attrs.get("name"),
                "start_time": attrs.get("start"),
                "end_time": attrs.get("end"),
                "length": attrs.get("length"),
                "registered_count": attrs.get("registered_count"),
                "remaining_slots": attrs.get("open_slots"),
                "registration_status": attrs.get("registration_status"),
                "composite_capacity": attrs.get("composite_capacity"),
                "resource_name": res_attrs.get("name") or "Unknown Rink",
                "facility_name": fac_attrs.get("name") or "Main Facility"
            }
            flat_records.append(flat_record)

        return flat_records