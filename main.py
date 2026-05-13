"""
main.py — LensAdvisor entry point
────────────────────────────────────────
Launches the PyQt5 contact lens fitting assistant application.

Usage:
    python main.py

Requirements:
    pip install PyQt5>=5.15.0
"""

import sys
import os

# Ensure the project root directory is in sys.path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from views.main_window import MainWindow


def main() -> None:
    # Required before QApplication creation on some HiDPI displays
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("LensAdvisor")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Orthoptic Clinic")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()