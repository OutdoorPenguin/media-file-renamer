# cdl_extractor.py
# Drag an EDL onto the app, extract CDL values, export as .cdl or .cc files

import sys
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QComboBox, QMessageBox,
    QHeaderView
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPalette, QColor, QFont, QDragEnterEvent, QDropEvent

# --- Style ---
DARK_BG = "#1a1a1a"
PANEL_BG = "#242424"
ACCENT = "#E50914"
TEXT = "#ffffff"
SUBTEXT = "#888888"
BORDER = "#333333"

STYLESHEET = f"""
    QMainWindow, QWidget {{
        background-color: {DARK_BG};
        color: {TEXT};
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }}
    QLabel {{
        color: {TEXT};
    }}
    QPushButton {{
        background-color: {ACCENT};
        color: {TEXT};
        border: none;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: bold;
        border-radius: 3px;
    }}
    QPushButton:hover {{
        background-color: #ff1a27;
    }}
    QPushButton:disabled {{
        background-color: #444444;
        color: {SUBTEXT};
    }}
    QPushButton#secondary {{
        background-color: {PANEL_BG};
        border: 1px solid {BORDER};
        color: {TEXT};
    }}
    QPushButton#secondary:hover {{
        border: 1px solid {ACCENT};
        color: {ACCENT};
    }}
    QTableWidget {{
        background-color: {PANEL_BG};
        border: 1px solid {BORDER};
        gridline-color: {BORDER};
        color: {TEXT};
        font-size: 12px;
    }}
    QTableWidget::item:selected {{
        background-color: {ACCENT};
        color: {TEXT};
    }}
    QHeaderView::section {{
        background-color: {DARK_BG};
        color: {SUBTEXT};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 6px;
        font-size: 11px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    QComboBox {{
        background-color: {PANEL_BG};
        color: {TEXT};
        border: 1px solid {BORDER};
        padding: 6px 12px;
        border-radius: 3px;
        font-size: 13px;
        min-width: 150px;
    }}
    QComboBox:hover {{
        border: 1px solid {ACCENT};
    }}
    QComboBox QAbstractItemView {{
        background-color: {PANEL_BG};
        color: {TEXT};
        selection-background-color: {ACCENT};
        border: 1px solid {BORDER};
    }}
"""

def parse_edl(edl_path):
    """Parses an EDL and extracts CDL values per event."""
    clips = []
    current = {}

    with open(edl_path, "r", errors="replace") as f:
        for line in f:
            line = line.strip()

            # Edit line (event number + reel)
            if re.match(r"^\d{6}", line):
                if current and "sop" in current:
                    clips.append(current)
                parts = line.split()
                current = {"reel": parts[1] if len(parts) > 1 else ""}

            elif line.startswith("*FROM CLIP NAME:"):
                current["clip_name"] = line.replace("*FROM CLIP NAME:", "").strip().strip("*").strip()

            elif line.startswith("*LOC:"):
                parts = line.split()
                current["locator"] = parts[-1] if len(parts) > 1 else ""

            elif line.startswith("*ASC_SOP"):
                match = re.findall(r"\(([\d\s.\-]+)\)", line)
                if len(match) == 3:
                    current["sop"] = match
                    current["slope"] = match[0].strip()
                    current["offset"] = match[1].strip()
                    current["power"] = match[2].strip()

            elif line.startswith("*ASC_SAT"):
                parts = line.split()
                current["saturation"] = parts[1] if len(parts) > 1 else "1.0"

    if current and "sop" in current:
        clips.append(current)

    return clips

def write_cdl(clip, output_path):
    """Writes a .cdl file for a single clip."""
    clip_id = output_path.stem
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<ColorDecisionList xmlns="urn:ASC:CDL:v1.01">
    <ColorDecision>
        <ColorCorrection id="{clip_id}">
            <SOPNode>
                <Slope>{clip['slope']}</Slope>
                <Offset>{clip['offset']}</Offset>
                <Power>{clip['power']}</Power>
            </SOPNode>
            <SATNode>
                <Saturation>{clip.get('saturation', '1.0')}</Saturation>
            </SATNode>
        </ColorCorrection>
    </ColorDecision>
</ColorDecisionList>"""
    output_path.write_text(content)

def write_cc(clip, output_path):
    """Writes a .cc file for a single clip."""
    clip_id = output_path.stem
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<ColorCorrection id="{clip_id}">
    <SOPNode>
        <Slope>{clip['slope']}</Slope>
        <Offset>{clip['offset']}</Offset>
        <Power>{clip['power']}</Power>
    </SOPNode>
    <SATNode>
        <Saturation>{clip.get('saturation', '1.0')}</Saturation>
    </SATNode>
</ColorCorrection>"""
    output_path.write_text(content)


