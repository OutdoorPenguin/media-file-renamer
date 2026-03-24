# folder_monitor.py
# Scans a folder of media files and logs codec, resolution, and frame rate
# Flags inconsistencies like mixed codecs, resolutions, or frame rates

import subprocess
import json
import csv
from pathlib import Path
from datetime import datetime

# --- SETTINGS ---
WATCH_FOLDER = Path("/Users/rachelmcintire/Desktop/test_folder")
LOG_FILE = Path("/Users/rachelmcintire/PycharmProjects/Claude/transcode_log.csv")
MEDIA_EXTENSIONS = {".mov", ".mp4", ".mxf", ".dpx", ".exr"}

def get_metadata(file_path):
    """Uses ffprobe to extract metadata from a media file."""
    cmd = [
        "/opt/homebrew/bin/ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def extract_video_info(data):
    """Pulls just the useful fields from ffprobe output."""
    video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if video_stream:
        return {
            "codec": video_stream.get("codec_name", "unknown"),
            "resolution": f"{video_stream.get('width')}x{video_stream.get('height')}",
            "fps": video_stream.get("r_frame_rate", "unknown"),
            "duration": video_stream.get("duration", "unknown")
        }
    return None

if __name__ == "__main__":
    # --- Scan folder and log results ---
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
                "duration": info["duration"]
            }
            log_entries.append(entry)
            print(f"{file.name} — {info['codec']} {info['resolution']} {info['fps']}fps")

    # --- Consistency checks ---
    codecs = set(e["codec"] for e in log_entries)
    resolutions = set(e["resolution"] for e in log_entries)
    fps_values = set(e["fps"] for e in log_entries)

    print("\n--- Consistency Report ---")

    if len(codecs) > 1:
        print(f"  ⚠️  Mixed codecs detected: {', '.join(codecs)}")
    else:
        print(f"  ✅  Codec consistent: {', '.join(codecs)}")

    if len(resolutions) > 1:
        print(f"  ⚠️  Mixed resolutions detected: {', '.join(resolutions)}")
    else:
        print(f"  ✅  Resolution consistent: {', '.join(resolutions)}")

    if len(fps_values) > 1:
        print(f"  ⚠️  Mixed frame rates detected: {', '.join(fps_values)}")
    else:
        print(f"  ✅  Frame rate consistent: {', '.join(fps_values)}")

    # --- Save log ---
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "file_name", "codec", "resolution", "fps", "duration"])
        writer.writeheader()
        writer.writerows(log_entries)

    print(f"\nLog saved to: {LOG_FILE}")
