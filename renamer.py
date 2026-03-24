# renamer.py
# Batch renames media files to camera roll convention (e.g. A001C001.mov)
# Logs every rename to a CSV file for reference

from pathlib import Path
import csv
from datetime import datetime

# --- SETTINGS — edit these before running ---
FOLDER = Path("/Users/rachelmcintire/Desktop/test_folder")
CAMERA = "A"       # Camera letter (A, B, C...)
REEL = 1           # Starting reel number
CLIP = 1           # Starting clip number
DRY_RUN = True     # True = preview only. Change to False to actually rename.

# --- File types to include ---
MEDIA_EXTENSIONS = {".mov", ".mp4", ".mxf", ".dpx", ".exr", ".jpg", ".jpeg"}

# --- Find and sort all media files in the folder ---
files = sorted([f for f in FOLDER.iterdir() if f.suffix.lower() in MEDIA_EXTENSIONS])

if not files:
    print("No media files found. Check folder path and try again.")
else:
    log_entries = []

    for i, file in enumerate(files):
        # Build the new filename
        new_name = f"{CAMERA}{REEL:03d}C{CLIP + i:03d}{file.suffix.lower()}"
        new_path = FOLDER / new_name

        if DRY_RUN:
            print(f"[DRY RUN] {file.name}  →  {new_name}")
        else:
            file.rename(new_path)
            print(f"Renamed: {file.name}  →  {new_name}")
            log_entries.append({
                "timestamp": datetime.now().isoformat(),
                "original": file.name,
                "renamed": new_name
            })

    # Save log to CSV (only when not a dry run)
    if not DRY_RUN and log_entries:
        log_file = FOLDER / "rename_log.csv"
        with open(log_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "original", "renamed"])
            writer.writeheader()
            writer.writerows(log_entries)
        print(f"\nLog saved to: {log_file}")