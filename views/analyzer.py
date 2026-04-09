import customtkinter as ctk
import re
from utils import ToolTip

class FrameAnalyzer(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        
        ctk.CTkLabel(self, text="Análisis Profundo de Errores", font=("Segoe UI", 24, "bold"), text_color="#F8FAFC").pack(anchor="w", pady=(0, 5))
        
        info_text = (
            "Cómo usar:\n"
            "1. Si tu app crasheó, ve a la pestaña 'Logcat en Vivo' y copia el texto rojo de error.\n"
            "2. Pega ese texto abajo.\n"
            "3. Haz clic en 'Analizar Traza' para que identifique el archivo y línea responsable."
        )
        ctk.CTkLabel(self, text=info_text, font=("Segoe UI", 13), text_color="#94A3B8", justify="left").pack(anchor="w", pady=(0, 15))
        
        self.txt_input = ctk.CTkTextbox(self, height=120, text_color="#64748B", fg_color="#0B0F19", border_width=1, border_color="#252D40", corner_radius=12, font=("Consolas", 12))
        self.txt_input.pack(fill="x", pady=10)
        self.txt_input.insert("1.0", "[Pega el registro de error o stack trace aquí...]")
        
        self.txt_input.bind("<FocusIn>", self.on_focus)
        self.txt_input.bind("<FocusOut>", self.on_unfocus)
        
        btn = ctk.CTkButton(self, text="⚡ Analizar Traza", width=160, height=40, font=("Segoe UI", 13, "bold"), fg_color="#38BDF8", hover_color="#0284C7", command=self.analyze)
        btn.pack(anchor="w", pady=10)
        ToolTip(btn, "Escanea el texto en busca de 'FATAL EXCEPTION' y explica la causa de forma sencilla.")
        
        ctk.CTkLabel(self, text="Reporte de Análisis:", font=("Segoe UI", 15, "bold"), text_color="#F8FAFC").pack(anchor="w", pady=(20, 8))
        self.res = ctk.CTkTextbox(self, fg_color="#0B0F19", text_color="#E2E8F0", border_width=1, border_color="#252D40", corner_radius=12, font=("Consolas", 13))
        self.res.pack(fill="both", expand=True, pady=5)
        self.res.configure(state="disabled")

    def on_focus(self, event):
        if self.txt_input.get("1.0", "end-1c") == "[Pega el registro de error o stack trace aquí...]":
            self.txt_input.delete("1.0", "end")
            self.txt_input.configure(text_color="#E2E8F0")

    def on_unfocus(self, event):
        if not self.txt_input.get("1.0", "end-1c").strip():
            self.txt_input.configure(text_color="#64748B")
            self.txt_input.insert("1.0", "[Pega el registro de error o stack trace aquí...]")

    def analyze(self):
        log = self.txt_input.get("1.0", "end")
        
        self.res.configure(state="normal")
        
        if "Pega el registro" in log: 
            self.res.delete("1.0", "end")
            self.res.insert("end", "⚠️ Por favor, pega un registro primero.")
            self.res.configure(state="disabled")
            return

        report = "✅ No se detectó ningún crash en el texto proporcionado."
        if "FATAL" in log or "Exception" in log:
            report = "🔥 CRASH DETECTADO\n" + "-"*40 + "\n"
            lines = log.split('\n')
            
            root_cause = "Error Desconocido"
            for line in lines:
                if "Caused by:" in line:
                    root_cause = line.split("Caused by:")[1].strip()
            
            if root_cause == "Error Desconocido":
                match = re.search(r"FATAL EXCEPTION:.*?\n.*?(\w+\.\w+Exception)", log, re.DOTALL)
                if match:
                    root_cause = match.group(1)

            loc = "Framework del Sistema (¿No es tu código?)"
            for line in lines:
                if "at " in line and "(" in line:
                    if not any(x in line for x in ["android.", "java.", "com.android", "zygote", "androidx."]):
                        loc = line.strip().replace("at ", "")
                        break
            
            report += f"❌ CAUSA: {root_cause}\n\n📍 ARCHIVO SOSPECHOSO:\n   {loc}\n"
            
            if "NullPointer" in root_cause:
                report += "\n💡 EXPLICACIÓN: Intentaste usar una variable que estaba vacía (null). Verifica si inicializaste tus vistas o variables."
            if "IndexOutOfBounds" in root_cause:
                report += "\n💡 EXPLICACIÓN: Intentaste obtener un ítem de una lista, pero el índice era demasiado grande (o la lista estaba vacía)."
            if "ActivityNotFound" in root_cause:
                report += "\n💡 EXPLICACIÓN: Intentaste abrir una pantalla (Activity) que no está declarada en el AndroidManifest.xml."

        self.res.delete("1.0", "end")
        self.res.insert("end", report)
        self.res.configure(state="disabled")