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
    QMessageBox, QDialog, QTextEdit, QCheckBox, QScrollArea,
    QProgressBar, QSlider, QSpinBox, QGroupBox, QGridLayout
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

BURNIN_FIELDS = [
    "Filename", "Timecode", "Reel", "Show", "Episode",
    "Scene", "Camera", "Date", "Shoot Day", "Custom"
]

POSITIONS = [
    "bottom_center", "bottom_left", "bottom_right",
    "top_left", "top_center", "top_right",
    "center_left", "center_center", "center_right"
]

class DailiesApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dailies Toolkit")
        self.setMinimumSize(1400, 800)
        self.setAcceptDrops(True)
        self._sync_matches = {}

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

        transcode_btn = QPushButton("Transcode")
        transcode_btn.clicked.connect(self.open_transcode_dialog)
        toolbar.addWidget(transcode_btn)

        render_btn = QPushButton("Render")
        render_btn.clicked.connect(self.open_render_dialog)
        toolbar.addWidget(render_btn)

        sync_btn = QPushButton("Sync Audio")
        sync_btn.clicked.connect(self.open_sync_dialog)
        toolbar.addWidget(sync_btn)

        # --- Main layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_layout.addWidget(QLabel("Active Show"))
        self.active_show_combo = QComboBox()
        self.active_show_combo.addItem("All Shows")
        left_layout.addWidget(self.active_show_combo)
        self.active_show_combo.currentTextChanged.connect(self.set_active_show)

        left_layout.addWidget(QLabel(""))

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
        self.clip_table.setSelectionBehavior(self.clip_table.SelectionBehavior.SelectRows)
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

    def set_active_show(self, show):
        if show == "All Shows":
            self.show_filter.setCurrentText("All")
        else:
            self.show_filter.setCurrentText(show)

    def load_clips(self):
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
        for row in range(self.clip_table.rowCount()):
            match = False
            for col in range(self.clip_table.columnCount()):
                item = self.clip_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.clip_table.setRowHidden(row, not match)

    def populate_filters(self):
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

        current_active = self.active_show_combo.currentText()
        self.active_show_combo.blockSignals(True)
        self.active_show_combo.clear()
        self.active_show_combo.addItem("All Shows")
        cursor.execute("SELECT DISTINCT show FROM clips WHERE show != '' ORDER BY show")
        for row in cursor.fetchall():
            self.active_show_combo.addItem(row[0])
        if current_active:
            self.active_show_combo.setCurrentText(current_active)
        self.active_show_combo.blockSignals(False)

        conn.close()

        self.show_filter.currentTextChanged.connect(self.apply_filters)
        self.episode_filter.currentTextChanged.connect(self.apply_filters)
        self.camera_filter.currentTextChanged.connect(self.apply_filters)

    def apply_filters(self):
        show = self.show_filter.currentText()
        episode = self.episode_filter.currentText()
        camera = self.camera_filter.currentText()

        for row in range(self.clip_table.rowCount()):
            show_match = show == "All" or (self.clip_table.item(row, 2) and self.clip_table.item(row, 2).text() == show)
            episode_match = episode == "All" or (self.clip_table.item(row, 3) and self.clip_table.item(row, 3).text() == episode)
            camera_match = camera == "All" or (self.clip_table.item(row, 10) and self.clip_table.item(row, 10).text() == camera)
            self.clip_table.setRowHidden(row, not (show_match and episode_match and camera_match))

    def clear_filters(self):
        self.show_filter.setCurrentText("All")
        self.episode_filter.setCurrentText("All")
        self.camera_filter.setCurrentText("All")

    def show_clip_details(self, row, col):
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
            details = f"""File: {clip_data.get('file_name', '')}
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
Director: {clip_data.get('director', '')}"""
            color = f"""Input LUT: {clip_data.get('input_lut', '')}
Output LUT: {clip_data.get('output_lut', '')}
CDL Slope: {clip_data.get('cdl_slope', '')}
CDL Offset: {clip_data.get('cdl_offset', '')}
CDL Power: {clip_data.get('cdl_power', '')}
CDL Saturation: {clip_data.get('cdl_saturation', '')}

MD5: {clip_data.get('checksum_md5', '')}
xxHash: {clip_data.get('checksum_xxhash', '')}
SHA-256: {clip_data.get('checksum_sha256', '')}"""
            self.details_label.setText(details.strip())
            self.color_label.setText(color.strip())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
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
            cursor.execute("SELECT id FROM clips WHERE file_name = ? AND show = ?", (file.name, show))
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
                """, (file.name, show, episode, info["codec"], info["resolution"], info["fps"],
                      camera, reel, checksum_md5, checksum_xxhash, checksum_sha256, "ok"))
                added += 1

        conn.commit()
        conn.close()
        self.load_clips()
        self.populate_filters()
        QMessageBox.information(self, "Ingest Complete", f"{added} clips added, {skipped} skipped.")

    def ask_checksum_algorithm(self):
        algorithm, ok = QInputDialog.getItem(self, "Checksum Algorithm",
            "Generate checksums using:", ["None", "MD5", "xxHash", "SHA-256"], editable=False)
        if not ok:
            return None
        return None if algorithm == "None" else algorithm.lower().replace("-", "")

    def _get_visible_clips(self):
        """Helper to get all visible clips from the database."""
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clips")
        all_clips = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return [clip for i, clip in enumerate(all_clips) if not self.clip_table.isRowHidden(i)]

    def open_transcode_dialog(self):
        """Opens the transcode dialog for visible/selected clips."""
        from transcoder import transcode, CODEC_MAP, CODEC_EXTENSIONS

        visible_clips = self._get_visible_clips()
        if not visible_clips:
            QMessageBox.warning(self, "Transcode", "No clips to transcode.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Transcode")
        dialog.setMinimumSize(700, 600)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(f"Clips to transcode: {len(visible_clips)}"))

        layout.addWidget(QLabel("Source folder:"))
        source_row = QHBoxLayout()
        source_field = QLineEdit()
        source_field.setPlaceholderText("/path/to/source/files")
        source_browse = QPushButton("Browse")
        source_browse.clicked.connect(lambda: source_field.setText(
            QFileDialog.getExistingDirectory(dialog, "Select Source Folder")))
        source_row.addWidget(source_field)
        source_row.addWidget(source_browse)
        layout.addLayout(source_row)

        layout.addWidget(QLabel("Output folder:"))
        output_row = QHBoxLayout()
        output_field = QLineEdit()
        output_field.setPlaceholderText("/path/to/output")
        output_browse = QPushButton("Browse")
        output_browse.clicked.connect(lambda: output_field.setText(
            QFileDialog.getExistingDirectory(dialog, "Select Output Folder")))
        output_row.addWidget(output_field)
        output_row.addWidget(output_browse)
        layout.addLayout(output_row)

        codec_row = QHBoxLayout()
        codec_row.addWidget(QLabel("Output codec:"))
        codec_combo = QComboBox()
        codec_combo.addItems(list(CODEC_MAP.keys()))
        codec_row.addWidget(codec_combo)
        codec_row.addStretch()
        layout.addLayout(codec_row)

        suffix_row = QHBoxLayout()
        suffix_row.addWidget(QLabel("Filename suffix:"))
        suffix_field = QLineEdit()
        suffix_field.setPlaceholderText("_PROXY")
        suffix_field.setMaximumWidth(150)
        suffix_row.addWidget(suffix_field)
        suffix_row.addStretch()
        layout.addLayout(suffix_row)

        use_cdl = QCheckBox("Apply stored CDL values")
        use_cdl.setChecked(True)
        layout.addWidget(use_cdl)

        lut_group = QGroupBox("LUTs")
        lut_layout = QVBoxLayout(lut_group)

        input_lut_row = QHBoxLayout()
        input_lut_row.addWidget(QLabel("Input LUT:"))
        input_lut_field = QLineEdit()
        input_lut_field.setPlaceholderText("Optional — .cube or .3dl")
        input_lut_browse = QPushButton("Browse")
        input_lut_browse.clicked.connect(lambda: input_lut_field.setText(
            QFileDialog.getOpenFileName(dialog, "Select Input LUT", "", "LUT Files (*.cube *.3dl)")[0]))
        input_lut_clear = QPushButton("Clear")
        input_lut_clear.clicked.connect(lambda: input_lut_field.clear())
        input_lut_row.addWidget(input_lut_field)
        input_lut_row.addWidget(input_lut_browse)
        input_lut_row.addWidget(input_lut_clear)
        lut_layout.addLayout(input_lut_row)

        output_lut_row = QHBoxLayout()
        output_lut_row.addWidget(QLabel("Output LUT:"))
        output_lut_field = QLineEdit()
        output_lut_field.setPlaceholderText("Optional — .cube or .3dl")
        output_lut_browse = QPushButton("Browse")
        output_lut_browse.clicked.connect(lambda: output_lut_field.setText(
            QFileDialog.getOpenFileName(dialog, "Select Output LUT", "", "LUT Files (*.cube *.3dl)")[0]))
        output_lut_clear = QPushButton("Clear")
        output_lut_clear.clicked.connect(lambda: output_lut_field.clear())
        output_lut_row.addWidget(output_lut_field)
        output_lut_row.addWidget(output_lut_browse)
        output_lut_row.addWidget(output_lut_clear)
        lut_layout.addLayout(output_lut_row)
        layout.addWidget(lut_group)

        burnin_group = QGroupBox("Burnins (requires ffmpeg with freetype — see setup docs)")
        burnin_layout = QVBoxLayout(burnin_group)
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Field"), 1)
        header_row.addWidget(QLabel("Enable"), 0)
        header_row.addWidget(QLabel("Position"), 2)
        burnin_layout.addLayout(header_row)

        burnin_checks = {}
        burnin_positions = {}
        burnin_custom_field = QLineEdit()
        burnin_custom_field.setPlaceholderText("Custom text...")
        burnin_custom_field.setEnabled(False)

        for field in BURNIN_FIELDS:
            row = QHBoxLayout()
            label = QLabel(field)
            label.setMinimumWidth(100)
            cb = QCheckBox()
            pos_combo = QComboBox()
            pos_combo.addItems(POSITIONS)
            pos_combo.setCurrentText("bottom_center")
            burnin_checks[field] = cb
            burnin_positions[field] = pos_combo
            row.addWidget(label, 1)
            row.addWidget(cb, 0)
            row.addWidget(pos_combo, 2)
            if field == "Custom":
                cb.stateChanged.connect(lambda state: burnin_custom_field.setEnabled(state == 2))
                row.addWidget(burnin_custom_field, 2)
            burnin_layout.addLayout(row)

        style_row = QHBoxLayout()
        box_check = QCheckBox("Black box")
        box_check.setChecked(True)
        opacity_slider = QSlider(Qt.Orientation.Horizontal)
        opacity_slider.setRange(0, 100)
        opacity_slider.setValue(50)
        opacity_slider.setMaximumWidth(100)
        opacity_label = QLabel("50%")
        opacity_slider.valueChanged.connect(lambda v: opacity_label.setText(f"{v}%"))
        fontsize_label = QLabel("Font size:")
        fontsize_spin = QSpinBox()
        fontsize_spin.setRange(12, 120)
        fontsize_spin.setValue(36)
        style_row.addWidget(box_check)
        style_row.addWidget(QLabel("Opacity:"))
        style_row.addWidget(opacity_slider)
        style_row.addWidget(opacity_label)
        style_row.addWidget(fontsize_label)
        style_row.addWidget(fontsize_spin)
        style_row.addStretch()
        burnin_layout.addLayout(style_row)
        layout.addWidget(burnin_group)

        retime_row = QHBoxLayout()
        use_retime = QCheckBox("Retime to FPS:")
        retime_field = QLineEdit()
        retime_field.setPlaceholderText("23.976")
        retime_field.setMaximumWidth(80)
        retime_row.addWidget(use_retime)
        retime_row.addWidget(retime_field)
        retime_row.addStretch()
        layout.addLayout(retime_row)

        progress = QProgressBar()
        progress.setMaximum(len(visible_clips))
        progress.setValue(0)
        layout.addWidget(progress)

        self.transcode_log = QTextEdit()
        self.transcode_log.setReadOnly(True)
        self.transcode_log.setMaximumHeight(100)
        layout.addWidget(self.transcode_log)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        save_preset_btn = QPushButton("Save as Preset")
        go_btn = QPushButton("Start Transcode")

        def save_as_preset():
            from presets import save_preset
            active_show = self.active_show_combo.currentText()
            if active_show == "All Shows":
                QMessageBox.warning(dialog, "No Show", "Please select an active show first.")
                return
            name, ok = QInputDialog.getText(dialog, "Preset Name", f"Save preset for {active_show}:")
            if not ok or not name:
                return
            settings = {
                "source_folder": source_field.text(),
                "output_folder": output_field.text(),
                "codec": codec_combo.currentText(),
                "suffix": suffix_field.text(),
                "use_cdl": use_cdl.isChecked(),
                "input_lut": input_lut_field.text(),
                "output_lut": output_lut_field.text(),
                "retime_enabled": use_retime.isChecked(),
                "retime_fps": retime_field.text(),
                "burnins": {field: {"enabled": cb.isChecked(),
                    "position": burnin_positions[field].currentText()}
                    for field, cb in burnin_checks.items()},
                "fontsize": fontsize_spin.value(),
                "box_opacity": opacity_slider.value()
            }
            save_preset(active_show, name, settings)
            QMessageBox.information(dialog, "Saved", f"Preset '{name}' saved for {active_show}.")

        save_preset_btn.clicked.connect(save_as_preset)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_preset_btn)
        btn_row.addStretch()
        btn_row.addWidget(go_btn)
        layout.addLayout(btn_row)

        def start_transcode():
            source_dir = Path(source_field.text())
            output_dir = Path(output_field.text())
            codec = codec_combo.currentText()
            suffix = suffix_field.text() or "_OUT"

            if not source_dir.exists():
                QMessageBox.warning(dialog, "Error", "Source folder not found.")
                return
            if not output_dir.exists():
                QMessageBox.warning(dialog, "Error", "Output folder not found.")
                return

            ext = CODEC_EXTENSIONS.get(codec, ".mov")
            done = 0
            failed = 0

            for clip in visible_clips:
                file_name = clip.get("file_name", "")
                source_file = source_dir / file_name

                if not source_file.exists():
                    self.transcode_log.append(f"⚠️  Not found: {file_name}")
                    failed += 1
                    continue

                stem = Path(file_name).stem
                output_file = output_dir / f"{stem}{suffix}{ext}"
                input_lut = input_lut_field.text() or None
                output_lut = output_lut_field.text() or None

                cdl = None
                if use_cdl.isChecked() and clip.get("cdl_slope"):
                    cdl = {"slope": clip.get("cdl_slope"), "offset": clip.get("cdl_offset"),
                           "power": clip.get("cdl_power"), "saturation": clip.get("cdl_saturation", "1.0")}

                burnin_list = []
                field_map = {
                    "Filename": clip.get("file_name", ""), "Timecode": clip.get("start_tc", ""),
                    "Reel": clip.get("reel", ""), "Show": clip.get("show", ""),
                    "Episode": clip.get("episode", ""), "Scene": clip.get("scene", ""),
                    "Camera": clip.get("camera_id", ""), "Date": clip.get("date_recorded", ""),
                    "Shoot Day": clip.get("date_recorded", ""), "Custom": burnin_custom_field.text(),
                }
                for field, cb in burnin_checks.items():
                    if cb.isChecked():
                        text = field_map.get(field, "")
                        if text:
                            burnin_list.append({"text": text,
                                "position": burnin_positions[field].currentText(),
                                "fontsize": fontsize_spin.value(),
                                "box": box_check.isChecked(),
                                "box_opacity": opacity_slider.value() / 100})
                if burnin_list:
                    self.transcode_log.append(f"⚠️  Burnins skipped — ffmpeg freetype not available")
                    burnin_list = None

                retime = None
                if use_retime.isChecked() and retime_field.text():
                    try:
                        target_fps = float(retime_field.text())
                        source_fps_str = str(clip.get("fps", "24"))
                        if "/" in source_fps_str:
                            num, den = source_fps_str.split("/")
                            source_fps = float(num) / float(den)
                        else:
                            source_fps = float(source_fps_str) if source_fps_str else 24.0
                        retime = target_fps / source_fps
                    except Exception as e:
                        self.transcode_log.append(f"⚠️  Retime calculation failed: {e}")

                self.transcode_log.append(f"Transcoding: {file_name}...")
                QApplication.processEvents()

                ok, msg = transcode(source_file, output_file, codec, cdl=cdl,
                                    input_lut=input_lut, output_lut=output_lut,
                                    burnins=burnin_list, retime=retime)

                if ok:
                    self.transcode_log.append(f"✅  Done: {output_file.name}")
                    done += 1
                else:
                    self.transcode_log.append(f"❌  Failed: {file_name} — {msg[:500]}")
                    failed += 1

                progress.setValue(done + failed)
                QApplication.processEvents()

            self.transcode_log.append(f"\nFinished — {done} done, {failed} failed.")
            if failed == 0:
                QMessageBox.information(dialog, "Transcode Complete", f"✅ All {done} clips transcoded successfully.")
            else:
                QMessageBox.warning(dialog, "Transcode Complete",
                    f"Finished with issues:\n✅ {done} succeeded\n❌ {failed} failed\n\nCheck the log for details.")
            dialog.accept()

        go_btn.clicked.connect(start_transcode)
        dialog.exec()

    def open_render_dialog(self):
        """Opens the render dialog with presets for the active show."""
        from presets import load_presets_for_show
        from transcoder import transcode, CODEC_EXTENSIONS

        active_show = self.active_show_combo.currentText()
        if active_show == "All Shows":
            QMessageBox.warning(self, "No Show", "Please select an active show first.")
            return

        presets = load_presets_for_show(active_show)
        if not presets:
            QMessageBox.warning(self, "No Presets",
                f"No transcode presets found for {active_show}.\n\nUse the Transcode button to create and save a preset first.")
            return

        visible_clips = self._get_visible_clips()
        if not visible_clips:
            QMessageBox.warning(self, "Render", "No clips to render.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Render — {active_show}")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(f"Show: {active_show}"))
        layout.addWidget(QLabel(f"Clips: {len(visible_clips)}"))
        layout.addWidget(QLabel(""))
        layout.addWidget(QLabel("Select presets to run:"))

        preset_checks = {}
        for preset_name, settings in presets.items():
            row = QHBoxLayout()
            cb = QCheckBox(preset_name)
            cb.setChecked(True)
            summary = QLabel(f"{settings.get('codec', '')} → {settings.get('suffix', '')}  |  CDL: {'Yes' if settings.get('use_cdl') else 'No'}  |  LUT: {'Yes' if settings.get('output_lut') else 'No'}")
            summary.setStyleSheet("color: gray; font-size: 11px;")
            row.addWidget(cb)
            row.addWidget(summary)
            row.addStretch()
            layout.addLayout(row)
            preset_checks[preset_name] = cb

        layout.addStretch()

        progress = QProgressBar()
        progress.setMaximum(len(visible_clips) * len(presets))
        progress.setValue(0)
        layout.addWidget(progress)

        self.transcode_log = QTextEdit()
        self.transcode_log.setReadOnly(True)
        self.transcode_log.setMaximumHeight(120)
        layout.addWidget(self.transcode_log)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        go_btn = QPushButton("Render")
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(go_btn)
        layout.addLayout(btn_row)

        def start_render():
            total_done = 0
            total_failed = 0

            for preset_name, cb in preset_checks.items():
                if not cb.isChecked():
                    continue

                settings = presets[preset_name]
                codec = settings.get("codec", "ProRes 422")
                suffix = settings.get("suffix", "_OUT")
                source_dir = Path(settings.get("source_folder", ""))
                output_dir = Path(settings.get("output_folder", ""))
                ext = CODEC_EXTENSIONS.get(codec, ".mov")

                if not source_dir.exists() or not output_dir.exists():
                    self.transcode_log.append(f"⚠️  Skipping '{preset_name}' — folder not found")
                    continue

                self.transcode_log.append(f"\n--- Running preset: {preset_name} ---")

                for clip in visible_clips:
                    file_name = clip.get("file_name", "")
                    source_file = source_dir / file_name

                    if not source_file.exists():
                        self.transcode_log.append(f"⚠️  Not found: {file_name}")
                        total_failed += 1
                        continue

                    stem = Path(file_name).stem
                    output_file = output_dir / f"{stem}{suffix}{ext}"

                    cdl = None
                    if settings.get("use_cdl") and clip.get("cdl_slope"):
                        cdl = {"slope": clip.get("cdl_slope"), "offset": clip.get("cdl_offset"),
                               "power": clip.get("cdl_power"), "saturation": clip.get("cdl_saturation", "1.0")}

                    input_lut = settings.get("input_lut") or None
                    output_lut = settings.get("output_lut") or None

                    retime = None
                    if settings.get("retime_enabled") and settings.get("retime_fps"):
                        try:
                            target_fps = float(settings["retime_fps"])
                            source_fps_str = str(clip.get("fps", "24"))
                            if "/" in source_fps_str:
                                num, den = source_fps_str.split("/")
                                source_fps = float(num) / float(den)
                            else:
                                source_fps = float(source_fps_str) if source_fps_str else 24.0
                            retime = target_fps / source_fps
                        except:
                            pass

                    self.transcode_log.append(f"Rendering: {file_name}...")
                    QApplication.processEvents()

                    ok, msg = transcode(source_file, output_file, codec, cdl=cdl,
                                        input_lut=input_lut, output_lut=output_lut, retime=retime)

                    if ok:
                        self.transcode_log.append(f"✅  Done: {output_file.name}")
                        total_done += 1
                    else:
                        self.transcode_log.append(f"❌  Failed: {file_name} — {msg[:200]}")
                        total_failed += 1

                    progress.setValue(total_done + total_failed)
                    QApplication.processEvents()

            self.transcode_log.append(f"\nRender complete — {total_done} done, {total_failed} failed.")
            if total_failed == 0:
                QMessageBox.information(dialog, "Render Complete", f"✅ All {total_done} clips rendered successfully.")
            else:
                QMessageBox.warning(dialog, "Render Complete",
                    f"Finished with issues:\n✅ {total_done} succeeded\n❌ {total_failed} failed")
            dialog.accept()

        go_btn.clicked.connect(start_render)
        dialog.exec()

    def open_sync_dialog(self):
        """Opens the audio sync dialog."""
        from syncer import find_matching_audio, sync_audio

        visible_clips = self._get_visible_clips()
        if not visible_clips:
            QMessageBox.warning(self, "Sync", "No clips to sync.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Sync Audio")
        dialog.setMinimumSize(700, 600)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(f"Clips to sync: {len(visible_clips)}"))

        layout.addWidget(QLabel("Video source folder:"))
        video_row = QHBoxLayout()
        video_field = QLineEdit()
        video_field.setPlaceholderText("/path/to/video/files")
        video_browse = QPushButton("Browse")
        video_browse.clicked.connect(lambda: video_field.setText(
            QFileDialog.getExistingDirectory(dialog, "Select Video Folder")))
        video_row.addWidget(video_field)
        video_row.addWidget(video_browse)
        layout.addLayout(video_row)

        layout.addWidget(QLabel("Audio folder:"))
        audio_row = QHBoxLayout()
        audio_field = QLineEdit()
        audio_field.setPlaceholderText("/path/to/audio/files")
        audio_browse = QPushButton("Browse")
        audio_browse.clicked.connect(lambda: audio_field.setText(
            QFileDialog.getExistingDirectory(dialog, "Select Audio Folder")))
        audio_row.addWidget(audio_field)
        audio_row.addWidget(audio_browse)
        layout.addLayout(audio_row)

        layout.addWidget(QLabel("Output folder:"))
        output_row = QHBoxLayout()
        output_field = QLineEdit()
        output_field.setPlaceholderText("/path/to/output")
        output_browse = QPushButton("Browse")
        output_browse.clicked.connect(lambda: output_field.setText(
            QFileDialog.getExistingDirectory(dialog, "Select Output Folder")))
        output_row.addWidget(output_field)
        output_row.addWidget(output_browse)
        layout.addLayout(output_row)

        options_row = QHBoxLayout()
        embed_check = QCheckBox("Embed audio in video")
        embed_check.setChecked(True)
        replace_scratch_check = QCheckBox("Replace scratch audio")
        replace_scratch_check.setChecked(True)
        options_row.addWidget(embed_check)
        options_row.addWidget(replace_scratch_check)
        options_row.addStretch()
        layout.addLayout(options_row)

        offset_row = QHBoxLayout()
        manual_offset_check = QCheckBox("Manual offset (frames):")
        manual_offset_field = QLineEdit()
        manual_offset_field.setPlaceholderText("0")
        manual_offset_field.setMaximumWidth(80)
        manual_offset_field.setEnabled(False)
        manual_offset_check.stateChanged.connect(lambda state: manual_offset_field.setEnabled(state == 2))
        offset_row.addWidget(manual_offset_check)
        offset_row.addWidget(manual_offset_field)
        offset_row.addStretch()
        layout.addLayout(offset_row)

        suffix_row = QHBoxLayout()
        suffix_row.addWidget(QLabel("Output suffix:"))
        suffix_field = QLineEdit()
        suffix_field.setText("_SYNC")
        suffix_field.setMaximumWidth(100)
        suffix_row.addWidget(suffix_field)
        suffix_row.addStretch()
        layout.addLayout(suffix_row)

        layout.addWidget(QLabel("TC Match Preview (click Scan to populate):"))
        results_table = QTableWidget()
        results_table.setColumnCount(4)
        results_table.setHorizontalHeaderLabels(["Video Clip", "Matched Audio", "Offset (sec)", "Confidence"])
        results_table.horizontalHeader().setStretchLastSection(True)
        results_table.setMaximumHeight(150)
        layout.addWidget(results_table)

        progress = QProgressBar()
        progress.setMaximum(len(visible_clips))
        progress.setValue(0)
        layout.addWidget(progress)

        self.sync_log = QTextEdit()
        self.sync_log.setReadOnly(True)
        self.sync_log.setMaximumHeight(100)
        layout.addWidget(self.sync_log)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        scan_btn = QPushButton("Scan for Matches")
        go_btn = QPushButton("Sync")
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(scan_btn)
        btn_row.addStretch()
        btn_row.addWidget(go_btn)
        layout.addLayout(btn_row)

        self._sync_matches = {}

        def scan_matches():
            video_dir = Path(video_field.text())
            audio_dir = Path(audio_field.text())
            if not video_dir.exists() or not audio_dir.exists():
                QMessageBox.warning(dialog, "Error", "Check folder paths.")
                return

            self._sync_matches = {}
            results_table.setRowCount(0)

            for clip in visible_clips:
                file_name = clip.get("file_name", "")
                video_file = video_dir / file_name
                if not video_file.exists():
                    continue

                matches = find_matching_audio(video_file, audio_dir)
                row = results_table.rowCount()
                results_table.insertRow(row)

                if matches:
                    audio_file, offset, confidence = matches[0]
                    self._sync_matches[file_name] = (audio_file, offset)
                    results_table.setItem(row, 0, QTableWidgetItem(file_name))
                    results_table.setItem(row, 1, QTableWidgetItem(audio_file.name))
                    results_table.setItem(row, 2, QTableWidgetItem(f"{offset:.4f}"))
                    results_table.setItem(row, 3, QTableWidgetItem(confidence))
                else:
                    results_table.setItem(row, 0, QTableWidgetItem(file_name))
                    results_table.setItem(row, 1, QTableWidgetItem("No match found"))
                    results_table.setItem(row, 2, QTableWidgetItem(""))
                    results_table.setItem(row, 3, QTableWidgetItem(""))

            self.sync_log.append(f"Scan complete — {len(self._sync_matches)} matches found.")

        def start_sync():
            video_dir = Path(video_field.text())
            output_dir = Path(output_field.text())
            suffix = suffix_field.text() or "_SYNC"
            embed = embed_check.isChecked()

            if not video_dir.exists() or not output_dir.exists():
                QMessageBox.warning(dialog, "Error", "Check folder paths.")
                return

            if not self._sync_matches:
                QMessageBox.warning(dialog, "No Matches", "Run Scan first to find audio matches.")
                return

            done = 0
            failed = 0

            for file_name, (audio_file, auto_offset) in self._sync_matches.items():
                video_file = video_dir / file_name
                stem = Path(file_name).stem
                ext = Path(file_name).suffix
                output_file = output_dir / f"{stem}{suffix}{ext}" if embed else output_dir / f"{stem}{suffix}.wav"

                if manual_offset_check.isChecked() and manual_offset_field.text():
                    try:
                        offset = float(manual_offset_field.text()) / 24.0
                    except:
                        offset = auto_offset
                else:
                    offset = auto_offset

                self.sync_log.append(f"Syncing: {file_name} + {audio_file.name} (offset: {offset:.4f}s)...")
                QApplication.processEvents()

                ok, msg = sync_audio(video_file, audio_file, output_file, offset_seconds=offset, embed=embed)

                if ok:
                    self.sync_log.append(f"✅  Done: {output_file.name}")
                    done += 1
                else:
                    self.sync_log.append(f"❌  Failed: {file_name} — {msg[:200]}")
                    failed += 1

                progress.setValue(done + failed)
                QApplication.processEvents()

            self.sync_log.append(f"\nFinished — {done} synced, {failed} failed.")
            if failed == 0:
                QMessageBox.information(dialog, "Sync Complete", f"✅ All {done} clips synced successfully.")
            else:
                QMessageBox.warning(dialog, "Sync Complete",
                    f"Finished:\n✅ {done} succeeded\n❌ {failed} failed")
            dialog.accept()

        scan_btn.clicked.connect(scan_matches)
        go_btn.clicked.connect(start_sync)
        dialog.exec()

    def import_csv(self):
        """Opens a file picker to select a CSV and imports it."""
        from import_clips import load_csv, import_to_db

        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
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

        visible_clips = self._get_visible_clips()
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

        format_choice, ok = QInputDialog.getItem(self, "Export Format", "Choose format:",
            ["CSV", "ALE", "FCP7 XML", "FCPXML", "EDL"], editable=False)
        if not ok:
            return

        ext_map = {"CSV": "*.csv", "ALE": "*.ale", "FCP7 XML": "*.xml", "FCPXML": "*.fcpxml", "EDL": "*.edl"}
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Export", "", ext_map[format_choice])
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

        file_path = QFileDialog.getExistingDirectory(self, "Select folder containing media files")
        if not file_path:
            return

        visible_clips = self._get_visible_clips()
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
                        choice = QMessageBox.question(self, "Checksum Mismatch",
                            f"{file_name} failed {algo.upper()} verification.\n{msg}\n\nContinue verifying?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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
        visible_clips = self._get_visible_clips()
        if not visible_clips:
            QMessageBox.warning(self, "Report", "No clips to check.")
            return

        codecs = set(c["codec"] for c in visible_clips if c["codec"])
        resolutions = set(c["resolution"] for c in visible_clips if c["resolution"])
        fps_values = set(str(c["fps"]) for c in visible_clips if c["fps"])

        lines = [f"Consistency Report — {len(visible_clips)} clips\n", "=" * 40]

        lines.append(f"⚠️  Mixed codecs: {', '.join(codecs)}" if len(codecs) > 1
                     else f"✅  Codec consistent: {', '.join(codecs)}")
        lines.append(f"⚠️  Mixed resolutions: {', '.join(resolutions)}" if len(resolutions) > 1
                     else f"✅  Resolution consistent: {', '.join(resolutions)}")
        lines.append(f"⚠️  Mixed frame rates: {', '.join(fps_values)}" if len(fps_values) > 1
                     else f"✅  Frame rate consistent: {', '.join(fps_values)}")

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

        visible_clips = self._get_visible_clips()
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
            btn.customContextMenuRequested.connect(lambda pos, n=name: self.show_view_context_menu(pos, n))
            self.saved_views_layout.addWidget(btn)

    def show_view_context_menu(self, pos, name):
        """Shows a right-click menu to delete a saved view."""
        from PyQt6.QtWidgets import QMenu
        from views import delete_view

        menu = QMenu(self)
        delete_action = menu.addAction(f"Delete '{name}'")
        action = menu.exec(self.cursor().pos())

        if action == delete_action:
            delete_action = QMessageBox.question(self, "Delete View",
                f"Are you sure you want to delete '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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