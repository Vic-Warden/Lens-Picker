"""
views/main_window.py
Main graphical interface — Contact lens fitting assistant.

MVC architecture:
  - This module contains only the view (PyQt5).
  - All business logic is delegated to the controllers.

Changes vs v1.0:
  - [P0] Bug fix: compute_cl_refraction_multifocal() now called for presbyopic patients.
  - [P0] Bug fix: axis QSpinBox minimum set to 1 (optometric convention 1–180).
  - [P1] Interface LARS: drift input + "Correct Axis" button in the notes panel.
  - [P1] Brands derived dynamically from LENS_DATABASE (no hard-coded list).
  - [P1] Keratometry displayed in diopters (K1, K2, Km, corneal Ast) live.
  - [P2] Keratometry clinical warnings (K > 48 D → keratoconus suspicion).
  - [P2] "Copy Prescription" button to clipboard.
  - [P2] Informative empty-result messages (explains which filter rejected).
  - [P2] BC fitting rule selector (ortho-K support).
  - [P2] UI constants sourced from config.py.
"""

import sys
from typing import List, Optional, Dict

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QDoubleSpinBox, QSpinBox, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QTextEdit, QFrame, QMessageBox, QStatusBar,
    QCheckBox, QSizePolicy, QAbstractItemView, QApplication,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

from config import (
    UI_MIN_WIDTH, UI_MIN_HEIGHT, UI_DEFAULT_WIDTH, UI_DEFAULT_HEIGHT,
    UI_LEFT_PANEL_MAX_WIDTH, UI_SPLITTER_LEFT, UI_SPLITTER_RIGHT,
    UI_NOTES_MAX_HEIGHT,
    KERATO_SUSPECT_THRESHOLD_D, KERO_R_MIN_MM, KERO_R_MAX_MM,
)

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
COLOR_OD        = "#FF6B6B"   # soft red for right eye header
COLOR_OS        = "#6BCB77"   # soft green for left eye header

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
QLabel#kDioptersLabel {{
    color: {COLOR_ACCENT2};
    font-size: 11px;
    font-style: italic;
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

/* LARS / copy button */
QPushButton#btnSecondary {{
    background-color: transparent;
    color: {COLOR_ACCENT};
    border: 1px solid {COLOR_ACCENT};
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 12px;
}}
QPushButton#btnSecondary:hover {{
    background-color: {COLOR_ACCENT};
    color: white;
}}
QPushButton#btnSecondary:pressed {{
    background-color: #2D65CC;
    color: white;
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

# Column tooltips for the result table
COLUMN_TOOLTIPS = {
    "Score":  "Score de compatibilité (0–100). Sphère 40 pts · Cylindre 30 pts · RC 20 pts · Addition 10 pts.",
    "Marque": "Fabricant / marque.",
    "Modèle": "Nom du modèle de lentille.",
    "Type":   "Modalité de port : journalière / mensuelle / bimensuelle / orthokératologie.",
    "Sph":    "Puissance sphérique commandée au plan cornéen (dioptries).",
    "Cyl":    "Puissance cylindrique commandée, convention cylindre négatif (dioptries). '—' = sphérique.",
    "Axe":    "Axe du cylindre commandé (degrés, 1–180). '—' = sphérique.",
    "RC":     "Rayon de courbure — rayon de la face postérieure de la lentille (mm). Dérivé de la kératométrie.",
    "Dia":    "Diamètre total de la lentille (mm).",
    "Add":    "Puissance d'addition commandée pour les lentilles multifocales. Inclut la désignation fabricant si disponible.",
}


# French label → internal value mappings (keeps business logic unchanged)
WEAR_TYPE_FR = {
    "Tous":              None,
    "Journalière":       "daily",
    "Mensuelle":         "monthly",
    "Bimensuelle":       "biweekly",
    "Orthokératologie":  "orthokeratology",
}

BC_RULE_FR = {
    "K plat + 0,10 mm":        "flat_k_plus_offset",
    "K moyen":                  "mean_k",
    "K plat + 0,50 mm (ortho-K)": "ortho_k_flat_k",
}


# Main window

