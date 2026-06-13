import datetime
import requests
from src.parsers.base_parser import BaseParser


class IceAndFieldParser(BaseParser):
    def __init__(self, base_url):
        """
        Initializes the parser with the parameter-free base URL
        loaded from feeds.json.
        """
        self.base_url = base_url

    def _build_params(self):
        """
        Gathers and compiles all static and dynamic GET parameters.
        Automatically shifts the lookahead window from midnight today to exactly +90 days out.
        """
        # 1. Capture today's date at midnight local time
        today = datetime.datetime.now()
        start_date = today.strftime("%Y-%m-%d 00:00:00")

        # 2. Pure Python approach: Approximate 3 months forward using 90 days
        three_months_out = today + datetime.timedelta(days=90)
        end_date = three_months_out.strftime("%Y-%m-%d 23:59:59")

        # Initialize core parameters and sideload directives
        params = {
            "company": "iceandfield",
            "cache[save]": "false",
            "page[size]": "100",
            "filter[start__gte]": start_date,
            "filter[start__lte]": end_date,
            "include": "eventType,summary,resource.facility"
        }

        # Programmatically append the specific target event type codes
        target_codes = ["10", "12", "15", "16", "17", "22", "g", "r"]
        for index, code in enumerate(target_codes):
            params[f"filter[or][{index}][eventType.code]"] = code

        return params

    def fetch_feed_data(self):
        """
        Executes the API request using the gathered parameters.
        Returns the raw data and included nodes.
        """
        headers = {"Accept": "application/vnd.api+json"}
        query_params = self._build_params()

        print(f"🚀 Initiating request to DaySmart API...")
        print(f"📅 Dynamic Window: {query_params['filter[start__gte]']} ➔ {query_params['filter[start__lte]']}")

        response = requests.get(self.base_url, params=query_params, headers=headers)
        response.raise_for_status()

        payload = response.json()
        return payload.get("data", []), payload.get("included", [])

    def parse_records(self, events, included):
        """
        Maps, cross-references, and flattens JSON:API objects into
        denormalized dictionaries matching our database schema.
        """
        # 1. Map sideloaded metadata by (type, id) for lightning-fast matching
        included_map = {}
        for item in included:
            included_map[(item.get("type"), item.get("id"))] = item

        flat_records = []

        # 2. Extract and flatten every event entry
        for event in events:
            event_id = event.get("id")
            attrs = event.get("attributes", {})
            rels = event.get("relationships", {})

            # Match Event Type Details
            et_ref = rels.get("eventType", {}).get("data", {})
            et_id = et_ref.get("id") if et_ref else None
            et_obj = included_map.get(("eventTypes", et_id), {}) if et_id else {}
            et_attrs = et_obj.get("attributes", {})

            # Match Summary Details
            sum_ref = rels.get("summary", {}).get("data", {})
            sum_id = sum_ref.get("id") if sum_ref else None
            sum_obj = included_map.get(("summaries", sum_id), {}) if sum_id else {}
            sum_attrs = sum_obj.get("attributes", {})

            # Match Facility Details (Nested inside Resource relationships)
            res_ref = rels.get("resource", {}).get("data", {})
            res_id = res_ref.get("id") if res_ref else None
            res_obj = included_map.get(("resources", res_id), {}) if res_id else {}

            fac_ref = res_obj.get("relationships", {}).get("facility", {}).get("data", {}) if res_obj else {}
            fac_id = fac_ref.get("id") if fac_ref else None
            fac_obj = included_map.get(("facilities", fac_id), {}) if fac_id else {}
            fac_attrs = fac_obj.get("attributes", {})

            # 3. Compile everything into a single flat schema model dictionary
            flat_record = {
                "id": event_id,
                "name": attrs.get("name"),
                "start_time": attrs.get("start"),
                "end_time": attrs.get("end"),
                "open_slots": attrs.get("open_slots"),
                "registration_status": attrs.get("registration_status"),
                "event_type_id": et_id,
                "event_type_code": et_attrs.get("code"),
                "event_type_name": et_attrs.get("name"),
                "summary_id": sum_id,
                "summary_name": sum_attrs.get("name"),
                "facility_id": fac_id,
                "facility_name": fac_attrs.get("name")
            }
            flat_records.append(flat_record)

        return flat_records