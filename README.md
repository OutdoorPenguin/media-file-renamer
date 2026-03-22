# dailies-toolkit 🎬

A suite of Python tools for post-production dailies workflow. Built for film and TV — handles ingest, metadata, color, and notifications.

---

## Tools

### 🖥️ Dailies App (`dailies_app.py`)
Full desktop application for managing dailies. Features:
- Drag and drop media ingest via ffprobe
- CSV import from Premiere, Resolve, Avid, Silverstack, and Pomfort
- 39-column database with search, sort, and horizontal scroll
- Filter by show, episode, and camera
- Saved views with right-click delete
- Consistency report — flags mixed codecs, resolutions, and frame rates
- Slack notifications
- Custom column export to CSV, ALE, FCP7 XML, FCPXML, and EDL

### 🎨 CDL Extractor (`cdl_extractor.py`)
Standalone desktop app — drag an EDL onto it, extract embedded CDL values, and export one `.cdl` or `.cc` file per clip. Name files by clip name, locator, or reel. Dark UI with Netflix red highlights. Distributable as a standalone `.app` — no Python required for end users.

### 📁 File Renamer (`renamer.py`)
Batch renames media files to camera roll convention (e.g. `A001C001.mov`). Dry run mode previews before renaming. Logs every rename to CSV.

### 📋 Ingest Log Parser (`log_parser.py`)
Reads a media ingest log CSV and flags potential issues — duplicate filenames, missing file sizes, zero-byte files, and bad status flags.

### 🔍 Folder Monitor (`folder_monitor.py`)
Scans a folder of media files and pulls codec, resolution, and frame rate via ffprobe. Flags mixed codecs, resolutions, and frame rates.

### 🗄️ Dailies Database (`dailies_db.py`)
Creates the SQLite database schema — 39 columns covering video, audio, camera, lens, exposure, color, and production metadata.

### 📥 CSV Importer (`import_clips.py`)
Imports clip metadata from CSV exports into the database. Normalizes column names automatically across different app exports. Flags duplicates per show.

### 🎨 CDL Parser (`cdl_parser.py`)
Reads `.cdl` files and extracts slope, offset, power, and saturation values per clip.

### 🗺️ Column Mapper (`column_map.py`)
Normalizes column names from Premiere, Resolve, Avid, Silverstack, and Pomfort into a standard format.

### 📣 Slack Notifier (`notifier.py`)
Sends a formatted Slack summary after ingest — show, episode, clip count, codec/resolution/fps, and consistency warnings.

### 📤 Exporters (`exporters.py`)
Handles all export formats: CSV, ALE, FCP7 XML, FCPXML, EDL.

### 🔐 Checksum Verifier (`checksum.py`)
Generates and verifies MD5, xxHash, and SHA-256 checksums for media files. Checksums are stored in the database and can be verified later via the Verify Files button in the app to confirm files haven't been corrupted or changed.

### ⭐ Views (`views.py`)
Saves and loads favorite filter combos in the app sidebar.

---

## Requirements
- Python 3.x
- ffmpeg / ffprobe — `brew install ffmpeg`
- `pip install watchdog pandas requests python-dotenv PyQt6 Pillow`
- DB Browser for SQLite — https://sqlitebrowser.org/dl/
- xxhash - `pip install watchdog pandas requests python-dotenv PyQt6 Pillow xxhash`

---

## Setup
1. Clone the repo
2. Install requirements above
3. Create a `.env` file with your Slack token: `SLACK_TOKEN=xoxb-yourtoken`
4. Run `dailies_db.py` once to create the database
5. Launch `dailies_app.py` to start the app

## Building the CDL Extractor as a standalone app
```
pyinstaller --windowed --name "CDL Extractor" --icon "CDL_Extractor.icns" cdl_extractor.py
```
The `.app` will appear in the `dist` folder. Zip and share — no Python needed on the receiving end.

---

*Built by a post production professional learning Python. Phase 2 (transcode pipeline, LUT application, audio sync) coming soon.*
