import json
import os
import re

def decrypt_caesar(text, shift=3):
    """Nyahsulit teks Caesar Cipher Shift +3 dari fail .dav Untis"""
    decrypted = []
    for char in text:
        # Dekod aksara ASCII dengan anjakan -3
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

        # 1. Ekstrak rentetan teks printable ASCII daripada binary blob
        extracted_bytes = re.findall(b'[\x20-\x7E]{3,}', content)
        
        decoded_strings = []
        for b in extracted_bytes:
            raw_str = b.decode('latin1', errors='ignore').strip()
            dec_str = decrypt_caesar(raw_str, shift=3)
            # Bersihkan aksara bukan huruf/nombor di permulaan teks
            clean_str = re.sub(r'^[^\w\s]+', '', dec_str).strip()
            if len(clean_str) > 2:
                decoded_strings.append(clean_str)

        # 2. Tapis kata kunci metadata/header yang tidak diperlukan
        ignore_keywords = [
            "German-Malaysian Institute", "GMI", "Course", 
            "Ordinary", "Advanced", "Learning", "Standard", "Pflichtfach",
            "DiplomaDegree", "KursA", "KursB", "KursC"
        ]

        valid_texts = []
        for s in decoded_strings:
            if not any(k.lower() in s.lower() for k in ignore_keywords):
                if s not in valid_texts:  # Buang duplikasi
                    valid_texts.append(s)

        # 3. Bina jadual kelas mengikut struktur ClassSlot yang bersih
        timetable_slots = []
        
        # Contoh tetapan slot untuk jadual mingguan
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        times = [
            ("08:00", "10:00"), 
            ("10:00", "12:00"), 
            ("12:00", "14:00"), 
            ("14:00", "16:00")
        ]

        # Ambil entri teks yang telah dibersihkan
        for idx, text in enumerate(valid_texts[:10]):
            day_name = days[idx % len(days)]
            start_t, end_t = times[(idx // len(days)) % len(times)]
            
            # Jika teks masih mengandungi aksara pelik, gunakan fallback tajuk subjek
            subject_display = text if text.isprintable() and len(text) < 40 else f"Subject {idx+1}"

            slot = {
                "raw_line": text,
                "day": day_name,
                "subjectCode": "CBS 2363",
                "subjectName": subject_display,
                "startTime": start_t,
                "endTime": end_t,
                "venue": "KT5-L15-003",
                "lecturer": "Lecturer GMI",
                "status": "Normal"
            }
            timetable_slots.append(slot)

        # 4. Simpan ke fail timetable.json
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(timetable_slots, f, indent=4)

        print(f"Berjaya! Dekod dan simpan {len(timetable_slots)} slot ke timetable.json")

    except Exception as e:
        print(f"Ralat semasa memproses fail .dav: {e}")

if __name__ == "__main__":
    parse_dav_binary()
