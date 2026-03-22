# dailies_app.py
# Dailies Toolkit — main application window

import sys
import sqlite3
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QSplitter, QLabel, QToolBar,
    QLineEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QPushButton, QFileDialog, QInputDialog,
    QMessageBox, QDialog, QTextEdit, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt

DB_FILE = Path("/Users/rachelmcintire/PycharmProjects/Claude/dailies.db")

ALL_COLUMNS = [
    "id", "file_name", "show", "episode", "date_recorded",
    "start_tc", "end_tc", "duration", "scene", "circle_take",
    "camera_id", "reel", "codec", "resolution", "fps",
    "bit_depth", "audio_codec", "audio_sample_rate", "audio_channels",
    "camera_type", "camera_manufacturer", "camera_serial",
    "iso", "white_balance", "shutter_angle", "lens_type",
    "focal_length", "nd_filter", "location", "dop", "director",
    "production_company", "input_lut", "output_lut",
    "cdl_slope", "cdl_offset", "cdl_power", "cdl_saturation",
    "checksum_md5", "checksum_xxhash", "checksum_sha256", "status"
]

DISPLAY_HEADERS = [
    "ID", "File Name", "Show", "Episode", "Date",
    "Start TC", "End TC", "Duration", "Scene", "Circle Take",
    "Camera", "Reel", "Codec", "Resolution", "FPS",
    "Bit Depth", "Audio Codec", "Sample Rate", "Audio Ch",
    "Cam Type", "Manufacturer", "Serial",
    "ISO", "White Balance", "Shutter", "Lens",
    "Focal Length", "ND", "Location", "DOP", "Director",
    "Production Co", "Input LUT", "Output LUT",
    "CDL Slope", "CDL Offset", "CDL Power", "CDL Sat",
    "MD5", "xxHash", "SHA-256", "Status"
]

class DailiesApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dailies Toolkit")
        self.setMinimumSize(1400, 800)
        self.setAcceptDrops(True)

        # --- Toolbar ---
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        import_btn = QPushButton("Import CSV")
        import_btn.clicked.connect(self.import_csv)
        toolbar.addWidget(import_btn)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_clips)
        toolbar.addWidget(export_btn)

        report_btn = QPushButton("Consistency Report")
        report_btn.clicked.connect(self.run_consistency_report)
        toolbar.addWidget(report_btn)

        slack_btn = QPushButton("Send to Slack")
        slack_btn.clicked.connect(self.send_to_slack)
        toolbar.addWidget(slack_btn)

        save_view_btn = QPushButton("Save View")
        save_view_btn.clicked.connect(self.save_view)
        toolbar.addWidget(save_view_btn)

        verify_btn = QPushButton("Verify Files")
        verify_btn.clicked.connect(self.verify_checksums)
        toolbar.addWidget(verify_btn)

        # --- Main layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_layout.addWidget(QLabel("Filters"))

        left_layout.addWidget(QLabel("Show"))
        self.show_filter = QComboBox()
        left_layout.addWidget(self.show_filter)

        left_layout.addWidget(QLabel("Episode"))
        self.episode_filter = QComboBox()
        left_layout.addWidget(self.episode_filter)

        left_layout.addWidget(QLabel("Camera"))
        self.camera_filter = QComboBox()
        left_layout.addWidget(self.camera_filter)

        clear_btn = QPushButton("Clear Filters")
        clear_btn.clicked.connect(self.clear_filters)
        left_layout.addWidget(clear_btn)

        left_layout.addStretch()
        left_layout.addWidget(QLabel("Saved Views"))
        self.saved_views_layout = QVBoxLayout()
        left_layout.addLayout(self.saved_views_layout)
        left_panel.setMinimumWidth(200)
        left_panel.setMaximumWidth(250)

        # Center clip table
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search clips...")
        center_layout.addWidget(self.search_bar)

        self.clip_table = QTableWidget()
        self.clip_table.setColumnCount(len(ALL_COLUMNS))
        self.clip_table.setHorizontalHeaderLabels(DISPLAY_HEADERS)
        self.clip_table.horizontalHeader().setStretchLastSection(False)
        self.clip_table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.clip_table.setSelectionBehavior(
            self.clip_table.SelectionBehavior.SelectRows
        )
        self.clip_table.setSortingEnabled(True)
        center_layout.addWidget(self.clip_table)

        # Right detail panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        right_layout.addWidget(QLabel("Clip Details"))
        self.details_label = QLabel("Select a clip to view details")
        self.details_label.setWordWrap(True)
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.addWidget(self.details_label)

        right_layout.addWidget(QLabel("Color"))
        self.color_label = QLabel("")
        self.color_label.setWordWrap(True)
        self.color_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.addWidget(self.color_label)

        right_layout.addStretch()
        right_panel.setMinimumWidth(250)
        right_panel.setMaximumWidth(350)

        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([220, 900, 280])

        main_layout.addWidget(splitter)

        self.search_bar.textChanged.connect(self.filter_table)
        self.clip_table.cellClicked.connect(self.show_clip_details)
        self.load_clips()
        self.populate_filters()
        self.refresh_saved_views()

    def load_clips(self):
        """Loads all clips from the database and populates the table."""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clips")
        rows = cursor.fetchall()
        conn.close()

        self.clip_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value) if value else "")
                self.clip_table.setItem(row_idx, col_idx, item)

    def filter_table(self, text):
        """Filters the clip table based on search text."""
        for row in range(self.clip_table.rowCount()):
            match = False
            for col in range(self.clip_table.columnCount()):
                item = self.clip_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.clip_table.setRowHidden(row, not match)

    def populate_filters(self):
        """Populates filter dropdowns from the database."""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        self.show_filter.clear()
        self.show_filter.addItem("All")
        cursor.execute("SELECT DISTINCT show FROM clips WHERE show != '' ORDER BY show")
        for row in cursor.fetchall():
            self.show_filter.addItem(row[0])

        self.episode_filter.clear()
        self.episode_filter.addItem("All")
        cursor.execute("SELECT DISTINCT episode FROM clips WHERE episode != '' ORDER BY episode")
        for row in cursor.fetchall():
            self.episode_filter.addItem(row[0])

        self.camera_filter.clear()
        self.camera_filter.addItem("All")
        cursor.execute("SELECT DISTINCT camera_id FROM clips WHERE camera_id != '' ORDER BY camera_id")
        for row in cursor.fetchall():
            self.camera_filter.addItem(row[0])

        conn.close()

        self.show_filter.currentTextChanged.connect(self.apply_filters)
        self.episode_filter.currentTextChanged.connect(self.apply_filters)
        self.camera_filter.currentTextChanged.connect(self.apply_filters)

    def apply_filters(self):
        """Filters the table based on dropdown selections."""
        show = self.show_filter.currentText()
        episode = self.episode_filter.currentText()
        camera = self.camera_filter.currentText()

        for row in range(self.clip_table.rowCount()):
            show_match = show == "All" or (self.clip_table.item(row, 2) and self.clip_table.item(row, 2).text() == show)
            episode_match = episode == "All" or (self.clip_table.item(row, 3) and self.clip_table.item(row, 3).text() == episode)
            camera_match = camera == "All" or (self.clip_table.item(row, 10) and self.clip_table.item(row, 10).text() == camera)
            self.clip_table.setRowHidden(row, not (show_match and episode_match and camera_match))

    def clear_filters(self):
        """Resets all filters to All."""
        self.show_filter.setCurrentText("All")
        self.episode_filter.setCurrentText("All")
        self.camera_filter.setCurrentText("All")

    def show_clip_details(self, row, col):
        """Shows full clip details in the right panel when a row is clicked."""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        file_name = self.clip_table.item(row, 1).text()
        show_name = self.clip_table.item(row, 2).text()
        cursor.execute("SELECT * FROM clips WHERE file_name = ? AND show = ?", (file_name, show_name))
        clip = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        if clip:
            clip_data = dict(zip(columns, clip))
            details = f"""
File: {clip_data.get('file_name', '')}
Show: {clip_data.get('show', '')}
Episode: {clip_data.get('episode', '')}
Scene: {clip_data.get('scene', '')}
Circle Take: {clip_data.get('circle_take', '')}
Date: {clip_data.get('date_recorded', '')}
Start TC: {clip_data.get('start_tc', '')}
End TC: {clip_data.get('end_tc', '')}
Camera: {clip_data.get('camera_id', '')}
Reel: {clip_data.get('reel', '')}
Codec: {clip_data.get('codec', '')}
Resolution: {clip_data.get('resolution', '')}
FPS: {clip_data.get('fps', '')}
ISO: {clip_data.get('iso', '')}
White Balance: {clip_data.get('white_balance', '')}
Shutter: {clip_data.get('shutter_angle', '')}
Lens: {clip_data.get('lens_type', '')}
Focal Length: {clip_data.get('focal_length', '')}
ND: {clip_data.get('nd_filter', '')}
DOP: {clip_data.get('dop', '')}
Director: {clip_data.get('director', '')}
            """
            color = f"""
Input LUT: {clip_data.get('input_lut', '')}
Output LUT: {clip_data.get('output_lut', '')}
CDL Slope: {clip_data.get('cdl_slope', '')}
CDL Offset: {clip_data.get('cdl_offset', '')}
CDL Power: {clip_data.get('cdl_power', '')}
CDL Saturation: {clip_data.get('cdl_saturation', '')}

MD5: {clip_data.get('checksum_md5', '')}
xxHash: {clip_data.get('checksum_xxhash', '')}
SHA-256: {clip_data.get('checksum_sha256', '')}
            """
            self.details_label.setText(details.strip())
            self.color_label.setText(color.strip())

    def dragEnterEvent(self, event):
        """Accepts drag events for media files."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handles dropped media files and ingests them."""
        from folder_monitor import get_metadata, extract_video_info

        urls = event.mimeData().urls()
        files = [Path(url.toLocalFile()) for url in urls]

        MEDIA_EXTENSIONS = {".mov", ".mp4", ".mxf", ".dpx", ".exr", ".r3d"}
        media_files = [f for f in files if f.suffix.lower() in MEDIA_EXTENSIONS]

        if not media_files:
            QMessageBox.warning(self, "No Media", "No supported media files detected.")
            return

        show, ok1 = QInputDialog.getText(self, "Show Name", "Enter show name:")
        if not ok1 or not show:
            return

        episode, ok2 = QInputDialog.getText(self, "Episode", "Enter episode:")
        if not ok2 or not episode:
            return

        algorithm = self.ask_checksum_algorithm()

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        added = 0
        skipped = 0

        for file in media_files:
            cursor.execute(
                "SELECT id FROM clips WHERE file_name = ? AND show = ?",
                (file.name, show)
            )
            if cursor.fetchone():
                skipped += 1
                continue

            data = get_metadata(file)
            info = extract_video_info(data)

            if info:
                camera = file.name[0] if file.name else "unknown"
                reel = file.name[:4] if len(file.name) >= 4 else "unknown"

                checksum_md5 = checksum_xxhash = checksum_sha256 = None
                if algorithm:
                    from checksum import generate_checksum
                    value = generate_checksum(file, algorithm)
                    if algorithm == "md5":
                        checksum_md5 = value
                    elif algorithm == "xxhash":
                        checksum_xxhash = value
                    elif algorithm == "sha256":
                        checksum_sha256 = value

                cursor.execute("""
                    INSERT INTO clips (file_name, show, episode, codec, resolution, fps,
                        camera_id, reel, checksum_md5, checksum_xxhash, checksum_sha256, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file.name, show, episode,
                    info["codec"], info["resolution"], info["fps"],
                    camera, reel, checksum_md5, checksum_xxhash, checksum_sha256, "ok"
                ))
                added += 1

        conn.commit()
        conn.close()
        self.load_clips()
        self.populate_filters()
        QMessageBox.information(self, "Ingest Complete", f"{added} clips added, {skipped} skipped.")

    def ask_checksum_algorithm(self):
        """Asks the user which checksum algorithm to use."""
        algorithm, ok = QInputDialog.getItem(
            self, "Checksum Algorithm",
            "Generate checksums using:",
            ["None", "MD5", "xxHash", "SHA-256"],
            editable=False
        )
        if not ok:
            return None
        return None if algorithm == "None" else algorithm.lower().replace("-", "")

    def import_csv(self):
        """Opens a file picker to select a CSV and imports it."""
        from import_clips import load_csv, import_to_db

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv)"
        )
        if not file_path:
            return

        show, ok1 = QInputDialog.getText(self, "Show Name", "Enter show name:")
        if not ok1 or not show:
            return

        episode, ok2 = QInputDialog.getText(self, "Episode", "Enter episode:")
        if not ok2 or not episode:
            return

        try:
            rows = load_csv(file_path)
            import_to_db(rows, show, episode)
            self.load_clips()
            self.populate_filters()
            QMessageBox.information(self, "Import Complete", f"{len(rows)} rows processed.")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Error: {str(e)}")

    def export_clips(self):
        """Opens export dialog to choose format, columns, and save location."""
        from exporters import export_csv, export_ale, export_fcp7_xml, export_fcpxml, export_edl

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clips")
        all_clips = [dict(row) for row in cursor.fetchall()]
        conn.close()

        visible_clips = []
        for i, clip in enumerate(all_clips):
            if not self.clip_table.isRowHidden(i):
                visible_clips.append(clip)

        if not visible_clips:
            QMessageBox.warning(self, "Export", "No clips to export.")
            return

        col_dialog = QDialog(self)
        col_dialog.setWindowTitle("Choose Export Columns")
        col_dialog.setMinimumSize(400, 500)
        col_layout = QVBoxLayout(col_dialog)
        col_layout.addWidget(QLabel("Select columns to export:"))

        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        checkboxes = {}
        for col in ALL_COLUMNS:
            cb = QCheckBox(col)
            cb.setChecked(True)
            scroll_layout.addWidget(cb)
            checkboxes[col] = cb

        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        col_layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes.values()])
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes.values()])
        btn_row.addWidget(select_all_btn)
        btn_row.addWidget(clear_all_btn)
        col_layout.addLayout(btn_row)

        ok_btn = QPushButton("Continue")
        ok_btn.clicked.connect(col_dialog.accept)
        col_layout.addWidget(ok_btn)

        if col_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_columns = [col for col, cb in checkboxes.items() if cb.isChecked()]
        if not selected_columns:
            QMessageBox.warning(self, "Export", "No columns selected.")
            return

        filtered_clips = [{col: clip.get(col, "") for col in selected_columns} for clip in visible_clips]

        format_choice, ok = QInputDialog.getItem(
            self, "Export Format", "Choose format:",
            ["CSV", "ALE", "FCP7 XML", "FCPXML", "EDL"],
            editable=False
        )
        if not ok:
            return

        ext_map = {
            "CSV": "*.csv",
            "ALE": "*.ale",
            "FCP7 XML": "*.xml",
            "FCPXML": "*.fcpxml",
            "EDL": "*.edl"
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Export", "", ext_map[format_choice]
        )
        if not file_path:
            return

        if format_choice == "CSV":
            export_csv(filtered_clips, file_path)
        elif format_choice == "ALE":
            export_ale(filtered_clips, file_path)
        elif format_choice == "FCP7 XML":
            export_fcp7_xml(filtered_clips, file_path)
        elif format_choice == "FCPXML":
            export_fcpxml(filtered_clips, file_path)
        elif format_choice == "EDL":
            export_edl(filtered_clips, file_path)

        QMessageBox.information(self, "Export Complete", f"Exported {len(filtered_clips)} clips to {file_path}")

    def verify_checksums(self):
        """Verifies checksums for all visible clips that have a stored checksum."""
        from checksum import verify_checksum

        file_path = QFileDialog.getExistingDirectory(
            self, "Select folder containing media files"
        )
        if not file_path:
            return

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clips")
        all_clips = [dict(row) for row in cursor.fetchall()]
        conn.close()

        visible_clips = []
        for i, clip in enumerate(all_clips):
            if not self.clip_table.isRowHidden(i):
                visible_clips.append(clip)

        results = []
        for clip in visible_clips:
            file_name = clip.get("file_name", "")
            file = Path(file_path) / file_name

            for algo, col in [("md5", "checksum_md5"), ("xxhash", "checksum_xxhash"), ("sha256", "checksum_sha256")]:
                stored = clip.get(col)
                if stored:
                    ok, msg = verify_checksum(file, stored, algo)
                    if ok is None:
                        results.append(f"❓ {file_name} — file not found")
                    elif ok:
                        results.append(f"✅ {file_name} — {algo.upper()} OK")
                    else:
                        results.append(f"⚠️  {file_name} — {algo.upper()} FAILED: {msg}")
                        choice = QMessageBox.question(
                            self, "Checksum Mismatch",
                            f"{file_name} failed {algo.upper()} verification.\n{msg}\n\nContinue verifying?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if choice == QMessageBox.StandardButton.No:
                            break

        if not results:
            QMessageBox.information(self, "Verify", "No clips with stored checksums found.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Verification Report")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setText("\n".join(results))
        layout.addWidget(text)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.exec()

    def run_consistency_report(self):
        """Runs a consistency check on visible clips and shows a report."""
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clips")
        all_clips = [dict(row) for row in cursor.fetchall()]
        conn.close()

        visible_clips = []
        for i, clip in enumerate(all_clips):
            if not self.clip_table.isRowHidden(i):
                visible_clips.append(clip)

        if not visible_clips:
            QMessageBox.warning(self, "Report", "No clips to check.")
            return

        codecs = set(c["codec"] for c in visible_clips if c["codec"])
        resolutions = set(c["resolution"] for c in visible_clips if c["resolution"])
        fps_values = set(str(c["fps"]) for c in visible_clips if c["fps"])

        lines = [f"Consistency Report — {len(visible_clips)} clips\n"]
        lines.append("=" * 40)

        if len(codecs) > 1:
            lines.append(f"⚠️  Mixed codecs: {', '.join(codecs)}")
        else:
            lines.append(f"✅  Codec consistent: {', '.join(codecs)}")

        if len(resolutions) > 1:
            lines.append(f"⚠️  Mixed resolutions: {', '.join(resolutions)}")
        else:
            lines.append(f"✅  Resolution consistent: {', '.join(resolutions)}")

        if len(fps_values) > 1:
            lines.append(f"⚠️  Mixed frame rates: {', '.join(fps_values)}")
        else:
            lines.append(f"✅  Frame rate consistent: {', '.join(fps_values)}")

        missing_cdl = [c["file_name"] for c in visible_clips if not c["cdl_slope"]]
        if missing_cdl:
            lines.append(f"\n⚠️  {len(missing_cdl)} clips missing CDL values")

        missing_scene = [c["file_name"] for c in visible_clips if not c["scene"]]
        if missing_scene:
            lines.append(f"⚠️  {len(missing_scene)} clips missing scene info")

        dialog = QDialog(self)
        dialog.setWindowTitle("Consistency Report")
        dialog.setMinimumSize(500, 400)
        layout = QVBoxLayout(dialog)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setText("\n".join(lines))
        layout.addWidget(text)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    def send_to_slack(self):
        """Sends a consistency summary of visible clips to Slack."""
        from notifier import send_slack_message, build_summary

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clips")
        all_clips = [dict(row) for row in cursor.fetchall()]
        conn.close()

        visible_clips = []
        for i, clip in enumerate(all_clips):
            if not self.clip_table.isRowHidden(i):
                visible_clips.append(clip)

        if not visible_clips:
            QMessageBox.warning(self, "Slack", "No clips to send.")
            return

        show = visible_clips[0].get("show", "Unknown")
        episode = visible_clips[0].get("episode", "Unknown")
        shoot_date = visible_clips[0].get("date_recorded", "Unknown")

        issues = []
        codecs = set(c["codec"] for c in visible_clips if c["codec"])
        resolutions = set(c["resolution"] for c in visible_clips if c["resolution"])
        fps_values = set(str(c["fps"]) for c in visible_clips if c["fps"])

        if len(codecs) > 1:
            issues.append(f"Mixed codecs: {', '.join(codecs)}")
        if len(resolutions) > 1:
            issues.append(f"Mixed resolutions: {', '.join(resolutions)}")
        if len(fps_values) > 1:
            issues.append(f"Mixed frame rates: {', '.join(fps_values)}")

        message = build_summary(show, episode, shoot_date, visible_clips, issues)

        try:
            result = send_slack_message(message)
            if result.get("ok"):
                QMessageBox.information(self, "Slack", "Message sent successfully.")
            else:
                QMessageBox.warning(self, "Slack", f"Failed: {result.get('error')}")
        except Exception as e:
            QMessageBox.critical(self, "Slack Error", str(e))

    def save_view(self):
        """Saves the current filter state as a named view."""
        from views import save_view as save

        name, ok = QInputDialog.getText(self, "Save View", "Enter a name for this view:")
        if not ok or not name:
            return

        filters = {
            "show": self.show_filter.currentText(),
            "episode": self.episode_filter.currentText(),
            "camera": self.camera_filter.currentText(),
            "search": self.search_bar.text()
        }

        save(name, filters)
        self.refresh_saved_views()
        QMessageBox.information(self, "Saved", f"View '{name}' saved.")

    def refresh_saved_views(self):
        """Refreshes the saved views list in the sidebar."""
        from views import load_all_views, delete_view

        while self.saved_views_layout.count():
            item = self.saved_views_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        views = load_all_views()
        for name, filters in views.items():
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, f=filters: self.apply_saved_view(f))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, n=name: self.show_view_context_menu(pos, n)
            )
            self.saved_views_layout.addWidget(btn)

    def show_view_context_menu(self, pos, name):
        """Shows a right-click menu to delete a saved view."""
        from PyQt6.QtWidgets import QMenu
        from views import delete_view

        menu = QMenu(self)
        delete_action = menu.addAction(f"Delete '{name}'")
        action = menu.exec(self.cursor().pos())

        if action == delete_action:
            delete_action = QMessageBox.question(
                self, "Delete View",
                f"Are you sure you want to delete '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if delete_action == QMessageBox.StandardButton.Yes:
                delete_view(name)
                self.refresh_saved_views()

    def apply_saved_view(self, filters):
        """Applies a saved view's filters."""
        self.show_filter.setCurrentText(filters.get("show", "All"))
        self.episode_filter.setCurrentText(filters.get("episode", "All"))
        self.camera_filter.setCurrentText(filters.get("camera", "All"))
        self.search_bar.setText(filters.get("search", ""))

# --- Run ---
app = QApplication(sys.argv)
window = DailiesApp()
window.show()
sys.exit(app.exec())