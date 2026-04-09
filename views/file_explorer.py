import customtkinter as ctk
import re
import os
from tkinter import filedialog
import utils
from utils import ToolTip, requires_device, run_async

class FrameFileExplorer(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.current_path = "/sdcard/"

        ctk.CTkLabel(self, text="Explorador de Archivos", font=("Segoe UI", 24, "bold"), text_color="#F8FAFC").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self, text="Navega, extrae y envía archivos al dispositivo.", font=("Segoe UI", 13), text_color="#94A3B8").pack(anchor="w", pady=(0, 15))

        nav_frame = ctk.CTkFrame(self, fg_color="#181D2B", corner_radius=12, border_width=1, border_color="#252D40")
        nav_frame.pack(fill="x", pady=5)

        self.btn_up = ctk.CTkButton(nav_frame, text="⬆ Volver", width=90, height=40, font=("Segoe UI", 13, "bold"), fg_color="#475569", hover_color="#334155", command=self.go_up)
        self.btn_up.pack(side="left", padx=15, pady=15)
        ToolTip(self.btn_up, "Subir un directorio hacia atrás.")

        self.entry_path = ctk.CTkEntry(nav_frame, font=("Consolas", 13), height=40, fg_color="#0B0F19", border_color="#252D40", text_color="#E2E8F0")
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.entry_path.insert(0, self.current_path)
        self.entry_path.bind("<Return>", lambda e: self.load_files())

        self.btn_push = ctk.CTkButton(nav_frame, text="⬆️ Subir Archivo", width=130, height=40, font=("Segoe UI", 13, "bold"), fg_color="#10B981", hover_color="#059669", command=self.upload_file)
        self.btn_push.pack(side="right", padx=15, pady=15)
        ToolTip(self.btn_push, "Envía un archivo desde tu PC a esta carpeta en el teléfono.")

        self.btn_refresh = ctk.CTkButton(nav_frame, text="🔄 Actualizar", width=110, height=40, font=("Segoe UI", 13, "bold"), fg_color="#38BDF8", hover_color="#0284C7", command=self.load_files)
        self.btn_refresh.pack(side="right", padx=(0, 15), pady=15)
        ToolTip(self.btn_refresh, "Recarga la lista de archivos de la carpeta actual.")

        self.scroll_files = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_files.pack(fill="both", expand=True, pady=10)

    @requires_device
    def load_files(self):
        self.app.show_toast("Cargando archivos...", color="#38BDF8")
        path = self.entry_path.get()
        run_async(lambda: self.app.adb_cmd(["shell", "ls", "-lA", f'"{path}"']), self._update_ui_with_files, self.app)

    def _update_ui_with_files(self, adb_output):
        for widget in self.scroll_files.winfo_children():
            widget.destroy()

        if not adb_output or "Permission denied" in adb_output:
            ctk.CTkLabel(self.scroll_files, text="Carpeta vacía o sin permisos (requiere root).", font=("Segoe UI", 13), text_color="#64748B").pack(pady=20)
            return

        pattern = re.compile(r'^([dl\-])[^\s]+\s+.*?\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|\w{3}\s+\d{2}\s+(?:\d{4}|\d{2}:\d{2}))\s+(.*)$')

        for line in adb_output.split('\n'):
            line = line.strip()
            if not line or line.startswith("total"):
                continue
            
            match = pattern.match(line)
            if match:
                f_type, f_date, f_name = match.group(1), match.group(2), match.group(3)
                if f_type == 'l' and " -> " in f_name:
                    f_name = f_name.split(" -> ")[0]
                self.create_file_row(f_type, f_name, f_date)
            else:
                if "No such file" not in line:
                    ctk.CTkLabel(self.scroll_files, text=line, text_color="#EF4444", font=("Consolas", 11)).pack(anchor="w")

    def create_file_row(self, f_type, f_name, f_date):
        row = ctk.CTkFrame(self.scroll_files, fg_color="#181D2B", height=45, corner_radius=8, border_width=1, border_color="#252D40")
        row.pack(fill="x", pady=3, padx=5)
        
        if f_type in ['d', 'l']:
            icon, color, action = "📁", "#FBBF24", lambda: self.enter_folder(f_name)
        else:
            icon, color, action = "📄", "#E2E8F0", lambda: self.download_file(f_name) 
            
        btn_icon = ctk.CTkButton(row, text=icon, width=35, height=35, fg_color="transparent", text_color=color, hover_color="#1E293B", font=("Segoe UI Emoji", 18), command=action)
        btn_icon.pack(side="left", padx=8, pady=5)
        
        lbl_name = ctk.CTkLabel(row, text=f_name, font=("Segoe UI", 14), text_color=color, anchor="w")
        lbl_name.pack(side="left", padx=5, fill="x", expand=True)
        lbl_name.bind("<Double-Button-1>", lambda e, act=action: act())
        
        ctk.CTkLabel(row, text=f_date, font=("Consolas", 12), text_color="#64748B").pack(side="right", padx=20)
        
        btn_del = ctk.CTkButton(row, text="🗑️", width=40, height=32, fg_color="#EF4444", hover_color="#DC2626", command=lambda fn=f_name, ft=f_type: self.delete_file(fn, ft))
        btn_del.pack(side="right", padx=8)
        ToolTip(btn_del, "Eliminar permanentemente del dispositivo.")

        if f_type == '-':
            btn_ext = ctk.CTkButton(row, text="📥 Extraer", width=80, height=32, font=("Segoe UI", 12, "bold"), fg_color="#38BDF8", hover_color="#0284C7", command=action)
            btn_ext.pack(side="right", padx=5)
            ToolTip(btn_ext, "Descargar este archivo a tu computadora.")

    def delete_file(self, f_name, f_type):
        if utils.AskYesNo(self.app, "Confirmar", f"¿Eliminar '{f_name}' permanentemente?").get():
            target = f"{self.entry_path.get().rstrip('/')}/{f_name}"
            
            def on_delete_done(res):
                if res and ("Read-only" in res or "Permission denied" in res or "No such file" in res):
                    self.app.show_toast("Error de permisos/sistema", color="#F59E0B")
                else:
                    self.app.show_toast("Eliminado", color="#EF4444")
                self.load_files()
                
            run_async(lambda: self.app.adb_cmd(["shell", "rm", "-rf", f'"{target}"']), on_delete_done, self.app)

    def enter_folder(self, folder_name):
        new_path = f"{self.entry_path.get().rstrip('/')}/{folder_name}/"
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, new_path)
        self.load_files()

    @requires_device
    def download_file(self, file_name):
        remote_path = f"{self.entry_path.get().rstrip('/')}/{file_name}"
        local_path = filedialog.asksaveasfilename(initialfile=file_name, title="Guardar como...")
        
        if local_path:
            self.app.show_toast(f"Descargando {file_name}...", color="#38BDF8")
            def callback(res):
                if res and "error" not in res.lower():
                    self.app.show_toast("¡Guardado con éxito!")
                else:
                    self.app.show_toast("Error al descargar", color="#EF4444")
            run_async(lambda: self.app.adb_cmd(["pull", remote_path, local_path], timeout=None), callback, self.app)

    @requires_device
    def upload_file(self):
        local_path = filedialog.askopenfilename(title="Seleccionar archivo")
        if local_path:
            file_name = os.path.basename(local_path)
            remote_path = f"{self.entry_path.get().rstrip('/')}/{file_name}"
            
            self.app.show_toast(f"Subiendo {file_name}...", color="#38BDF8")
            def callback(res):
                if res and "error" not in res.lower():
                    self.app.show_toast("¡Subido con éxito!")
                    self.load_files()
                else:
                    self.app.show_toast("Error al subir", color="#EF4444")
            run_async(lambda: self.app.adb_cmd(["push", local_path, remote_path], timeout=None), callback, self.app)

    def go_up(self):
        current = self.entry_path.get()
        if current not in ["/", "/sdcard/"]:
            new_path = "/" + "/".join([p for p in current.split("/") if p][:-1]) + "/"
            if new_path == "//":
                new_path = "/"
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, new_path)
            self.load_files()