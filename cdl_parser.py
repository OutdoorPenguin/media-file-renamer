# cdl_parser.py
# Parses .cdl files and returns slope, offset, power, and saturation values
# Returns None if the file doesn't exist or can't be parsed

import xml.etree.ElementTree as ET
from pathlib import Path

def parse_cdl(cdl_path):
    """Reads a .cdl file and returns a dict of color values, or None if not found."""
    cdl_path = Path(cdl_path)

    if not cdl_path.exists():
        return None

    try:
        tree = ET.parse(cdl_path)
        root = tree.getroot()
        ns = {"cdl": "urn:ASC:CDL:v1.01"}

        return {
            "cdl_slope": root.find(".//cdl:Slope", ns).text.strip(),
            "cdl_offset": root.find(".//cdl:Offset", ns).text.strip(),
            "cdl_power": root.find(".//cdl:Power", ns).text.strip(),
            "cdl_saturation": root.find(".//cdl:Saturation", ns).text.strip()
        }

    except Exception as e:
        print(f"⚠️  Could not parse CDL file {cdl_path.name}: {e}")
        return None

def find_cdl_for_clip(clip_name, search_folders):
    """Looks for a matching CDL file by clip name across one or more folders."""
    stem = Path(clip_name).stem  # filename without extension
    for folder in search_folders:
        folder = Path(folder)
        if folder.exists():
            for cdl_file in folder.glob("*.cdl"):
                if stem in cdl_file.stem:
                    return parse_cdl(cdl_file)
    return None