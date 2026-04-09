import shutil
import os
import subprocess
import json
import threading
import platform
import urllib.request
import zipfile
import io
import time
import customtkinter as ctk
from tkinter import filedialog

CONFIG_FILE = "config.json"

class ConfigManager:
    @staticmethod
    def load_config():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}

    @staticmethod
    def save_config(key, value):
        data = ConfigManager.load_config()
        data[key] = value
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f)
        except:
            pass

def find_adb():
    data = ConfigManager.load_config()
    saved = data.get("adb_path")
    if saved and os.path.exists(saved):
        return saved
    
    adb_path = shutil.which("adb")
    if adb_path:
        return adb_path
    
    possible = [
        os.path.expanduser("~\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe"),
        "C:\\Android\\platform-tools\\adb.exe",
        "/usr/local/bin/adb"
    ]
    for p in possible:
        if os.path.exists(p):
            return p
    return None

ADB_PATH = find_adb()

def get_adb_url_and_sys():
    system = platform.system().lower()
    if system == "windows":
        return "https://dl.google.com/android/repository/platform-tools-latest-windows.zip", "adb.exe"
    elif system == "darwin":
        return "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip", "adb"
    else:
        return "https://dl.google.com/android/repository/platform-tools-latest-linux.zip", "adb"

def check_adb_update():
    if not ADB_PATH or not os.path.exists(ADB_PATH):
        return False, None
    url, _ = get_adb_url_and_sys()
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as response:
            remote_ver = response.headers.get('ETag') or response.headers.get('Last-Modified')
            local_ver = ConfigManager.load_config().get("adb_version")
            return (remote_ver != local_ver), remote_ver
    except:
        return False, None