class MainWindow(QMainWindow):
    """Main window of the contact lens fitting assistant."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LensAdvisor — Assistant d'Adaptation en Lentilles de Contact")
        self.setMinimumSize(UI_MIN_WIDTH, UI_MIN_HEIGHT)
        self.resize(UI_DEFAULT_WIDTH, UI_DEFAULT_HEIGHT)
        self.setStyleSheet(STYLESHEET)

        # Late import to avoid circular imports at module load time
        from controllers.optics_engine import OpticsEngine, SpectacleRx, Keratometry
        from controllers.matching_engine import MatchingEngine

        self._optics = OpticsEngine()
        self._matching = MatchingEngine()

        # Stores the last computed candidates per eye for LARS correction
        self._last_candidates: Dict[str, list] = {"od": [], "os": []}

        self._build_ui()
        self._connect_signals()
        self._set_status("Prêt — Saisissez la réfraction et la kératométrie du patient.")

    # UI construction

    def _build_ui(self) -> None:
        """Assemble the full window layout."""
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 12, 16, 8)
        root_layout.setSpacing(10)

        root_layout.addWidget(self._build_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([UI_SPLITTER_LEFT, UI_SPLITTER_RIGHT])
        root_layout.addWidget(splitter, stretch=1)

        self.statusBar().setVisible(True)

    def _build_header(self) -> QWidget:
        """Application title bar."""
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 0, 4, 0)

        lbl_title = QLabel("LensAdvisor")
        lbl_title.setObjectName("titleLabel")
        lbl_sub = QLabel("Assistant d'Adaptation en Lentilles de Contact — Usage clinique pour orthoptistes")
        lbl_sub.setObjectName("subtitleLabel")

        lbl_version = QLabel("v2.0")
        lbl_version.setObjectName("dimLabel")
        lbl_version.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lay.addWidget(lbl_title)
        lay.addSpacing(12)
        lay.addWidget(lbl_sub, stretch=1)
        lay.addWidget(lbl_version)
        return w

    def _build_left_panel(self) -> QWidget:
        """Left panel: all patient data entry fields and filters."""
        w = QWidget()
        w.setMaximumWidth(UI_LEFT_PANEL_MAX_WIDTH)
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
        """Spectacle refraction input grid (OD / OS)."""
        grp = QGroupBox("Réfraction en Lunettes")
        grid = QGridLayout(grp)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        for col, txt in enumerate(["Paramètre", "OD (droit)", "OG (gauche)"]):
            lbl = QLabel(txt)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"color: {COLOR_TEXT_DIM}; font-size: 11px; font-weight: bold;"
            )
            grid.addWidget(lbl, 0, col)

        # Column headers with OD/OS colour coding
        grid.itemAtPosition(0, 1).widget().setStyleSheet(
            f"color: {COLOR_OD}; font-size: 11px; font-weight: bold;"
        )
        grid.itemAtPosition(0, 2).widget().setStyleSheet(
            f"color: {COLOR_OS}; font-size: 11px; font-weight: bold;"
        )

        rows = [
            ("Sphère (D)",    "sph",  -25.00, +25.00, 0.25, "D"),
            ("Cylindre (D)",  "cyl",  -10.00,   0.00, 0.25, "D"),
            ("Axe (°)",       "axis",      1,    180,    1,  "°"),
            ("Addition (D)",  "add",   0.00,   4.00,  0.25, "D"),
        ]

        self._inputs = {}

        for r, (label, key, mn, mx, step, unit) in enumerate(rows, start=1):
            grid.addWidget(QLabel(label), r, 0)
            for eye in ("od", "os"):
                w_key = f"{key}_{eye}"
                if key == "axis":
                    spin = QSpinBox()
                    spin.setRange(int(mn), int(mx))  # 1–180, convention optométrique
                    spin.setSuffix(f" {unit}")
                    spin.setValue(90)
                    spin.setToolTip("Axe du cylindre — convention optométrique : 1° à 180°.")
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

        grid.addWidget(QLabel("Distance vertex (mm)"), len(rows) + 1, 0)
        self._vertex_spin = QDoubleSpinBox()
        self._vertex_spin.setRange(8.0, 18.0)
        self._vertex_spin.setValue(12.0)
        self._vertex_spin.setSingleStep(0.5)
        self._vertex_spin.setDecimals(1)
        self._vertex_spin.setSuffix(" mm")
        self._vertex_spin.setToolTip(
            "Distance entre la face postérieure du verre correcteur et l'apex cornéen (défaut 12 mm)."
        )
        grid.addWidget(self._vertex_spin, len(rows) + 1, 1, 1, 2)

        return grp

    def _build_keratometry_group(self) -> QGroupBox:
        """Keratometry inputs with live dioptre display and clinical warnings."""
        grp = QGroupBox("Kératométrie")
        grid = QGridLayout(grp)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        for col, txt in enumerate(["Paramètre", "OD (droit)", "OG (gauche)"]):
            lbl = QLabel(txt)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"color: {COLOR_TEXT_DIM}; font-size: 11px; font-weight: bold;"
            )
            grid.addWidget(lbl, 0, col)

        grid.itemAtPosition(0, 1).widget().setStyleSheet(
            f"color: {COLOR_OD}; font-size: 11px; font-weight: bold;"
        )
        grid.itemAtPosition(0, 2).widget().setStyleSheet(
            f"color: {COLOR_OS}; font-size: 11px; font-weight: bold;"
        )

        kero_rows = [
            ("R1 — méridien plat (mm)", "r1", KERO_R_MIN_MM, KERO_R_MAX_MM, 0.01),
            ("R2 — méridien cambré (mm)", "r2", KERO_R_MIN_MM, KERO_R_MAX_MM, 0.01),
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
                spin.setToolTip(
                    "Méridien plat (K1) : rayon le plus grand — puissance la plus faible.\n"
                    "Méridien cambré (K2) : rayon le plus petit — puissance la plus forte.\n"
                    f"Plage physiologique : {mn:.2f}–{mx:.2f} mm."
                )
                self._inputs[w_key] = spin
                col = 1 if eye == "od" else 2
                grid.addWidget(spin, r, col)
                # Connect live update
                spin.valueChanged.connect(self._update_kero_display)

        hint = QLabel("R1 ≥ R2  (méridien plat → rayon plus grand)")
        hint.setObjectName("dimLabel")
        hint.setWordWrap(True)
        grid.addWidget(hint, 3, 0, 1, 3)

        # Live K dioptre labels — one per eye
        self._lbl_k_od = QLabel("")
        self._lbl_k_od.setObjectName("kDioptersLabel")
        self._lbl_k_od.setWordWrap(True)
        self._lbl_k_os = QLabel("")
        self._lbl_k_os.setObjectName("kDioptersLabel")
        self._lbl_k_os.setWordWrap(True)
        grid.addWidget(self._lbl_k_od, 4, 1)
        grid.addWidget(self._lbl_k_os, 4, 2)

        # Trigger initial display
        self._update_kero_display()

        return grp

    def _build_filters_group(self) -> QGroupBox:
        """Search filters: wear type, brands (dynamic), result count, BC rule."""
        grp = QGroupBox("Filtres de Recherche")
        lay = QVBoxLayout(grp)
        lay.setSpacing(8)

        # Wear type
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Type de port :"))
        self._combo_type = QComboBox()
        self._combo_type.addItems(list(WEAR_TYPE_FR.keys()))
        self._combo_type.setToolTip("Filtrer par modalité de renouvellement.")
        row1.addWidget(self._combo_type, stretch=1)
        lay.addLayout(row1)

        # BC fitting rule
        row_bc = QHBoxLayout()
        row_bc.addWidget(QLabel("Règle RC :"))
        self._combo_bc_rule = QComboBox()
        self._combo_bc_rule.addItems(list(BC_RULE_FR.keys()))
        self._combo_bc_rule.setToolTip(
            "Règle de sélection du rayon de courbure :\n"
            "• K plat + 0,10 mm : règle standard LC souples\n"
            "• K moyen : moyenne des deux méridiens\n"
            "• K plat + 0,50 mm (ortho-K) : règle empirique initiale orthokératologie"
        )
        row_bc.addWidget(self._combo_bc_rule, stretch=1)
        lay.addLayout(row_bc)

        # Brands — derived dynamically from the database
        lay.addWidget(QLabel("Marques :"))
        from data.lens_database import LENS_DATABASE
        brands = sorted({lens["brand"] for lens in LENS_DATABASE})
        self._brand_checks: Dict[str, QCheckBox] = {}
        brand_grid = QGridLayout()
        brand_grid.setHorizontalSpacing(6)
        brand_grid.setVerticalSpacing(4)
        for i, brand in enumerate(brands):
            cb = QCheckBox(brand)
            cb.setChecked(True)
            self._brand_checks[brand] = cb
            brand_grid.addWidget(cb, i // 2, i % 2)
        lay.addLayout(brand_grid)

        # Number of results
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Nombre de résultats :"))
        self._spin_top_n = QSpinBox()
        self._spin_top_n.setRange(1, 10)
        self._spin_top_n.setValue(5)
        row2.addWidget(self._spin_top_n)
        row2.addStretch()
        lay.addLayout(row2)

        return grp

    def _build_buttons(self) -> QWidget:
        """Calculate and Reset buttons."""
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(10)

        self._btn_calc = QPushButton("Calculer & Recommander")
        self._btn_calc.setObjectName("btnCalculate")
        self._btn_calc.setCursor(Qt.PointingHandCursor)
        self._btn_calc.setToolTip("Lancer le moteur de recommandation pour les deux yeux (F5).")

        self._btn_reset = QPushButton("Réinitialiser")
        self._btn_reset.setObjectName("btnReset")
        self._btn_reset.setCursor(Qt.PointingHandCursor)
        self._btn_reset.setToolTip("Effacer tous les champs (Ctrl+R).")

        lay.addWidget(self._btn_calc, stretch=3)
        lay.addWidget(self._btn_reset, stretch=1)
        return w

    def _build_right_panel(self) -> QWidget:
        """Right panel: converted refraction, result tables, notes, LARS, copy."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 0, 0, 0)
        lay.setSpacing(8)

        # Converted CL refraction summary
        self._grp_conversion = QGroupBox("Réfraction convertie au plan cornéen (LC)")
        conv_lay = QHBoxLayout(self._grp_conversion)
        conv_lay.setSpacing(20)

        for eye, label in [("od", "Œil Droit (OD)"), ("os", "Œil Gauche (OG)")]:
            sub = QVBoxLayout()
            lbl_head = QLabel(label)
            head_color = COLOR_OD if eye == "od" else COLOR_OS
            lbl_head.setStyleSheet(
                f"color: {head_color}; font-weight: bold; font-size: 13px;"
            )
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

        self._tbl_od = self._make_result_table("OD — Œil Droit", "od")
        self._tbl_os = self._make_result_table("OG — Œil Gauche", "os")
        tabs_lay.addWidget(self._tbl_od[0])
        tabs_lay.addWidget(self._tbl_os[0])
        lay.addWidget(tabs_widget, stretch=1)

        # Notes area
        self._grp_notes = QGroupBox("Avertissements & Notes Cliniques")
        notes_lay = QVBoxLayout(self._grp_notes)
        self._txt_notes = QTextEdit()
        self._txt_notes.setReadOnly(True)
        self._txt_notes.setMaximumHeight(UI_NOTES_MAX_HEIGHT)
        self._txt_notes.setPlaceholderText(
            "Les avertissements cliniques s'afficheront ici après le calcul..."
        )
        notes_lay.addWidget(self._txt_notes)

        # Action row: LARS correction + Copy prescription
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        lars_lbl = QLabel("Rotation lentille d'essai :")
        lars_lbl.setObjectName("dimLabel")
        action_row.addWidget(lars_lbl)

        self._lars_spin = QSpinBox()
        self._lars_spin.setRange(-45, 45)
        self._lars_spin.setValue(0)
        self._lars_spin.setSuffix("°")
        self._lars_spin.setToolTip(
            "Règle LARS — rotation observée de la lentille torique d'essai :\n"
            " + = rotation vers la GAUCHE  (ajouter à l'axe)\n"
            " − = rotation vers la DROITE (soustraire à l'axe)\n"
            "Référence : Gasson & Morris, Contact Lens Manual 4e éd. (2010)."
        )
        self._lars_spin.setMinimumWidth(80)
        action_row.addWidget(self._lars_spin)

        self._btn_lars = QPushButton("Corriger l'Axe (LARS)")
        self._btn_lars.setObjectName("btnSecondary")
        self._btn_lars.setCursor(Qt.PointingHandCursor)
        self._btn_lars.setToolTip(
            "Appliquer la correction LARS à l'axe du candidat torique sélectionné."
        )
        action_row.addWidget(self._btn_lars)

        action_row.addStretch()

        self._btn_copy = QPushButton("Copier l'Ordonnance")
        self._btn_copy.setObjectName("btnSecondary")
        self._btn_copy.setCursor(Qt.PointingHandCursor)
        self._btn_copy.setToolTip(
            "Copier l'ordonnance de la lentille sélectionnée dans le presse-papiers."
        )
        action_row.addWidget(self._btn_copy)

        notes_lay.addLayout(action_row)
        lay.addWidget(self._grp_notes)

        return w

    def _make_result_table(self, title: str, eye: str):
        """
        Create a GroupBox containing a result table.

        Args:
            title: display title for the GroupBox
            eye:   "od" or "os" — used to bind the selection signal

        Returns:
            Tuple (QGroupBox, QTableWidget)
        """
        grp = QGroupBox(f"Candidats — {title}")
        lay = QVBoxLayout(grp)
        lay.setContentsMargins(6, 6, 6, 6)

        tbl = QTableWidget()
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setShowGrid(True)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)

        columns = ["Score", "Marque", "Modèle", "Type", "Sph", "Cyl", "Axe", "RC", "Dia", "Add"]
        tbl.setColumnCount(len(columns))
        tbl.setHorizontalHeaderLabels(columns)

        # Tooltips on column headers
        for i, col_name in enumerate(columns):
            tbl.horizontalHeaderItem(i).setToolTip(
                COLUMN_TOOLTIPS.get(col_name, col_name)
            )

        widths = [55, 120, 160, 90, 60, 55, 50, 50, 45, 70]
        for i, w in enumerate(widths):
            tbl.setColumnWidth(i, w)

        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        tbl.setMinimumHeight(200)

        tbl.itemSelectionChanged.connect(
            lambda t=tbl, e=eye: self._on_row_selected(t, e)
        )

        lay.addWidget(tbl)
        return grp, tbl

    # Signal connections

    def _connect_signals(self) -> None:
        """Wire all interactive signals to their slots."""
        self._btn_calc.clicked.connect(self._on_calculate)
        self._btn_reset.clicked.connect(self._on_reset)
        self._btn_lars.clicked.connect(self._on_apply_lars)
        self._btn_copy.clicked.connect(self._on_copy_prescription)

        # Keyboard shortcuts
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        QShortcut(QKeySequence("F5"), self).activated.connect(self._on_calculate)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self._on_reset)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self._on_copy_prescription)

    # Live keratometry display

    def _update_kero_display(self) -> None:
        """
        Recalculate and display K1, K2, Km, corneal astigmatism in diopters
        whenever any keratometry spin changes.  Also emits clinical warnings
        for out-of-range values.
        """
        from controllers.optics_engine import Keratometry

        for eye, lbl in [("od", self._lbl_k_od), ("os", self._lbl_k_os)]:
            r1 = self._inputs[f"k_r1_{eye}"].value()
            r2 = self._inputs[f"k_r2_{eye}"].value()

            # Swap silently for display purposes (do not mutate spinboxes here)
            flat_r = max(r1, r2)
            steep_r = min(r1, r2)

            try:
                kero = Keratometry(r1=flat_r, r2=steep_r)
                k1 = kero.k1_diopters
                k2 = kero.k2_diopters
                km = kero.km_diopters
                ast = kero.corneal_astigmatism_diopters

                warnings = []
                if k1 >= KERATO_SUSPECT_THRESHOLD_D or k2 >= KERATO_SUSPECT_THRESHOLD_D:
                    warnings.append("⚠ K > 48 D — suspicion de kératocône")

                warn_str = f"  {warnings[0]}" if warnings else ""
                lbl.setText(
                    f"K1 {k1:.2f} D · K2 {k2:.2f} D · Km {km:.2f} D · "
                    f"Ast {ast:.2f} D{warn_str}"
                )
                if warnings:
                    lbl.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 11px; font-style: italic;")
                else:
                    lbl.setStyleSheet(f"color: {COLOR_ACCENT2}; font-size: 11px; font-style: italic;")
            except Exception:
                lbl.setText("")

    # Main calculation slot

    def _on_calculate(self) -> None:
        """Trigger computation for both eyes."""
        self._txt_notes.clear()
        self._clear_tables()
        self._last_candidates = {"od": [], "os": []}

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
                        "R1 doit être le méridien plat (valeur plus grande). Corrigé automatiquement."
                    )
                    r1, r2 = r2, r1

                kero = Keratometry(r1=r1, r2=r2)
                self._compute_eye(eye, rx, kero)

            except ValueError as exc:
                errors.append(f"Erreur de saisie {eye.upper()} : {exc}")
            except Exception as exc:
                errors.append(f"Erreur inattendue {eye.upper()} : {exc}")

        if errors:
            self._append_note("\n".join(errors), color=COLOR_WARNING)

        self._set_status("Calcul terminé — Cliquez sur une ligne pour afficher les détails.")

    def _compute_eye(self, eye: str, rx, kero) -> None:
        """
        Compute CL refraction and run matching for one eye.

        Key fix (v2.0): uses compute_cl_refraction_multifocal() for presbyopic
        patients (addition > 0), which starts from the spherical equivalent.
        """
        from controllers.optics_engine import SpectacleRx

        # [P0 FIX] Route to the correct computation method
        if rx.addition > 0.0:
            cl_rx = self._optics.compute_cl_refraction_multifocal(rx)
        else:
            cl_rx = self._optics.compute_cl_refraction(rx)

        lbl = getattr(self, f"_lbl_lc_{eye}")
        lbl.setText(str(cl_rx))

        # Filters — map French display labels to internal values
        type_filter = WEAR_TYPE_FR.get(self._combo_type.currentText())

        brands = [b for b, cb in self._brand_checks.items() if cb.isChecked()]
        if len(brands) == len(self._brand_checks):
            brands = None  # all brands → no filter

        top_n = self._spin_top_n.value()
        bc_rule = BC_RULE_FR.get(self._combo_bc_rule.currentText(), "flat_k_plus_offset")

        # Matching
        candidates = self._matching.find_candidates(
            cl_rx=cl_rx,
            kero=kero,
            lens_type_filter=type_filter,
            brand_filter=brands,
            top_n=top_n,
            bc_fitting_rule=bc_rule,
        )

        self._last_candidates[eye] = candidates

        # Populate table
        tbl = self._tbl_od[1] if eye == "od" else self._tbl_os[1]
        self._populate_table(tbl, candidates)

        if not candidates:
            reason = self._explain_empty_results(cl_rx, type_filter, brands)
            self._append_note(
                f"{eye.upper()} : Aucune lentille compatible trouvée. {reason}",
                color=COLOR_WARNING,
            )

    def _explain_empty_results(
        self,
        cl_rx,
        type_filter: Optional[str],
        brands: Optional[List[str]],
    ) -> str:
        """
        Generate a human-readable explanation for why no candidates were found.
        Checks sphere range, cylinder range, and active filters.
        """
        from data.lens_database import LENS_DATABASE

        reasons = []

        # Check if sphere is out of all lenses in the DB
        any_sph = any(
            lens["sphere_range"][0] <= cl_rx.sphere <= lens["sphere_range"][1]
            for lens in LENS_DATABASE
        )
        if not any_sph:
            reasons.append(
                f"La sphère {cl_rx.sphere:+.2f} D est hors de toutes les plages disponibles."
            )

        # Check if cylinder is out of all toric lenses
        if abs(cl_rx.cylinder) >= 1.0:
            any_cyl = any(
                lens["cylinder_range"] is not None and
                lens["cylinder_range"][1] <= cl_rx.cylinder <= lens["cylinder_range"][0]
                for lens in LENS_DATABASE
            )
            if not any_cyl:
                reasons.append(
                    f"Le cylindre {cl_rx.cylinder:+.2f} D dépasse toutes les plages toriques."
                )

        if type_filter:
            reasons.append(f"Filtre de type de port actif : '{type_filter}'.")
        if brands:
            reasons.append(f"Filtre de marque actif : {', '.join(brands)}.")

        return " ".join(reasons) if reasons else "Vérifiez les filtres ou élargissez la plage de réfraction."

    # Table population and row selection

    def _populate_table(self, tbl: QTableWidget, candidates) -> None:
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
            # Show LARS-corrected axis if available, else standard axis
            displayed_axis = (
                c.lars_corrected_axis
                if c.lars_corrected_axis is not None
                else c.ordered_axis
            )
            axis_str = f"{displayed_axis}°" if c.ordered_cylinder != 0.0 else "—"
            if c.lars_corrected_axis is not None and c.ordered_cylinder != 0.0:
                axis_str += " ✓"  # visual indicator that LARS was applied

            add_str = c.ordered_addition if c.ordered_addition else "—"

            # Dk/t badge
            dkt_badge = " ★" if c.dk_t >= 140 else ""
            model_str = c.model + dkt_badge

            values = [
                score_item,
                c.brand,
                model_str,
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

            # Store candidate object on the score item for later retrieval
            tbl.item(row, 0).setData(Qt.UserRole, c)

    def _on_row_selected(self, tbl: QTableWidget, eye: str) -> None:
        """Display detailed warnings and prescription for the selected lens row."""
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
        eye_label = "Œil Droit (OD)" if eye == "od" else "Œil Gauche (OG)"
        header = (
            f"<b>{candidate.brand} — {candidate.model}</b> "
            f"| {eye_label} | Score : {candidate.score:.0f}%<br>"
        )
        self._txt_notes.append(header)

        if candidate.warnings:
            for w in candidate.warnings:
                self._append_note(f"⚠  {w}", color=COLOR_WARNING)
        else:
            self._txt_notes.append("Aucun avertissement — adaptation standard.")

        if candidate.fit_notes:
            self._txt_notes.append(
                f"<br><i>Note fabricant : {candidate.fit_notes}</i>"
            )

        # Determine which axis to display
        axis_display = (
            candidate.lars_corrected_axis
            if candidate.lars_corrected_axis is not None
            else candidate.ordered_axis
        )
        lars_tag = " (axe corrigé LARS ✓)" if candidate.lars_corrected_axis is not None else ""

        detail = (
            f"<br><b>Ordonnance LC suggérée :</b><br>"
            f"  Sph {candidate.ordered_sphere:+.2f} D  |  "
            f"  Cyl {candidate.ordered_cylinder:+.2f} D  |  "
            f"  Axe {axis_display}°{lars_tag}  |  "
            f"  RC {candidate.ordered_bc:.2f} mm  |  "
            f"  Dia {candidate.ordered_diameter:.1f} mm"
        )
        if candidate.ordered_addition:
            detail += f"  |  Add {candidate.ordered_addition}"
        self._txt_notes.append(detail)

        dk_info = f"<br><small>Matériau : {candidate.material} · Dk/t : {candidate.dk_t}</small>"
        self._txt_notes.append(dk_info)

    # LARS correction slot

    def _on_apply_lars(self) -> None:
        """
        Apply the LARS correction to the selected row in the active table.

        Determines which table is active by checking which has a current selection.
        Updates the candidate's lars_corrected_axis and refreshes the table row.
        """
        from controllers.matching_engine import MatchingEngine

        drift = self._lars_spin.value()
        if drift == 0:
            self._append_note(
                "LARS : dérive à 0° — aucune correction appliquée.", color=COLOR_TEXT_DIM
            )
            return

        # Find the table that has an active selection
        active_tbl = None
        active_eye = None
        for eye, tbl_tuple in [("od", self._tbl_od), ("os", self._tbl_os)]:
            if tbl_tuple[1].selectedItems():
                active_tbl = tbl_tuple[1]
                active_eye = eye
                break

        if active_tbl is None:
            self._append_note(
                "LARS : sélectionnez d'abord une lentille torique dans un tableau de résultats.",
                color=COLOR_WARNING,
            )
            return

        sel = active_tbl.selectedItems()
        row = sel[0].row()
        score_item = active_tbl.item(row, 0)
        if score_item is None:
            return

        candidate = score_item.data(Qt.UserRole)
        if candidate is None:
            return

        if candidate.ordered_cylinder == 0.0:
            self._append_note(
                "LARS : la lentille sélectionnée est sphérique — aucun axe à corriger.",
                color=COLOR_WARNING,
            )
            return

        original_axis = candidate.ordered_axis
        corrected_axis = MatchingEngine.apply_lars(original_axis, drift)
        candidate.lars_corrected_axis = corrected_axis

        # Refresh display
        self._populate_table(active_tbl, self._last_candidates[active_eye])

        # Re-select the same row
        active_tbl.selectRow(row)

        self._append_note(
            f"LARS appliqué : axe {original_axis}° + dérive {drift:+d}° → "
            f"axe corrigé {corrected_axis}°.",
            color=COLOR_ACCENT2,
        )

    # Copy prescription slot

    def _on_copy_prescription(self) -> None:
        """
        Copy the currently displayed prescription (notes panel) to the clipboard
        in plain-text format, suitable for pasting into a patient record.
        """
        # Find active candidate from whichever table has a selection
        candidate = None
        eye_label = ""
        for eye, tbl_tuple in [("od", self._tbl_od), ("os", self._tbl_os)]:
            tbl = tbl_tuple[1]
            sel = tbl.selectedItems()
            if sel:
                row = sel[0].row()
                item = tbl.item(row, 0)
                if item:
                    candidate = item.data(Qt.UserRole)
                    eye_label = "Œil Droit (OD)" if eye == "od" else "Œil Gauche (OG)"
                break

        if candidate is None:
            self._append_note(
                "Copie : sélectionnez d'abord une ligne.", color=COLOR_WARNING
            )
            return

        axis_display = (
            candidate.lars_corrected_axis
            if candidate.lars_corrected_axis is not None
            else candidate.ordered_axis
        )
        lars_note = " [axe corrigé LARS]" if candidate.lars_corrected_axis is not None else ""

        lines = [
            f"LensAdvisor — Récapitulatif Ordonnance",
            f"Œil :       {eye_label}",
            f"Marque :    {candidate.brand}",
            f"Modèle :    {candidate.model}",
            f"Matériau :  {candidate.material}  |  Dk/t : {candidate.dk_t}",
            f"---",
            f"Sphère :    {candidate.ordered_sphere:+.2f} D",
            f"Cylindre :  {candidate.ordered_cylinder:+.2f} D",
            f"Axe :       {axis_display}°{lars_note}",
            f"RC :        {candidate.ordered_bc:.2f} mm",
            f"Diamètre :  {candidate.ordered_diameter:.1f} mm",
        ]
        if candidate.ordered_addition:
            lines.append(f"Addition :  {candidate.ordered_addition}")
        if candidate.warnings:
            lines.append("---")
            lines.append("Avertissements :")
            for w in candidate.warnings:
                lines.append(f"  * {w}")
        if candidate.fit_notes:
            lines.append(f"Note : {candidate.fit_notes}")

        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        self._set_status("Ordonnance copiée dans le presse-papiers.")
        self._append_note("Ordonnance copiée dans le presse-papiers.", color=COLOR_ACCENT2)

    # Reset slot

    def _on_reset(self) -> None:
        """Reset all input fields to defaults."""
        for key, spin in self._inputs.items():
            if isinstance(spin, QSpinBox):
                spin.setValue(90)  # default axis 90°
            elif "k_r" in key:
                spin.setValue(7.80 if "r1" in key else 7.60)
            else:
                spin.setValue(0.0)
        self._vertex_spin.setValue(12.0)
        self._combo_type.setCurrentIndex(0)
        self._combo_bc_rule.setCurrentIndex(0)
        for cb in self._brand_checks.values():
            cb.setChecked(True)
        self._spin_top_n.setValue(5)
        self._lars_spin.setValue(0)
        self._clear_tables()
        self._txt_notes.clear()
        for eye in ("od", "os"):
            getattr(self, f"_lbl_lc_{eye}").setText("—")
        self._last_candidates = {"od": [], "os": []}
        self._update_kero_display()
        self._set_status("Formulaire réinitialisé.")

    # Helpers

    def _clear_tables(self) -> None:
        """Remove all rows from both result tables."""
        for tbl in (self._tbl_od[1], self._tbl_os[1]):
            tbl.setRowCount(0)

    def _append_note(self, text: str, color: str = COLOR_TEXT) -> None:
        """Append coloured text to the notes panel."""
        self._txt_notes.setTextColor(QColor(color))
        self._txt_notes.append(text)
        self._txt_notes.setTextColor(QColor(COLOR_TEXT))

    def _set_status(self, msg: str) -> None:
        """Update the status bar message."""
        self.statusBar().showMessage(f"  {msg}")