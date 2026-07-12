#!/usr/bin/env python3
import sys
import os
import subprocess
import platform

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(APP_DIR, "src")
VENV_DIR = os.path.join(APP_DIR, "venv")


def in_venv():
    return hasattr(sys, 'base_prefix') and sys.prefix != sys.base_prefix


def ensure_deps():
    try:
        import PyQt6
        import requests
    except ImportError:
        if platform.system() == "Windows":
            pip = os.path.join(VENV_DIR, "Scripts", "pip")
        else:
            pip = os.path.join(VENV_DIR, "bin", "pip")
        subprocess.run([pip, "install", "-r", os.path.join(APP_DIR, "requirements.txt")], check=True)


def main():
    sys.path.insert(0, SRC_DIR)
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QColor
    from manager import PyIsaacLauncher

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(palette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(palette.ColorRole.Base, QColor(45, 45, 45))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(35, 35, 35))
    palette.setColor(palette.ColorRole.ToolTipBase, QColor(50, 50, 50))
    palette.setColor(palette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(palette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(palette.ColorRole.Button, QColor(60, 60, 60))
    palette.setColor(palette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(palette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(palette.ColorRole.Highlight, QColor(31, 83, 141))
    palette.setColor(palette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = PyIsaacLauncher()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    if not in_venv():
        subprocess.run([sys.executable, os.path.join(SRC_DIR, "setup.py")])
        sys.exit(0)

    ensure_deps()
    main()
