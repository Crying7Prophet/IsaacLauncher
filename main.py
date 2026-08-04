#!/usr/bin/env python3
import sys
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(APP_DIR, "src")


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
    main()
