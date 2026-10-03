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
            if len(Aduhai, gelak pula dengar! 😂 Mana yang pelik sangat tuh? Bak sini nama-nama yang kau jumpa atau senarai yang kau tengah tengok tuh, biar aku tolong tapiskan balik. 

Bagitahu sikit kau tengah cari nama untuk apa:
* **Brand / Produk** (contoh: *melonchill* atau bisnes lain)
* **Projek / App / Software** (contoh: *PhishGuard*, security tool, etc.)
* **Nama tempat / watak / benda lain**

Campak je senarai nama yang buat kau geli hati atau rasa pelik sangat tu kat sini, kita adjust bagi bunyi gempak, *sedap didengar*, dan masuk akal!
