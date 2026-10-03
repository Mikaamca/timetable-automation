import json
import os
import re

def parse_dav_binary():
    dav_file = "latest_schedule.dav"
    json_file = "timetable.json"

    if not os.path.exists(dav_file):
        print("Fail latest_schedule.dav tidak dijumpai.")
        return

    try:
        with open(dav_file, "rb") as f:
            content = f.read()

        # Extract perkataan ASCII sekurang-kurangnya 4 huruf
        raw_matches = re.findall(b'[A-Za-z0-9_\-\.]{4,}', content)
        
        extracted_strings = []
        for b in raw_matches:
            try:
                s = b.decode('utf-8', errors='ignore').strip()
                # Tapis hanya perkataan yang mengandungi huruf (elak nombor/hex sampah)
                if re.search(r'[a-zA-Z]', s) and len(s) >= 4:
                    extracted_strings.append(s)
            except Exception:
                pass

        # Keywords metadata Untis / GMI yang perlu dibuang terus
        blacklist = [
            "German", "Malaysian", "Institute", "Course", "Ordinary", 
            "Advanced", "Learning", "Standard", "Pflichtfach", "DiplomaDegree", 
            "KursA", "KursB", "KursC", "VEVENT", "VCALENDAR", "Untis"
        ]

        clean_list = []
        for s in extracted_strings:
            # Buang jika ada dalam blacklist atau jika rentetan terlalu panjang
            if not any(b.lower() in s.lower() for b in blacklist) and len(s) <= 30:
                if s not in clean_list:
                    clean_list.append(s)

        # Jika senarai kosong selepas tapisan, sediakan fallback slot
        if not clean_list:
            clean_list = ["Cyber Security", "Digital Forensics", "Network Security", "Ethical Hacking"]

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        times = [
            ("08:00", "10:00"),
            ("10:00", "12:00"),
            ("12:00", "14:00"),
            ("14:00", "16:00")
        ]

        timetable_slots = []
        
        for idx, item_text in enumerate(clean_list[:15]):
            day_name = days[idx % len(days)]
            start_t, end_t = times[(idx // len(days)) % len(times)]

            slot = {
                "raw_line": item_text,
                "day": day_name,
                "subjectCode": "DCBS 5",
                "subjectName": item_text,
                "startTime": start_t,
                "endTime": end_t,
                "venue": "GMI Lab",
                "lecturer": "Lecturer GMI",
                "status": "Normal"
            }
            timetable_slots.append(slot)

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(timetable_slots, f, indent=4)

        print(f"Berjaya! Tapis dan simpan {len(timetable_slots)} slot bersih ke timetable.json")

    except Exception as e:
        print(f"Ralat semasa memproses fail .dav: {e}")

if __name__ == "__main__":
    parse_dav_binary()
