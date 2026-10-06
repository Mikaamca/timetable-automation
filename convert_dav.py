#!/usr/bin/env python3
"""
Convert a GMI DaVinci timetable (.dav, format V30) into timetable.json
for ONE class, in the shape the MyTimetable app's ClassSlot model expects
(a flat JSON array, one entry per lesson block, for every week of the term).

Usage:
    python convert_dav.py latest_schedule.dav timetable.json
    python convert_dav.py latest_schedule.dav timetable.json --class "SEM 5 - DCBS 5" --year 2026
    python convert_dav.py ... --subjects subjects.json   # {"CBS 2363": "Full subject name", ...}

Also writes <out>_meta.json (source file, weeks covered, warnings).

Exit codes (timetable.json is NOT touched on any failure, so the app keeps
showing the last good timetable):
    0  OK
    1  input file missing
    2  file is not the expected format (magic/version mismatch)
    3  class not found, or no lessons could be decoded
"""
import argparse
import datetime
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

MAGIC = b"\x03V30"        # header of every .dav seen so far
FIRST_PERIOD_HOUR = 8     # period 1 = 08:00, each period = 1 hour
DAY_NAMES = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_FULL = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# The .dav only stores subject CODES. Full names come from here (or --subjects).
DEFAULT_SUBJECT_NAMES = {
    "NTC 1052": "Network Management & Monitoring Systems",
    "SPG 0562": "Android Programming",
    "CBS 2363": "Digital Forensics & Incident Response",
    "CBS 2383": "Internet of Things",
    "CBS 2372": "Cryptography",
}

# id (4 bytes, high byte 0x06) + 0x02 0xff + 0x06 + len + text  ->  named object
NAME_RE = re.compile(rb"(....)\x02\xff\x06([\x01-\x60])", re.S)
# lesson header: id, -1, class, teacher, room, 0x02, number of slots
EVENT_RE = re.compile(
    rb"(....)\xff\xff\xff\xff(....)(....)(....)\x02([\x01-\x20])", re.S
)
# one slot: slot-id, lesson-id, day, period, fixed padding
SLOT_RE = re.compile(
    rb"(....)(....)([\x00-\x0f])([\x00-\x1f])\x00{7}\x01\x00{8}\x02\x00\x02\x00",
    re.S,
)
NO_REF = b"\xff\xff\xff\xff"


def read_pstr(d, p):
    """Length-prefixed string: 0x06, len, bytes. Returns (text, next_pos)."""
    if p + 2 > len(d) or d[p] != 6:
        return None, p
    n = d[p + 1]
    return d[p + 2 : p + 2 + n].decode("latin1"), p + 2 + n


def build_names(d):
    names = {}
    for m in NAME_RE.finditer(d):
        n = m.group(2)[0]
        s = d[m.end() : m.end() + n]
        if len(s) == n and all(32 <= c < 127 for c in s):
            names.setdefault(m.group(1), s.decode().strip())
    return names


def active_weeks(mask):
    """A cleared bit N means the lesson is active in ISO week N."""
    return [w for w in range(1, 54) if not (mask >> w) & 1]


def parse_class_lessons(d, names, class_name):
    ids = [k for k, v in names.items() if v == class_name]
    if not ids:
        return None
    class_id = ids[0]
    lessons = []
    for m in EVENT_RE.finditer(d):
        if m.group(2) != class_id:
            continue
        lesson_id, teacher_id, room_id = m.group(1), m.group(3), m.group(4)
        n_slots = m.group(5)[0]
        q = m.end()
        s = SLOT_RE.match(d, q)
        if not s or s.group(2) != lesson_id:
            continue
        slots = []
        while s and s.group(2) == lesson_id and len(slots) < n_slots:
            slots.append((s.group(3)[0], s.group(4)[0]))
            q = s.end() + 12          # skip: room, teacher, -1
            s = SLOT_RE.match(d, q)
        # tail: parent-id(4) + week-mask(8) + 02 00 02 00 + note + subject-id ...
        mask = struct.unpack_from("<Q", d, q + 4)[0]
        p = q + 12
        if d[p : p + 4] != b"\x02\x00\x02\x00":
            continue
        note, p = read_pstr(d, p + 4)
        subject = names.get(d[p : p + 4])
        lessons.append(
            dict(
                slots=slots,
                weeks=active_weeks(mask),
                subject=subject,
                teacher=None if teacher_id == NO_REF else names.get(teacher_id),
                room=None if room_id == NO_REF else names.get(room_id),
                note=(note or "").strip(),
            )
        )
    return lessons


