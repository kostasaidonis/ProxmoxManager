import threading
import time

from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QStatusBar, QHeaderView,
    QMessageBox,
)


class VMSignals(QObject):
    update = Signal(list)
    error = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self, api_client):
        super().__init__()
        self.api = api_client
        self.setWindowTitle("Proxmox VM Manager")
        self.resize(1000, 600)

        self.selected_vmid = None
        self.selected_node = None
        self._running = True
        self._vnc_window = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Proxmox VM Manager")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 2px;")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.btn_start = QPushButton("Start VM")
        self.btn_stop = QPushButton("Stop VM")
        self.btn_vnc = QPushButton("Launch VNC")
        self.btn_refresh = QPushButton("Refresh")
        for b in (self.btn_start, self.btn_stop, self.btn_vnc, self.btn_refresh):
            toolbar.addWidget(b)
        toolbar.addStretch()
        layout.addLayout(toolbar)

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
        layout.addWidget(self.table)

        self.setStatusBar(QStatusBar())
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
        self.table.setRowCount(0)
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
                self.table.setItem(row, c, item)

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