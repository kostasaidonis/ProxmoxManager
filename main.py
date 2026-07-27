import os
import sys

# Must be set before QApplication / WebEngine is initialised
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--ignore-certificate-errors"

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

from login_dialog import LoginDialog
from proxmox_ui import MainWindow


DARK_QSS = """
QWidget#central { background-color: #1a1a1a; }
QMainWindow { background-color: #1a1a1a; }
QDialog { background-color: #1e1e1e; }
QLabel { color: #e8e8e8; }

QLineEdit {
    background-color: #2a2a2a;
    color: #e8e8e8;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 6px 8px;
    selection-background-color: #0078d4;
}
QLineEdit:focus { border-color: #0078d4; }

QPushButton {
    padding: 8px 16px;
    border-radius: 6px;
    background-color: #3a3a3a;
    color: #e8e8e8;
    font-size: 13px;
    font-weight: 500;
    border: 1px solid #555;
}
QPushButton:hover { background-color: #4a4a4a; border-color: #666; }
QPushButton:pressed { background-color: #2a2a2a; }
QPushButton:disabled { color: #666; background-color: #2a2a2a; }

QMessageBox {
    background-color: #1e1e1e;
}
QMessageBox QLabel { color: #e8e8e8; }
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Proxmox VM Manager")

    # Dark Fusion palette
    pal = app.palette()
    pal.setColor(QPalette.Window, QColor("#1a1a1a"))
    pal.setColor(QPalette.WindowText, QColor("#e8e8e8"))
    pal.setColor(QPalette.Base, QColor("#1e1e1e"))
    pal.setColor(QPalette.AlternateBase, QColor("#252525"))
    pal.setColor(QPalette.Text, QColor("#e8e8e8"))
    pal.setColor(QPalette.Button, QColor("#3a3a3a"))
    pal.setColor(QPalette.ButtonText, QColor("#e8e8e8"))
    pal.setColor(QPalette.Highlight, QColor("#0078d4"))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ToolTipBase, QColor("#2a2a2a"))
    pal.setColor(QPalette.ToolTipText, QColor("#e8e8e8"))
    app.setPalette(pal)
    app.setStyleSheet(DARK_QSS)

    dlg = LoginDialog()
    if dlg.exec() != LoginDialog.Accepted or dlg.client() is None:
        sys.exit(0)

    win = MainWindow(dlg.client())
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()