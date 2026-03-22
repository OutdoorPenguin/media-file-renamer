# checksum.py
# Generates and verifies checksums for media files
# Supports MD5, xxHash, and SHA-256

import hashlib
import xxhash
from pathlib import Path

def generate_checksum(file_path, algorithm="md5"):
    """Generates a checksum for a file using the specified algorithm."""
    file_path = Path(file_path)

    if not file_path.exists():
        return None

    if algorithm == "md5":
        h = hashlib.md5()
    elif algorithm == "sha256":
        h = hashlib.sha256()
    elif algorithm == "xxhash":
        h = xxhash.xxh64()
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    # Read in chunks to handle large files
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()

def verify_checksum(file_path, expected, algorithm="md5"):
    """Verifies a file's checksum against an expected value."""
    actual = generate_checksum(file_path, algorithm)
    if actual is None:
        return None, "File not found"
    if actual == expected:
        return True, "OK"
    return False, f"Mismatch — expected {expected[:12]}... got {actual[:12]}..."

def get_checksum_column(algorithm):
    """Returns the database column name for a given algorithm."""
    return {
        "md5": "checksum_md5",
        "xxhash": "checksum_xxhash",
        "sha256": "checksum_sha256"
    }.get(algorithm)