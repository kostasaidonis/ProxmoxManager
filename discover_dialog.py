import socket
import threading
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

import netifaces
import requests
import urllib3
from zeroconf import Zeroconf, ServiceBrowser

from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QMessageBox, QCheckBox,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------------------------------
# Worker signals (must live on a QObject so we can emit from threads)
# ---------------------------------------------------------------------------

class DiscoverSignals(QObject):
    scan_started = Signal()
    scan_progress = Signal(int, int)          # done, total
    server_found = Signal(str, str, str, str)  # ip, hostname, port, proxmox_version
    scan_finished = Signal()
    scan_error = Signal(str)


# ---------------------------------------------------------------------------
# mDNS listener
# ---------------------------------------------------------------------------

class ZeroconfListener:
    """Collects mDNS services and forwards Proxmox-relevant ones via signal."""

    def __init__(self, signals):
        self.signals = signals
        self._seen = set()

    def add_service(self, zc, type_, name):
        self._resolve(zc, type_, name)

    def update_service(self, zc, type_, name):
        self._resolve(zc, type_, name)

    def remove_service(self, zc, type_, name):
        pass

    def _resolve(self, zc, type_, name):
        try:
            info = zc.get_service_info(type_, name, timeout=2000)
            if info is None:
                return
            ip = socket.inet_ntoa(info.addresses[0]) if info.addresses else ""
            port = str(info.port)
            hostname = name.removesuffix("." + type_).removesuffix(".")
            key = (ip, port)
            if key in self._seen:
                return
            self._seen.add(key)
            if port == "8006":
                self.signals.server_found.emit(ip, hostname, port, "mDNS")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Subnet helpers
# ---------------------------------------------------------------------------

def enumerate_subnets():
    """Return list of (label, network_cidr) for every AF_INET interface."""
    results = []
    try:
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET)
            if not addrs:
                continue
            for a in addrs:
                ip = a.get("addr")
                mask = a.get("netmask")
                if not ip or not mask:
                    continue
                try:
                    net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
                except ValueError:
                    continue
                label = f"{net} — {iface}"
                results.append((label, str(net)))
    except Exception:
        pass
    return results


def _check_port(ip, port, timeout=0.5):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((ip, port)) == 0
    except Exception:
        return False


def _verify_proxmox(ip, port=8006, timeout=1.5):
    """Return Proxmox VE version string or empty."""
    try:
        r = requests.get(
            f"https://{ip}:{port}/api2/json/version",
            verify=False,
            timeout=timeout,
        )
        if r.status_code == 200:
            data = r.json().get("data", {})
            return data.get("version", "Proxmox VE")
    except Exception:
        pass
    return ""


