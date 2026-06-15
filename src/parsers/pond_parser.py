import re
from datetime import datetime
from bs4 import BeautifulSoup
from src.parsers.base_parser import BaseParser


class PondParser(BaseParser):
    def parse_html_payload(self, html_content: str, current_year: int) -> list[dict]:
        soup = BeautifulSoup(html_content, "html.parser")
        flat_records = []

        # Find all section headers
        headers = soup.find_all("div", class_="section-header")
        for header in headers:
            date_p = header.find("p", class_="section-header--left")
            if not date_p:
                continue

            date_str = date_p.get_text(strip=True)

            # Rule: Only grab events matching the current year
            if str(current_year) not in date_str:
                continue

            # Find the subsequent grid wrapper
            grid = header.find_next_sibling("div", class_="grid")
            if not grid:
                continue

            # Rule: Ignore empty grid nodes
            items = grid.find_all("div", class_="grid-item")
            if not items:
                continue

            # Parse "June 19th, Friday 2026" into a base date string
            match = re.search(r'([A-Za-z]+)\s+(\d+).*?(\d{4})', date_str)
            base_date = ""
            if match:
                month_str, day_str, year_str = match.groups()
                try:
                    parsed_date = datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y")
                    base_date = parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue

            if not base_date:
                continue

            for item in items:
                a_tag = item.find("a")
                if not a_tag:
                    continue

                # Rule: absolute URL prefixed to the href tag
                event_url = "https://the-pond-hockey-club.myshopify.com" + a_tag.get("href", "")

                p_tag = item.find("p")
                summary_name = p_tag.get_text(strip=True) if p_tag else "Unnamed Session"

                # Rule: Extract time string and convert to ISO format and calculate length
                start_time = ""
                end_time = ""
                length = 0
                time_match = re.search(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', summary_name)

                if time_match:
                    t1, t2 = time_match.groups()

                    def to_24h(t_str):
                        h, m = map(int, t_str.split(":"))
                        # Assuming hockey schedules generally default to afternoon/evening PM hours (1-11)
                        if 1 <= h <= 11:
                            h += 12
                        return f"{h:02d}:{m:02d}:00"

                    start_time_24 = to_24h(t1)
                    end_time_24 = to_24h(t2)

                    start_time = f"{base_date}T{start_time_24}"
                    end_time = f"{base_date}T{end_time_24}"

                    s_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
                    e_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S")
                    length = int((e_dt - s_dt).total_seconds() / 60)
                    if length < 0:
                        length += 24 * 60  # Handle late games crossing midnight boundaries

                # Rule: Barn unless "PT" is found
                resource_name = "Pond" if "PT" in summary_name else "Barn"

                flat_records.append({
                    "summary_name": summary_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "length": length,
                    "registered_count": 0,
                    "remaining_slots": 0,
                    "composite_capacity": 0,
                    "registration_status": "",
                    "resource_name": resource_name,
                    "facility_name": "The Pond Hockey Club",
                    "event_url": event_url
                })

        return flat_records