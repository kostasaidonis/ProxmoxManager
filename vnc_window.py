from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtNetwork import QNetworkCookie
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow


class InsecureWebEnginePage(QWebEnginePage):
    """Accepts self-signed certificates (Proxmox default install uses them)."""

    def certificateError(self, error):
        error.acceptCertificate()
        return True


class VNCWindow(QMainWindow):
    """Embeds Proxmox noVNC console in a QWebEngineView with pre-set auth cookie."""

    def __init__(self, host, node, vmid, auth_ticket, vnc_ticket, port, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"VNC Console - VM {vmid} ({node})")
        self.resize(1024, 768)

        self.view = QWebEngineView()
        self.setCentralWidget(self.view)

        profile = self.view.page().profile()
        store = profile.cookieStore()

        origin = QUrl(f"https://{host}:8006")
        cookie = QNetworkCookie(b"PVEAuthCookie", auth_ticket.encode())
        cookie.setDomain(host)
        cookie.setPath("/")
        store.setCookie(cookie, origin)

        # Replace the default page so self-signed certs are accepted
        page = InsecureWebEnginePage(profile, self.view)
        self.view.setPage(page)

        # Let the noVNC JavaScript do its thing
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

        encoded_vnc_ticket = quote(vnc_ticket, safe="")
        url = (
            f"https://{host}:8006/?console=kvm&novnc=1&node={node}"
            f"&resize=off&vmid={vmid}"
            f"&path=api2/json/nodes/{node}/qemu/{vmid}"
            f"/vncwebsocket/port/{port}/vncticket/{encoded_vnc_ticket}"
        )
        self.view.setUrl(QUrl(url))