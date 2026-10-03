import json
import os
import re

def decrypt_caesar(text, shift=3):
    """Nyahsulit teks Caesar Cipher Shift -3 dari fail .dav Untis/GMI"""
    decrypted = []
    for char in text:
        decrypted.append(chr(ord(char) - shift))
    return "".join(decrypted)

def clean_subject_name(text):
    """Saring teks supaya hanya nama subjek/kod yang bersih diambil"""
    # Buang simbol di awal/akhir
    text = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', text).strip()
    
    # Abaikan jika terlalu pendek atau terlalu panjang
    if len(text) < 3 or len(text) > 35:
        return None
        
    # Abaikan jika mengandungi susunan nombor/simbol acak (sampah offset binary)
    if re.search(r'[\d_]{3,}', text) or re.search(r'[#\$%\^&\*=\+<>\\/]', text):
        return None

    # Pastikan teks sekurang-kurangnya 60% huruf biasa
    letters = sum(c.isalpha() for c in text)
    if letters / len(text) < 0.6:
        return None

    return text

def parse_dav_binary():
    dav_file = "latest_schedule.dav"
    json_file = "timetable.json"

    if not os.path.exists(dav_file):
        print("Fail latest_schedule.dav tidak dijumpai.")
        return

    try:
        with open(dav_file, "rb") as f:
            content = f.read()

        # 1. Ekstrak teks ASCII dari binary blob
        raw_matches = re.findall(b'[\x20-\x7E]{4,}', content)
        
        # 2. Dekod & Nyahsulit
        decoded_strings = []
        for b in raw_matches:
            try:
                raw_str = b.decode('latin1', errors='ignore').strip()
                dec_str = decrypt_caesar(raw_str, shift=3)
                cleaned = clean_subject_name(dec_str)
                if cleaned:
                    decoded_strings.append(cleaned)
            except Exception:
                pass

        # 3. Senarai hitam metadata & cuti awam
        blacklist = [
            "German", "Malaysian", "Institute", "Course", "Ordinary", 
            "Advanced", "Learning", "Standard", "Pflichtfach", "DiplomaDegree", 
            "KursA", "KursB", "KursC", "VEVENT", "VCALENDAR", "Untis", "Hari",
            "Break", "Year", "Day", "Holiday", "Chinese", "Nuzul", "Eid", "Labour",
            "Thaipusam", "Wesak", "Keputeraan", "Agong"
        ]

        # 4. Tapis dan buang duplikasi
        valid_subjects = []
        for item in decoded_strings:
            if not any(b.lower() in item.lower() for b in blacklist):
                if item not in valid_subjects:
                    valid_subjects.append(item)

        # 5. Petakan secara dinamik mengikut senarai yang berjaya diproses
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        times = [
            ("08:00", "09:00"),
            ("09:00", "10:00"),
            ("10:00", "11:00"),
            ("11:00", "12:00"),
            ("12:00", "13:00"),
            ("13:00", "14:00"),
            ("14:00", "15:00"),
            ("15:00", "16:00")
        ]

        timetable_slots = []
        
        for idx, sub_name in enumerate(valid_subjects):
            day_name = days[idx % len(days)]
            start_t, end_t = times[(idx // len(days)) % len(times)]

            slot = {
                "raw_line": sub_name,
                "day": day_name,
                "subjectCode": "DCBS 5",
                "subjectName": sub_name,
                "startTime": start_t,
                "endTime": end_t,
                "venue": "KT5-L15-003",
                "lecturer": "Lecturer GMI",
                "status": "Normal"
            }
            timetable_slots.append(slot)

        # Simpan hasil dinamik
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(timetable_slots, f, indent=4)

        print(f"Berjaya! Ekstrak {len(timetable_slots)} slot dinamik ke timetable.json")

    except Exception as e:
        print(f"Ralat semasa memproses fail .dav: {e}")

if __name__ == "__main__":
    parse_dav_binary()
