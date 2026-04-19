import customtkinter as ctk
import threading
import re
import time
import urllib.request
import urllib.parse
import ssl
from PIL import Image
import io
import random
import utils
from utils import run_adb, ToolTip

class FrameWireless(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        
        ctk.CTkLabel(self, text="Conectar Dispositivo", font=("Segoe UI", 24, "bold"), text_color="#F8FAFC").pack(anchor="w", pady=(0,5))
        ctk.CTkLabel(self, text="Conecta tu dispositivo mediante Wi-Fi de forma remota o cable USB.", font=("Segoe UI", 13), text_color="#94A3B8").pack(anchor="w", pady=(0,15))
        
        ctk.CTkLabel(self, text="⚠️ Nota: Asegúrate de pausar cualquier VPN o Adblocker (ej. Blokada/AdGuard) antes de conectar de forma inalámbrica.", text_color="#F59E0B", font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 15))

        self.tabs = ctk.CTkTabview(self, fg_color="#181D2B", segmented_button_fg_color="#0B0F19", segmented_button_selected_color="#1E293B", segmented_button_selected_hover_color="#252D40", segmented_button_unselected_hover_color="#181D2B", text_color="#E2E8F0", border_width=1, border_color="#252D40", corner_radius=12)
        self.tabs.pack(fill="both", expand=True, pady=5)
        
        self.tab_qr = self.tabs.add("📱 Escanear QR")
        self.tab_manual = self.tabs.add("⌨️ Conectar por IP/Puerto")
        self.tab_legacy = self.tabs.add("🔌 Conectar con Cable USB")
        
        self.setup_qr_tab()
        self.setup_manual_tab()
        self.setup_legacy_tab()

    def _add_tab_header(self, tab, title, instructions):
        f_header = ctk.CTkFrame(tab, fg_color="transparent")
        f_header.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(f_header, text=title, font=("Segoe UI", 16, "bold"), text_color="#F8FAFC").pack(anchor="w")
        ctk.CTkLabel(f_header, text=instructions, font=("Segoe UI", 13), text_color="#94A3B8", justify="left").pack(anchor="w", pady=(2, 0))

    def _safe_after(self, delay, callback):
        try:
            self.app.after(delay, callback)
        except:
            pass

    def _wait_for_connection_port(self, target_ip, timeout=12):
        start_time = time.time()
        while time.time() - start_time < timeout:
            out = run_adb(["mdns", "services"]) 
            if out:
                for line in out.split('\n'):
                    if "_adb-tls-connect" in line and target_ip in line:
                        match = re.search(r"(\d+\.\d+\.\d+\.\d+:\d+)", line)
                        if match:
                            return match.group(1)
            time.sleep(1.5) 
        return None

    def _end_process(self, btn, text, msg, success=False):
        self._safe_after(0, lambda: btn.configure(text=text, state="normal"))
        self._safe_after(100, lambda: utils.ShowInfo(self.app, "¡Éxito!" if success else "Error de Conexión", msg, not success))

    def setup_qr_tab(self):
        self.qr_pass = str(random.randint(100000, 999999))
        self.qr_name = f"DevThinker-{random.randint(100,999)}"
        self.qr_data = f"WIFI:T:ADB;S:{self.qr_name};P:{self.qr_pass};;"
        
        instructions = (
            "1. Ve a Opciones de Desarrollador > Depuración Inalámbrica.\n"
            "2. Toca 'Vincular dispositivo con código QR' y escanea esto:"
        )
        self._add_tab_header(self.tab_qr, "📱 Conexión por Código QR", instructions)
        
        f_content = ctk.CTkFrame(self.tab_qr, fg_color="transparent")
        f_content.pack(fill="both", expand=True)
        
        self.lbl_qr = ctk.CTkLabel(f_content, text="Cargando código QR seguro...", font=("Segoe UI", 12), text_color="#94A3B8")
        self.lbl_qr.pack(expand=True)
        
        self.btn_scan = ctk.CTkButton(f_content, text="🔍 Buscar y Conectar", font=("Segoe UI", 14, "bold"), fg_color="#10B981", hover_color="#059669", height=45, width=220, command=self.scan_mdns, text_color_disabled="#94A3B8")
        self.btn_scan.pack(pady=20)
        ToolTip(self.btn_scan, "Busca el dispositivo en la red Wi-Fi y maneja ambos puertos automáticamente.")
        
        threading.Thread(target=self.load_qr, daemon=True).start()

    def load_qr(self):
        try:
            data = urllib.parse.quote(self.qr_data)
            urls = [
                f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={data}&bgcolor=FFFFFF",
                f"https://quickchart.io/qr?text={data}&size=200&light=ffffff",
                f"https://chart.googleapis.com/chart?chs=200x200&cht=qr&chl={data}"
            ]
            
            img_data = None
            ctx = ssl._create_unverified_context()
            
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, context=ctx, timeout=6) as response:
                        img_data = response.read()
                        if img_data:
                            break
                except:
                    continue
                    
            if not img_data:
                raise Exception("APIs failed")
                
            image = Image.open(io.BytesIO(img_data))
            ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(200, 200))
            self._safe_after(0, lambda: self.lbl_qr.configure(image=ctk_img, text=""))
        except:
            self._safe_after(0, lambda: self.lbl_qr.configure(text="❌ Error al cargar QR.\nVerifica tu conexión a Internet o Firewall.", text_color="#EF4444"))

    def scan_mdns(self):
        self.btn_scan.configure(text="⏳ Rastreando la red local...", state="disabled")
        threading.Thread(target=self._mdns_thread, daemon=True).start()

    def _mdns_thread(self):
        run_adb(["mdns", "check"])
        out = run_adb(["mdns", "services"])
        if not out:
            self._end_process(self.btn_scan, "🔍 Buscar y Conectar", "La red local no responde. Verifica que la PC tenga Wi-Fi activado o desactiva VPNs.", False)
            return
            
        lines = out.split('\n')
        pairing_ip_port = None
        for line in lines:
            if self.qr_name in line and "_adb-tls-pairing" in line:
                match = re.search(r"(\d+\.\d+\.\d+\.\d+:\d+)", line)
                if match:
                    pairing_ip_port = match.group(1)
        
        if not pairing_ip_port:
            self._end_process(self.btn_scan, "🔍 Buscar y Conectar", "No se detectó el celular.\n1. Asegúrate de tener la pantalla del escáner QR abierta en el teléfono.\n2. Revisa que estén en la misma red Wi-Fi.", False)
            return
            
        self._safe_after(0, lambda: self.btn_scan.configure(text="⏳ Vinculando dispositivo..."))
        
        pair_res = run_adb(["pair", pairing_ip_port, self.qr_pass]) 
        if not pair_res or ("Failed" in pair_res or "error" in pair_res.lower()):
            self._end_process(self.btn_scan, "🔍 Buscar y Conectar", f"El teléfono rechazó la vinculación. Intenta de nuevo.\nDetalle: {pair_res}", False)
            return
            
        self._safe_after(0, lambda: self.btn_scan.configure(text="⏳ Cazando puerto de conexión..."))
        
        ip_only = pairing_ip_port.split(':')[0]
        connect_ip_port = self._wait_for_connection_port(ip_only)
        
        if connect_ip_port:
            conn_res = run_adb(["connect", connect_ip_port]) 
            if "connected" in conn_res.lower():
                self._end_process(self.btn_scan, "🔍 Buscar y Conectar", f"El dispositivo se conectó exitosamente de forma inalámbrica en:\n{connect_ip_port}", True)
            else:
                self._end_process(self.btn_scan, "🔍 Buscar y Conectar", f"Se encontró el puerto, pero ADB denegó la conexión final:\n{conn_res}", False)
        else:
            self._end_process(self.btn_scan, "🔍 Buscar y Conectar", "El dispositivo se vinculó con éxito, pero Android nunca expuso el puerto de conexión final.\nIntenta desactivar y reactivar la 'Depuración Inalámbrica' en el celular.", False)

    def setup_manual_tab(self):
        instructions = (
            "Ingresa la IP y el Puerto de 'Depuración Inalámbrica'. El código es opcional y solo necesario si es la primera vez en Android 11+.\n"
            "Presiona 'Vincular / Conectar' para iniciar el proceso."
        )
        self._add_tab_header(self.tab_manual, "⌨️ Conexión Manual por IP", instructions)
        
        f_main = ctk.CTkFrame(self.tab_manual, fg_color="#0B0F19", corner_radius=12, border_width=1, border_color="#252D40")
        f_main.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        f_center = ctk.CTkFrame(f_main, fg_color="transparent")
        f_center.pack(expand=True)
        
        row1 = ctk.CTkFrame(f_center, fg_color="transparent")
        row1.pack(fill="x", pady=15)
        
        self.entry_ip = ctk.CTkEntry(row1, placeholder_text="IP (ej. 192.168.1.5)", font=("Consolas", 13), width=200, height=45, fg_color="#181D2B", border_color="#252D40", text_color="#F8FAFC")
        self.entry_ip.pack(side="left", padx=(0, 15))
        
        self.entry_port = ctk.CTkEntry(row1, placeholder_text="Puerto", font=("Consolas", 13), width=100, height=45, fg_color="#181D2B", border_color="#252D40", text_color="#F8FAFC")
        self.entry_port.pack(side="left", padx=(0, 15))
        
        self.entry_code = ctk.CTkEntry(row1, placeholder_text="Código (Opcional)", font=("Consolas", 13), width=150, height=45, fg_color="#181D2B", border_color="#252D40", text_color="#F8FAFC")
        self.entry_code.pack(side="left")

        self.btn_manual_connect = ctk.CTkButton(f_center, text="Vincular / Conectar", font=("Segoe UI", 14, "bold"), height=45, width=220, fg_color="#38BDF8", hover_color="#0284C7", command=self.start_manual_connection)
        self.btn_manual_connect.pack(pady=20)

    def start_manual_connection(self):
        ip = self.entry_ip.get().strip()
        port = self.entry_port.get().strip()
        pair_code = self.entry_code.get().strip()

        if not ip or not port:
            self.app.show_toast("Debes rellenar al menos la IP y el Puerto", color="#F59E0B")
            return

        pair_addr = f"{ip}:{port}"
        self.btn_manual_connect.configure(text="⏳ Procesando...", state="disabled")
        
        if pair_code:
            threading.Thread(target=self._manual_connect_thread, args=(pair_addr, pair_code), daemon=True).start()
        else:
            self.app.show_toast("Conectando...", color="#38BDF8")
            utils.run_async(lambda: run_adb(['connect', pair_addr]), lambda res: self._post_connect_legacy(res), self.app)

    def _post_connect_legacy(self, res):
        self.app.show_toast(f"Intento: {res}")
        self._safe_after(0, lambda: self.btn_manual_connect.configure(text="Vincular / Conectar", state="normal"))

    def _manual_connect_thread(self, pair_addr, pair_code):
        run_adb(["mdns", "check"]) 
        pair_res = run_adb(["pair", pair_addr, pair_code])
        
        if pair_res and ("Successfully paired" in pair_res or "Already paired" in pair_res or "successfully" in pair_res.lower()):
            self._safe_after(0, lambda: self.btn_manual_connect.configure(text="⏳ Conectando..."))
            
            ip_only = pair_addr.split(':')[0]
            connect_ip_port = self._wait_for_connection_port(ip_only)
            
            if connect_ip_port:
                conn_res = run_adb(["connect", connect_ip_port])
                if "connected" in conn_res.lower():
                    self._end_process(self.btn_manual_connect, "Vincular / Conectar", f"¡Conexión inyectada automáticamente en {connect_ip_port}!", True)
                    return
            
            self._end_process(self.btn_manual_connect, "Vincular / Conectar", "Se vinculó correctamente, pero el router bloqueó el auto-descubrimiento.\nVe a Utilidades y conéctate usando el puerto principal manualmente.", False)
        else:
            self._end_process(self.btn_manual_connect, "Vincular / Conectar", f"Credenciales rechazadas por el teléfono:\n{pair_res}", False)

    def setup_legacy_tab(self):
        instructions = (
            "1. Activa la 'Depuración USB' en las Opciones de Desarrollador.\n"
            "2. Conecta tu teléfono a la PC usando el cable USB."
        )
        self._add_tab_header(self.tab_legacy, "🔌 Conexión por Cable USB", instructions)
        
        f_content = ctk.CTkFrame(self.tab_legacy, fg_color="#0B0F19", corner_radius=12, border_width=1, border_color="#252D40")
        f_content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        f_center = ctk.CTkFrame(f_content, fg_color="transparent")
        f_center.pack(expand=True)
        
        ctk.CTkLabel(f_center, text="🔌", font=("Segoe UI Emoji", 45), text_color="#F8FAFC").pack(pady=(0, 20))

        self.btn_usb_connect = ctk.CTkButton(f_center, text="Buscar Dispositivo USB", font=("Segoe UI", 14, "bold"), height=45, width=220, fg_color="#8B5CF6", hover_color="#7C3AED", command=self.conectar_usb_directo)
        self.btn_usb_connect.pack()
        ToolTip(self.btn_usb_connect, "Fuerza la detección del teléfono conectado por cable.")

    def conectar_usb_directo(self):
        self.btn_usb_connect.configure(text="⏳ Buscando...", state="disabled")
        
        def task():
            run_adb(["kill-server"])
            run_adb(["start-server"])
            return run_adb(["devices"])
            
        def on_done(out):
            self._safe_after(0, lambda: self.btn_usb_connect.configure(text="Buscar Dispositivo USB", state="normal"))
            
            if not out:
                self.app.show_toast("Error crítico al ejecutar ADB", color="#EF4444")
                return
                
            lines = out.strip().split('\n')
            state = "missing"
            
            for line in lines:
                if "List" in line or not line.strip(): continue
                if "unauthorized" in line:
                    state = "unauthorized"
                    break
                elif "offline" in line:
                    state = "offline"
                    break
                elif "device" in line:
                    state = "connected"
                    break
                    
            if state == "connected":
                self.app.show_toast("¡Dispositivo USB detectado y listo!", color="#10B981")
            elif state == "unauthorized":
                utils.ShowInfo(self.app, "Autorización Pendiente", "El dispositivo está conectado pero bloqueado.\n\nPor favor, enciende la pantalla de tu celular y presiona 'Permitir depuración USB'.", True)
            elif state == "offline":
                self.app.show_toast("Dispositivo offline. Desconecta y reconecta el cable.", color="#F59E0B")
            else:
                utils.ShowInfo(self.app, "No Detectado", "No se encontró ningún teléfono.\n\n1. Revisa el cable USB.\n2. Asegúrate de tener activada la 'Depuración USB' en tu celular.", True)

        utils.run_async(task, on_done, self.app)