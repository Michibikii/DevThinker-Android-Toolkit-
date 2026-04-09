import customtkinter as ctk
import threading
import subprocess
import utils 
from utils import ToolTip

class FrameLiveLog(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.process = None
        self.is_running = False

        ctk.CTkLabel(self, text="Logcat en Vivo", font=("Segoe UI", 24, "bold"), text_color="#F8FAFC").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self, text="Ve todo lo que pasa en tu teléfono en tiempo real.", font=("Segoe UI", 13), text_color="#94A3B8").pack(anchor="w", pady=(0, 15))
        
        c = ctk.CTkFrame(self, fg_color="#181D2B", corner_radius=12, border_width=1, border_color="#252D40")
        c.pack(fill="x", pady=5)
        
        self.btn_toggle = ctk.CTkButton(c, text="▶ Iniciar", width=120, height=40, font=("Segoe UI", 13, "bold"), fg_color="#10B981", hover_color="#059669", command=self.toggle)
        self.btn_toggle.pack(side="left", padx=15, pady=15)
        ToolTip(self.btn_toggle, "Empieza a leer el flujo de registros del sistema del teléfono.")
        
        btn_clear = ctk.CTkButton(c, text="🧹 Limpiar", width=110, height=40, font=("Segoe UI", 13, "bold"), fg_color="#F59E0B", hover_color="#D97706", command=self.clear)
        btn_clear.pack(side="left", padx=5)
        ToolTip(btn_clear, "Limpia la pantalla y el historial interno del teléfono.")
        
        btn_copy = ctk.CTkButton(c, text="📋 Copiar", width=110, height=40, font=("Segoe UI", 13, "bold"), fg_color="#38BDF8", hover_color="#0284C7", command=self.copy_all)
        btn_copy.pack(side="left", padx=5)
        ToolTip(btn_copy, "Copia todo el texto al portapapeles (Pégalo en Análisis de Errores).")
        
        self.chk_errors = ctk.CTkCheckBox(c, text="Solo Errores", font=("Segoe UI", 12), text_color="#E2E8F0", fg_color="#38BDF8", hover_color="#0284C7", onvalue=True, offvalue=False)
        self.chk_errors.pack(side="right", padx=15)
        self.chk_errors.select()
        ToolTip(self.chk_errors, "Recomendado: Oculta información irrelevante, muestra solo Crashes y Advertencias.")
        
        self.entry_filter = ctk.CTkEntry(c, placeholder_text="Filtro (ej. instagram)", width=180, height=40, font=("Segoe UI", 12), fg_color="#0B0F19", border_color="#252D40", text_color="#F8FAFC")
        self.entry_filter.pack(side="right", padx=5)
        ToolTip(self.entry_filter, "Muestra solo las líneas que contienen esta palabra.")

        self.txt_log = ctk.CTkTextbox(self, font=("Consolas", 12), text_color="#E2E8F0", fg_color="#0B0F19", border_width=1, border_color="#252D40", corner_radius=12)
        self.txt_log.pack(fill="both", expand=True, pady=15)
        self.txt_log.tag_config("error", foreground="#EF4444")
        self.txt_log.tag_config("warn", foreground="#F59E0B")
        self.txt_log.configure(state="disabled")

    def toggle(self):
        if self.is_running:
            self.stop()
        else:
            self.start()
    
    def start(self):
        if not self.app.current_device_id: 
            self.app.show_toast("Sin Dispositivo Conectado", color="#EF4444")
            return
            
        self.is_running = True
        self.btn_toggle.configure(text="⏹ Detener", fg_color="#EF4444", hover_color="#DC2626")
        
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")
        
        cmd = [utils.ADB_PATH, "-s", self.app.current_device_id, "logcat", "-v", "time"]
        threading.Thread(target=self.run, args=(cmd,), daemon=True).start()

    def stop(self):
        self.is_running = False
        if self.process: 
            try:
                self.process.terminate()
            except:
                pass
        try:
            self.btn_toggle.configure(text="▶ Iniciar", fg_color="#10B981", hover_color="#059669")
        except:
            pass

    def run(self, cmd):
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, startupinfo=si, encoding='utf-8', errors='replace')
            for line in self.process.stdout:
                if not self.is_running:
                    break
                
                is_error_or_warn = (" E/" in line or "FATAL" in line or " W/" in line)
                if self.chk_errors.get() and not is_error_or_warn:
                    continue
                    
                f = self.entry_filter.get().lower()
                if f and f not in line.lower():
                    continue
                
                tags = "error" if (" E/" in line or "FATAL" in line) else "warn" if " W/" in line else "normal"
                try:
                    self.app.after(0, self._safe_insert, line, tags)
                except:
                    pass
        except:
            pass
        self.stop()

    def _safe_insert(self, line, tags):
        try:
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", line, tags)
            if self.txt_log.yview()[1] > 0.9:
                self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        except:
            pass

    def clear(self): 
        self.app.adb_cmd(["logcat", "-c"])
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")
    
    def copy_all(self):
        self.clipboard_clear()
        self.clipboard_append(self.txt_log.get("1.0", "end"))
        self.app.show_toast("¡Log copiado al portapapeles!", color="#38BDF8")