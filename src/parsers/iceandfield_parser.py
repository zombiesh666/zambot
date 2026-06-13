from src.parsers.base_parser import BaseParser


class IceAndFieldParser(BaseParser):

    def parse_facility_info(self, raw_json: dict) -> dict:
        data = raw_json.get("data", {})
        attr = data.get("attributes", {})
        return {
            "id": str(data.get("id", "1")),
            "name": attr.get("name"),
            "phone": attr.get("phone"),
            "email": attr.get("email"),
            "timezone": attr.get("tz", "America/Chicago")
        }

    def parse_event_types(self, raw_json: dict) -> list[dict]:
        parsed_types = []
        for item in raw_json.get("data", []):
            attr = item.get("attributes", {})
            parsed_types.append({
                "id": str(item.get("id")),
                "code": attr.get("code"),
                "name": attr.get("name")
            })
        return parsed_types

    def parse_sessions(self, raw_json: dict, facility_id: str = "1") -> list[dict]:
        # Dictionary mapping for context lookup inside the "included" section
        resource_lookup = {}
        for item in raw_json.get("included", []):
            if item.get("type") == "resources":
                resource_lookup[str(item.get("id"))] = item.get("attributes", {}).get("name")

        parsed_sessions = []
        for item in raw_json.get("data", []):
            attr = item.get("attributes", {})
            relationships = item.get("relationships", {})

            # Find the target rink string value ("Gold Rink"/"Silver Rink")
            res_id = str(relationships.get("resource", {}).get("data", {}).get("id", ""))
            rink_name = resource_lookup.get(res_id, "Unknown Rink")

            start_iso = attr.get("start", "")
            session_date = start_iso.split("T")[0] if "T" in start_iso else ""

            # DaySmart lists detailed capacity slots context inside summary attributes
            open_slots = attr.get("open_slots", 0)
            status = attr.get("registration_status", "unknown")

            parsed_sessions.append({
                "id": str(item.get("id")),
                "facility_id": facility_id,
                "rink_name": rink_name,
                "event_type_id": str(relationships.get("eventType", {}).get("data", {}).get("id", "")),
                "session_name": attr.get("desc"),
                "session_date": session_date,
                "session_start_time": attr.get("event_start_time"),
                "session_end_time": attr.get("end", "").split("T")[-1] if "T" in attr.get("end", "") else "",
                "open_slots": open_slots,
                "status": status
            })
        return parsed_sessions
