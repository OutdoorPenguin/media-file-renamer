# folder_monitor.py
# Scans a folder of media files and logs codec, resolution, and frame rate
# Flags inconsistencies like mixed codecs, resolutions, or frame rates

import subprocess
import json
import csv
import re
from pathlib import Path
from datetime import datetime

# --- SETTINGS ---
WATCH_FOLDER = Path("/Users/rachelmcintire/Desktop/test_folder")
LOG_FILE = Path("/Users/rachelmcintire/PycharmProjects/Claude/transcode_log.csv")
MEDIA_EXTENSIONS = {".mov", ".mp4", ".mxf", ".dpx", ".exr"}

def get_metadata(file_path):
    """Uses ffprobe to extract metadata from a media file — streams and format."""
    cmd = [
        "/opt/homebrew/bin/ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return {"streams": [], "format": {}}

def parse_date_from_filename(filename):
    """
    Tries to extract a date from common camera filename patterns.
    ARRI: DW0001C004_251020_113048 → 251020 = 20 Oct 2025
    """
    # ARRI pattern: XXXXXX_YYMMDD_HHMMSS
    match = re.search(r'_(\d{2})(\d{2})(\d{2})_\d{6}', filename)
    if match:
        day, month, year = match.groups()
        try:
            return f"20{year}-{month}-{day}"
        except:
            pass
    return None

def extract_video_info(data):
    """Pulls all useful fields from ffprobe output including format tags."""
    streams = data.get("streams", [])
    format_data = data.get("format", {})
    format_tags = format_data.get("tags", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    if not video_stream:
        return None

    # --- Video ---
    codec_name = video_stream.get("codec_name", "unknown")
    profile = video_stream.get("profile", "")
    codec = f"{codec_name} {profile}".strip() if profile else codec_name

    resolution = f"{video_stream.get('width')}x{video_stream.get('height')}"
    fps = video_stream.get("r_frame_rate", "unknown")
    duration = video_stream.get("duration") or format_data.get("duration", "")
    bit_depth = video_stream.get("bits_per_raw_sample", "")
    color_space = video_stream.get("color_space", "")

    # --- Timecode ---
    # Check stream tags first, then format tags
    timecode = None
    for stream in streams:
        tags = stream.get("tags", {})
        for key in ["timecode", "TIMECODE", "time_code"]:
            if key in tags:
                timecode = tags[key]
                break
    if not timecode:
        for key in ["timecode", "TIMECODE", "time_code"]:
            if key in format_tags:
                timecode = format_tags[key]
                break

    # --- Date ---
    date_recorded = None
    mod_date = format_tags.get("modification_date", "")
    if mod_date:
        try:
            date_recorded = mod_date.split("T")[0]
        except:
            pass

    # --- Camera info ---
    camera_manufacturer = format_tags.get("company_name", "")
    camera_type = format_tags.get("product_name", "")

    # --- Audio ---
    audio_codec = ""
    audio_sample_rate = ""
    audio_channels = 0
    audio_bit_depth = ""

    if audio_streams:
        first_audio = audio_streams[0]
        audio_codec = first_audio.get("codec_name", "")
        audio_sample_rate = first_audio.get("sample_rate", "")
        audio_channels = len(audio_streams)  # count of audio streams = channels in MXF
        audio_bit_depth = str(first_audio.get("bits_per_sample", ""))

    return {
        "codec": codec,
        "resolution": resolution,
        "fps": fps,
        "duration": duration,
        "bit_depth": bit_depth,
        "color_space": color_space,
        "start_tc": timecode,
        "date_recorded": date_recorded,
        "camera_manufacturer": camera_manufacturer,
        "camera_type": camera_type,
        "audio_codec": audio_codec,
        "audio_sample_rate": audio_sample_rate,
        "audio_channels": str(audio_channels),
        "audio_bit_depth": audio_bit_depth,
    }


if __name__ == "__main__":
    files = [f for f in WATCH_FOLDER.iterdir() if f.suffix.lower() in MEDIA_EXTENSIONS]
    log_entries = []

    for file in sorted(files):
        data = get_metadata(file)
        info = extract_video_info(data)

        if info:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "file_name": file.name,
                "codec": info["codec"],
                "resolution": info["resolution"],
                "fps": info["fps"],
                "duration": info["duration"],
                "start_tc": info["start_tc"],
                "date_recorded": info["date_recorded"],
                "camera_type": info["camera_type"],
            }
            log_entries.append(entry)
            print(f"{file.name} — {info['codec']} {info['resolution']} {info['fps']}fps TC:{info['start_tc']}")

    codecs = set(e["codec"] for e in log_entries)
    resolutions = set(e["resolution"] for e in log_entries)
    fps_values = set(e["fps"] for e in log_entries)

    print("\n--- Consistency Report ---")
    print(f"  {'⚠️  Mixed codecs' if len(codecs) > 1 else '✅  Codec consistent'}: {', '.join(codecs)}")
    print(f"  {'⚠️  Mixed resolutions' if len(resolutions) > 1 else '✅  Resolution consistent'}: {', '.join(resolutions)}")
    print(f"  {'⚠️  Mixed frame rates' if len(fps_values) > 1 else '✅  Frame rate consistent'}: {', '.join(fps_values)}")

    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(log_entries[0].keys()) if log_entries else [])
        writer.writeheader()
        writer.writerows(log_entries)

    print(f"\nLog saved to: {LOG_FILE}")