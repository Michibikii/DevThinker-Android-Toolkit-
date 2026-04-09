import customtkinter as ctk
import subprocess
import shutil
import os
from datetime import datetime
from tkinter import filedialog
import utils
from utils import run_adb, ToolTip, requires_device, run_async

class FrameTools(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        
        ctk.CTkLabel(self, text="Utilidades", font=("Segoe UI", 24, "bold"), text_color="#F8FAFC").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self, text="Herramientas rápidas y gestión del motor interno.", font=("Segoe UI", 13), text_color="#94A3B8").pack(anchor="w", pady=(0, 15))
        
        self.grid_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.grid_container.pack(fill="both", expand=True)
        self.grid_container.grid_columnconfigure(0, weight=1)
        self.grid_container.grid_columnconfigure(1, weight=1)
        
        self.create_adb_card(0, 0)
        
        self.add("📸 Captura", "Guardar en PC", self.screenshot, 1, 0, "Toma una captura de pantalla y la guarda como archivo PNG.")
        self.add("⌨️ Ingresar Texto", "Escribir al teléfono", self.input_text, 1, 1, "Escribe texto desde tu computadora directamente al teléfono.")
        self.add("👆 Mostrar Toques", "Alternar toques", self.toggle_taps, 2, 0, "Muestra/Oculta los puntos blancos al tocar la pantalla.")
        self.add("🔄 Reiniciar", "Reiniciar Dispositivo", self.reboot, 2, 1, "Reinicia el teléfono conectado.")
        self.add("📱 Scrcpy", "Espejar Pantalla", self.scrcpy_panel, 3, 0, "Abre un panel avanzado para configurar y lanzar 'scrcpy'.")
        self.add("🌐 Abrir Enlace", "Navegador del teléfono", self.open_url, 3, 1, "Abre una página web en el navegador del dispositivo.")
        self.add("📺 Pantalla On/Off", "Botón de encendido", self.toggle_screen, 4, 0, "Simula presionar el botón de encendido del teléfono.")
        self.add("🏠 Botón Inicio", "Ir a inicio", self.home_button, 4, 1, "Simula presionar el botón de Inicio (Home) del teléfono.")
        self.add("🔙 Botón Atrás", "Retroceder menú", self.back_button, 5, 0, "Simula presionar el botón físico de Atrás del teléfono.")

    def add(self, t, s, cmd, r, c, tip):
        f = ctk.CTkFrame(self.grid_container, fg_color="#181D2B", corner_radius=12, border_width=1, border_color="#252D40")
        f.grid(row=r, column=c, padx=10, pady=10, sticky="ew")
        f.bind("<Button-1>", lambda e: cmd())
        l1 = ctk.CTkLabel(f, text=t, font=("Segoe UI", 15, "bold"), text_color="#F8FAFC")
        l1.pack(anchor="w", padx=20, pady=(20,5))
        l1.bind("<Button-1>", lambda e: cmd())
        l2 = ctk.CTkLabel(f, text=s, font=("Segoe UI", 12), text_color="#94A3B8")
        l2.pack(anchor="w", padx=20, pady=(0,15))
        l2.bind("<Button-1>", lambda e: cmd())
        btn = ctk.CTkButton(f, text="Ejecutar", height=38, font=("Segoe UI", 13, "bold"), fg_color="#38BDF8", hover_color="#0284C7", command=cmd)
        btn.pack(fill="x", padx=20, pady=(0,20))
        ToolTip(btn, tip)
        ToolTip(f, tip)

    def create_adb_card(self, r, c):
        self.adb_card = ctk.CTkFrame(self.grid_container, fg_color="#0B0F19", corner_radius=12, border_width=1, border_color="#38BDF8")
        self.adb_card.grid(row=r, column=c, columnspan=2, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.adb_card, text="⚙️ Motor ADB", font=("Segoe UI", 16, "bold"), text_color="#F8FAFC").pack(anchor="w", padx=20, pady=(20,5))
        ctk.CTkLabel(self.adb_card, text="Componente necesario para el funcionamiento del programa.", font=("Segoe UI", 13), text_color="#94A3B8").pack(anchor="w", padx=20, pady=(0,15))
        
        self.adb_btn_frame = ctk.CTkFrame(self.adb_card, fg_color="transparent")
        self.adb_btn_frame.pack(fill="x", padx=20, pady=(0,20))
        
        self.refresh_adb_card_ui()

    def refresh_adb_card_ui(self):
        for w in self.adb_btn_frame.winfo_children():
            w.destroy()
        
        if not utils.ADB_PATH or not os.path.exists(utils.ADB_PATH):
            btn_inst = ctk.CTkButton(self.adb_btn_frame, text="📥 Instalar ADB", height=45, font=("Segoe UI", 14, "bold"), fg_color="#10B981", hover_color="#059669", command=self.prompt_install)
            btn_inst.pack(fill="x", expand=True)
            ToolTip(btn_inst, "Descarga e instala los binarios oficiales para hacer funcionar la app.")
            self.app.adb_update_available = False
        else:
            btn_restart = ctk.CTkButton(self.adb_btn_frame, text="💀 Reiniciar", width=110, height=40, font=("Segoe UI", 13, "bold"), fg_color="#8B5CF6", hover_color="#7C3AED", command=self.kill_adb)
            btn_restart.pack(side="left", padx=(0,8))
            ToolTip(btn_restart, "Mata y reinicia el servidor ADB de fondo. Úsalo si falla la conexión.")

            btn_re = ctk.CTkButton(self.adb_btn_frame, text="Reinstalar", width=110, height=40, font=("Segoe UI", 13, "bold"), fg_color="#F59E0B", hover_color="#D97706", command=self.prompt_install)
            btn_re.pack(side="left", padx=(0,8))
            ToolTip(btn_re, "Vuelve a descargar los binarios de ADB.")
            
            btn_un = ctk.CTkButton(self.adb_btn_frame, text="Desinstalar", width=110, height=40, font=("Segoe UI", 13, "bold"), fg_color="#EF4444", hover_color="#DC2626", command=self.uninstall_adb)
            btn_un.pack(side="left", padx=(0,15))
            ToolTip(btn_un, "Elimina ADB de tu PC.")
            
            self.btn_upd = ctk.CTkButton(self.adb_btn_frame, text="Buscando actualizaciones...", height=40, font=("Segoe UI", 13, "bold"), state="disabled", fg_color="#1E293B", text_color_disabled="#64748B")
            self.btn_upd.pack(side="left", fill="x", expand=True)
            
            utils.run_async(utils.check_adb_update, self._update_btn_state, self.app)

    def _update_btn_state(self, res):
        has_update, new_ver = res
        if has_update:
            self.btn_upd.configure(text="Actualización Disponible", fg_color="#38BDF8", hover_color="#0284C7", state="normal", text_color="#0B0F19", command=self.prompt_install)
            ToolTip(self.btn_upd, "Una versión oficial más reciente está lista para descargar.")
            self.app.adb_update_available = True
        else:
            self.btn_upd.configure(text="ADB Actualizado", fg_color="#10B981", state="disabled", text_color_disabled="#F8FAFC")
            self.app.adb_update_available = False

    def kill_adb(self): 
        self.app.show_toast("Reiniciando ADB en segundo plano...", color="#8B5CF6")
        def task():
            run_adb(["kill-server"])
            run_adb(["start-server"])
        run_async(task, lambda res: self.app.show_toast("ADB Reiniciado con éxito", color="#10B981"), self.app)

    def uninstall_adb(self):
        if utils.AskYesNo(self.app, "Confirmar", "¿Eliminar ADB del sistema? El programa dejará de funcionar hasta que lo reinstales.").get():
            utils.uninstall_adb()
            self.app.show_toast("ADB Desinstalado exitosamente", "#EF4444")
            self.refresh_adb_card_ui()

    def prompt_install(self):
        self.install_win = ctk.CTkToplevel(self)
        self.install_win.title("Instalar ADB")
        self.install_win.configure(fg_color="#0B0F19")
        utils.center_toplevel(self.install_win, self.app, 400, 260)
        self.install_win.attributes("-topmost", True)
        self.install_win.transient(self.app)
        
        ctk.CTkLabel(self.install_win, text="Opciones de Instalación", font=("Segoe UI", 18, "bold"), text_color="#F8FAFC").pack(pady=(20, 5))
        ctk.CTkLabel(self.install_win, text="Elige dónde instalar los binarios oficiales de Google.", font=("Segoe UI", 13), text_color="#94A3B8").pack()
        
        self.prog_bar = ctk.CTkProgressBar(self.install_win, height=12, fg_color="#1E293B", progress_color="#38BDF8")
        self.prog_bar.set(0)
        self.lbl_prog = ctk.CTkLabel(self.install_win, text="", font=("Segoe UI", 12), text_color="#94A3B8")
        
        self.f_btns = ctk.CTkFrame(self.install_win, fg_color="transparent")
        self.f_btns.pack(pady=20)
        
        ctk.CTkButton(self.f_btns, text="Ruta Automática (Recomendado)", font=("Segoe UI", 13, "bold"), height=40, fg_color="#10B981", hover_color="#059669", command=lambda: self.start_download(None)).pack(pady=5, fill="x")
        ctk.CTkButton(self.f_btns, text="Elegir Ruta Manual", font=("Segoe UI", 13, "bold"), height=40, fg_color="#8B5CF6", hover_color="#7C3AED", command=lambda: self.start_download(filedialog.askdirectory())).pack(pady=5, fill="x")

    def start_download(self, path):
        if path == "":
            return 
        
        self.f_btns.destroy()
        self.prog_bar.pack(fill="x", padx=30, pady=(20, 10))
        self.lbl_prog.pack()
        
        def progress(dl, total, speed, state_msg):
            self.app.after(0, lambda: self._update_progress_ui(dl, total, speed, state_msg))
            
        def task():
            return utils.download_and_install_adb(path, progress)
            
        def on_done(success):
            self.install_win.destroy()
            if success:
                self.app.show_toast("¡ADB Instalado Correctamente!", color="#10B981")
                run_adb(["start-server"])
                self.refresh_adb_card_ui()
            else:
                self.app.show_toast("Error en la instalación de red", color="#EF4444")
                
        utils.run_async(task, on_done, self.app)

    def _update_progress_ui(self, dl, total, speed, state_msg):
        pct = dl/total if total > 0 else 0
        self.prog_bar.set(pct)
        if total > 0:
            self.lbl_prog.configure(text=f"{state_msg}\n{dl/1024/1024:.1f} MB / {total/1024/1024:.1f} MB  ({speed:.1f} MB/s)")
        else:
            self.lbl_prog.configure(text=state_msg)

    @requires_device
    def screenshot(self): 
        t = datetime.now().strftime("%H%M%S")
        self.app.adb_cmd(["shell", "screencap", "-p", "/sdcard/s.png"])
        self.app.adb_cmd(["pull", "/sdcard/s.png", f"shot_{t}.png"])
        self.app.show_toast("Captura Guardada exitosamente", color="#38BDF8")

    @requires_device
    def reboot(self): 
        if utils.AskYesNo(self.app, "Reiniciar", "¿Seguro que quieres reiniciar el teléfono?").get():
            self.app.adb_cmd(["reboot"])

    @requires_device
    def input_text(self): 
        txt = utils.AskString(self.app, "Ingresar", "Texto:").get()
        if txt: 
            safe_txt = txt.replace(" ", "%s").replace('"', '\\"') 
            self.app.adb_cmd(["shell", "input", "text", f'"{safe_txt}"'])
            self.app.show_toast("Texto inyectado", color="#38BDF8")

    @requires_device
    def toggle_taps(self):
        v = "0" if "1" in self.app.adb_cmd(["shell", "settings", "get", "system", "show_touches"]) else "1"
        self.app.adb_cmd(["shell", "settings", "put", "system", "show_touches", v])
        self.app.show_toast(f"Toques en pantalla: {'Activados' if v=='1' else 'Desactivados'}", color="#10B981" if v=='1' else "#EF4444")

    @requires_device
    def scrcpy_panel(self):
        if not shutil.which("scrcpy"): 
            self.app.show_toast("Error: No se encontró Scrcpy en el PATH", color="#EF4444")
            return
            
        win = ctk.CTkToplevel(self)
        win.title("Control Avanzado de Scrcpy")
        win.configure(fg_color="#0B0F19")
        utils.center_toplevel(win, self.app, 400, 450)
        win.attributes("-topmost", True)
        win.transient(self.app)

        ctk.CTkLabel(win, text="Configuración de Espejo", font=("Segoe UI", 18, "bold"), text_color="#F8FAFC").pack(pady=(20, 5))
        ctk.CTkLabel(win, text="Ajusta los parámetros antes de transmitir.", font=("Segoe UI", 13), text_color="#94A3B8").pack(pady=(0, 20))

        f_opts = ctk.CTkFrame(win, fg_color="#181D2B", corner_radius=12, border_width=1, border_color="#252D40")
        f_opts.pack(fill="x", padx=20, pady=10)

        chk_off = ctk.CTkSwitch(f_opts, text="Apagar pantalla del celular", font=("Segoe UI", 13), fg_color="#475569", progress_color="#38BDF8")
        chk_off.pack(anchor="w", padx=20, pady=(20, 10))

        chk_awake = ctk.CTkSwitch(f_opts, text="Mantener dispositivo despierto", font=("Segoe UI", 13), fg_color="#475569", progress_color="#38BDF8")
        chk_awake.pack(anchor="w", padx=20, pady=10)
        chk_awake.select()

        chk_audio = ctk.CTkSwitch(f_opts, text="Desactivar transmisión de audio", font=("Segoe UI", 13), fg_color="#475569", progress_color="#38BDF8")
        chk_audio.pack(anchor="w", padx=20, pady=10)

        chk_fps = ctk.CTkSwitch(f_opts, text="Limitar a 30 FPS (Mejor para Wi-Fi)", font=("Segoe UI", 13), fg_color="#475569", progress_color="#38BDF8")
        chk_fps.pack(anchor="w", padx=20, pady=(10, 20))

        def launch():
            cmd = ["scrcpy", "-s", self.app.current_device_id]
            if chk_off.get():
                cmd.append("--turn-screen-off")
            if chk_awake.get():
                cmd.append("--stay-awake")
            if chk_audio.get():
                cmd.append("--no-audio")
            if chk_fps.get():
                cmd.extend(["--max-fps", "30"])

            subprocess.Popen(cmd, shell=True)
            win.destroy()

        ctk.CTkButton(win, text="▶ Iniciar Transmisión", font=("Segoe UI", 14, "bold"), height=45, fg_color="#10B981", hover_color="#059669", command=launch).pack(fill="x", padx=20, pady=20)

    @requires_device
    def open_url(self):
        url = utils.AskString(self.app, "Abrir Enlace", "URL (ej. google.com):").get()
        if url:
            if not url.startswith("http"):
                url = "https://" + url
            self.app.adb_cmd(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", f'"{url}"'])
            self.app.show_toast("Abriendo enlace...", color="#38BDF8")

    @requires_device
    def toggle_screen(self):
        self.app.adb_cmd(["shell", "input", "keyevent", "26"])
        self.app.show_toast("Botón de encendido simulado", color="#38BDF8")

    @requires_device
    def home_button(self):
        self.app.adb_cmd(["shell", "input", "keyevent", "3"])
        self.app.show_toast("Botón de Inicio simulado", color="#38BDF8")

    @requires_device
    def back_button(self):
        self.app.adb_cmd(["shell", "input", "keyevent", "4"])
        self.app.show_toast("Botón de Atrás simulado", color="#38BDF8")