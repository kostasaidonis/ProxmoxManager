import requests
from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.label import Label
from kivy.properties import BooleanProperty, StringProperty, ObjectProperty, NumericProperty
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.uix.button import Button
import urllib3
from urllib.parse import quote
import threading
import time
import os
from playwright.sync_api import sync_playwright
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(os.getcwd(), 'playwright_browsers')
# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Custom SelectableLabel class
class SelectableLabel(Label, RecycleDataViewBehavior):
    selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(SelectableLabel, self).__init__(**kwargs)
        self.color = (0, 0, 0, 1)  # Set text color to black

    def refresh_view_attrs(self, rv, index, data):
        """Refresh the view attributes with new data"""
        self.index = index
        return super(SelectableLabel, self).refresh_view_attrs(rv, index, data)

    def apply_selection(self, rv, index, is_selected):
        """Apply selection visuals when an item is selected"""
        self.selected = is_selected


Factory.register('SelectableLabel', cls=SelectableLabel)

KV = '''
<VMListItem>:
    orientation: 'horizontal'
    canvas.before:
        Color:
            rgba: (0.2, 0.6, 0.8, 1) if self.selected else (1, 1, 1, 1)  # Light blue when selected
        Rectangle:
            pos: self.pos
            size: self.size

    SelectableLabel:
        text: root.vmid
        size_hint_x: 0.1
    SelectableLabel:
        text: root.name
        size_hint_x: 0.2
    SelectableLabel:
        text: root.status
        size_hint_x: 0.15
    SelectableLabel:
        text: root.node
        size_hint_x: 0.15
    SelectableLabel:
        text: root.cpu
        size_hint_x: 0.15
    SelectableLabel:
        text: root.memory
        size_hint_x: 0.15
    SelectableLabel:
        text: root.uptime
        size_hint_x: 0.2

<Button@Button>:
    background_normal: ''
    background_color: 0.2, 0.6, 0.8, 1  # Default color (e.g., blue)
<ProxmoxUI>:
    orientation: 'vertical'
    padding: '10dp'
    spacing: '10dp'

    Label:
        text: 'Proxmox VM Manager'
        font_size: 24

    BoxLayout:
        size_hint_y: None
        height: '30dp'
        spacing: '10dp'
        padding: '5dp'

        Label:
            text: 'VMID'
            size_hint_x: 0.1
            bold: True
        Label:
            text: 'Name'
            size_hint_x: 0.2
            bold: True
        Label:
            text: 'Status'
            size_hint_x: 0.15
            bold: True
        Label:
            text: 'Node'
            size_hint_x: 0.15
            bold: True
        Label:
            text: 'CPU (%)'
            size_hint_x: 0.15
            bold: True
        Label:
            text: 'Memory (%)'
            size_hint_x: 0.15
            bold: True
        Label:
            text: 'Uptime'
            size_hint_x: 0.2
            bold: True

    RecycleView:
        id: vm_list
        viewclass: 'VMListItem'
        SelectableRecycleBoxLayout:
            id: layout
            default_size: None, dp(50)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
            multiselect: False
            touch_multiselect: False

    BoxLayout:
        size_hint_y: None
        height: '48dp'
        spacing: '10dp'

        Button:
            text: 'Start VM'
            background_normal: ''
            background_color: 0.2, 0.6, 0.8, 1  # Default color
            on_press: self.background_color = 1, 0.5, 0.5, 1  # Change to red when pressed
            on_release:
                self.background_color = 0.2, 0.6, 0.8, 1  # Change back to default
                root.start_vm()  # Trigger the function

        Button:
            text: 'Stop VM'
            background_normal: ''
            background_color: 0.2, 0.6, 0.8, 1  # Default color
            on_press: self.background_color = 1, 0.5, 0.5, 1  # Change to red when pressed
            on_release:
                self.background_color = 0.2, 0.6, 0.8, 1  # Change back to default
                root.stop_vm()  # Trigger the function

        Button:
            text: 'Launch VNC'
            background_normal: ''
            background_color: 0.2, 0.6, 0.8, 1  # Default color
            on_press: self.background_color = 1, 0.5, 0.5, 1  # Change to red when pressed
            on_release:
                self.background_color = 0.2, 0.6, 0.8, 1  # Change back to default
                root.launch_vnc()  # Trigger the function

    Label:
        id: status_label
        size_hint_y: None
        height: '30dp'
        text: 'Ready'
        color: 0, 0, 0, 1

<ProxmoxLoginPopup>:
    title: 'Proxmox Authentication'
    size_hint: 0.5, 0.5
    auto_dismiss: False

    BoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '10dp'

        Label:
            text: 'Enter Proxmox Credentials'

        TextInput:
            id: host_input
            hint_text: 'Proxmox Host'
            focus: True
            multiline: False
            focus_next: username_input  # Set the next focus

        TextInput:
            id: username_input
            hint_text: 'Username'
            multiline: False
            focus_next: password_input  # Set the next focus

        TextInput:
            id: password_input
            hint_text: 'Password'
            password: True
            multiline: False

        Button:
            text: 'Authenticate'
            on_press: root.authenticate()
'''


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout):
    """ Adds selection and focus behavior to the view. """
    pass


