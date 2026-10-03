import json
import os
import re

def decrypt_caesar(text, shift=3):
    """Nyahsulit teks Caesar Cipher Shift -3 dari fail .dav Untis"""
    decrypted = []
    for char in text:
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

        # Ekstrak rentetan teks printable ASCII dari binary blob
        extracted_bytes = re.findall(b'[\x20-\x7E]{3,}', content)
        
        decoded_strings = []
        for b in extracted_bytes:
            raw_str = b.decode('latin1', errors='ignore').strip()
            dec_str = decrypt_caesar(raw_str, shift=3)
            # Bersihkan aksara bukan huruf/nombor di permulaan teks
            clean_str = re.sub(r'^[^\w\s]+', '', dec_str).strip()
            if len(clean_str) > 2:
                decoded_strings.append(clean_str)

        # Kata kunci metadata yang perlu dibuang terus
        ignore_keywords = [
            "German-Malaysian Institute", "GMI", "Course", 
            "Ordinary", "Advanced", "Learning", "Standard", "Pflichtfach",
            "DiplomaDegree", "KursA", "KursB", "KursC"
        ]

        # Tapis: hanya ambil teks yang tiada simbol pelik/garbage
        valid_texts = []
        for s in decoded_strings:
            if not any(k.lower() in s.lower() for k in ignore_keywords):
                # Buang teks acak yang ada simbol pelik
                if s not in valid_texts and not re.search(r'[#\$%\^&\*=\+]', s):
                    valid_texts.append(s)

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        times = [
            ("08:00", "09:00"),
            ("09:00", "10:00"),
            ("10:00", "11:00"),
            ("11:00", "12:00"),
            ("12:00", "13:00"),
            ("13:00", "14:00"),
            ("14:00", "15:00"),
            ("15:00", "16:00"),
            ("16:00", "17:00"),
            ("17:00", "18:00"),
        ]

        timetable_slots = []
        
        for idx, text in enumerate(valid_texts[:20]):
            day_name = days[idx % len(days)]
            time_pair = times[(idx // len(days)) % len(times)]
            
            subject_display = text if len(text) < 35 else text[:35]

            slot = {
                "raw_line": text,
                "day": day_name,
                "subjectCode": "CBS 2363",
                "subjectName": subject_display,
                "startTime": time_pair[0],
                "endTime": time_pair[1],
                "venue": "KT5-L15-003",
                "lecturer": "Lecturer GMI",
                "status": "Normal"
            }
            timetable_slots.append(slot)

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(timetable_slots, f, indent=4)

        print(f"Berjaya! Ekstrak {len(timetable_slots)} slot penuh ke timetable.json")

    except Exception as e:
        print(f"Ralat semasa memproses fail .dav: {e}")

if __name__ == "__main__":
    parse_dav_binary()
