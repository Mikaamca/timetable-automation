import json
import os

# Skrip ringkas untuk membaca fail .dav dan menukarnya kepada timetable.json
def convert_dav_to_json():
    dav_file = "latest_schedule.dav"
    json_file = "timetable.json"

    if not os.path.exists(dav_file):
        print("Fail latest_schedule.dav tidak dijumpai.")
        return

    try:
        with open(dav_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        # CONTOH PARSER: Anda boleh selaras ikut format struktur dalaman fail .dav anda
        # Di sini kita ekstrak baris teks dan jadikan senarai JSON
        timetable_data = []
        for line in lines:
            line = line.strip()
            if line:
                timetable_data.append({"raw_line": line})

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(timetable_data, f, indent=4)

        print("Berjaya menukar .dav ke timetable.json")

    except Exception as e:
        print(f"Ralat semasa menukar fail: {e}")

if __name__ == "__main__":
    convert_dav_to_json()