class VMListItem(RecycleDataViewBehavior, BoxLayout):
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)
    index = NumericProperty(0)
    vmid = StringProperty('')
    name = StringProperty('')
    status = StringProperty('')
    node = StringProperty('')
    cpu = StringProperty('')
    memory = StringProperty('')
    uptime = StringProperty('')

    def refresh_view_attrs(self, rv, index, data):
        """ Refresh the view attributes with new data """
        self.index = index
        for key, value in data.items():
            setattr(self, key, str(value))
        return super(VMListItem, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        """ Capture touch event to handle selection """
        if super(VMListItem, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.parent and hasattr(self.parent, 'select_with_touch'):
            self.parent.select_with_touch(self.index, touch)
            return True
        return False

    def apply_selection(self, rv, index, is_selected):
        """ Apply selection visuals when an item is selected """
        self.selected = is_selected

        # Access the ProxmoxUI parent through the widget hierarchy
        vm_manager = rv.parent
        if isinstance(vm_manager, ProxmoxUI):
            if is_selected:
                vm_manager.selected_vm = self
                vm_manager.ids.status_label.text = f'Selected VM: {self.name} (VMID: {self.vmid})'
            else:
                vm_manager.ids.status_label.text = 'Ready'


class ProxmoxUI(BoxLayout):
    selected_vm = ObjectProperty(None, allownone=True)

    def __init__(self, session, ticket, csrf_token, host, ui_user, password, **kwargs):
        # Initialize superclass without passing the problematic properties
        super().__init__(**kwargs)

        # Store the session details and credentials
        self.session = session
        self.ticket = ticket
        self.csrf_token = csrf_token
        self.host = host
        self.ui_user = ui_user  # Store the UI username
        self.password = password  # Store the password

        # Start background thread for refreshing the VM list
        threading.Thread(target=self.update_vm_list_periodically, daemon=True).start()

    def update_vm_list_periodically(self):
        while True:
            # Schedule UI update in the main thread
            Clock.schedule_once(lambda dt: self.update_vm_list())
            time.sleep(5)

    def update_vm_list(self):
        if not self.session:
            return

        url = f"https://{self.host}:8006/api2/json/cluster/resources?type=vm"
        try:
            response = self.session.get(url, verify=False)
            response.raise_for_status()

            vm_data = []
            for vm in response.json()["data"]:
                cpu = vm.get('cpu', 0) * 100
                memory = (vm.get('mem', 0) / vm.get('maxmem', 1)) * 100 if vm.get('maxmem') else 0
                uptime = self.format_uptime(vm.get('uptime', 0))

                vm_data.append({
                    'vmid': str(vm.get('vmid', 'N/A')),
                    'name': vm.get('name', 'Unknown'),
                    'status': vm.get('status', 'Unknown'),
                    'node': vm.get('node', 'Unknown'),
                    'cpu': f"{cpu:.1f}",
                    'memory': f"{memory:.1f}",
                    'uptime': uptime
                })

            self.ids.vm_list.data = vm_data
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch VM list: {e}")

    def format_uptime(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    def start_vm(self):
        if not self.selected_vm:
            print("Please select a VM first")
            return
        vm_id = self.selected_vm.vmid

        node = self.selected_vm.node
        url = f"https://{self.host}:8006/api2/json/nodes/{node}/qemu/{vm_id}/status/start"
        try:
            response = self.session.post(url, verify=False)
            response.raise_for_status()
            self.update_vm_list()
        except requests.exceptions.RequestException as e:
            print(f"Failed to start VM: {e}")

    def stop_vm(self):
        if not self.selected_vm:
            print("Please select a VM first")
            return
        vm_id = self.selected_vm.vmid
        node = self.selected_vm.node
        url = f"https://{self.host}:8006/api2/json/nodes/{node}/qemu/{vm_id}/status/stop"
        try:
            response = self.session.post(url, verify=False)
            response.raise_for_status()
            self.update_vm_list()
        except requests.exceptions.RequestException as e:
            print(f"Failed to stop VM: {e}")

    def launch_vnc(self):
        if not self.selected_vm:
            print("Please select a VM first")
            return
        vm_id = self.selected_vm.vmid
        node = self.selected_vm.node
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(ignore_https_errors=True)
                page = context.new_page()
                page.goto(f"https://{self.host}:8006")
                page.wait_for_selector("input[name='username']")
                page.fill("input[name='username']", self.ui_user)  # Use stored username
                page.fill("input[name='password']", self.password)  # Use stored password
                page.click("#button-1070-btnInnerEl")
                page.wait_for_load_state("networkidle")

                encoded_ticket = quote(self.ticket, safe='')
                vnc_url = (
                    f"https://{self.host}:8006/?console=kvm&novnc=1&node={node}"
                    f"&resize=off&vmid={vm_id}&path=api2/json/nodes/{node}/qemu/{vm_id}/vncwebsocket/port/5900/vncticket/{encoded_ticket}"
                )

                vnc_page = context.new_page()
                vnc_page.goto(vnc_url)
                vnc_page.wait_for_selector("canvas", timeout=60000)
                vnc_page.set_viewport_size({"width": 1024, "height": 768})
                page.close()
                vnc_page.wait_for_event("close", timeout=0)
                browser.close()
        except Exception as e:
            print(f"Error while launching VNC: {e}")


class ProxmoxLoginPopup(Popup):
    title = "Proxmox Authentication"

    def authenticate(self):
        # Get host, username, and password
        host = self.ids.host_input.text
        username = self.ids.username_input.text
        password = self.ids.password_input.text

        if not host or not username or not password:
            print("Please enter all fields.")
            return

        api_user = f"{username}@pam"
        url = f"https://{host}:8006/api2/json/access/ticket"
        data = {"username": api_user, "password": password}
        try:
            response = requests.post(url, data=data, verify=False)
            response.raise_for_status()
            data = response.json()["data"]
            ticket = data["ticket"]
            csrf_prevention_token = data["CSRFPreventionToken"]
            session = requests.Session()
            session.headers.update({
                "CSRFPreventionToken": csrf_prevention_token,
                "Cookie": f"PVEAuthCookie={ticket}"
            })

            # If authentication is successful, open the main UI and close the login popup
            proxmox_ui = ProxmoxUI(
                session=session,
                ticket=ticket,
                csrf_token=csrf_prevention_token,
                host=host,
                ui_user=username,  # Pass username for UI login
                password=password  # Pass password for UI login
            )
            app.root.clear_widgets()
            app.root.add_widget(proxmox_ui)
            self.dismiss()
        except requests.exceptions.RequestException as e:
            print(f"Authentication error: {e}")


class ProxmoxApp(App):
    def build(self):
        Builder.load_string(KV)
        login_popup = ProxmoxLoginPopup()
        login_popup.open()
        return BoxLayout()

if __name__ == "__main__":
    app = ProxmoxApp()
    app.run()

