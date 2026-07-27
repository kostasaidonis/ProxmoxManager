import threading
import time

from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QStatusBar, QHeaderView,
    QMessageBox, QFrame,
)


class VMSignals(QObject):
    update = Signal(list)
    error = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self.setWindowTitle("Proxmox VM Manager")
        self.resize(1100, 650)

        self.selected_vmid = None
        self.selected_node = None
        self._running = True
        self._vnc_window = None

        central = QWidget()
        self.setObjectName("central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- Title bar ----
        title = QLabel("Proxmox VM Manager")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #e8e8e8;")
        layout.addWidget(title)

        # ---- Toolbar ----
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_start = QPushButton("▶  Start")
        self.btn_stop = QPushButton("■  Stop")
        self.btn_vnc = QPushButton("🖥  Launch VNC")
        self.btn_refresh = QPushButton("↻  Refresh")

        btn_style = """
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
        """
        for b in (self.btn_start, self.btn_stop, self.btn_vnc, self.btn_refresh):
            b.setStyleSheet(btn_style)
            toolbar.addWidget(b)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # ---- Table ----
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["VMID", "Name", "Status", "Node", "CPU (%)", "Memory (%)", "Uptime"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252525;
                color: #e8e8e8;
                border: 1px solid #383838;
                border-radius: 4px;
                gridline-color: #333;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #aaa;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #383838;
                font-weight: 600;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #2a2a2a;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
        """)
        layout.addWidget(self.table)

        self.setStatusBar(QStatusBar())
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #1a1a1a;
                color: #999;
                border-top: 1px solid #333;
            }
        """)
        self.statusBar().showMessage("Ready")

        self.btn_start.clicked.connect(self.start_vm)
        self.btn_stop.clicked.connect(self.stop_vm)
        self.btn_vnc.clicked.connect(self.launch_vnc)
        self.btn_refresh.clicked.connect(self.refresh_now)
        self.table.itemSelectionChanged.connect(self.on_selection)

        self.signals = VMSignals()
        self.signals.update.connect(self.populate_table)
        self.signals.error.connect(self.on_error)

        threading.Thread(target=self._refresh_loop, daemon=True).start()

    def _refresh_loop(self):
        while self._running:
            self._fetch()
            time.sleep(5)

    def refresh_now(self):
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            vms = self.api.get_vms()
            self.signals.update.emit(vms)
        except Exception as e:
            self.signals.error.emit(str(e))

    @Slot(list)
    def populate_table(self, vms):
        # Remember which VMID was selected so we can restore it after refresh
        saved_vmid = self.selected_vmid

        self.table.setRowCount(0)
        restore_row = -1

        for vm in vms:
            row = self.table.rowCount()
            self.table.insertRow(row)
            cpu = vm.get("cpu", 0) * 100
            mem = (vm.get("mem", 0) / vm.get("maxmem", 1)) * 100 if vm.get("maxmem") else 0
            up = self._format_uptime(vm.get("uptime", 0))
            vals = [
                str(vm.get("vmid", "")),
                vm.get("name", ""),
                vm.get("status", ""),
                vm.get("node", ""),
                f"{cpu:.1f}",
                f"{mem:.1f}",
                up,
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setData(Qt.UserRole, vm.get("vmid"))

                # Color-code the status column
                if c == 2:
                    status = v.lower()
                    if status == "running":
                        item.setForeground(QColor("#4caf50"))
                        f = QFont()
                        f.setBold(True)
                        item.setFont(f)
                    elif status == "stopped":
                        item.setForeground(QColor("#f44336"))
                    elif status == "paused":
                        item.setForeground(QColor("#ff9800"))

                self.table.setItem(row, c, item)

            if str(vm.get("vmid")) == saved_vmid:
                restore_row = row

        # Restore selection if the same VMID is still present
        if restore_row >= 0:
            self.table.selectRow(restore_row)
        else:
            self.selected_vmid = None
            self.selected_node = None

    @staticmethod
    def _format_uptime(seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"

    def on_selection(self):
        items = self.table.selectedItems()
        if not items:
            self.selected_vmid = None
            self.selected_node = None
            self.statusBar().showMessage("Ready")
            return
        row = items[0].row()
        self.selected_vmid = self.table.item(row, 0).text()
        self.selected_node = self.table.item(row, 3).text()
        name = self.table.item(row, 1).text()
        self.statusBar().showMessage(
            f"Selected: {name} (VMID {self.selected_vmid}, node {self.selected_node})"
        )

    def start_vm(self):
        if not self.selected_vmid:
            QMessageBox.information(self, "No selection", "Please select a VM first.")
            return
        try:
            self.api.start_vm(self.selected_node, self.selected_vmid)
            self.statusBar().showMessage(f"Start requested for VM {self.selected_vmid}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to start VM:\n{e}")

    def stop_vm(self):
        if not self.selected_vmid:
            QMessageBox.information(self, "No selection", "Please select a VM first.")
            return
        try:
            self.api.stop_vm(self.selected_node, self.selected_vmid)
            self.statusBar().showMessage(f"Stop requested for VM {self.selected_vmid}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to stop VM:\n{e}")

    def launch_vnc(self):
        if not self.selected_vmid:
            QMessageBox.information(self, "No selection", "Please select a VM first.")
            return
        try:
            vnc_ticket, port, _ = self.api.get_vnc_proxy(self.selected_node, self.selected_vmid)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"VNC proxy request failed:\n{e}")
            return
        from vnc_window import VNCWindow
        self._vnc_window = VNCWindow(
            self.api.host, self.selected_node, self.selected_vmid,
            self.api.ticket, vnc_ticket, port, parent=self,
        )
        self._vnc_window.show()

    @Slot(str)
    def on_error(self, msg):
        self.statusBar().showMessage(f"Error: {msg}")

    def closeEvent(self, event):
        self._running = False
        super().closeEvent(event)