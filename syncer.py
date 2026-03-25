# syncer.py
# Handles audio/video sync using timecode matching
# Supports TC match, dual system, scratch replacement, and manual offset

import subprocess
import json
import re
from pathlib import Path

FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"


def tc_to_frames(tc_string, fps=24.0):
    """Converts a timecode string (HH:MM:SS:FF) to total frames."""
    tc_string = tc_string.strip().replace(";", ":")  # handle drop frame semicolons
    parts = tc_string.split(":")
    if len(parts) != 4:
        return None
    try:
        h, m, s, f = [int(x) for x in parts]
        return int((h * 3600 + m * 60 + s) * fps + f)
    except:
        return None


def frames_to_seconds(frames, fps=24.0):
    """Converts frames to seconds."""
    return frames / fps


def get_timecode(file_path):
    """Extracts timecode from a media file using ffprobe."""
    file_path = Path(file_path)
    if not file_path.exists():
        return None, None

    cmd = [
        FFPROBE, "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        data = json.loads(result.stdout)
    except:
        return None, None

    fps = 24.0

    # Get FPS from video stream
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            fps_str = stream.get("r_frame_rate", "24/1")
            try:
                num, den = fps_str.split("/")
                fps = float(num) / float(den)
            except:
                pass
            break

    # Check stream tags for timecode
    for stream in data.get("streams", []):
        tags = stream.get("tags", {})
        for key in ["timecode", "TIMECODE", "time_code"]:
            if key in tags:
                return tags[key], fps

    # Check format tags
    tags = data.get("format", {}).get("tags", {})
    for key in ["timecode", "TIMECODE", "time_code"]:
        if key in tags:
            return tags[key], fps

    return None, fps


def calculate_offset(video_tc, audio_tc, fps=24.0):
    """
    Calculates the offset in seconds between video and audio timecodes.
    Positive offset means audio starts after video (audio needs to be delayed).
    Negative offset means audio starts before video (audio needs to be trimmed).
    """
    video_frames = tc_to_frames(video_tc, fps)
    audio_frames = tc_to_frames(audio_tc, fps)

    if video_frames is None or audio_frames is None:
        return None

    offset_frames = audio_frames - video_frames
    return frames_to_seconds(offset_frames, fps)


def sync_audio(video_path, audio_path, output_path, offset_seconds=0.0,
               audio_channels=None, embed=True):
    """
    Syncs audio to video using the calculated offset.

    offset_seconds: positive = delay audio, negative = trim audio
    audio_channels: list of channel indices to include, None = all
    embed: True = embed audio in video file, False = create separate audio file
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)

    if not video_path.exists():
        return False, f"Video file not found: {video_path}"
    if not audio_path.exists():
        return False, f"Audio file not found: {audio_path}"

    if embed:
        # Embed audio into video
        cmd = [FFMPEG, "-y"]
        cmd += ["-i", str(video_path)]

        if offset_seconds >= 0:
            # Delay audio by offset
            cmd += ["-itsoffset", str(offset_seconds)]
            cmd += ["-i", str(audio_path)]
        else:
            # Trim audio by abs(offset)
            cmd += ["-ss", str(abs(offset_seconds))]
            cmd += ["-i", str(audio_path)]

        cmd += ["-c:v", "copy"]
        cmd += ["-c:a", "pcm_s24le"]
        cmd += ["-map", "0:v:0"]
        cmd += ["-map", "1:a"]
        cmd += [str(output_path)]

    else:
        # Create separate audio file synced to video duration
        cmd = [FFMPEG, "-y"]

        if offset_seconds >= 0:
            cmd += ["-itsoffset", str(offset_seconds)]

        cmd += ["-i", str(audio_path)]

        if offset_seconds < 0:
            cmd += ["-ss", str(abs(offset_seconds))]

        # Match duration to video
        probe_cmd = [FFPROBE, "-v", "quiet", "-show_entries",
                     "format=duration", "-of", "json", str(video_path)]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        try:
            duration = json.loads(probe_result.stdout)["format"]["duration"]
            cmd += ["-t", duration]
        except:
            pass

        cmd += ["-c:a", "pcm_s24le"]
        cmd += [str(output_path)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True, "OK"
        else:
            error = result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
            return False, error
    except Exception as e:
        return False, str(e)


def find_matching_audio(video_file, audio_folder, tolerance_frames=2):
    """
    Scans an audio folder for files with matching timecode to a video file.
    Returns list of (audio_file, offset_seconds, confidence) tuples.
    """
    video_path = Path(video_file)
    audio_folder = Path(audio_folder)

    video_tc, video_fps = get_timecode(video_path)
    if not video_tc:
        return []

    matches = []
    audio_extensions = {".wav", ".bwf", ".aiff", ".aif", ".mp3", ".m4a"}

    for audio_file in audio_folder.iterdir():
        if audio_file.suffix.lower() not in audio_extensions:
            continue

        audio_tc, audio_fps = get_timecode(audio_file)
        if not audio_tc:
            continue

        offset = calculate_offset(video_tc, audio_tc, video_fps)
        if offset is None:
            continue

        tolerance_seconds = tolerance_frames / video_fps
        confidence = "exact" if abs(offset) < tolerance_seconds else "close"
        matches.append((audio_file, offset, confidence))

    matches.sort(key=lambda x: abs(x[1]))
    return matches