def download_and_install_adb(target_dir=None, progress_callback=None):
    global ADB_PATH
    url, exe_name = get_adb_url_and_sys()
    if not target_dir:
        target_dir = os.path.join(os.path.expanduser("~"), ".devthinker")

    tools_dir = os.path.join(target_dir, "platform-tools")
    adb_path = os.path.join(tools_dir, exe_name)

    try:
        if progress_callback:
            progress_callback(0, 0, 0, "Preparando el sistema...")
        if platform.system().lower() == "windows":
            os.system("taskkill /F /IM adb.exe >nul 2>&1")
        else:
            os.system("killall adb >/dev/null 2>&1")
        time.sleep(1)

        req = urllib.request.Request(url, headers={'User-Agent': 'DevThinker/1.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(response.headers.get('content-length', 0))
            remote_ver = response.headers.get('ETag') or response.headers.get('Last-Modified')
            
            downloaded = 0
            chunk_size = 16384
            data = bytearray()
            start_time = time.time()
            last_update = 0
            
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                data.extend(chunk)
                downloaded += len(chunk)
                
                current_time = time.time()
                if progress_callback and (current_time - last_update > 0.1):
                    elapsed = current_time - start_time
                    speed = (downloaded / 1048576) / elapsed if elapsed > 0 else 0
                    progress_callback(downloaded, total_size, speed, "Descargando binarios...")
                    last_update = current_time

        if progress_callback:
            progress_callback(total_size, total_size, 0, "Extrayendo motor...")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(target_dir)
        
        if platform.system().lower() != "windows":
            os.chmod(adb_path, 0o755)
        
        ConfigManager.save_config("adb_path", adb_path)
        if remote_ver:
            ConfigManager.save_config("adb_version", remote_ver)
        
        ADB_PATH = adb_path
        return True
    except:
        return False

def uninstall_adb():
    global ADB_PATH
    if not ADB_PATH or not os.path.exists(ADB_PATH):
        ADB_PATH = None
        return True
    try:
        if platform.system().lower() == "windows":
            os.system("taskkill /F /IM adb.exe >nul 2>&1")
        else:
            os.system("killall adb >/dev/null 2>&1")
        time.sleep(1)
        
        adb_dir = os.path.dirname(ADB_PATH)
        if os.path.basename(adb_dir) == "platform-tools" and os.path.exists(adb_dir):
            shutil.rmtree(adb_dir, ignore_errors=True)
            
        ConfigManager.save_config("adb_path", None)
        ConfigManager.save_config("adb_version", None)
        ADB_PATH = None
        return True
    except:
        return False

def set_manual_adb_path():
    global ADB_PATH
    path = filedialog.askopenfilename(title="Seleccionar ADB", filetypes=[("exe", "*.exe"), ("all", "*.*")])
    if path and os.path.exists(path):
        ConfigManager.save_config("adb_path", path)
        ADB_PATH = path
        return True
    return False

def run_adb(args, timeout=15, encoding="utf-8"):
    if not ADB_PATH or not os.path.exists(ADB_PATH):
        return None
    try:
        cmd = [ADB_PATH] + args
        si = None
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, startupinfo=si, encoding=encoding, errors='replace')
        return res.stdout.strip()
    except:
        return None

def run_async(task_func, callback_func=None, app=None):
    def wrapper():
        try:
            result = task_func()
            if callback_func and app:
                def safe_cb():
                    try:
                        callback_func(result)
                    except:
                        pass
                app.after(0, safe_cb)
        except:
            pass
    threading.Thread(target=wrapper, daemon=True).start()

def requires_device(func):
    def wrapper(self, *args, **kwargs):
        if not self.app.current_device_id:
            self.app.show_toast("No hay dispositivo conectado", color="#e74c3c")
            return
        return func(self, *args, **kwargs)
    return wrapper

def center_toplevel(win, parent, w, h):
    win.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (w // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")

class AskYesNo(ctk.CTkToplevel):
    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.title(title)
        self.attributes("-topmost", True)
        self.transient(parent)
        self.result = False
        center_toplevel(self, parent, 400, 150)
        
        ctk.CTkLabel(self, text=text, font=("Segoe UI", 14), wraplength=350).pack(pady=20, padx=20, expand=True)
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", pady=10)
        ctk.CTkButton(f, text="Sí", font=("Segoe UI", 13, "bold"), width=100, fg_color="#e74c3c", hover_color="#c0392b", command=self.yes).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(f, text="No", font=("Segoe UI", 13, "bold"), width=100, fg_color="#475569", hover_color="#334155", command=self.no).pack(side="right", expand=True, padx=10)
        self.grab_set()
        self.wait_window()

    def yes(self):
        self.result = True
        self.destroy()

    def no(self):
        self.result = False
        self.destroy()

    def get(self):
        return self.result

class AskString(ctk.CTkToplevel):
    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.title(title)
        self.attributes("-topmost", True)
        self.transient(parent)
        self.result = None
        center_toplevel(self, parent, 400, 180)
        
        ctk.CTkLabel(self, text=text, font=("Segoe UI", 14)).pack(pady=(20, 10))
        self.entry = ctk.CTkEntry(self, width=300)
        self.entry.pack(pady=5)
        self.entry.focus()
        
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", pady=15)
        ctk.CTkButton(f, text="Aceptar", font=("Segoe UI", 13, "bold"), width=100, fg_color="#38BDF8", hover_color="#0284C7", command=self.ok).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(f, text="Cancelar", font=("Segoe UI", 13, "bold"), width=100, fg_color="#475569", hover_color="#334155", command=self.cancel).pack(side="right", expand=True, padx=10)
        self.bind("<Return>", lambda e: self.ok())
        self.grab_set()
        self.wait_window()

    def ok(self):
        self.result = self.entry.get()
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()

    def get(self):
        return self.result

class ShowInfo(ctk.CTkToplevel):
    def __init__(self, parent, title, text, is_error=False):
        super().__init__(parent)
        self.title(title)
        self.attributes("-topmost", True)
        self.transient(parent)
        center_toplevel(self, parent, 400, 180)
        
        c = "#EF4444" if is_error else "#10B981"
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 16, "bold"), text_color=c).pack(pady=(20, 5))
        ctk.CTkLabel(self, text=text, font=("Segoe UI", 13), wraplength=350).pack(pady=5, padx=20, expand=True)
        ctk.CTkButton(self, text="Aceptar", font=("Segoe UI", 13, "bold"), width=100, fg_color="#38BDF8", hover_color="#0284C7", command=self.destroy).pack(pady=15)
        self.bind("<Return>", lambda e: self.destroy())
        self.grab_set()
        self.wait_window()

class ToolTip:
    def __init__(self, widget, text, delay=600):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule)
        self.widget.bind("<Leave>", self.hide)
        self.widget.bind("<ButtonPress>", self.hide)

    def schedule(self, event=None):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def show(self):
        if self.tip_window or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
            self.tip_window = ctk.CTkToplevel(self.widget)
            self.tip_window.wm_overrideredirect(True)
            self.tip_window.wm_geometry(f"+{x}+{y}")
            self.tip_window.attributes('-topmost', True) 
            label = ctk.CTkLabel(self.tip_window, text=self.text, justify='left', fg_color="#181D2B", text_color="#F8FAFC", border_width=1, border_color="#252D40", corner_radius=6, font=("Segoe UI", 11))
            label.pack(ipadx=8, ipady=4)
        except:
            self.hide()

    def hide(self, event=None):
        self.unschedule()
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except:
                pass
            self.tip_window = None

class ToastNotification(ctk.CTkToplevel):
    def __init__(self, parent, message, color="#10B981"):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            x = parent.winfo_x() + parent.winfo_width() - 320
            y = parent.winfo_y() + parent.winfo_height() - 70
            self.geometry(f"300x50+{x}+{y}")
        except:
            self.geometry("300x50")
        f = ctk.CTkFrame(self, fg_color=color, corner_radius=10)
        f.pack(fill="both", expand=True)
        ctk.CTkLabel(f, text=message, font=("Segoe UI", 13, "bold"), text_color="white").pack(expand=True)
        self.after(2500, self.destroy)