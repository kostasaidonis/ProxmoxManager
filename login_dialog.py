from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QPushButton,
)
from PySide6.QtCore import Signal

from proxmox_api import ProxmoxAPIClient


class LoginDialog(QDialog):
    authenticated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Proxmox Authentication")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        heading = QLabel("Enter Proxmox Credentials")
        heading.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addRow(heading)

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("192.168.1.10")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("root")
        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("Password")
        self.pw_input.setEchoMode(QLineEdit.Password)

        layout.addRow("Host:", self.host_input)
        layout.addRow("Username:", self.user_input)
        layout.addRow("Password:", self.pw_input)

        self.btn = QPushButton("Authenticate")
        self.btn.setDefault(True)
        self.btn.clicked.connect(self._on_auth)
        layout.addRow(self.btn)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #c0392b;")
        self.error_label.setWordWrap(True)
        layout.addRow(self.error_label)

        self._client = None

    def _on_auth(self):
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        pw = self.pw_input.text()
        if not host or not user or not pw:
            self.error_label.setText("Please fill in all fields.")
            return
        client = ProxmoxAPIClient(host, user, pw)
        try:
            client.authenticate()
        except Exception as e:
            self.error_label.setText(f"Authentication failed: {e}")
            return
        self._client = client
        self.authenticated.emit(client)
        self.accept()

    def client(self):
        return self._client