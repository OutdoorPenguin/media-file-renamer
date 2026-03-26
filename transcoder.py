# transcoder.py
# Handles all ffmpeg transcoding operations
# Supports CDL, LUTs, burnins, retime, and multiple output codecs

import subprocess
from pathlib import Path

# --- ffmpeg path ---
FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFMPEG_FULL = "/Applications/ffmpeg"  # has drawtext/freetype
FFPROBE = "/opt/homebrew/bin/ffprobe"

# --- Codec settings ---
CODEC_MAP = {
    # ProRes
    "ProRes 422 LT":      ["-c:v", "prores_ks", "-profile:v", "1", "-pix_fmt", "yuv422p10le"],
    "ProRes 422":         ["-c:v", "prores_ks", "-profile:v", "2", "-pix_fmt", "yuv422p10le"],
    "ProRes 422 HQ":      ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"],
    "ProRes 4444":        ["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuv444p10le"],
    "ProRes 4444 XQ":     ["-c:v", "prores_ks", "-profile:v", "5", "-pix_fmt", "yuv444p10le"],

    # H.264
    "H.264 High Quality": ["-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p"],
    "H.264":              ["-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p"],
    "H.264 Web":          ["-c:v", "libx264", "-crf", "23", "-preset", "fast", "-pix_fmt", "yuv420p"],

    # H.265
    "H.265 High Quality": ["-c:v", "libx265", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p"],
    "H.265":              ["-c:v", "libx265", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p"],
    "H.265 Web":          ["-c:v", "libx265", "-crf", "28", "-preset", "fast", "-pix_fmt", "yuv420p"],

    # DNxHD/DNxHR
    "DNxHD 115":          ["-c:v", "dnxhd", "-b:v", "115M", "-pix_fmt", "yuv422p"],
    "DNxHR SQ":           ["-c:v", "dnxhd", "-profile:v", "dnxhr_sq", "-pix_fmt", "yuv422p10le"],
    "DNxHR HQ":           ["-c:v", "dnxhd", "-profile:v", "dnxhr_hq", "-pix_fmt", "yuv422p10le"],
    "DNxHR HQX":          ["-c:v", "dnxhd", "-profile:v", "dnxhr_hqx", "-pix_fmt", "yuv422p12le"],
    "DNxHR 444":          ["-c:v", "dnxhd", "-profile:v", "dnxhr_444", "-pix_fmt", "yuv444p10le"],

    # JPEG 2000
    "JPEG 2000":          ["-c:v", "libopenjpeg", "-pix_fmt", "yuv422p10le"],

    # Uncompressed
    "Uncompressed 10-bit": ["-c:v", "v210", "-pix_fmt", "yuv422p10le"],

    # MXF OP1a (uses H.264 inside MXF wrapper)
    "MXF OP1a (H.264)":   ["-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p"],
}

CODEC_EXTENSIONS = {
    "ProRes 422 LT":       ".mov",
    "ProRes 422":          ".mov",
    "ProRes 422 HQ":       ".mov",
    "ProRes 4444":         ".mov",
    "ProRes 4444 XQ":      ".mov",
    "H.264 High Quality":  ".mp4",
    "H.264":               ".mp4",
    "H.264 Web":           ".mp4",
    "H.265 High Quality":  ".mp4",
    "H.265":               ".mp4",
    "H.265 Web":           ".mp4",
    "DNxHD 115":           ".mxf",
    "DNxHR SQ":            ".mxf",
    "DNxHR HQ":            ".mxf",
    "DNxHR HQX":           ".mxf",
    "DNxHR 444":           ".mxf",
    "JPEG 2000":           ".mxf",
    "Uncompressed 10-bit": ".mov",
    "MXF OP1a (H.264)":    ".mxf",
}

# --- Position map for burnins ---
POSITION_MAP = {
    "top_left":       ("20", "20"),
    "top_center":     ("(w-tw)/2", "20"),
    "top_right":      ("w-tw-20", "20"),
    "bottom_left":    ("20", "h-th-20"),
    "bottom_center":  ("(w-tw)/2", "h-th-20"),
    "bottom_right":   ("w-tw-20", "h-th-20"),
}

def build_filter_chain(cdl=None, input_lut=None, output_lut=None,
                       burnins=None, retime=None, pix_fmt="yuv422p10le"):
    """Builds the ffmpeg filter chain string."""
    filters = []

    # Always start with colorspace conversion to handle wide gamut sources
    filters.append(f"colorspace=all=bt709:iall=bt709:fast=1,format={pix_fmt}")

    # Input LUT
    if input_lut:
        input_lut_path = Path(input_lut)
        if input_lut_path.exists():
            # Escape spaces and special chars in path
            safe_path = str(input_lut_path).replace("\\", "/").replace("'", "\\'").replace(":", "\\:")
            filters.append(f"lut3d=file='{safe_path}'")
        else:
            print(f"⚠️  Input LUT not found: {input_lut}")
    # CDL
    if cdl:
        slope = cdl.get("slope", "1.0 1.0 1.0")
        sat = float(cdl.get("saturation", "1.0"))

        sr, sg, sb = [float(x) for x in slope.split()]
        filters.append(
            f"curves=r='0/0 1/{sr}':g='0/0 1/{sg}':b='0/0 1/{sb}'"
        )
        if sat != 1.0:
            filters.append(f"hue=s={sat}")

        # Output LUT
        if output_lut:
            output_lut_path = Path(output_lut)
            if output_lut_path.exists():
                safe_path = str(output_lut_path).replace("\\", "/").replace("'", "\\'").replace(":", "\\:")
                filters.append(f"lut3d=file='{safe_path}'")
            else:
                print(f"⚠️  Output LUT not found: {output_lut}")

    # Retime
    if retime and retime != 1.0:
        filters.append(f"setpts={1/retime}*PTS")

    # Burnins
    if burnins:
        for burnin in burnins:
            text = burnin.get("text", "").replace("'", "\\'").replace(":", "\\:")
            position = burnin.get("position", "bottom_center")
            fontsize = burnin.get("fontsize", 36)
            box = burnin.get("box", True)
            box_opacity = burnin.get("box_opacity", 0.5)

            x, y = POSITION_MAP.get(position, ("(w-tw)/2", "h-th-20"))
            box_str = f":box=1:boxcolor=black@{box_opacity}:boxborderw=8" if box else ""
            filters.append(
                f"drawtext=text='{text}':fontcolor=white:fontsize={fontsize}{box_str}:x={x}:y={y}"
            )

    return ",".join(filters) if filters else None


def transcode(source_path, output_path, codec, cdl=None,
              input_lut=None, output_lut=None, burnins=None, retime=None,
              progress_callback=None):
    """Transcodes a single file with optional CDL, LUTs, burnins and retime."""
    source_path = Path(source_path)
    output_path = Path(output_path)

    if not source_path.exists():
        return False, f"Source file not found: {source_path}"

    codec_args = CODEC_MAP.get(codec)
    if not codec_args:
        return False, f"Unknown codec: {codec}"

    # Get target pixel format from codec args
    pix_fmt = "yuv422p10le"
    if "-pix_fmt" in codec_args:
        pix_fmt = codec_args[codec_args.index("-pix_fmt") + 1]

    filter_chain = build_filter_chain(cdl, input_lut, output_lut, burnins, retime, pix_fmt)

    # Use full ffmpeg build if burnins are requested (requires freetype)
    ffmpeg_bin = FFMPEG_FULL if burnins else FFMPEG
    cmd = [ffmpeg_bin, "-y", "-i", str(source_path)]

    if filter_chain:
        cmd += ["-vf", filter_chain]

    cmd += codec_args

    # Force output frame rate if retiming
    if retime and retime != 1.0:
        source_fps = None
        try:
            probe = subprocess.run(
                [FFPROBE, "-v", "quiet", "-print_format", "json", "-show_streams", str(source_path)],
                capture_output=True, text=True
            )
            import json
            data = json.loads(probe.stdout)
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    fps_str = stream.get("r_frame_rate", "24/1")
                    num, den = fps_str.split("/")
                    source_fps = float(num) / float(den)
                    break
        except:
            source_fps = 24.0

        if source_fps:
            target_fps = source_fps * retime
            cmd += ["-r", str(round(target_fps, 3))]

    cmd += ["-c:a", "copy"]
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