def _reverse_dns(ip):
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class DiscoverDialog(QDialog):
    """Discover Proxmox VE servers on the local network (port 8006)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Discover Proxmox Servers")
        self.setModal(True)
        self.resize(680, 520)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #e8e8e8; }
            QLineEdit {
                background-color: #2a2a2a; color: #e8e8e8;
                border: 1px solid #444; border-radius: 4px; padding: 6px 8px;
            }
            QLineEdit:focus { border-color: #0078d4; }
            QPushButton {
                padding: 8px 16px; border-radius: 6px;
                background-color: #3a3a3a; color: #e8e8e8;
                font-size: 13px; font-weight: 500; border: 1px solid #555;
            }
            QPushButton:hover { background-color: #4a4a4a; border-color: #666; }
            QPushButton:pressed { background-color: #2a2a2a; }
            QPushButton:disabled { color: #666; background-color: #2a2a2a; }
            QComboBox {
                background-color: #2a2a2a; color: #e8e8e8;
                border: 1px solid #444; border-radius: 4px; padding: 6px 8px;
            }
            QProgressBar {
                background-color: #2a2a2a; border: 1px solid #444;
                border-radius: 4px; text-align: center; color: #e8e8e8;
            }
            QProgressBar::chunk { background-color: #0078d4; border-radius: 4px; }
            QTableWidget {
                background-color: #1e1e1e; alternate-background-color: #252525;
                color: #e8e8e8; border: 1px solid #383838; border-radius: 4px;
                gridline-color: #333;
            }
            QHeaderView::section {
                background-color: #2d2d2d; color: #aaa; padding: 6px;
                border: none; border-bottom: 1px solid #383838;
                font-weight: 600; font-size: 12px;
            }
            QTableWidget::item { padding: 4px 8px; border-bottom: 1px solid #2a2a2a; }
            QTableWidget::item:selected { background-color: #0078d4; color: #ffffff; }
        """)

        self._scan_cancelled = False
        self._zc = None
        self._zc_browser = None
        self._executor = None
        self._selected_ip = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Heading
        heading = QLabel("Discover Proxmox VE Servers")
        heading.setStyleSheet("font-size: 15px; font-weight: 600; color: #e8e8e8;")
        layout.addWidget(heading)

        # Subnet row
        subnet_row = QHBoxLayout()
        subnet_row.addWidget(QLabel("Subnet:"))
        self.subnet_combo = QComboBox()
        self.subnet_combo.setEditable(True)
        self.subnet_combo.setMinimumWidth(280)
        subnet_row.addWidget(self.subnet_combo, 1)
        self.btn_scan = QPushButton("▶  Scan")
        self.btn_scan.clicked.connect(self.start_scan)
        subnet_row.addWidget(self.btn_scan)
        self.btn_stop = QPushButton("■  Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_scan)
        subnet_row.addWidget(self.btn_stop)
        layout.addLayout(subnet_row)

        self.subnets = enumerate_subnets()
        if self.subnets:
            for label, _ in self.subnets:
                self.subnet_combo.addItem(label)
        self.subnet_combo.setCurrentText("")
        self.subnet_combo.setPlaceholderText("e.g. 192.168.1.0/24")

        # mDNS checkbox
        self.mdns_check = QCheckBox("mDNS auto-discovery (.local)")
        self.mdns_check.setChecked(True)
        self.mdns_check.stateChanged.connect(self._on_mdns_toggle)
        layout.addWidget(self.mdns_check)

        # Hostname resolver row
        host_row = QHBoxLayout()
        host_row.addWidget(QLabel("Hostname:"))
        self.hostname_input = QLineEdit()
        self.hostname_input.setPlaceholderText("e.g. pve  (tries pve.local)")
        self.btn_resolve = QPushButton("🔍 Resolve")
        self.btn_resolve.clicked.connect(self.resolve_hostname)
        host_row.addWidget(self.hostname_input, 1)
        host_row.addWidget(self.btn_resolve)
        layout.addLayout(host_row)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFormat("Idle")
        layout.addWidget(self.progress)

        # Results table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["IP Address", "Hostname", "Port 8006", "Proxmox VE"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        layout.addWidget(self.table)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_use = QPushButton("✓  Use Selected")
        self.btn_use.setEnabled(False)
        self.btn_use.clicked.connect(self._use_selected)
        btn_row.addWidget(self.btn_use)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

        # Signals
        self.signals = DiscoverSignals()
        self.signals.scan_started.connect(self._on_scan_started)
        self.signals.scan_progress.connect(self._on_scan_progress)
        self.signals.server_found.connect(self._on_server_found)
        self.signals.scan_finished.connect(self._on_scan_finished)
        self.signals.scan_error.connect(self._on_scan_error)

        # Start mDNS if checked
        QTimer.singleShot(100, self._maybe_start_mdns)

    # ----- mDNS -----

    def _on_mdns_toggle(self, state):
        if state == Qt.Checked:
            self._maybe_start_mdns()
        else:
            self._stop_mdns()

    def _maybe_start_mdns(self):
        if self.mdns_check.isChecked() and self._zc is None:
            self._zc = Zeroconf()
            self._listener = ZeroconfListener(self.signals)
            self._zc_browser = ServiceBrowser(
                self._zc, "_http._tcp.local.", self._listener
            )
            self._zc_browser2 = ServiceBrowser(
                self._zc, "_https._tcp.local.", self._listener
            )

    def _stop_mdns(self):
        if self._zc is not None:
            try:
                self._zc.close()
            except Exception:
                pass
            self._zc = None
            self._zc_browser = None
            self._zc_browser2 = None

    # ----- Scan -----

    def start_scan(self):
        text = self.subnet_combo.currentText().strip()
        if not text:
            QMessageBox.information(self, "No subnet", "Select or enter a subnet CIDR (e.g. 192.168.1.0/24).")
            return
        # If the text matches an enumerated subnet label, use its CIDR
        cidr = None
        idx = self.subnet_combo.currentIndex()
        if idx >= 0 and idx < len(self.subnets) and text == self.subnets[idx][0]:
            cidr = self.subnets[idx][1]
        else:
            # Try to interpret the typed text as a CIDR
            try:
                ipaddress.IPv4Network(text, strict=False)
                cidr = text
            except ValueError:
                QMessageBox.warning(self, "Invalid subnet", f"'{text}' is not a valid CIDR (e.g. 192.168.1.0/24).")
                return
        self._scan_cancelled = False
        self.signals.scan_started.emit()
        threading.Thread(target=self._scan_subnet, args=(cidr,), daemon=True).start()

    def _scan_subnet(self, cidr):
        try:
            net = ipaddress.IPv4Network(cidr, strict=False)
            hosts = [str(ip) for ip in net.hosts()]
            total = len(hosts)
            if total == 0:
                # /31 or /32 — just scan the network address
                hosts = [str(net.network_address)]
                total = 1
            done = 0
            self._executor = ThreadPoolExecutor(max_workers=50)
            futures = {}
            for ip in hosts:
                if self._scan_cancelled:
                    break
                futures[self._executor.submit(self._probe_ip, ip)] = ip

            for future in as_completed(futures):
                if self._scan_cancelled:
                    break
                ip = futures[future]
                result = future.result()
                if result:
                    self.signals.server_found.emit(*result)
                done += 1
                self.signals.scan_progress.emit(done, total)

            self._executor.shutdown(wait=False)
        except Exception as e:
            self.signals.scan_error.emit(str(e))
        finally:
            self.signals.scan_finished.emit()

    def _probe_ip(self, ip):
        if not _check_port(ip, 8006, timeout=0.5):
            return None
        hostname = _reverse_dns(ip)
        version = _verify_proxmox(ip)
        return (ip, hostname, "8006", version if version else "—")

    def stop_scan(self):
        self._scan_cancelled = True
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
        self.signals.scan_finished.emit()

    # ----- Hostname resolver -----

    def resolve_hostname(self):
        pattern = self.hostname_input.text().strip()
        if not pattern:
            QMessageBox.information(self, "No input", "Enter a hostname pattern (e.g. 'pve').")
            return
        candidates = [pattern, f"{pattern}.local"]
        found = False
        for candidate in candidates:
            try:
                ip = socket.gethostbyname(candidate)
                version = _verify_proxmox(ip)
                self.signals.server_found.emit(
                    ip, candidate, "8006", version if version else "—"
                )
                found = True
            except socket.gaierror:
                continue
        if not found:
            QMessageBox.information(
                self, "Not found",
                f"Could not resolve '{pattern}' or '{pattern}.local'."
            )

    # ----- Signal handlers -----

    def _on_scan_started(self):
        self.btn_scan.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress.setFormat("Scanning… %v/%m")
        self.progress.setValue(0)

    def _on_scan_progress(self, done, total):
        self.progress.setMaximum(total)
        self.progress.setValue(done)

    def _on_server_found(self, ip, hostname, port, version):
        # Avoid duplicates
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).text() == ip:
                return
        row = self.table.rowCount()
        self.table.insertRow(row)
        for c, val in enumerate([ip, hostname, port, version]):
            item = QTableWidgetItem(val)
            if c == 3 and val != "—" and val != "":
                from PySide6.QtGui import QColor, QFont
                item.setForeground(QColor("#4caf50"))
                f = QFont()
                f.setBold(True)
                item.setFont(f)
            self.table.setItem(row, c, item)

    def _on_scan_finished(self):
        self.btn_scan.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress.setFormat("Done — %v/%m")

    def _on_scan_error(self, msg):
        QMessageBox.warning(self, "Scan error", msg)

    # ----- Selection -----

    def _on_table_selection(self):
        self.btn_use.setEnabled(len(self.table.selectedItems()) > 0)

    def _use_selected(self):
        items = self.table.selectedItems()
        if not items:
            return
        self._selected_ip = self.table.item(items[0].row(), 0).text()
        self.accept()

    def selected_ip(self):
        return self._selected_ip

    # ----- Cleanup -----

    def closeEvent(self, event):
        self._scan_cancelled = True
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
        self._stop_mdns()
        super().closeEvent(event)