class DropZone(QLabel):
    """A label that accepts EDL file drops."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Drop EDL here\nor click to browse")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {BORDER};
                border-radius: 6px;
                color: {SUBTEXT};
                font-size: 14px;
                background-color: {PANEL_BG};
            }}
            QLabel:hover {{
                border-color: {ACCENT};
                color: {TEXT};
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() == ".edl":
                self.window().load_edl(path)
            else:
                QMessageBox.warning(self.window(), "Wrong file type", "Please drop an EDL file.")


class CDLExtractor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CDL Extractor")
        self.setMinimumSize(900, 650)
        self.clips = []

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # --- Header ---
        header = QHBoxLayout()
        title = QLabel("CDL EXTRACTOR")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; letter-spacing: 3px; color: {TEXT};")
        subtitle = QLabel("Extract color values from EDL")
        subtitle.setStyleSheet(f"font-size: 12px; color: {SUBTEXT};")
        header_text = QVBoxLayout()
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header.addLayout(header_text)
        header.addStretch()
        layout.addLayout(header)

        # --- Drop zone ---
        self.drop_zone = DropZone()
        self.drop_zone.mousePressEvent = lambda e: self.browse_edl()
        layout.addWidget(self.drop_zone)

        # --- EDL info ---
        self.edl_label = QLabel("")
        self.edl_label.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        layout.addWidget(self.edl_label)

        # --- Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Clip Name", "Locator", "Slope", "Offset", "Power", "Saturation"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # --- Export controls ---
        export_row = QHBoxLayout()

        naming_label = QLabel("Name files by:")
        naming_label.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        self.naming_combo = QComboBox()
        self.naming_combo.addItems(["Clip Name", "Locator", "Reel"])

        format_label = QLabel("Export as:")
        format_label.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        self.format_combo = QComboBox()
        self.format_combo.addItems([".cdl", ".cc"])

        self.export_btn = QPushButton("Export Files")
        self.export_btn.setDisabled(True)
        self.export_btn.clicked.connect(self.export)

        export_row.addWidget(naming_label)
        export_row.addWidget(self.naming_combo)
        export_row.addSpacing(20)
        export_row.addWidget(format_label)
        export_row.addWidget(self.format_combo)
        export_row.addStretch()
        export_row.addWidget(self.export_btn)
        layout.addLayout(export_row)

        # --- Status ---
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")
        layout.addWidget(self.status_label)

    def browse_edl(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select EDL", "", "EDL Files (*.edl)")
        if path:
            self.load_edl(Path(path))

    def load_edl(self, path):
        self.clips = parse_edl(path)
        self.edl_label.setText(f"Loaded: {path.name}  —  {len(self.clips)} events with CDL found")

        self.table.setRowCount(len(self.clips))
        for i, clip in enumerate(self.clips):
            self.table.setItem(i, 0, QTableWidgetItem(clip.get("clip_name", "")))
            self.table.setItem(i, 1, QTableWidgetItem(clip.get("locator", "")))
            self.table.setItem(i, 2, QTableWidgetItem(clip.get("slope", "")))
            self.table.setItem(i, 3, QTableWidgetItem(clip.get("offset", "")))
            self.table.setItem(i, 4, QTableWidgetItem(clip.get("power", "")))
            self.table.setItem(i, 5, QTableWidgetItem(clip.get("saturation", "1.0")))

        self.export_btn.setDisabled(len(self.clips) == 0)
        self.status_label.setText("")
        self.drop_zone.setText(f"✓  {path.name}")
        self.drop_zone.setStyleSheet(f"""
            QLabel {{
                border: 2px solid {ACCENT};
                border-radius: 6px;
                color: {TEXT};
                font-size: 14px;
                background-color: {PANEL_BG};
            }}
        """)

    def export(self):
        if not self.clips:
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Choose Output Folder")
        if not output_dir:
            return

        output_dir = Path(output_dir)
        fmt = self.format_combo.currentText()
        naming = self.naming_combo.currentText()

        written = 0
        for clip in self.clips:
            if naming == "Clip Name":
                name = clip.get("clip_name", f"clip_{written}")
            elif naming == "Locator":
                name = clip.get("locator", f"clip_{written}")
            else:
                name = clip.get("reel", f"clip_{written}")

            name = name.strip().replace(" ", "_").replace("*", "").replace("/", "_")
            if not name:
                name = f"clip_{written}"

            output_path = output_dir / f"{name}{fmt}"

            if fmt == ".cdl":
                write_cdl(clip, output_path)
            else:
                write_cc(clip, output_path)

            written += 1

        self.status_label.setText(f"✓  {written} files exported to {output_dir}")
        self.status_label.setStyleSheet(f"color: {ACCENT}; font-size: 12px;")
        QMessageBox.information(self, "Export Complete", f"{written} {fmt} files exported.")


# --- Run ---
app = QApplication(sys.argv)
app.setStyleSheet(STYLESHEET)
window = CDLExtractor()
window.show()
sys.exit(app.exec())