def build_blocks(lessons, year):
    """Expand to per-week lessons and merge consecutive periods into blocks."""
    grouped = {}
    for les in lessons:
        for week in les["weeks"]:
            for day, period in les["slots"]:
                if day < 1 or period < 1:      # day 0 = not placed in the grid
                    continue
                key = (week, day, les["subject"], les["teacher"], les["room"], les["note"])
                grouped.setdefault(key, set()).add(period)

    blocks = []
    for (week, day, subject, teacher, room, note), periods in grouped.items():
        periods = sorted(periods)
        runs, run = [], [periods[0]]
        for x in periods[1:]:
            if x == run[-1] + 1:
                run.append(x)
            else:
                runs.append(run)
                run = [x]
        runs.append(run)
        for r in runs:
            try:
                date = datetime.date.fromisocalendar(year, week, day).isoformat()
            except ValueError:
                date = None
            blocks.append(
                {
                    "week": week,
                    "date": date,
                    "day": day,
                    "day_name": DAY_NAMES[day],
                    "start": f"{FIRST_PERIOD_HOUR - 1 + r[0]:02d}:00",
                    "end": f"{FIRST_PERIOD_HOUR + r[-1]:02d}:00",
                    "subject": subject,
                    "teacher": teacher,
                    "room": room,
                    "online": room is None and "online" in note.lower(),
                    "note": note,
                }
            )
    blocks.sort(key=lambda b: (b["week"], b["day"], b["start"]))
    return blocks


def to_class_slots(blocks, subject_names):
    """Map blocks to the app's ClassSlot JSON. Every field is a non-null string
    (Gson would otherwise inject nulls into Kotlin non-null properties)."""
    slots = []
    for b in blocks:
        note = b["note"] or ""
        if "replacement" in note.lower():
            status = "Replacement"
        elif b["online"]:
            status = "Online"
        else:
            status = "Normal"
        subject = b["subject"] or ""
        venue = b["room"] or ("Online Class" if b["online"] else "")
        teacher = b["teacher"] or "N.N."
        slots.append(
            {
                "raw_line": f"{subject} | {teacher} | {venue or 'N.N.'}" + (f" | {note}" if note else ""),
                "day": DAY_FULL[b["day"]],
                "subjectCode": subject,
                "subjectName": subject_names.get(subject, ""),
                "startTime": b["start"],
                "endTime": b["end"],
                "venue": venue,
                "lecturer": teacher,
                "status": status,
                "week": b["week"],
                "date": b["date"] or "",
                "note": note,
            }
        )
    return slots


def find_overlaps(blocks):
    warnings = []
    for i, a in enumerate(blocks):
        for b in blocks[i + 1 :]:
            if (a["week"], a["day"]) != (b["week"], b["day"]):
                continue
            if a["start"] < b["end"] and b["start"] < a["end"]:
                warnings.append(
                    f"week {a['week']} {a['day_name']}: {a['subject']} "
                    f"{a['start']}-{a['end']} overlaps {b['subject']} {b['start']}-{b['end']}"
                )
    return warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dav")
    ap.add_argument("out")
    ap.add_argument("--class", dest="class_name", default="SEM 5 - DCBS 5")
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--source-name", default=None, help="original attachment name to record in the meta file")
    ap.add_argument("--subjects", default=None, help="JSON file mapping subject code -> full name")
    args = ap.parse_args()

    path = Path(args.dav)
    if not path.is_file():
        print(f"ERROR: {path} not found; timetable.json left unchanged.", file=sys.stderr)
        return 1
    d = path.read_bytes()
    if not d.startswith(MAGIC):
        print(f"ERROR: unexpected file header {d[:8]!r}, expected {MAGIC!r}. "
              "DaVinci format may have changed; timetable.json left unchanged.",
              file=sys.stderr)
        return 2

    year = args.year
    if year is None:
        m = re.search(r"(20\d\d)", path.name)
        year = int(m.group(1)) if m else datetime.date.today().year

    names = build_names(d)
    lessons = parse_class_lessons(d, names, args.class_name)
    if not lessons:
        print(f"ERROR: class {args.class_name!r} not found or has no lessons; "
              "timetable.json left unchanged.", file=sys.stderr)
        return 3

    blocks = build_blocks(lessons, year)
    if not blocks:
        print("ERROR: no lessons decoded; timetable.json left unchanged.", file=sys.stderr)
        return 3

    subject_names = dict(DEFAULT_SUBJECT_NAMES)
    if args.subjects:
        subject_names.update(json.loads(Path(args.subjects).read_text(encoding="utf-8")))

    out_path = Path(args.out)
    slots = to_class_slots(blocks, subject_names)
    meta = {
        "class": args.class_name,
        "source_file": args.source_name or path.name,
        "source_sha256": hashlib.sha256(d).hexdigest(),
        "format": "V30",
        "year": year,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "weeks": sorted({b["week"] for b in blocks}),
        "lesson_count": len(blocks),
        "unnamed_subjects": sorted({b["subject"] for b in blocks if b["subject"] and b["subject"] not in subject_names}),
        "warnings": find_overlaps(blocks),
    }
    out_path.write_text(json.dumps(slots, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path = out_path.with_name(out_path.stem + "_meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(slots)} lessons, weeks {meta['weeks'][0]}-{meta['weeks'][-1]}, "
          f"{len(meta['warnings'])} warnings -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
