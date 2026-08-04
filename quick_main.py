import os
import sys

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--ignore-certificate-errors"

try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ProxmoxManager.QuickConnect")
except Exception:
    pass

from PySide6.QtGui import QPalette, QColor, QIcon, QFont, QGradient, QLinearGradient, QBrush, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt, QSize

from quick_config import QuickConfig
from quick_settings_dialog import SettingsDialog
from proxmox_api import ProxmoxAPIClient
from vnc_window import VNCWindow


def resource_path(relative):
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


FANCY_QSS = """
QMainWindow#quickCentral {
    background-color: #0f2027;
}
QLabel { color: #e8f4f8; }
QLabel#appTitle {
    color: #00d2ff;
    font-size: 18px;
    font-weight: 800;
    padding: 0;
}
QLabel#summaryLabel {
    color: #b8e0e8;
    font-size: 12px;
}
QLabel#statusLabel {
    color: #6b9aab;
    font-size: 11px;
}
QPushButton#btnConnect {
    background-color: #00d2ff;
    color: #0f2027;
    font-size: 14px;
    font-weight: 800;
    border: none;
    border-radius: 10px;
    padding: 14px 0;
}
QPushButton#btnConnect:hover { background-color: #00b8d9; }
QPushButton#btnConnect:pressed { background-color: #0099b8; }
QPushButton#btnConnect:disabled { background-color: #2c5364; color: #6b9aab; }
QPushButton#btnSettings {
    background-color: transparent;
    color: #00d2ff;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid #2c5364;
    border-radius: 10px;
    padding: 10px 0;
}
QPushButton#btnSettings:hover {
    border-color: #00d2ff;
    background-color: rgba(0, 210, 255, 0.05);
}
QPushButton#btnSettings:pressed { border-color: #0099b8; }
"""


def gradient_brush(widget):
    grad = QLinearGradient(0, 0, 0, widget.height())
    grad.setColorAt(0.0, QColor("#0f2027"))
    grad.setColorAt(0.5, QColor("#203a43"))
    grad.setColorAt(1.0, QColor("#2c5364"))
    return QBrush(grad)


class QuickConnectWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("quickCentral")
        self.setWindowTitle("Proxmox Quick Connect")
        self.setFixedSize(QSize(320, 220))
        self.setStyleSheet(FANCY_QSS)

        self.config = QuickConfig()

        central = QWidget(self)
        central.setObjectName("quickCentral")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("Proxmox Quick Connect")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.summary_label = QLabel("Δεν έχουν οριστεί ρυθμίσεις")
        self.summary_label.setObjectName("summaryLabel")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_settings = QPushButton("Ρυθμίσεις")
        self.btn_settings.setObjectName("btnSettings")
        self.btn_settings.clicked.connect(self._open_settings)
        btn_row.addWidget(self.btn_settings)

        self.btn_connect = QPushButton("Σύνδεση")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.clicked.connect(self._on_connect)
        btn_row.addWidget(self.btn_connect)

        layout.addLayout(btn_row)

        self.vnc_window = None
        self._refresh_summary()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), gradient_brush(self))
        super().paintEvent(event)

    def _refresh_summary(self):
        host, user, _pw, node, vmid = self.config.load()
        if host and node and vmid:
            self.summary_label.setText(
                f"Διακομιστής: <b style='color:#00d2ff'>{host}</b><br>"
                f"Κόμβος: <b style='color:#00d2ff'>{node}</b> · VM: <b style='color:#00d2ff'>{vmid}</b>"
            )
            self.status_label.setText("")
        else:
            self.summary_label.setText("Δεν έχουν οριστεί ρυθμίσεις")
            self.status_label.setText("Πατήστε «Ρυθμίσεις» για να ξεκινήσετε")

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.saved.connect(self._refresh_summary)
        dlg.exec()

    def _on_connect(self):
        host, user, pw, node, vmid = self.config.load()
        if not host or not user or not pw or not node or not vmid:
            QMessageBox.warning(self, "Λείπουν ρυθμίσεις",
                                "Παρακαλώ ορίστε διακομιστή, χρήστη, κωδικό, κόμβο και VM ID στις ρυθμίσεις.")
            return

        self.status_label.setText("Σύνδεση…")
        QApplication.processEvents()

        client = ProxmoxAPIClient(host, user, pw)
        try:
            client.authenticate()
        except Exception as e:
            self.status_label.setText("")
            QMessageBox.critical(self, "Σφάλμα Σύνδεσης", f"Αποτυχία αυθεντικοποίησης:\n{e}")
            return

        try:
            vnc_ticket, port, _user = client.get_vnc_proxy(node, vmid)
        except Exception as e:
            self.status_label.setText("")
            QMessageBox.critical(self, "Σφάλμα VNC", f"Αποτυχία λήψης VNC proxy:\n{e}")
            return

        self.status_label.setText("")
        self.vnc_window = VNCWindow(host, node, vmid, client.ticket, vnc_ticket, port)
        self.vnc_window.show()
        self.vnc_window.raise_()
        self.vnc_window.activateWindow()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Proxmox Quick Connect")
    app.setWindowIcon(QIcon(resource_path("quick.ico")))

    pal = app.palette()
    pal.setColor(QPalette.Window, QColor("#0f2027"))
    pal.setColor(QPalette.WindowText, QColor("#e8f4f8"))
    pal.setColor(QPalette.Base, QColor("#1a3a4a"))
    pal.setColor(QPalette.Text, QColor("#e8f4f8"))
    pal.setColor(QPalette.Button, QColor("#00d2ff"))
    pal.setColor(QPalette.ButtonText, QColor("#0f2027"))
    pal.setColor(QPalette.Highlight, QColor("#00d2ff"))
    pal.setColor(QPalette.HighlightedText, QColor("#0f2027"))
    app.setPalette(pal)

    win = QuickConnectWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()