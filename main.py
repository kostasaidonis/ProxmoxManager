import sys

from PySide6.QtWidgets import QApplication

from login_dialog import LoginDialog
from proxmox_ui import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Proxmox VM Manager")

    dlg = LoginDialog()
    if dlg.exec() != LoginDialog.Accepted or dlg.client() is None:
        sys.exit(0)

    win = MainWindow(dlg.client())
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()