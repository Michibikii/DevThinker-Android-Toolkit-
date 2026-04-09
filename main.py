import customtkinter as ctk
import threading
import time
import re
import json
import urllib.request
import urllib.parse
import os
import sys
import traceback
from datetime import datetime
import utils 
from utils import run_adb, ToastNotification
from views import (FrameLiveLog, FrameAnalyzer, FrameFileExplorer, 
                   FrameDeviceStats, FrameWireless, FramePackages, FrameTools, FrameTerminal)

def global_exception_handler(exc_type, exc_value, exc_traceback):
    try:
        with open("crash_report.txt", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FATAL CRASH\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except:
        pass

sys.excepthook = global_exception_handler

ctk.set_appearance_mode("Dark")

class DevThinkerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DevThinker - Android Toolkit")
        self.geometry("1200x800")
        self.configure(fg_color="#0B0F19")
        self.after(10, self.maximize_window)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.current_device_id = None
        self.is_monitoring = True
        self.adb_update_available = False
        
        self.last_state = False
        self.current_tab = "wireless"
        
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color="#111522")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="🧠 DevThinker", font=("Segoe UI", 26, "bold"), text_color="#E2E8F0").pack(pady=(40, 25))
        
        self.info_card = ctk.CTkFrame(self.sidebar, fg_color="#181D2B", corner_radius=12, border_width=1, border_color="#252D40")
        self.info_card.pack(fill="x", padx=18, pady=(0, 20))
        
        self.lbl_model = ctk.CTkLabel(self.info_card, text="🚫 Sin Dispositivo", font=("Segoe UI", 15, "bold"), text_color="#F8FAFC", anchor="w", justify="left", wraplength=190)
        self.lbl_model.pack(fill="x", padx=15, pady=(15, 2))
        
        self.lbl_sub1 = ctk.CTkLabel(self.info_card, text="Esperando conexión...", font=("Segoe UI", 12), text_color="#94A3B8", anchor="w", justify="left", wraplength=190)
        self.lbl_sub1.pack(fill="x", padx=15, pady=0)
        
        self.lbl_sub2 = ctk.CTkLabel(self.info_card, text="", font=("Segoe UI", 11), text_color="#64748B", anchor="w", justify="left", wraplength=190)
        self.lbl_sub2.pack(fill="x", padx=15, pady=(2, 15))

        self.btn_disconnect = ctk.CTkButton(self.info_card, text="Desconectar", fg_color="#EF4444", hover_color="#DC2626", height=28, font=("Segoe UI", 12, "bold"), command=self.disconnect_device)

        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.pack(fill="both", expand=True)

        self.nav_btns = {}
        self.render_menu()
            
        ctk.CTkLabel(self.sidebar, text="Premium", font=("Segoe UI", 10), text_color="#475569").pack(side="bottom", pady=15)
        
        self.container = ctk.CTkFrame(self, fg_color="#111522", corner_radius=16, border_width=1, border_color="#1E2538")
        self.container.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)
        
        self.frames = {
            "live": FrameLiveLog(self.container, self),
            "analyze": FrameAnalyzer(self.container),
            "files": FrameFileExplorer(self.container, self),
            "stats": FrameDeviceStats(self.container, self),
            "wireless": FrameWireless(self.container, self),
            "packages": FramePackages(self.container, self),
            "terminal": FrameTerminal(self.container, self),
            "tools": FrameTools(self.container, self)
        }
        self.show_frame("wireless")
        
        self.monitor_thread = threading.Thread(target=self.device_monitor_loop, daemon=True)
        self.monitor_thread.start()

    def report_callback_exception(self, exc, val, tb):
        global_exception_handler(exc, val, tb)
        try:
            self.show_toast("Error interno guardado en crash_report.txt", color="#EF4444")
        except:
            pass

    def adb_cmd(self, command_list, timeout=15):
        if not self.current_device_id:
            self.show_toast("No hay dispositivo conectado", color="#EF4444")
            return None
        return run_adb(["-s", self.current_device_id] + command_list, timeout=timeout)

    def maximize_window(self):
        try:
            self.state('zoomed')
        except:
            pass

    def on_closing(self):
        self.is_monitoring = False
        if "live" in self.frames:
            self.frames["live"].stop()
        self.destroy()
        sys.exit(0)

    def render_menu(self):
        for widget in self.nav_frame.winfo_children():
            widget.destroy()

        self.nav_btns = {}
        buttons = []

        if not self.last_state:
            buttons.append(("📡  Conectar Dispositivo", "wireless"))

        buttons.extend([
            ("📊  Monitor del Sistema", "stats"),
            ("🔴  Logcat en Vivo", "live"), 
            ("🔎  Análisis de Errores", "analyze"), 
            ("💻  Terminal ADB", "terminal"),
            ("📁  Explorador de Archivos", "files"),
            ("📦  Gestor de Paquetes", "packages"), 
            ("🔧  Utilidades", "tools") 
        ])

        for text, name in buttons:
            btn = ctk.CTkButton(self.nav_frame, text=text, height=42, anchor="w", fg_color="transparent", 
                                text_color="#94A3B8", hover_color="#1E293B", corner_radius=8, font=("Segoe UI", 14), 
                                command=lambda n=name: self.show_frame(n))
            btn.pack(fill="x", padx=18, pady=4)
            self.nav_btns[name] = btn

        if self.current_tab in self.nav_btns:
            self.nav_btns[self.current_tab].configure(fg_color="#1E293B", text_color="#38BDF8", font=("Segoe UI", 14, "bold"))

    def show_frame(self, name):
        self.current_tab = name
        for btn_name, btn in self.nav_btns.items():
            btn.configure(fg_color="transparent", text_color="#94A3B8", font=("Segoe UI", 14, "normal"))
        if name in self.nav_btns:
            self.nav_btns[name].configure(fg_color="#1E293B", text_color="#38BDF8", font=("Segoe UI", 14, "bold"))
            
        for f in self.frames.values():
            f.pack_forget()
            
        self.frames[name].pack(fill="both", expand=True, padx=25, pady=25)
        
        if name == "tools":
            self.frames["tools"].refresh_adb_card_ui()
        elif name == "files" and self.current_device_id:
            self.frames["files"].load_files()

    def disconnect_device(self):
        if self.current_device_id:
            self.show_toast("Desconectando...", color="#F59E0B")
            utils.run_async(lambda: run_adb(["disconnect"]), lambda res: None, self)
            self.current_device_id = None
            self.thread_safe_update("🚫 Sin Dispositivo", "Esperando conexión...", "", "#181D2B", "#F8FAFC", False)
            self.show_frame("wireless")

    def device_monitor_loop(self):
        while self.is_monitoring:
            if not utils.ADB_PATH or not os.path.exists(utils.ADB_PATH):
                self.current_device_id = None
                self.thread_safe_update("⚠️ ADB no encontrado", "Vaya a Utilidades e instálelo\npara continuar.", "", "#3F1D1D", "#EF4444", False)
                time.sleep(3)
                continue

            out = run_adb(["devices"])
            
            if out is None:
                self.current_device_id = None
                self.thread_safe_update("⚠️ Error de ADB", "El motor falló o está corrupto.\nReinstálelo desde Utilidades.", "", "#3F1D1D", "#EF4444", False)
                time.sleep(3)
                continue

            lines = out.strip().split('\n')
            found_line = None
            
            for line in lines:
                if "List of devices" in line or not line.strip():
                    continue
                if "device" in line and "unauthorized" not in line and "offline" not in line:
                    found_line = line
                    break
                elif "unauthorized" in line:
                    self.current_device_id = None
                    self.thread_safe_update("⚠️ No Autorizado", "Acepta el aviso en la\npantalla del celular.", "", "#422C10", "#F59E0B", False)
                    found_line = "error"
                    break
                elif "offline" in line:
                    self.current_device_id = None
                    self.thread_safe_update("🔌 Dispositivo Offline", "Reinicia la conexión USB\no el Wi-Fi.", "", "#3F1D1D", "#EF4444", False)
                    found_line = "error"
                    break

            if found_line == "error":
                time.sleep(2)
                continue
            elif found_line:
                try:
                    dev_id = found_line.split()[0]
                    self.current_device_id = dev_id
                    
                    props_raw = self.adb_cmd(["shell", "getprop"])
                    brand, model, ver, api, cpu = "Desconocido", "Dispositivo", "?", "?", "?"
                    market_name = ""
                    
                    if props_raw:
                        props = dict(re.findall(r'\[(.*?)\]:\s*\[(.*?)\]', props_raw))
                        brand = props.get('ro.product.brand', 'Desconocido').capitalize()
                        model = props.get('ro.product.model', 'Dispositivo')
                        ver   = props.get('ro.build.version.release', '?')
                        api   = props.get('ro.build.version.sdk', '?')
                        cpu   = props.get('ro.product.cpu.abi', '?')
                        
                        market_name = props.get('ro.product.marketname', '')
                        if not market_name:
                            market_name = props.get('ro.product.vendor.marketname', '')
                            
                    if not market_name:
                        dev_name_out = self.adb_cmd(["shell", "settings", "get", "global", "device_name"])
                        if dev_name_out and "null" not in dev_name_out and "error" not in dev_name_out.lower():
                            market_name = dev_name_out.strip()
                    
                    full_name = f"📱 {brand} {model}" if brand != "Desconocido" else f"📱 {model}"
                    
                    if not market_name:
                        market_name = model
                        
                    online_info = f"✅ Modelo: {market_name}"
                    
                    if self.adb_update_available:
                        online_info += "\n🔔 ¡Actualización de ADB\nrecomendada en Utilidades!"
                    
                    bat_raw = self.adb_cmd(["shell", "dumpsys", "battery"])
                    level = "?"
                    if bat_raw:
                        for l in bat_raw.split('\n'):
                            if "level:" in l:
                                level = l.split(":")[1].strip() + "%"
                                break
                    
                    sub1 = f"🤖 Android {ver}   |   🔋 {level}"
                    sub2 = f"⚙️ API {api} • {cpu}\n{online_info}"

                    self.thread_safe_update(full_name, sub1, sub2, "#132E25", "#10B981", True)
                except:
                    pass
            else:
                self.current_device_id = None
                self.thread_safe_update("🚫 Sin Dispositivo", "Esperando conexión...", "", "#181D2B", "#F8FAFC", False)
            
            time.sleep(3)

    def thread_safe_update(self, name, sub1, sub2, bg_color, title_color, is_conn):
        if self.is_monitoring:
            try:
                self.after(0, lambda: self._update_ui(name, sub1, sub2, bg_color, title_color, is_conn))
            except:
                pass

    def _update_ui(self, name, sub1, sub2, bg_color, title_color, is_conn):
        try:
            self.lbl_model.configure(text=name, text_color=title_color)
            self.lbl_sub1.configure(text=sub1)
            self.lbl_sub2.configure(text=sub2)
            self.info_card.configure(fg_color=bg_color)
            
            if is_conn and not self.last_state:
                self.last_state = True
                self.lbl_sub2.pack_configure(pady=(2, 10))
                self.btn_disconnect.pack(fill="x", padx=15, pady=(0, 15))
                self.render_menu()
                if self.current_tab == "wireless":
                    self.show_frame("stats")
                    
            elif not is_conn and self.last_state:
                self.last_state = False
                self.btn_disconnect.pack_forget()
                self.lbl_sub2.pack_configure(pady=(2, 15))
                self.render_menu()
                if self.current_tab not in self.nav_btns:
                    self.show_frame("wireless")
        except:
            pass

    def show_toast(self, msg, color="#10B981"):
        ToastNotification(self, msg, color)

if __name__ == "__main__":
    app = DevThinkerApp()
    app.mainloop()