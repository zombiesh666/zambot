from src.parsers.base_parser import BaseParser


class IceAndFieldParser(BaseParser):
    def parse_page_payload(self, raw_json: dict) -> list[dict]:
        included = raw_json.get("included", []) or []

        included_map = {}
        for item in included:
            i_type = item.get("type")
            i_id = str(item.get("id"))
            if i_type not in included_map:
                included_map[i_type] = {}
            included_map[i_type][i_id] = item

        flat_records = []
        for item in raw_json.get("data", []) or []:
            item_id = str(item.get("id"))
            attr = item.get("attributes", {}) or {}
            rels = item.get("relationships", {}) or {}

            res_id = str(rels.get("resource", {}).get("data", {}).get("id", ""))
            res_obj = included_map.get("resources", {}).get(res_id, {})
            res_attrs = res_obj.get("attributes", {}) or {}
            res_rels = res_obj.get("relationships", {}) or {}
            rink_name = res_attrs.get("name") or "Unknown Rink"

            fac_ref = res_rels.get("facility", {}).get("data", {}) or {}
            fac_id = str(fac_ref.get("id", ""))
            fac_obj = included_map.get("facilities", {}).get(fac_id, {})
            fac_attrs = fac_obj.get("attributes", {}) or {}
            facility_name = fac_attrs.get("name") or "Main Facility"

            et_id = str(rels.get("eventType", {}).get("data", {}).get("id", ""))
            et_obj = included_map.get("event-types", {}).get(et_id, {})
            et_attrs = et_obj.get("attributes", {}) or {}

            sum_obj = included_map.get("event-summaries", {}).get(item_id, {})
            if not sum_obj:
                sum_id = str(rels.get("summary", {}).get("data", {}).get("id", ""))
                sum_obj = included_map.get("event-summaries", {}).get(sum_id, {})
            sum_attrs = sum_obj.get("attributes", {}) or {}

            session_name = sum_attrs.get("name") or attr.get("desc") or attr.get("name") or "Unnamed Session"

            # --- Event Type Mapping ---
            event_type_str = "unknown"
            if et_id == "10":
                event_type_str = "public"
            elif et_id in ["12", "15", "16", "17"]:
                event_type_str = "dropin"
            elif et_id == "22":
                event_type_str = "stickandpuck"

            raw_length = et_attrs.get("length") or attr.get("length", 0)
            length_minutes = 0

            if isinstance(raw_length, str) and ":" in raw_length:
                parts = raw_length.split(":")
                if len(parts) >= 2:
                    length_minutes = int(parts[0]) * 60 + int(parts[1])
            else:
                try:
                    length_minutes = int(float(raw_length) * 60)
                except (ValueError, TypeError):
                    length_minutes = 0

            registered_count = sum_attrs.get("registered_count")
            if registered_count is None: registered_count = 0

            status = sum_attrs.get("registration_status") or attr.get("registration_status", "unknown")

            # --- Dynamic Capacity Normalization Fallback Matrix ---
            # Resolves feed anomalies where slot availability or capacities drop to -1
            is_crossover = "crossover" in facility_name.lower()
            session_lower = session_name.lower()

            if event_type_str == "public" and is_crossover:
                composite_capacity = 250
                skaters_open_slots = max(0, composite_capacity - registered_count)
            elif event_type_str == "stickandpuck" and is_crossover:
                composite_capacity = 25
                skaters_open_slots = max(0, composite_capacity - registered_count)
            elif event_type_str == "dropin" and is_crossover and (
                    "first responders drop-in" in session_lower or "adult drop-in" in session_lower):
                composite_capacity = 20
                skaters_open_slots = max(0, composite_capacity - registered_count)
            else:
                composite_capacity = sum_attrs.get("composite_capacity")
                if composite_capacity is None: composite_capacity = 0

                skaters_open_slots = sum_attrs.get("remaining_registration_slots")
                if skaters_open_slots is None: skaters_open_slots = sum_attrs.get("open_slots")
                if skaters_open_slots is None: skaters_open_slots = attr.get("open_slots", 0)

                if skaters_open_slots <= -1:
                    skaters_open_slots = max(0, composite_capacity - registered_count)

            start_time_iso = attr.get("start") or ""
            end_time_iso = attr.get("end") or ""

            start_date = start_time_iso.split("T")[0] if "T" in start_time_iso else start_time_iso.split(" ")[0]
            end_date = end_time_iso.split("T")[0] if "T" in end_time_iso else end_time_iso.split(" ")[0]
            if not end_date: end_date = start_date

            event_url = ""
            if start_date and et_id:
                event_url = f"https://apps.daysmartrecreation.com/dash/x/#/online/iceandfield/calendar?location=1&start={start_date}&end={end_date}&event_type={et_id}"

            flat_records.append({
                "id": item_id,
                "summary_name": session_name,
                "start_time": start_time_iso,
                "end_time": end_time_iso,
                "length": length_minutes,
                "skaters_registered": registered_count,
                "skaters_open_slots": skaters_open_slots,
                "skaters_capacity": composite_capacity,
                "goalies_registered": 0,
                "goalies_open_slots": 0,
                "goalies_capacity": 0,
                "registration_status": status,
                "resource_name": rink_name,
                "facility_name": facility_name,
                "event_url": event_url,
                "event_type": event_type_str
            })

        return flat_records