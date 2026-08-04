import base64
import configparser
import os
import sys


class QuickConfig:
    """Reads and writes quick_connect_config.ini next to the main script/exe."""

    def __init__(self, filename="quick_connect_config.ini"):
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        self.path = os.path.join(base, filename)

    def load(self):
        parser = configparser.ConfigParser()
        parser.read(self.path)
        if not parser.has_section("proxmox"):
            return "", "", "", "", ""
        host = parser.get("proxmox", "host", fallback="")
        user = parser.get("proxmox", "username", fallback="")
        pw_b64 = parser.get("proxmox", "password", fallback="")
        pw = base64.b64decode(pw_b64).decode() if pw_b64 else ""
        node = parser.get("proxmox", "node", fallback="")
        vmid = parser.get("proxmox", "vmid", fallback="")
        return host, user, pw, node, vmid

    def save(self, host, username, password, node, vmid):
        parser = configparser.ConfigParser()
        parser["proxmox"] = {
            "host": host,
            "username": username,
            "password": base64.b64encode(password.encode()).decode(),
            "node": node,
            "vmid": vmid,
        }
        with open(self.path, "w") as f:
            parser.write(f)