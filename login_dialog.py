from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QPushButton, QCheckBox,
)
from PySide6.QtCore import Signal

from proxmox_api import ProxmoxAPIClient
from config import AppConfig


class LoginDialog(QDialog):
    authenticated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Proxmox Authentication")
        self.setModal(True)
        self.setMinimumWidth(360)

        self.config = AppConfig()

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        heading = QLabel("Enter Proxmox Credentials")
        heading.setStyleSheet("font-size: 15px; font-weight: 600; color: #e8e8e8; padding-bottom: 4px;")
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

        self.remember_check = QCheckBox("Remember credentials")
        self.remember_check.setChecked(True)
        layout.addRow(self.remember_check)

        self.btn = QPushButton("Authenticate")
        self.btn.setDefault(True)
        self.btn.clicked.connect(self._on_auth)
        layout.addRow(self.btn)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #c0392b;")
        self.error_label.setWordWrap(True)
        layout.addRow(self.error_label)

        self._client = None

        # Pre-fill from config
        host, user, pw = self.config.load()
        if host:
            self.host_input.setText(host)
        if user:
            self.user_input.setText(user)
        if pw:
            self.pw_input.setText(pw)
        if host and user and pw:
            self.host_input.setFocus()

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

        if self.remember_check.isChecked():
            try:
                self.config.save(host, user, pw)
            except Exception:
                pass

        self.authenticated.emit(client)
        self.accept()

    def client(self):
        return self._client