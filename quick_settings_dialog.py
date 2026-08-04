from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal, Qt

from quick_config import QuickConfig


SETTINGS_QSS = """
QDialog#settingsDialog {
    background-color: #0f2027;
}
QLabel { color: #e8f4f8; }
QLabel#settingsTitle {
    color: #00d2ff;
    font-size: 16px;
    font-weight: 700;
    padding-bottom: 8px;
}
QLineEdit {
    background-color: #1a3a4a;
    color: #e8f4f8;
    border: 1px solid #2c5364;
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: #00d2ff;
    selection-color: #0f2027;
}
QLineEdit:focus { border: 1px solid #00d2ff; }
QPushButton#btnSave {
    background-color: #00d2ff;
    color: #0f2027;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
}
QPushButton#btnSave:hover { background-color: #00b8d9; }
QPushButton#btnSave:pressed { background-color: #0099b8; }
QPushButton#btnCancel {
    background-color: transparent;
    color: #e8f4f8;
    border: 1px solid #2c5364;
    border-radius: 8px;
    padding: 9px 18px;
}
QPushButton#btnCancel:hover { border-color: #00d2ff; color: #00d2ff; }
"""


class SettingsDialog(QDialog):
    saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowTitle("Ρυθμίσεις — Proxmox Quick Connect")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setStyleSheet(SETTINGS_QSS)

        self.config = QuickConfig()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(10)

        title = QLabel("Ρυθμίσεις Σύνδεσης")
        title.setObjectName("settingsTitle")
        outer.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft)

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("192.168.1.10")
        form.addRow(self._label("Διακομιστής:"), self.host_input)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("root")
        form.addRow(self._label("Χρήστης:"), self.user_input)

        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("Κωδικός")
        self.pw_input.setEchoMode(QLineEdit.Password)
        form.addRow(self._label("Κωδικός:"), self.pw_input)

        self.node_input = QLineEdit()
        self.node_input.setPlaceholderText("pve1")
        form.addRow(self._label("Κόμβος:"), self.node_input)

        self.vmid_input = QLineEdit()
        self.vmid_input.setPlaceholderText("100")
        form.addRow(self._label("VM ID:"), self.vmid_input)

        outer.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff6b6b; font-size: 12px;")
        self.error_label.setWordWrap(True)
        outer.addWidget(self.error_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Άκυρο")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Αποθήκευση")
        self.btn_save.setObjectName("btnSave")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self.btn_save)

        outer.addLayout(btn_row)

        self._load_config()

    @staticmethod
    def _label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #a8d8e8; font-weight: 600;")
        return lbl

    def _load_config(self):
        host, user, pw, node, vmid = self.config.load()
        self.host_input.setText(host)
        self.user_input.setText(user)
        self.pw_input.setText(pw)
        self.node_input.setText(node)
        self.vmid_input.setText(vmid)

    def _on_save(self):
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        pw = self.pw_input.text()
        node = self.node_input.text().strip()
        vmid = self.vmid_input.text().strip()
        if not host or not user or not pw or not node or not vmid:
            self.error_label.setText("Παρακαλώ συμπληρώστε όλα τα πεδία.")
            return
        try:
            self.config.save(host, user, pw, node, vmid)
        except Exception as e:
            self.error_label.setText(f"Σφάλμα αποθήκευσης: {e}")
            return
        self.saved.emit()
        self.accept()

    def values(self):
        return (
            self.host_input.text().strip(),
            self.user_input.text().strip(),
            self.pw_input.text(),
            self.node_input.text().strip(),
            self.vmid_input.text().strip(),
        )