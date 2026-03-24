# log_parser.py
# Reads a media ingest log CSV and flags potential issues
# Checks for: duplicate files, missing size, zero size, and bad status

import csv
from pathlib import Path

# --- SETTINGS ---
LOG_FILE = Path("/Users/rachelmcintire/PycharmProjects/Claude/ingest_log.csv")
REPORT_FILE = Path("/Users/rachelmcintire/PycharmProjects/Claude/ingest_report.csv")

seen_files = []  # tracks filenames already processed
issues = []      # collects all flagged problems

# --- Read and check the log ---
with open(LOG_FILE, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:

        # Duplicate filename
        if row["file_name"] in seen_files:
            issues.append(f"DUPLICATE: {row['file_name']} at {row['timestamp']}")
        else:
            seen_files.append(row["file_name"])

        # Missing size
        if row["size_mb"] == "":
            issues.append(f"MISSING SIZE: {row['file_name']}")

        # Zero size
        if row["size_mb"] == "0":
            issues.append(f"ZERO SIZE: {row['file_name']}")

        # Bad status
        if row["status"] != "ok":
            issues.append(f"BAD STATUS ({row['status']}): {row['file_name']}")

# --- Print results ---
if issues:
    print(f"Found {len(issues)} issue(s):\n")
    for issue in issues:
        print(f"  ⚠️  {issue}")
else:
    print("No issues found.")

# --- Save report ---
with open(REPORT_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["issue"])
    for issue in issues:
        writer.writerow([issue])

print(f"\nReport saved to: {REPORT_FILE}")
