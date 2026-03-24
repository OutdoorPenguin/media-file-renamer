# transcoder.py
# Handles all ffmpeg transcoding operations
# Supports CDL, LUTs, burnins, retime, and multiple output codecs

import subprocess
from pathlib import Path

# --- ffmpeg path ---
FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"

# --- Codec settings ---
CODEC_MAP = {
    "ProRes 422 LT":  ["-c:v", "prores_ks", "-profile:v", "1", "-pix_fmt", "yuv422p10le"],
    "ProRes 422":     ["-c:v", "prores_ks", "-profile:v", "2", "-pix_fmt", "yuv422p10le"],
    "ProRes 422 HQ":  ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"],
    "ProRes 4444":    ["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuv444p10le"],
    "H.264":          ["-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p"],
    "H.265":          ["-c:v", "libx265", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p"],
    "DNxHD 115":      ["-c:v", "dnxhd", "-b:v", "115M", "-pix_fmt", "yuv422p"],
    "DNxHR SQ":       ["-c:v", "dnxhd", "-profile:v", "dnxhr_sq", "-pix_fmt", "yuv422p10le"],
}

CODEC_EXTENSIONS = {
    "ProRes 422 LT":  ".mov",
    "ProRes 422":     ".mov",
    "ProRes 422 HQ":  ".mov",
    "ProRes 4444":    ".mov",
    "H.264":          ".mp4",
    "H.265":          ".mp4",
    "DNxHD 115":      ".mxf",
    "DNxHR SQ":       ".mxf",
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
    if input_lut and Path(input_lut).exists():
        filters.append(f"lut3d='{input_lut}'")

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
    if output_lut and Path(output_lut).exists():
        filters.append(f"lut3d='{output_lut}'")

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

    cmd = [FFMPEG, "-y", "-i", str(source_path)]

    if filter_chain:
        cmd += ["-vf", filter_chain]

    cmd += codec_args
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