# column_map.py
# Maps column names from different apps to our standard database column names
# Supports: Premiere, Resolve, Avid, Silverstack, Pomfort

COLUMN_MAP = {
    # File info
    "file_name":            ["File Name", "Clip Name", "Name", "Filename", "Clip", "Master Clip Name"],
    "date_recorded":        ["Date Recorded", "Shoot Date", "Record Date", "Date", "Creation Date", "Capture Date"],
    "location":             ["Location", "Shoot Location", "GPS", "Site"],

    # Timecode
    "start_tc":             ["Start TC", "Start Timecode", "Timecode", "TC In", "Start", "Clip In"],
    "end_tc":               ["End TC", "End Timecode", "TC Out", "End", "Clip Out"],
    "duration":             ["Duration TC", "Duration", "Clip Duration"],

    # Video
    "resolution":           ["Resolution", "Frame Size", "Image Size", "Format", "Video Resolution"],
    "codec":                ["Video Codec", "Codec", "Video Format", "Compression"],
    "fps":                  ["Shot Frame Rate", "Frame Rate", "FPS", "Camera FPS", "Capture FPS"],
    "bit_depth":            ["Bit Depth", "Bits Per Channel", "Color Depth"],

    # Audio
    "audio_codec":          ["Audio Codec", "Audio Format", "Audio Compression"],
    "audio_sample_rate":    ["Audio Sample Rate", "Sample Rate", "Audio Rate"],
    "audio_channels":       ["Audio Channels", "Channels", "Audio Track Count"],

    # Camera
    "camera_type":          ["Camera Type", "Camera Model", "Camera", "Model"],
    "camera_manufacturer":  ["Camera Manufacturer", "Manufacturer", "Make"],
    "camera_serial":        ["Camera Serial #", "Serial Number", "Camera Serial", "Body Serial"],
    "camera_id":            ["Camera ID", "Camera #", "Camera Letter", "Cam ID", "Camera Number"],
    "reel":                 ["Reel Number", "Reel", "Magazine", "Roll", "Card"],

    # Exposure
    "iso":                  ["ISO", "Exposure Index", "EI", "ASA"],
    "white_balance":        ["White Point (Kelvin)", "White Balance", "WB", "Color Temp", "Kelvin"],
    "shutter_angle":        ["Shutter Angle", "Shutter", "Angle"],
    "nd_filter":            ["ND Filter", "ND", "Neutral Density"],

    # Lens
    "lens_type":            ["Lens Type", "Lens", "Lens Model", "Optics"],
    "focal_length":         ["Focal Point (mm)", "Focal Length", "Lens Focal Length", "FL"],

    # Scene
    "scene":                ["Scene", "Scene Number", "Slate Scene"],
    "circle_take":          ["Good Take", "Circle Take", "Take Rating", "Printed"],

    # Production
    "production_company":   ["Production Company", "Company", "Prod Company"],
    "show":                 ["Production Name", "Show", "Project", "Production"],
    "director":             ["Director", "Dir"],
    "dop":                  ["DOP", "DP", "Director of Photography", "Cinematographer"],
}

def normalize_columns(row, column_map=COLUMN_MAP):
    """Takes a raw CSV row and returns a dict with standardized column names."""
    normalized = {}
    for standard_name, variants in column_map.items():
        for variant in variants:
            if variant in row:
                normalized[standard_name] = row[variant]
                break
    return normalized