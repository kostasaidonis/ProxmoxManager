import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProxmoxAPIClient:
    """Thin wrapper around the Proxmox API using a requests.Session."""

    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.ticket = None
        self.csrf_token = None

    @property
    def base_url(self):
        return f"https://{self.host}:8006"

    def authenticate(self):
        url = f"{self.base_url}/api2/json/access/ticket"
        data = {"username": f"{self.username}@pam", "password": self.password}
        r = requests.post(url, data=data, verify=False)
        r.raise_for_status()
        d = r.json()["data"]
        self.ticket = d["ticket"]
        self.csrf_token = d["CSRFPreventionToken"]
        self.session.headers.update({
            "CSRFPreventionToken": self.csrf_token,
            "Cookie": f"PVEAuthCookie={self.ticket}",
        })

    def get_vms(self):
        url = f"{self.base_url}/api2/json/cluster/resources?type=vm"
        r = self.session.get(url)
        r.raise_for_status()
        return r.json()["data"]

    def start_vm(self, node, vmid):
        url = f"{self.base_url}/api2/json/nodes/{node}/qemu/{vmid}/status/start"
        r = self.session.post(url)
        r.raise_for_status()
        return r.json()

    def stop_vm(self, node, vmid):
        url = f"{self.base_url}/api2/json/nodes/{node}/qemu/{vmid}/status/stop"
        r = self.session.post(url)
        r.raise_for_status()
        return r.json()

    def get_vnc_proxy(self, node, vmid):
        """Request a VNC proxy ticket + port for the noVNC console."""
        url = f"{self.base_url}/api2/json/nodes/{node}/qemu/{vmid}/vncproxy"
        r = self.session.post(url)
        r.raise_for_status()
        d = r.json()["data"]
        return d["ticket"], d["port"], d.get("user", "root@pam")