# dailies_db.py
# Creates the dailies SQLite database and table schema
# Run this once to set up the database before importing clips

import sqlite3
from pathlib import Path

# --- SETTINGS ---
DB_FILE = Path("/Users/rachmcintire/PycharmProjects/Claude/dailies.db")

# --- Create database and table ---
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS clips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT,
        show TEXT,
        episode TEXT,
        date_recorded TEXT,
        start_tc TEXT,
        end_tc TEXT,
        duration TEXT,
        scene TEXT,
        circle_take TEXT,
        camera_id TEXT,
        reel TEXT,
        codec TEXT,
        resolution TEXT,
        fps REAL,
        bit_depth TEXT,
        audio_codec TEXT,
        audio_sample_rate TEXT,
        audio_channels TEXT,
        camera_type TEXT,
        camera_manufacturer TEXT,
        camera_serial TEXT,
        iso TEXT,
        white_balance TEXT,
        shutter_angle TEXT,
        lens_type TEXT,
        focal_length TEXT,
        nd_filter TEXT,
        location TEXT,
        dop TEXT,
        director TEXT,
        production_company TEXT,
        input_lut TEXT,
        output_lut TEXT,
        cdl_slope TEXT,
        cdl_offset TEXT,
        cdl_power TEXT,
        cdl_saturation TEXT,
        status TEXT
    )
""")

conn.commit()
conn.close()
print("Database created successfully.")