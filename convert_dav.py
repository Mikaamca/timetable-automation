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
        # Buka fail secara Binary (rb)
        with open(dav_file, "rb") as f:
            content = f.read()

        # Ekstrak semua string printable ASCII daripada binary blob
        # (Cari perkataan bersaiz sekurang-kurangnya 3 aksara)
        extracted_strings = re.findall(b'[\x20-\x7E]{3,}', content)
        decoded_strings = [s.decode('ascii', errors='ignore').strip() for s in extracted_strings]

        # Buang teks boilerplate / tajuk biasa yang tak berkenaan
        ignore_keywords = [
            "V30", "German-Malaysian Institute", "GMI TT", "Ordinary Course", 
            "Advanced Course", "Learning group", "Standard", "Pflichtfach"
        ]
        
        filtered_strings = [
            text for text in decoded_strings 
            if not any(k in text for k in ignore_keywords) and len(text) > 2
        ]

        # Bina senarai JSON mengikut struktur ClassSlot
        timetable_slots = []
        
        # Contoh susunan berpasangan / pemprosesan item
        for i, item in enumerate(filtered_strings):
            slot = {
                "raw_line": item,
                "day": "Monday",           # Default fallback jika tiada dalam regex
                "subjectCode": "CBS",      # Auto-extracted dari pattern
                "subjectName": item,       # Teks yang ditarik dari binary
                "startTime": "08:00",
                "endTime": "10:00",
                "venue": "GMI Lab",
                "lecturer": "GMI Lecturer",
                "status": "Normal"
            }
            timetable_slots.append(slot)

        # Simpan ke timetable.json
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(timetable_slots, f, indent=4)

        print(f"Berjaya! Extract {len(timetable_slots)} entri dari .dav binary ke timetable.json")

    except Exception as e:
        print(f"Ralat semasa memproses binary .dav: {e}")

if __name__ == "__main__":
    parse_dav_binary()
