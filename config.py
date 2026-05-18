"""
config.py — Global constants for LensAdvisor (clinical thresholds, scoring, UI).
"""

# Vertex compensation threshold (D)
VERTEX_COMPENSATION_THRESHOLD: float = 4.0

# Default vertex distance (mm)
DEFAULT_VERTEX_MM: float = 12.0

# BC delta (mm) above which a warning is raised
BC_DELTA_WARN: float = 0.30

# Astigmatism threshold (D) — spherical vs toric
ASTIG_THRESHOLD: float = 0.75

# J&J Simplifit MF — spherical treatment limit
ASTIG_SPHERICAL_MF_MAX: float = 0.75

# J&J Simplifit MF — toric MF without sphere adjustment
ASTIG_TORIC_MF_LOW_MAX: float = 1.25

# J&J Simplifit MF — toric MF with −0.25 D sphere adjustment
ASTIG_TORIC_MF_HIGH_MAX: float = 1.75

# Scoring weights
SCORE_SPHERE_MAX: int = 40
SCORE_CYL_MAX: int = 30
SCORE_BC_MAX: int = 20
SCORE_ADD_MAX: int = 10
SCORE_DKT_HIGH_BONUS: int = 3   # Dk/t >= 140
SCORE_DKT_MID_BONUS: int = 1    # Dk/t >= 100

DKT_HIGH_THRESHOLD: int = 140
DKT_MID_THRESHOLD: int = 100

# K > threshold → keratoconus suspicion
KERATO_SUSPECT_THRESHOLD_D: float = 48.0

# Physiological flat radius range (mm)
KERO_R_MIN_MM: float = 6.80
KERO_R_MAX_MM: float = 9.00

# UI dimensions (PyQt5)
UI_MIN_WIDTH: int = 1200
UI_MIN_HEIGHT: int = 750
UI_DEFAULT_WIDTH: int = 1350
UI_DEFAULT_HEIGHT: int = 820

UI_LEFT_PANEL_MAX_WIDTH: int = 440
UI_SPLITTER_LEFT: int = 420
UI_SPLITTER_RIGHT: int = 900

UI_NOTES_MAX_HEIGHT: int = 180
UI_TABLE_MIN_HEIGHT: int = 200
