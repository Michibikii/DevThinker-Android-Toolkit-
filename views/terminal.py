import customtkinter as ctk
import shlex
import utils
from utils import run_async

class FrameTerminal(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        
        ctk.CTkLabel(self, text="Terminal ADB", font=("Segoe UI", 24, "bold"), text_color="#F8FAFC").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self, text="Ejecuta comandos directamente en el dispositivo. No necesitas escribir 'adb', solo el comando (ej. shell ls).", font=("Segoe UI", 13), text_color="#94A3B8").pack(anchor="w", pady=(0, 15))
        
        self.txt_out = ctk.CTkTextbox(self, font=("Consolas", 13), fg_color="#0B0F19", text_color="#E2E8F0", border_width=1, border_color="#252D40", corner_radius=12)
        self.txt_out.pack(fill="both", expand=True, pady=(0, 15))
        self.txt_out.configure(state="disabled")
        
        self.txt_out.tag_config("cmd", foreground="#38BDF8")
        self.txt_out.tag_config("err", foreground="#EF4444")
        self.txt_out.tag_config("sys", foreground="#F59E0B")
        
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x")
        
        ctk.CTkLabel(input_frame, text="> adb", font=("Consolas", 15, "bold"), text_color="#10B981").pack(side="left", padx=(0, 10))
        
        self.entry_cmd = ctk.CTkEntry(input_frame, font=("Consolas", 14), height=45, fg_color="#181D2B", border_color="#252D40", text_color="#F8FAFC")
        self.entry_cmd.pack(side="left", fill="x", expand=True)
        self.entry_cmd.bind("<Return>", self.execute_command)
        
        btn_run = ctk.CTkButton(input_frame, text="Ejecutar", font=("Segoe UI", 13, "bold"), height=45, width=110, fg_color="#38BDF8", hover_color="#0284C7", command=self.execute_command)
        btn_run.pack(side="left", padx=(10, 0))
        
        btn_clear = ctk.CTkButton(input_frame, text="Limpiar", font=("Segoe UI", 13, "bold"), height=45, width=100, fg_color="#475569", hover_color="#334155", command=self.clear_terminal)
        btn_clear.pack(side="left", padx=(10, 0))

    def append_output(self, text, tag=None):
        self.txt_out.configure(state="normal")
        if tag:
            self.txt_out.insert("end", text + "\n", tag)
        else:
            self.txt_out.insert("end", text + "\n")
        self.txt_out.see("end")
        self.txt_out.configure(state="disabled")

    def clear_terminal(self):
        self.txt_out.configure(state="normal")
        self.txt_out.delete("1.0", "end")
        self.txt_out.configure(state="disabled")

    def execute_command(self, event=None):
        raw_cmd = self.entry_cmd.get().strip()
        if not raw_cmd:
            return
            
        self.entry_cmd.delete(0, "end")
        
        if raw_cmd.startswith("adb "):
            raw_cmd = raw_cmd[4:]
            
        self.append_output(f"\n> adb {raw_cmd}", "cmd")
        
        if not self.app.current_device_id and raw_cmd not in ["devices", "start-server", "kill-server", "version", "help"]:
            self.append_output("Error: Ningún dispositivo conectado o autorizado.", "err")
            return

        try:
            cmd_args = shlex.split(raw_cmd)
        except Exception as e:
            self.append_output(f"Error de sintaxis en el comando: {e}", "err")
            return

        self.entry_cmd.configure(state="disabled")
        
        def task():
            if raw_cmd in ["devices", "start-server", "kill-server", "version", "help"]:
                return utils.run_adb(cmd_args, timeout=None)
            else:
                return self.app.adb_cmd(cmd_args, timeout=None)
            
        def on_done(res):
            if res is not None:
                if res.strip() == "":
                    self.append_output("[Comando ejecutado sin salida en consola]", "sys")
                else:
                    self.append_output(res)
            else:
                self.append_output("Error interno: Falló la ejecución del comando o excedió el tiempo límite.", "err")
                
            self.entry_cmd.configure(state="normal")
            self.entry_cmd.focus()
            
        utils.run_async(task, on_done, self.app)