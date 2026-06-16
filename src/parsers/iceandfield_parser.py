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

            length = et_attrs.get("length")
            if length is None:
                length = attr.get("length", 0)

            registered_count = sum_attrs.get("registered_count")
            if registered_count is None: registered_count = 0

            open_slots = sum_attrs.get("remaining_registration_slots")
            if open_slots is None: open_slots = sum_attrs.get("open_slots")
            if open_slots is None: open_slots = attr.get("open_slots", 0)

            composite_capacity = sum_attrs.get("composite_capacity")
            if composite_capacity is None: composite_capacity = 0

            status = sum_attrs.get("registration_status") or attr.get("registration_status", "unknown")

            flat_records.append({
                "id": item_id,
                "summary_name": session_name,
                "start_time": attr.get("start") or "",
                "end_time": attr.get("end") or "",
                "length": length,
                "skaters_registered": registered_count,
                "skaters_open_slots": open_slots,
                "skaters_capacity": composite_capacity,
                "goalies_registered": 0,
                "goalies_open_slots": 0,
                "goalies_capacity": 0,
                "registration_status": status,
                "resource_name": rink_name,
                "facility_name": facility_name
            })

        return flat_records