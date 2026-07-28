# ProxmoxManager — Handover Document

> **Last updated:** 2026-07-28
> **Repository:** `C:\Users\KOSTASLAB\Documents\Pycharm2024Projects\ProxmoxManager`
> **Branch:** `main` · **Head:** `bec64cf refactor`

---

## 1. Project Summary

**ProxmoxManager** is a Windows desktop application for managing virtual machines on a Proxmox VE host. It authenticates against the Proxmox API, lists VMs with live CPU/memory/uptime metrics, and lets the user start, stop, and open a noVNC console for any VM.

### Tech Stack
- **Language:** Python 3
- **GUI Framework:** PySide6 (Qt 6) — dark theme via QPalette + stylesheet
- **HTTP:** `requests` with `urllib3` (SSL verification disabled for Proxmox self-signed certs)
- **VNC Console:** Proxmox noVNC embedded in `QWebEngineView` (Chromium), with the `PVEAuthCookie` pre-injected so the console opens authenticated
- **Packaging:** PyInstaller (`ProxmoxManager.spec`) → single `.exe`, windowed, icon `app.ico`
- **Config:** `proxmox_config.ini` (base64-encoded password) next to the exe

### Architecture (Active — PySide6)
| File | Role |
|------|------|
| `main.py` | Entry point. Builds `QApplication`, applies dark palette/QSS, shows `LoginDialog`, then `MainWindow`. |
| `login_dialog.py` | `QDialog` for host/user/password. Pre-fills from `AppConfig`. On success emits the authenticated `ProxmoxAPIClient`. |
| `config.py` | `AppConfig` — reads/writes `proxmox_config.ini` (base64 password). Resolves path for frozen exe. |
| `proxmox_api.py` | `ProxmoxAPIClient` — `requests.Session` wrapper. `authenticate()`, `get_vms()`, `start_vm()`, `stop_vm()`, `get_vnc_proxy()`. |
| `proxmox_ui.py` | `MainWindow` — VM table, toolbar (Start/Stop/VNC/Refresh), status bar, background refresh thread (5 s). |
| `vnc_window.py` | `VNCWindow` — `QWebEngineView` loading Proxmox noVNC. `InsecureWebEnginePage` accepts self-signed certs. |
| `ProxmoxManager.spec` | PyInstaller spec. Bundles `app.ico`, hidden imports for QtWebEngine/QtNetwork/etc. |
| `app.ico` | Application icon. |
| `generate_icon.py` | Script to regenerate `app.ico`. |

### Architecture (Legacy — Kivy)
| File | Role |
|------|------|
| `Proxmoxmanager.py` | Original Kivy-based UI. Uses `RecycleView`, Playwright (Chromium) for VNC, `ProxmoxLoginPopup`. **Not used by `main.py`.** Kept for reference. |

> **Note:** The project was refactored from Kivy → PySide6. The Kivy file (`Proxmoxmanager.py`) is the legacy implementation; `main.py` is the current entry point. `requirements.txt` lists only `requests`, `urllib3`, `PySide6` — Kivy/Playwright are no longer required for the active app.

### Key Behaviors
- **Auth:** Username is sent as `{user}@pam` to `/api2/json/access/ticket`. Ticket + CSRF token stored on the `requests.Session`.
- **VM refresh:** Background daemon thread polls `cluster/resources?type=vm` every 5 s; results emitted to UI thread via Qt signals. Selection (by VMID) is preserved across refreshes.
- **VNC:** `get_vnc_proxy()` returns `(ticket, port, user)`. `VNCWindow` injects `PVEAuthCookie` into the `QWebEngineProfile` cookie store, then loads the noVNC URL with the encoded VNC ticket.
- **SSL:** Self-signed certs accepted everywhere (`verify=False`, `certificateError.acceptCertificate()`). `QTWEBENGINE_CHROMIUM_FLAGS=--ignore-certificate-errors` is set before `QApplication` init.
- **Credentials:** "Remember credentials" checkbox in login dialog. Password stored base64-encoded in `proxmox_config.ini`.

### Build
```
pyinstaller ProxmoxManager.spec
```
Output: `dist/ProxmoxManager.exe` (windowed, no console).

---

## 2. Open Items Tracker

| ID | Title | Description | Status |
|----|-------|-------------|--------|
| 01-1 | Update PyInstaller spec | `ProxmoxManager.spec` may need hidden imports for `netifaces` and `zeroconf` when building the exe. | DONE |

