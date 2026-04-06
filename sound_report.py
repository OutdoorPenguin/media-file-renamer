# sound_report.py
# Parses sound report CSVs and imports into the database
# Matches to video clips by TC within 2 frames
# Supports multiple sound report formats

import csv
import sqlite3
from pathlib import Path

DB_FILE = Path("/Users/rachelmcintire/PycharmProjects/Claude/dailies.db")

def tc_to_frames(tc_string, fps=24.0):
    """Converts HH:MM:SS:FF to total frames."""
    if not tc_string:
        return None
    tc_string = tc_string.strip().replace(";", ":")
    parts = tc_string.split(":")
    if len(parts) != 4:
        return None
    try:
        h, m, s, f = [int(x) for x in parts]
        return int((h * 3600 + m * 60 + s) * fps + f)
    except:
        return None

def parse_fps(fps_string):
    """Parses fps string like '23.97 ND' or '30 ND' into a float."""
    if not fps_string:
        return 24.0
    fps_string = fps_string.strip().split()[0]
    try:
        return float(fps_string)
    except:
        return 24.0

def find_header_row(rows):
    """Finds the row index where actual data starts (after sound report header)."""
    for i, row in enumerate(rows):
        if row and row[0].strip().lower() == "file name":
            return i
    return None

def parse_sound_report(file_path):
    """
    Parses a sound report CSV and returns a list of dicts.
    Handles the multi-line header format used by most sound report software.
    """
    file_path = Path(file_path)
    rows = []

    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        raw_rows = list(reader)

    header_idx = find_header_row(raw_rows)
    if header_idx is None:
        raise ValueError("Could not find header row in sound report. Expected 'File Name' column.")

    headers = [h.strip() for h in raw_rows[header_idx]]
    data_rows = raw_rows[header_idx + 1:]

    for row in data_rows:
        if not row or not any(cell.strip() for cell in row):
            continue
        entry = {}
        for i, header in enumerate(headers):
            entry[header] = row[i].strip() if i < len(row) else ""
        rows.append(entry)

    return rows

def get_track_names(entry, headers):
    """Extracts track names from T1, T2... columns."""
    tracks = []
    for h in headers:
        if h.startswith("T") and h[1:].isdigit():
            val = entry.get(h, "").strip()
            if val and val != " ":
                tracks.append(val)
    return ", ".join(tracks)

def import_sound_report(file_path, show, fps=24.0, tolerance_frames=2):
    """
    Imports a sound report CSV into the database.
    Matches rows to clips by Start TC within tolerance.
    Returns (matched, wild, conflicts, already_imported) lists for reporting.
    """
    rows = parse_sound_report(file_path)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clips WHERE show = ?", (show,))
    clips = [dict(row) for row in cursor.fetchall()]

    # Build TC index for fast lookup
    clip_tc_index = {}
    for clip in clips:
        tc = clip.get("start_tc", "")
        if tc:
            frames = tc_to_frames(tc, fps)
            if frames is not None:
                clip_tc_index[frames] = clip_tc_index.get(frames, []) + [clip]

    matched = []
    wild = []
    conflicts = []
    already_imported = []

    # Get headers from first row
    if rows:
        headers = list(rows[0].keys())
    else:
        conn.close()
        return [], [], [], []

    try:
        for entry in rows:
            file_name = entry.get("File Name", "").strip()
            start_tc = entry.get("Start TC", "").strip()
            end_tc = entry.get("End TC", "").strip()
            scene = entry.get("Scene", "").strip()
            take = entry.get("Take", "").strip()
            sound_roll = entry.get("Tape", "").strip() or entry.get("Roll", "").strip()
            sample_rate = entry.get("Sample Rate", "").strip()
            bit_depth = entry.get("Bit Depth", "").strip()
            channels = entry.get("Channels", "").strip()
            circled = entry.get("Circled", "").strip()
            notes = entry.get("Notes", "").strip()
            track_names = get_track_names(entry, headers)

            entry_fps_str = entry.get("Frame Rate", "")
            entry_fps = parse_fps(entry_fps_str)
            if entry_fps:
                fps = entry_fps

            audio_frames = tc_to_frames(start_tc, fps)

            matching_clips = []
            if audio_frames is not None:
                for clip_frames, clip_list in clip_tc_index.items():
                    if abs(clip_frames - audio_frames) <= tolerance_frames:
                        matching_clips.extend(clip_list)

            if not matching_clips:
                # Check if this wild take was already imported
                cursor.execute(
                    "SELECT id FROM clips WHERE file_name = ? AND show = ? AND is_wild = 1",
                    (file_name, show)
                )
                if cursor.fetchone():
                    already_imported.append(file_name)
                    continue

                cursor.execute("""
                    INSERT INTO clips (file_name, show, sound_roll, sound_tc_start, sound_tc_end,
                        audio_sample_rate, bit_depth, audio_channels, sound_notes,
                        audio_track_names, scene, is_wild, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'wild')
                """, (file_name, show, sound_roll, start_tc, end_tc,
                      sample_rate, bit_depth, channels, notes, track_names, scene))
                wild.append(file_name)

            elif len(matching_clips) > 1:
                conflicts.append({
                    "audio_file": file_name,
                    "start_tc": start_tc,
                    "matches": [c["file_name"] for c in matching_clips]
                })

            else:
                clip = matching_clips[0]
                clip_id = clip["id"]

                # Skip if already imported
                if clip.get("sound_tc_start"):
                    already_imported.append(file_name)
                    continue

                circle_take = None
                if circled.lower() in ("x", "yes", "1", "true", "✓"):
                    circle_take = "true"
                elif circled.lower() in ("", " ", "no", "0", "false"):
                    circle_take = clip.get("circle_take", "")

                cursor.execute("""
                    UPDATE clips SET
                        sound_roll = ?,
                        sound_tc_start = ?,
                        sound_tc_end = ?,
                        audio_sample_rate = ?,
                        bit_depth = ?,
                        audio_channels = ?,
                        sound_notes = ?,
                        audio_track_names = ?,
                        circle_take = ?
                    WHERE id = ?
                """, (sound_roll, start_tc, end_tc, sample_rate, bit_depth,
                      channels, notes, track_names, circle_take, clip_id))
                matched.append(file_name)

        conn.commit()
        conn.close()
        return matched, wild, conflicts, already_imported

    except Exception as e:
        print(f"Error during import: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return matched, wild, conflicts, already_imported