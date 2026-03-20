# import_clips.py
# Imports clip metadata from a CSV into the dailies database
# Supports Premiere, Resolve, Avid, Silverstack, and Pomfort exports

import csv
import sqlite3
from pathlib import Path
from column_map import normalize_columns
from cdl_parser import find_cdl_for_clip

# --- SETTINGS ---
CSV_FILE = Path("/Users/rachmcintire/PycharmProjects/Claude/CSV_Test.csv")
DB_FILE = Path("/Users/rachmcintire/PycharmProjects/Claude/dailies.db")
CDL_FOLDERS = ["/Users/rachmcintire/PycharmProjects/Claude/"]

def load_csv(csv_file):
    """Reads a CSV file and returns a list of normalized rows."""
    rows = []
    with open(csv_file, newline="", encoding="utf-16") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = normalize_columns(row)
            rows.append(normalized)
    return rows

def import_to_db(rows, show, episode, cdl_folders=None):
    """Imports normalized CSV rows into the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    added = 0
    skipped = 0

    for row in rows:
        file_name = row.get("file_name", "")

        # --- Skip audio-only files ---
        AUDIO_EXTENSIONS = {".wav", ".mp3", ".aiff", ".aif", ".m4a"}
        if Path(file_name).suffix.lower() in AUDIO_EXTENSIONS:
            skipped += 1
            continue

        # --- Duplicate check ---
        cursor.execute("SELECT id FROM clips WHERE file_name = ?", (file_name,))
        existing = cursor.fetchone()

        if existing:
            print(f"\n⚠️  DUPLICATE DETECTED: {file_name} already exists in the database.")
            choice = input("   Overwrite? (y/n): ").strip().lower()
            if choice != "y":
                print(f"   Skipped.")
                skipped += 1
                continue
            else:
                cursor.execute("DELETE FROM clips WHERE file_name = ?", (file_name,))

        # --- CDL lookup ---
        cdl = None
        if cdl_folders:
            cdl = find_cdl_for_clip(file_name, cdl_folders)

        # --- Insert ---
        cursor.execute("""
            INSERT INTO clips (
                file_name, show, episode, date_recorded, start_tc, end_tc, duration,
                scene, circle_take, camera_id, reel, codec, resolution, fps, bit_depth,
                audio_codec, audio_sample_rate, audio_channels, camera_type,
                camera_manufacturer, camera_serial, iso, white_balance, shutter_angle,
                lens_type, focal_length, nd_filter, location, dop, director,
                production_company, input_lut, output_lut,
                cdl_slope, cdl_offset, cdl_power, cdl_saturation, status
            ) VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'ok'
            )
        """, (
            file_name, show, episode,
            row.get("date_recorded"), row.get("start_tc"), row.get("end_tc"), row.get("duration"),
            row.get("scene"), row.get("circle_take"), row.get("camera_id"), row.get("reel"),
            row.get("codec"), row.get("resolution"), row.get("fps"), row.get("bit_depth"),
            row.get("audio_codec"), row.get("audio_sample_rate"), row.get("audio_channels"),
            row.get("camera_type"), row.get("camera_manufacturer"), row.get("camera_serial"),
            row.get("iso"), row.get("white_balance"), row.get("shutter_angle"),
            row.get("lens_type"), row.get("focal_length"), row.get("nd_filter"),
            row.get("location"), row.get("dop"), row.get("director"), row.get("production_company"),
            None, None,
            cdl["cdl_slope"] if cdl else None,
            cdl["cdl_offset"] if cdl else None,
            cdl["cdl_power"] if cdl else None,
            cdl["cdl_saturation"] if cdl else None,
        ))
        print(f"Added: {file_name}")
        added += 1

    conn.commit()
    conn.close()
    print(f"\n✅ Done — {added} clips added, {skipped} skipped.")

# --- Run ---
SHOW = input("Show name: ")
EPISODE = input("Episode: ")

rows = load_csv(CSV_FILE)
import_to_db(rows, SHOW, EPISODE, CDL_FOLDERS)