---

## 3. ⚠️ IMPORTANT — Team Notes

| Date | Added By | Type | Note |
|------|----------|------|------|
| 2026-07-28 | qwen | INFO | HANDOVER.md created. Legacy Kivy UI lives in `Proxmoxmanager.py`; active app is PySide6 via `main.py`. |
| 2026-07-28 | qwen | DECISION | Server discovery uses `netifaces` for subnet enumeration and `zeroconf` for mDNS auto-discovery. Added to `requirements.txt`. |

---

## 4. Session Log

### Session 2026-07-28 — HANDOVER.md creation

**Branch:** `main`

**Summary:** Created `md/HANDOVER.md` to track the project summary, architecture, open items, and ongoing changes for the ProxmoxManager desktop app (PySide6, PyInstaller, Proxmox VE API).

**Files Modified:**
- `md/HANDOVER.md` — created (this file)

**Status:** ✅ DONE — 2026-07-28

### Session 2026-07-28 — Discovery dialog fixes

**Branch:** `main`

**Summary:** Fixed two issues in the Discover dialog: (1) "Use Selected" button was never enabled — connected `itemSelectionChanged` signal to toggle it. (2) Subnet combo was read-only — made it always editable so you can type a CIDR manually (e.g. `192.168.1.0/24`); `start_scan` now accepts typed CIDR strings in addition to the enumerated entries.

**Files Modified:**
- `discover_dialog.py` — combo `setEditable(True)` always, placeholder text, `start_scan` parses typed CIDR, added `_on_table_selection` handler connected to `itemSelectionChanged`.

**Verification:** `py_compile` — OK.

**Status:** ✅ DONE — 2026-07-28

### Session 2026-07-28 — New icon + exe rebuild

**Branch:** `main`

**Summary:** Redesigned the application icon to a magnifying-glass-over-server-bars design (dark charcoal background, cyan accent, green status dot) representing the new server discovery feature. Updated `generate_icon.py`, regenerated `app.ico`, added `netifaces`/`zeroconf`/`ifaddr` to the PyInstaller spec hidden imports, and rebuilt the exe successfully.

**Files Modified:**
- `generate_icon.py` — redesigned icon: dark charcoal bg, cyan magnifying glass, server rack bars inside lens, green status dot.
- `app.ico` — regenerated with new design.
- `ProxmoxManager.spec` — added `netifaces`, `zeroconf`, `ifaddr` to `hiddenimports`.

**Verification:**
- `python generate_icon.py` — app.ico created.
- `pyinstaller ProxmoxManager.spec --noconfirm` — Build complete (221 MB exe).
- `dist/ProxmoxManager.exe` — 221,174,348 bytes, dated 2026-07-28 09:19.

**Status:** ✅ DONE — 2026-07-28

### Session 2026-07-28 — Server Discovery Dialog

**Branch:** `main`

**Summary:** Added a "Discover Proxmox Servers" dialog reachable from the login screen via a `🔍 Discover` button next to the Host field. The dialog enumerates local subnets (`netifaces`), scans the selected subnet for port 8006 (50 concurrent workers, 0.5 s timeout), verifies each open port is a Proxmox VE server (`GET /api2/json/version`), resolves reverse DNS, optionally listens for mDNS services via `zeroconf`, and supports manual hostname resolution (`pve.local`). Selecting a server fills the Host field in the login dialog. All scanning runs in background threads with Qt signals for UI updates; mDNS and executor are properly cleaned up on dialog close.

**Files Modified:**
- `discover_dialog.py` — new file. `DiscoverDialog(QDialog)` with subnet enumeration, port scanning, Proxmox verification, mDNS browsing, hostname resolver.
- `login_dialog.py` — added `QHBoxLayout` for Host field + `🔍 Discover` button. Added `_open_discover()` method that opens `DiscoverDialog` and fills the Host field on accept.
- `requirements.txt` — added `netifaces` and `zeroconf`.
- `md/HANDOVER.md` — updated open items and session log.

**Verification:**
- `netifaces` and `zeroconf` installed via pip successfully.
- `py_compile` passed for both `discover_dialog.py` and `login_dialog.py`.
- Runtime import test (`from discover_dialog import DiscoverDialog; from login_dialog import LoginDialog`) — OK.

**Status:** ✅ DONE — 2026-07-28