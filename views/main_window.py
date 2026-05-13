"""
views/main_window.py
Main graphical interface — Contact lens fitting assistant.

MVC architecture:
  - This module contains only the view (PyQt5).
  - All business logic is delegated to the controllers.
"""

import sys
from typing import List, Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QDoubleSpinBox, QSpinBox, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QTextEdit, QFrame, QMessageBox, QStatusBar,
    QCheckBox, QSizePolicy, QAbstractItemView, QApplication,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

# Color palette
COLOR_BG        = "#1E2330"
COLOR_PANEL     = "#252C3E"
COLOR_ACCENT    = "#3D7EFF"
COLOR_ACCENT2   = "#2ECC71"
COLOR_WARNING   = "#E67E22"
COLOR_DANGER    = "#E74C3C"
COLOR_TEXT      = "#ECF0F1"
COLOR_TEXT_DIM  = "#8899AA"
COLOR_BORDER    = "#3A4460"
COLOR_ROW_ALT   = "#2A3347"
COLOR_ROW_SEL   = "#2D4A7A"

STYLESHEET = f"""
/* Window & background */
QMainWindow, QWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}}

/* GroupBox */
QGroupBox {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
    font-size: 13px;
    color: {COLOR_ACCENT};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 12px;
}}

/* Labels */
QLabel {{
    color: {COLOR_TEXT};
    font-size: 13px;
}}
QLabel#dimLabel {{
    color: {COLOR_TEXT_DIM};
    font-size: 11px;
}}
QLabel#titleLabel {{
    color: {COLOR_ACCENT};
    font-size: 18px;
    font-weight: bold;
}}
QLabel#subtitleLabel {{
    color: {COLOR_TEXT_DIM};
    font-size: 12px;
}}

/* SpinBox */
QDoubleSpinBox, QSpinBox {{
    background-color: #1A2035;
    border: 1px solid {COLOR_BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    color: {COLOR_TEXT};
    font-size: 13px;
    min-height: 28px;
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1px solid {COLOR_ACCENT};
}}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {{
    width: 18px;
    background-color: {COLOR_BORDER};
    border-radius: 3px;
}}

/* ComboBox */
QComboBox {{
    background-color: #1A2035;
    border: 1px solid {COLOR_BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    color: {COLOR_TEXT};
    min-height: 28px;
}}
QComboBox:focus {{ border: 1px solid {COLOR_ACCENT}; }}
QComboBox QAbstractItemView {{
    background-color: {COLOR_PANEL};
    color: {COLOR_TEXT};
    selection-background-color: {COLOR_ACCENT};
}}

/* Primary button */
QPushButton#btnCalculate {{
    background-color: {COLOR_ACCENT};
    color: white;
    border: none;
    border-radius: 7px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
    min-height: 40px;
}}
QPushButton#btnCalculate:hover {{
    background-color: #5590FF;
}}
QPushButton#btnCalculate:pressed {{
    background-color: #2D65CC;
}}

/* Secondary button */
QPushButton#btnReset {{
    background-color: transparent;
    color: {COLOR_TEXT_DIM};
    border: 1px solid {COLOR_BORDER};
    border-radius: 7px;
    padding: 8px 18px;
    font-size: 12px;
}}
QPushButton#btnReset:hover {{
    color: {COLOR_TEXT};
    border-color: {COLOR_TEXT_DIM};
}}

/* Table */
QTableWidget {{
    background-color: {COLOR_PANEL};
    alternate-background-color: {COLOR_ROW_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    gridline-color: {COLOR_BORDER};
    color: {COLOR_TEXT};
    font-size: 12px;
}}
QTableWidget::item {{
    padding: 6px 8px;
}}
QTableWidget::item:selected {{
    background-color: {COLOR_ROW_SEL};
    color: white;
}}
QHeaderView::section {{
    background-color: #1A2035;
    color: {COLOR_TEXT_DIM};
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid {COLOR_BORDER};
    font-weight: bold;
    font-size: 12px;
}}

/* TextEdit (notes) */
QTextEdit {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    color: {COLOR_TEXT};
    font-size: 12px;
    padding: 6px;
}}

/* CheckBox */
QCheckBox {{
    color: {COLOR_TEXT_DIM};
    font-size: 12px;
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLOR_BORDER};
    border-radius: 3px;
    background: #1A2035;
}}
QCheckBox::indicator:checked {{
    background-color: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT};
}}

/* Separator */
QFrame#hRule {{
    border: none;
    border-top: 1px solid {COLOR_BORDER};
    max-height: 1px;
}}

/* Status bar */
QStatusBar {{
    background-color: {COLOR_PANEL};
    color: {COLOR_TEXT_DIM};
    font-size: 11px;
    border-top: 1px solid {COLOR_BORDER};
}}

/* Splitter */
QSplitter::handle {{
    background-color: {COLOR_BORDER};
    width: 2px;
}}

/* Scrollbar */
QScrollBar:vertical {{
    background: {COLOR_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_TEXT_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""


# Main window

class MainWindow(QMainWindow):
    """Main window of the contact lens fitting assistant."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LensAdvisor — Contact Lens Fitting Assistant")
        self.setMinimumSize(1200, 750)
        self.resize(1350, 820)
        self.setStyleSheet(STYLESHEET)

        # Late import to avoid circular imports
        from controllers.optics_engine import OpticsEngine, SpectacleRx, Keratometry
        from controllers.matching_engine import MatchingEngine

        self._optics = OpticsEngine()
        self._matching = MatchingEngine()

        self._build_ui()
        self._connect_signals()
        self._set_status("Ready — Enter patient refraction and keratometry.")

    # UI construction

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 12, 16, 8)
        root_layout.setSpacing(10)

        root_layout.addWidget(self._build_header())

        sep = QFrame()
        sep.setObjectName("hRule")
        sep.setFrameShape(QFrame.HLine)
        root_layout.addWidget(sep)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([420, 900])
        root_layout.addWidget(splitter, stretch=1)

        self.statusBar().setVisible(True)

    def _build_header(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 0, 4, 0)

        lbl_title = QLabel("LensAdvisor")
        lbl_title.setObjectName("titleLabel")
        lbl_sub = QLabel("Contact Lens Fitting Assistant — Clinical use for orthoptists")
        lbl_sub.setObjectName("subtitleLabel")

        lbl_version = QLabel("v1.0")
        lbl_version.setObjectName("dimLabel")
        lbl_version.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lay.addWidget(lbl_title)
        lay.addSpacing(12)
        lay.addWidget(lbl_sub, stretch=1)
        lay.addWidget(lbl_version)
        return w

    def _build_left_panel(self) -> QWidget:
        """Left panel: patient data entry."""
        w = QWidget()
        w.setMaximumWidth(440)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(10)

        lay.addWidget(self._build_refraction_group())
        lay.addWidget(self._build_keratometry_group())
        lay.addWidget(self._build_filters_group())
        lay.addWidget(self._build_buttons())
        lay.addStretch()
        return w

    def _build_refraction_group(self) -> QGroupBox:
        grp = QGroupBox("Spectacle Refraction")
        grid = QGridLayout(grp)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        for col, txt in enumerate(["Parameter", "RE (right)", "LE (left)"]):
            lbl = QLabel(txt)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px; font-weight: bold;")
            grid.addWidget(lbl, 0, col)

        rows = [
            ("Sphere (D)",    "sph",  -25.00, +25.00, 0.25, "D"),
            ("Cylinder (D)",  "cyl",  -10.00,   0.00, 0.25, "D"),
            ("Axis (deg)",    "axis",     0,    180,    1,   "deg"),
            ("Addition (D)",  "add",   0.00,   4.00,  0.25, "D"),
        ]

        self._inputs = {}

        for r, (label, key, mn, mx, step, unit) in enumerate(rows, start=1):
            grid.addWidget(QLabel(label), r, 0)
            for eye in ("od", "os"):
                w_key = f"{key}_{eye}"
                if key == "axis":
                    spin = QSpinBox()
                    spin.setRange(int(mn), int(mx))
                    spin.setSuffix(f" {unit}")
                    spin.setValue(0)
                else:
                    spin = QDoubleSpinBox()
                    spin.setRange(mn, mx)
                    spin.setSingleStep(step)
                    spin.setDecimals(2)
                    spin.setSuffix(f" {unit}")
                    spin.setValue(0.0)
                spin.setMinimumWidth(120)
                self._inputs[w_key] = spin
                col = 1 if eye == "od" else 2
                grid.addWidget(spin, r, col)

        grid.addWidget(QLabel("Vertex distance (mm)"), len(rows) + 1, 0)
        self._vertex_spin = QDoubleSpinBox()
        self._vertex_spin.setRange(8.0, 18.0)
        self._vertex_spin.setValue(12.0)
        self._vertex_spin.setSingleStep(0.5)
        self._vertex_spin.setDecimals(1)
        self._vertex_spin.setSuffix(" mm")
        grid.addWidget(self._vertex_spin, len(rows) + 1, 1, 1, 2)

        return grp

    def _build_keratometry_group(self) -> QGroupBox:
        grp = QGroupBox("Keratometry")
        grid = QGridLayout(grp)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        for col, txt in enumerate(["Parameter", "RE (right)", "LE (left)"]):
            lbl = QLabel(txt)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px; font-weight: bold;")
            grid.addWidget(lbl, 0, col)

        kero_rows = [
            ("R1 — flat meridian (mm)", "r1", 6.50, 9.50, 0.01),
            ("R2 — steep meridian (mm)", "r2", 6.50, 9.50, 0.01),
        ]

        for r, (label, key, mn, mx, step) in enumerate(kero_rows, start=1):
            grid.addWidget(QLabel(label), r, 0)
            for eye in ("od", "os"):
                w_key = f"k_{key}_{eye}"
                spin = QDoubleSpinBox()
                spin.setRange(mn, mx)
                spin.setSingleStep(step)
                spin.setDecimals(2)
                spin.setSuffix(" mm")
                spin.setValue(7.80 if key == "r1" else 7.60)
                spin.setMinimumWidth(120)
                self._inputs[w_key] = spin
                col = 1 if eye == "od" else 2
                grid.addWidget(spin, r, col)

        hint = QLabel("R1 >= R2  (flat meridian always has the larger radius)")
        hint.setObjectName("dimLabel")
        hint.setWordWrap(True)
        grid.addWidget(hint, 3, 0, 1, 3)

        return grp

    def _build_filters_group(self) -> QGroupBox:
        grp = QGroupBox("Search Filters")
        lay = QVBoxLayout(grp)
        lay.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Wear type:"))
        self._combo_type = QComboBox()
        self._combo_type.addItems(["All", "daily", "monthly", "biweekly", "orthokeratology"])
        row1.addWidget(self._combo_type, stretch=1)
        lay.addLayout(row1)

        lay.addWidget(QLabel("Brands:"))
        brands = ["CooperVision", "Alcon", "Bausch + Lomb", "Johnson & Johnson", "FitBetter"]
        self._brand_checks = {}
        brand_grid = QGridLayout()
        brand_grid.setHorizontalSpacing(6)
        brand_grid.setVerticalSpacing(4)
        for i, brand in enumerate(brands):
            cb = QCheckBox(brand)
            cb.setChecked(True)
            self._brand_checks[brand] = cb
            brand_grid.addWidget(cb, i // 2, i % 2)
        lay.addLayout(brand_grid)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Number of results:"))
        self._spin_top_n = QSpinBox()
        self._spin_top_n.setRange(1, 10)
        self._spin_top_n.setValue(5)
        row2.addWidget(self._spin_top_n)
        row2.addStretch()
        lay.addLayout(row2)

        return grp

    def _build_buttons(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(10)

        self._btn_calc = QPushButton("Calculate & Recommend")
        self._btn_calc.setObjectName("btnCalculate")
        self._btn_calc.setCursor(Qt.PointingHandCursor)

        self._btn_reset = QPushButton("Reset")
        self._btn_reset.setObjectName("btnReset")
        self._btn_reset.setCursor(Qt.PointingHandCursor)

        lay.addWidget(self._btn_calc, stretch=3)
        lay.addWidget(self._btn_reset, stretch=1)
        return w

    def _build_right_panel(self) -> QWidget:
        """Right panel: results."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 0, 0, 0)
        lay.setSpacing(8)

        # Converted CL refraction summary
        self._grp_conversion = QGroupBox("Refraction converted to corneal plane (CL)")
        conv_lay = QHBoxLayout(self._grp_conversion)
        conv_lay.setSpacing(20)

        for eye, label in [("od", "Right Eye"), ("os", "Left Eye")]:
            sub = QVBoxLayout()
            lbl_head = QLabel(label)
            lbl_head.setStyleSheet(f"color: {COLOR_ACCENT}; font-weight: bold; font-size: 13px;")
            sub.addWidget(lbl_head)
            lbl_val = QLabel("—")
            lbl_val.setStyleSheet("font-size: 15px; color: white; font-weight: bold;")
            lbl_val.setObjectName(f"lc_result_{eye}")
            sub.addWidget(lbl_val)
            conv_lay.addLayout(sub)
            setattr(self, f"_lbl_lc_{eye}", lbl_val)

        lay.addWidget(self._grp_conversion)

        # Result tables
        tabs_widget = QWidget()
        tabs_lay = QHBoxLayout(tabs_widget)
        tabs_lay.setSpacing(8)

        self._tbl_od = self._make_result_table("RE — Right Eye")
        self._tbl_os = self._make_result_table("LE — Left Eye")
        tabs_lay.addWidget(self._tbl_od[0])
        tabs_lay.addWidget(self._tbl_os[0])
        lay.addWidget(tabs_widget, stretch=1)

        # Warnings / notes area
        self._grp_notes = QGroupBox("Warnings & Clinical Notes")
        notes_lay = QVBoxLayout(self._grp_notes)
        self._txt_notes = QTextEdit()
        self._txt_notes.setReadOnly(True)
        self._txt_notes.setMaximumHeight(140)
        self._txt_notes.setPlaceholderText("Clinical warnings will appear here after calculation...")
        notes_lay.addWidget(self._txt_notes)
        lay.addWidget(self._grp_notes)

        return w

    def _make_result_table(self, title: str):
        """Create a GroupBox containing a result table."""
        grp = QGroupBox(f"Candidates — {title}")
        lay = QVBoxLayout(grp)
        lay.setContentsMargins(6, 6, 6, 6)

        tbl = QTableWidget()
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setShowGrid(True)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)

        columns = ["Score", "Brand", "Model", "Type", "Sph", "Cyl", "Axis", "BC", "Dia", "Add"]
        tbl.setColumnCount(len(columns))
        tbl.setHorizontalHeaderLabels(columns)

        widths = [55, 120, 160, 90, 60, 55, 50, 50, 45, 70]
        for i, w in enumerate(widths):
            tbl.setColumnWidth(i, w)

        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        tbl.setMinimumHeight(200)

        tbl.itemSelectionChanged.connect(
            lambda t=tbl, eye=title: self._on_row_selected(t, eye)
        )

        lay.addWidget(tbl)
        return grp, tbl

    # Signals

    def _connect_signals(self):
        self._btn_calc.clicked.connect(self._on_calculate)
        self._btn_reset.clicked.connect(self._on_reset)

    # Slots

    def _on_calculate(self):
        """Trigger computation for both eyes."""
        self._txt_notes.clear()
        self._clear_tables()

        from controllers.optics_engine import SpectacleRx, Keratometry

        errors = []

        for eye in ("od", "os"):
            try:
                rx = SpectacleRx(
                    sphere=self._inputs[f"sph_{eye}"].value(),
                    cylinder=self._inputs[f"cyl_{eye}"].value(),
                    axis=self._inputs[f"axis_{eye}"].value(),
                    addition=self._inputs[f"add_{eye}"].value(),
                    vertex_distance=self._vertex_spin.value(),
                )
                r1 = self._inputs[f"k_r1_{eye}"].value()
                r2 = self._inputs[f"k_r2_{eye}"].value()

                if r1 < r2:
                    errors.append(
                        f"{eye.upper()}: R1 ({r1:.2f}) < R2 ({r2:.2f}) — "
                        "R1 must be the flat meridian (larger value). Auto-corrected."
                    )
                    r1, r2 = r2, r1

                kero = Keratometry(r1=r1, r2=r2)

                self._compute_eye(eye, rx, kero)

            except Exception as exc:
                errors.append(f"Error {eye.upper()}: {exc}")

        if errors:
            self._append_note("\n".join(errors), color=COLOR_WARNING)

        self._set_status("Calculation complete — Click a lens to view details.")

    def _compute_eye(self, eye: str, rx, kero):
        """Compute CL refraction and run matching for one eye."""
        # 1. Vertex conversion
        cl_rx = self._optics.compute_cl_refraction(rx)

        lbl = getattr(self, f"_lbl_lc_{eye}")
        lbl.setText(str(cl_rx))

        # 2. Filters
        type_filter = self._combo_type.currentText()
        if type_filter == "All":
            type_filter = None

        brands = [b for b, cb in self._brand_checks.items() if cb.isChecked()]
        if len(brands) == len(self._brand_checks):
            brands = None  # all brands selected = no filter

        top_n = self._spin_top_n.value()

        # 3. Matching
        candidates = self._matching.find_candidates(
            cl_rx=cl_rx,
            kero=kero,
            lens_type_filter=type_filter,
            brand_filter=brands,
            top_n=top_n,
        )

        # 4. Populate table
        tbl = self._tbl_od[1] if eye == "od" else self._tbl_os[1]
        self._populate_table(tbl, candidates)

        if not candidates:
            self._append_note(
                f"{eye.upper()}: No compatible lens found with current filters.",
                color=COLOR_WARNING,
            )

    def _populate_table(self, tbl: QTableWidget, candidates):
        """Populate a result table with the candidate list."""
        tbl.setRowCount(len(candidates))

        for row, c in enumerate(candidates):
            score_pct = c.score

            score_item = QTableWidgetItem(f"{score_pct:.0f}%")
            score_item.setTextAlignment(Qt.AlignCenter)
            if score_pct >= 70:
                score_item.setForeground(QColor(COLOR_ACCENT2))
            elif score_pct >= 45:
                score_item.setForeground(QColor(COLOR_WARNING))
            else:
                score_item.setForeground(QColor(COLOR_DANGER))

            cyl_str = (
                f"{c.ordered_cylinder:+.2f}" if c.ordered_cylinder != 0.0 else "—"
            )
            axis_str = (
                f"{c.ordered_axis}deg" if c.ordered_cylinder != 0.0 else "—"
            )
            add_str = c.ordered_addition if c.ordered_addition else "—"

            values = [
                score_item,
                c.brand,
                c.model,
                c.lens_type,
                f"{c.ordered_sphere:+.2f}",
                cyl_str,
                axis_str,
                f"{c.ordered_bc:.2f}",
                f"{c.ordered_diameter:.1f}",
                add_str,
            ]

            for col, val in enumerate(values):
                if isinstance(val, QTableWidgetItem):
                    item = val
                else:
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(row, col, item)

            tbl.item(row, 0).setData(Qt.UserRole, c)

    def _on_row_selected(self, tbl: QTableWidget, eye_label: str):
        """Display warnings for the selected lens."""
        sel = tbl.selectedItems()
        if not sel:
            return
        row = sel[0].row()
        score_item = tbl.item(row, 0)
        if score_item is None:
            return

        candidate = score_item.data(Qt.UserRole)
        if candidate is None:
            return

        self._txt_notes.clear()
        header = f"<b>{candidate.brand} — {candidate.model}</b> | Score: {candidate.score:.0f}%<br>"
        self._txt_notes.append(header)

        if candidate.warnings:
            for w in candidate.warnings:
                self._txt_notes.append(f"Warning: {w}")
        else:
            self._txt_notes.append("No warnings — standard fitting.")

        if candidate.fit_notes:
            self._txt_notes.append(f"<br><i>Manufacturer note: {candidate.fit_notes}</i>")

        detail = (
            f"<br><b>Suggested CL order:</b><br>"
            f"  Sph {candidate.ordered_sphere:+.2f} D | "
            f"  Cyl {candidate.ordered_cylinder:+.2f} D | "
            f"  Axis {candidate.ordered_axis}deg | "
            f"  BC {candidate.ordered_bc:.2f} mm | "
            f"  Dia {candidate.ordered_diameter:.1f} mm"
        )
        if candidate.ordered_addition:
            detail += f" | Add {candidate.ordered_addition}"
        self._txt_notes.append(detail)

    def _on_reset(self):
        """Reset all input fields."""
        for key, spin in self._inputs.items():
            if isinstance(spin, QSpinBox):
                spin.setValue(0)
            elif "k_r" in key:
                spin.setValue(7.80 if "r1" in key else 7.60)
            else:
                spin.setValue(0.0)
        self._vertex_spin.setValue(12.0)
        self._combo_type.setCurrentIndex(0)
        for cb in self._brand_checks.values():
            cb.setChecked(True)
        self._spin_top_n.setValue(5)
        self._clear_tables()
        self._txt_notes.clear()
        for eye in ("od", "os"):
            getattr(self, f"_lbl_lc_{eye}").setText("—")
        self._set_status("Form reset.")

    def _clear_tables(self):
        for tbl in (self._tbl_od[1], self._tbl_os[1]):
            tbl.setRowCount(0)

    # Helpers

    def _append_note(self, text: str, color: str = COLOR_TEXT):
        self._txt_notes.setTextColor(QColor(color))
        self._txt_notes.append(text)
        self._txt_notes.setTextColor(QColor(COLOR_TEXT))

    def _set_status(self, msg: str):
        self.statusBar().showMessage(f"  {msg}")
