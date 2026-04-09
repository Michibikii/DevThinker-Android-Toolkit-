import customtkinter as ctk
from tkinter import filedialog
import utils
from utils import ToolTip, requires_device, run_async

class FramePackages(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        
        ctk.CTkLabel(self, text="Gestor de Paquetes", font=("Segoe UI", 24, "bold"), text_color="#F8FAFC").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self, text="Gestiona aplicaciones de terceros instaladas en el dispositivo.", font=("Segoe UI", 13), text_color="#94A3B8").pack(anchor="w", pady=(0, 15))
        
        c = ctk.CTkFrame(self, fg_color="#181D2B", corner_radius=12, border_width=1, border_color="#252D40")
        c.pack(fill="x", pady=5)
        
        self.btn_ref = ctk.CTkButton(c, text="🔄 Refrescar Lista", width=140, height=40, font=("Segoe UI", 13, "bold"), fg_color="#38BDF8", hover_color="#0284C7", command=self.refresh, text_color_disabled="#64748B")
        self.btn_ref.pack(side="left", padx=15, pady=15)
        ToolTip(self.btn_ref, "Recarga la lista de aplicaciones instaladas.")
        
        self.btn_install = ctk.CTkButton(c, text="📥 Instalar APK", width=140, height=40, font=("Segoe UI", 13, "bold"), fg_color="#10B981", hover_color="#059669", command=self.install_apk)
        self.btn_install.pack(side="left", padx=(0, 15), pady=15)
        ToolTip(self.btn_install, "Selecciona e instala un archivo .apk desde la PC.")
        
        self.lbl_status = ctk.CTkLabel(c, text="", font=("Segoe UI", 12), text_color="#94A3B8")
        self.lbl_status.pack(side="left", padx=10)
        
        self.entry_s = ctk.CTkEntry(c, placeholder_text="Buscar paquete...", width=200, height=40, font=("Segoe UI", 12), fg_color="#0B0F19", border_color="#252D40", text_color="#F8FAFC")
        self.entry_s.pack(side="right", padx=15, pady=15)
        self.entry_s.bind("<KeyRelease>", self.filter_list)
        
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, pady=10)
        self.items = []

    @requires_device
    def install_apk(self):
        f = filedialog.askopenfilename(filetypes=[("APK", "*.apk")])
        if f:
            self.app.show_toast("Instalando... por favor espera.", color="#38BDF8")
            run_async(lambda: self.app.adb_cmd(["install", "-r", f'"{f}"'], timeout=None),
                      lambda res: self.app.show_toast("Instalación Terminada"), 
                      self.app)

    @requires_device
    def refresh(self):
        self.btn_ref.configure(state="disabled")
        self.lbl_status.configure(text="Cargando...")
        
        def task():
            out = self.app.adb_cmd(["shell", "pm", "list", "packages", "-3"])
            return [l.replace("package:", "").strip() for l in out.split('\n') if l] if out else []
            
        run_async(task, self.finish, self.app)

    def finish(self, pkgs): 
        self.items = pkgs
        for w in self.scroll.winfo_children():
            w.destroy()
        for p in pkgs:
            self.add_row(p)
        self.btn_ref.configure(state="normal")
        self.lbl_status.configure(text=f"Encontradas {len(pkgs)} apps")

    def add_row(self, pkg):
        f = ctk.CTkFrame(self.scroll, fg_color="#181D2B", height=45, corner_radius=8, border_width=1, border_color="#252D40")
        f.pack(fill="x", pady=3, padx=5)
        
        ctk.CTkLabel(f, text=pkg, font=("Consolas", 13), text_color="#E2E8F0").pack(side="left", padx=15, pady=8)
        
        btn_clr = ctk.CTkButton(f, text="Borrar", width=70, height=32, font=("Segoe UI", 12, "bold"), fg_color="#F59E0B", hover_color="#D97706", command=lambda pkg_name=pkg: self.act(pkg_name, "borrar"))
        btn_clr.pack(side="right", padx=8, pady=6)
        ToolTip(btn_clr, "Borra los datos de la app.")
        
        btn_un = ctk.CTkButton(f, text="Desinstalar", width=85, height=32, font=("Segoe UI", 12, "bold"), fg_color="#EF4444", hover_color="#DC2626", command=lambda pkg_name=pkg: self.act(pkg_name, "desinstalar"))
        btn_un.pack(side="right", padx=5, pady=6)
        ToolTip(btn_un, "Elimina la app permanentemente.")

        btn_stop = ctk.CTkButton(f, text="⏹ Detener", width=80, height=32, font=("Segoe UI", 12, "bold"), fg_color="#8B5CF6", hover_color="#7C3AED", command=lambda pkg_name=pkg: self.act(pkg_name, "forzar"))
        btn_stop.pack(side="right", padx=5, pady=6)
        ToolTip(btn_stop, "Fuerza el cierre de la aplicación.")

        btn_launch = ctk.CTkButton(f, text="▶ Abrir", width=70, height=32, font=("Segoe UI", 12, "bold"), fg_color="#38BDF8", hover_color="#0284C7", command=lambda pkg_name=pkg: self.act(pkg_name, "abrir"))
        btn_launch.pack(side="right", padx=8, pady=6)
        ToolTip(btn_launch, "Lanza la aplicación en el dispositivo.")

    @requires_device
    def act(self, pkg, action):
        if action == "abrir":
            run_async(lambda: self.app.adb_cmd(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"]))
            self.app.show_toast(f"Abriendo {pkg}...", color="#38BDF8")
            return
        
        if action == "forzar":
            run_async(lambda: self.app.adb_cmd(["shell", "am", "force-stop", pkg]))
            self.app.show_toast(f"Cerrando {pkg}...", color="#8B5CF6")
            return

        if utils.AskYesNo(self.app, "Confirmar", f"¿{action.title()} {pkg}?").get():
            cmd = ["uninstall", pkg] if action == "desinstalar" else ["shell", "pm", "clear", pkg]
            def callback(res):
                self.app.show_toast("Hecho")
                if action == "desinstalar":
                    self.refresh()
                
            run_async(lambda: self.app.adb_cmd(cmd), callback, self.app)

    def filter_list(self, e): 
        q = self.entry_s.get().lower()
        for w in self.scroll.winfo_children():
            w.destroy()
        for p in self.items:
            if q in p.lower():
                self.add_row(p)