import re
from datetime import datetime
from bs4 import BeautifulSoup
from src.parsers.base_parser import BaseParser


class PondParser(BaseParser):
    def parse_html_payload(self, html_content: str, current_year: int) -> list[dict]:
        """Scrapes the raw Shopify HTML to extract the core session parameters."""
        soup = BeautifulSoup(html_content, "html.parser")
        flat_records = []

        headers = soup.find_all("div", class_="section-header")
        for header in headers:
            date_p = header.find("p", class_="section-header--left")
            if not date_p: continue

            date_str = date_p.get_text(strip=True)
            if str(current_year) not in date_str: continue

            grid = header.find_next_sibling("div", class_="grid")
            if not grid: continue

            items = grid.find_all("div", class_="grid-item")
            if not items: continue

            match = re.search(r'([A-Za-z]+)\s+(\d+).*?(\d{4})', date_str)
            base_date = ""
            if match:
                month_str, day_str, year_str = match.groups()
                try:
                    parsed_date = datetime.strptime(f"{month_str} {day_str} {year_str}", "%B %d %Y")
                    base_date = parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue

            if not base_date: continue

            for item in items:
                a_tag = item.find("a")
                if not a_tag: continue

                raw_href = a_tag.get("href", "")
                prod_match = re.search(r'(/products/[^/?]+)', raw_href)
                if prod_match:
                    canonical_path = prod_match.group(1)
                else:
                    canonical_path = raw_href.split("?")[0]

                event_url = "https://the-pond-hockey-club.myshopify.com" + canonical_path
                p_tag = item.find("p")
                summary_name = p_tag.get_text(strip=True) if p_tag else "Unnamed Session"

                start_time = ""
                end_time = ""
                length = 0
                time_match = re.search(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', summary_name)

                if time_match:
                    t1, t2 = time_match.groups()

                    def to_24h(t_str):
                        h, m = map(int, t_str.split(":"))
                        if 1 <= h <= 11: h += 12
                        return f"{h:02d}:{m:02d}:00"

                    start_time_24 = to_24h(t1)
                    end_time_24 = to_24h(t2)
                    start_time = f"{base_date}T{start_time_24}"
                    end_time = f"{base_date}T{end_time_24}"

                    s_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
                    e_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S")
                    length = int((e_dt - s_dt).total_seconds() / 60)
                    if length < 0: length += 24 * 60

                resource_name = "Pond" if "PT" in summary_name else "Barn"

                flat_records.append({
                    "summary_name": summary_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "length": length,
                    "skaters_registered": 0,
                    "skaters_open_slots": 0,
                    "skaters_capacity": 0,
                    "goalies_registered": 0,
                    "goalies_open_slots": 0,
                    "goalies_capacity": 0,
                    "registration_status": "unknown",
                    "resource_name": resource_name,
                    "facility_name": "The Pond Hockey Club",
                    "event_url": event_url
                })

        return flat_records

    def enrich_with_json(self, record: dict, json_payload: dict):
        """Maps the detailed variant array JSON metrics directly onto the record."""
        product = json_payload.get("product", {})
        variants = product.get("variants", [])

        if not variants: return

        # Baselines
        skater_inv = 0
        skater_cap = 22
        goalie_inv = 0
        goalie_cap = 2  # Standard baseline based on Pond JSON descriptions

        found_skater = False
        found_goalie = False

        # Dynamically map both Skater and Goalie nodes
        for variant in variants:
            v_title = variant.get("title", "")

            if "Goalie" in v_title:
                goalie_inv = variant.get("inventory_quantity", 0)
                found_goalie = True
            else:
                skater_inv = variant.get("inventory_quantity", 0)
                if "Skater" in v_title:
                    skater_cap = 20
                else:
                    skater_cap = 22
                found_skater = True

        if not found_skater and not found_goalie: return

        # Calculate exact registrations, using max(0) to prevent negative counts if oversold
        skaters_registered = max(0, skater_cap - skater_inv)
        goalies_registered = max(0, goalie_cap - goalie_inv)

        # Status Logic: Closed only if both roles are fully booked out (or if skaters are booked and no goalies exist)
        registration_status = "open"
        if skater_inv <= 0 and (not found_goalie or goalie_inv <= 0):
            registration_status = "closed"

        # Apply to database record
        record["skaters_registered"] = skaters_registered
        record["skaters_open_slots"] = skater_inv
        record["skaters_capacity"] = skater_cap

        if found_goalie:
            record["goalies_registered"] = goalies_registered
            record["goalies_open_slots"] = goalie_inv
            record["goalies_capacity"] = goalie_cap

        record["registration_status"] = registration_status