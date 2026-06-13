import datetime
from src.parsers.base_parser import BaseParser


class IceAndFieldParser(BaseParser):
    def __init__(self, base_url=None):
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

        target_codes = ["10", "12", "15", "16", "17", "22", "g", "r"]
        for index, code in enumerate(target_codes):
            params[f"filter[or][{index}][eventType.code]"] = code

        return params

    def parse_page_payload(self, payload: dict) -> list[dict]:
        """
        Maps, cross-references, and flattens JSON:API nodes and sideloaded relationships.
        Corrects empty columns by targeting exact live payload attribute structures.
        """
        events = payload.get("data", [])
        included = payload.get("included", [])

        # 1. Map all sideloaded metadata by matching unique (type, id) pairs using string IDs
        included_map = {}
        for item in included:
            item_type = item.get("type")
            item_id = str(item.get("id")) if item.get("id") is not None else ""
            if item_type and item_id:
                included_map[(item_type, item_id)] = item

        flat_records = []

        # 2. Extract and link properties item by item
        for event in events:
            event_id = str(event.get("id"))
            attrs = event.get("attributes", {}) or {}
            rels = event.get("relationships", {}) or {}

            # Locate the summary object (Handles singular/plural naming variants natively)
            sum_ref = rels.get("summary", {}).get("data", {}) or {}
            sum_id = str(sum_ref.get("id", ""))
            sum_obj = included_map.get(("summary", sum_id)) or included_map.get(("summaries", sum_id)) or {}
            sum_attrs = sum_obj.get("attributes", {}) or {}

            # Locate Resource Node (Rink details linked from root event relationships)
            res_ref = rels.get("resource", {}).get("data", {}) or {}
            res_id = str(res_ref.get("id", ""))
            res_obj = included_map.get(("resource", res_id)) or included_map.get(("resources", res_id)) or {}
            res_attrs = res_obj.get("attributes", {}) or {}

            # Locate Facility Node (nested inside resource relationships hierarchy)
            fac_ref = res_obj.get("relationships", {}).get("facility", {}).get("data", {}) or {}
            fac_id = str(fac_ref.get("id", ""))
            fac_obj = included_map.get(("facility", fac_id)) or included_map.get(("facilities", fac_id)) or {}
            fac_attrs = fac_obj.get("attributes", {}) or {}

            # 3. Compile the flattened schema layout mapping the exact live keys
            flat_record = {
                "id": event_id,
                "summary_name": sum_attrs.get("name") or attrs.get("name") or attrs.get("desc") or "Unnamed Session",
                "start_time": attrs.get("start") or "",
                "end_time": attrs.get("end") or "",

                # Length/Duration in minutes is part of the root event attributes node
                "length": attrs.get("length") or 0,

                # Metrics all map safely from the matched event-summary included node attributes
                "registered_count": sum_attrs.get("registered_count") if sum_attrs.get(
                    "registered_count") is not None else 0,
                "remaining_slots": sum_attrs.get("open_slots") if sum_attrs.get("open_slots") is not None else 0,
                "registration_status": sum_attrs.get("registration_status") or attrs.get(
                    "registration_status") or "unknown",
                "composite_capacity": sum_attrs.get("composite_capacity") if sum_attrs.get(
                    "composite_capacity") is not None else 0,

                "resource_name": res_attrs.get("name") or "Unknown Rink",
                "facility_name": fac_attrs.get("name") or "Main Facility"
            }
            flat_records.append(flat_record)

        return flat_records