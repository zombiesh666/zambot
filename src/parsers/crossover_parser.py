from .base import BaseParser
from datetime import datetime


class CrossoverParser(BaseParser):
    def parse(self, json_data):
        sessions = json_data.get('data', [])
        extracted = []

        for item in sessions:
            raw_date = item.get('eventStartDate')
            raw_start = item.get('eventStartTime')
            raw_end = item.get('eventEndTime')

            try:
                formatted_date = raw_date.replace('/', '-')
                formatted_start = datetime.strptime(raw_start, "%H:%M:%S").strftime("%I:%M %p")
                formatted_end = datetime.strptime(raw_end, "%H:%M:%S").strftime("%I:%M %p")
            except:
                formatted_date, formatted_start, formatted_end = raw_date, raw_start, raw_end

            spaces = item.get('spaces', [])
            space_name = spaces[0].get('spaceName') if spaces else "Main Rink"

            extracted.append({
                "rink": f"Crossover - {space_name}",
                "event_name": item.get('eventName'),
                "session_name": item.get('sessionName'),
                "program_name": item.get('programName'),
                "date": formatted_date,
                "start": formatted_start,
                "end": formatted_end,
                "timezone": item.get('eventTimezone'),
                "status": item.get('status')
            })

        return extracted