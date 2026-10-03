import json
import os
import re

def decrypt_caesar(text, shift=3):
    """Nyahsulit teks Caesar Cipher Shift +3 dari fail .dav Untis"""
    decrypted = []
    for char in text:
        # Dekod bait/aksara berasaskan ASCII shift -3
        decrypted.append(chr(ord(char) - shift))
    return "".join(decrypted)

def parse_dav_binary():
    dav_file = "latest_schedule.dav"
    json_file = "timetable.json"

    if not os.path.exists(dav_file):
        print("Fail latest_schedule.dav tidak dijumpai.")
        return

    try:
        with open(dav_file, "rb") as f:
            content = f.read()

        # Ekstrak semua rentetan teks printable ASCII daripada binary blob
        extracted_bytes = re.findall(b'[\x20-\x7E]{3,}', content)
        
        decoded_strings = []
        for b in extracted_bytes:
            raw_str = b.decode('latin1', errors='ignore').strip()
            dec_str = decrypt_caesar(raw_str, shift=3)
            decoded_strings.append(dec_str)

        # Kata kunci yang hendak diabaikan (header/metadata)
        ignore_keywords = [
            "German-Malaysian Institute", "GMI", "Course", 
            "Ordinary", "Advanced", "Learning", "Standard", "Pflichtfach"
        ]

        filtered_strings = [
            s for s in decoded_strings 
            if not any(k.lower() in s.lower() for k in ignore_keywords) and len(s) > 2
        ]

        # Susun jadual mengikut struktur ClassSlot
        timetable_slots = []
        
        # Contoh pemetaan slot jadual
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        times = [
            ("08:00", "10:00"), 
            ("10:00", "12:00"), 
            ("12:00", "14:00"), 
            ("14:00", "16:00")
        ]

        for i, item in enumerate(filtered_strings[:20]): # Hadkan entri untuk ujian
            day_idx = i % len(days)
            time_idx = (i // len(days)) % len(times)
            
            slot = {
                "raw_line": item,
                "day": days[day_idx],
                "subjectCode": "CBS 2363",
                "subjectName": item if len(item) < 30 else item[:30],
                "startTime": times[time_idx][0],
                "endTime": times[time_idx][1],
                "venue": "GMI Lab",
                "lecturer": "GMI Lecturer",
                "status": "Normal"
            }
            timetable_slots.append(slot)

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(timetable_slots, f, indent=4)

        print(f"Berjaya! Dekod dan simpan {len(timetable_slots)} slot ke timetable.json")

    except Exception as e:
        print(f"Ralat semasa memproses fail .dav: {e}")

if __name__ == "__main__":
    parse_dav_binary()
