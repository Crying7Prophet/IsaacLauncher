import customtkinter as ctk
from tkinterweb import HtmlFrame 
import os
import json
import subprocess
import shutil
import threading
import re
from tkinter import filedialog

# === CONFIGURACIÓN ===
import sys

IS_LINUX = sys.platform.startswith("linux")

def get_default_steamcmd_path():
    return "steamcmd" if IS_LINUX else "D:/steamcmd/steamcmd.exe"

def get_default_mods_path():
    if IS_LINUX:
        return os.path.expanduser("~/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/mods")
    return "D:/Juegos/The.Binding.of.Isaac.Rebirth.v1.9.7.15-0xdeadcode/The.Binding.of.Isaac.Rebirth.v1.9.7.15-0xdeadcode/mods"

def get_default_exe_path():
    if IS_LINUX:
        return os.path.expanduser("~/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/isaac-ng")
    return ""

def get_default_downloads_path():
    return "./temp_downloads"

def cargar_config():
    ruta_mods_default = get_default_mods_path()
    config_default = {
        "steamcmd_path": get_default_steamcmd_path(),
        "isaac_mods_path": ruta_mods_default,
        "isaac_exe_path": get_default_exe_path(),
        "temp_download_path": get_default_downloads_path()
    }
    config_file = "config.json"
    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            json.dump(config_default, f, indent=4)
        return config_default
    with open(config_file, "r") as f:
        return json.load(f)

class IsaacRimLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = cargar_config()
        
        self.title("IsaacRim Mod Manager v1.0")
        self.geometry("1100x800")
        ctk.set_appearance_mode("dark")

        # --- ESTRUCTURA ---
        self.header = ctk.CTkFrame(self)
        self.header.pack(fill="x", padx=5, pady=5)
        
        self.entry_steamcmd, _ = self.crear_input_ruta("SteamCMD:", self.config["steamcmd_path"], is_file=True)
        self.entry_mods, _ = self.crear_input_ruta("Game folder (mods):", self.config["isaac_mods_path"], is_folder=True)
        self.entry_isaac, _ = self.crear_input_ruta("Isaac Executable:", self.config["isaac_exe_path"], is_file=True)
        self.entry_downloads, _ = self.crear_input_ruta("Downloads folder:", self.config["temp_download_path"], is_folder=True)
        
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=5, pady=5)

        self.tabview = ctk.CTkTabview(self.main_container)
        self.tabview.pack(side="left", fill="both", expand=True)
        self.tabview.add("Mods")
        self.tabview.add("Downloader")

        # Barra Lateral (RimPy Style)
        self.sidebar = ctk.CTkFrame(self.main_container, width=150)
        self.sidebar.pack(side="right", fill="y", padx=(5, 0))
        
        self.btn_run = ctk.CTkButton(self.sidebar, text="Run Isaac!", fg_color="#2d5a27", command=self.ejecutar_isaac)
        self.btn_run.pack(pady=20, padx=10, side="bottom", fill="x")

        # Cargar pestañas
        self.setup_downloader_tab()

    def crear_input_ruta(self, etiqueta, valor, is_file=False, is_folder=False):
        """Crea las filas de rutas en la parte superior."""
        frame = ctk.CTkFrame(self.header, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        ctk.CTkLabel(frame, text=etiqueta, width=120, anchor="w").pack(side="left", padx=5)
        
        entry = ctk.CTkEntry(frame)
        entry.insert(0, valor)
        entry.pack(side="left", fill="x", expand=True, padx=5)
        
        def browse_path():
            if is_file:
                path = filedialog.askopenfilename(title=f"Seleccionar {etiqueta}", filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
            elif is_folder:
                path = filedialog.askdirectory(title=f"Seleccionar {etiqueta}")
            else:
                path = None
            if path:
                entry.delete(0, "end")
                entry.insert(0, path)
                self.guardar_config()
        
        ctk.CTkButton(frame, text="📁", width=40, command=browse_path).pack(side="left", padx=2)
        
        return entry, None
    
    def guardar_config(self):
        """Guarda las rutas actuales en el archivo config.json"""
        self.config["steamcmd_path"] = self.entry_steamcmd.get()
        self.config["isaac_mods_path"] = self.entry_mods.get() if self.entry_mods else ""
        self.config["isaac_exe_path"] = self.entry_isaac.get() if self.entry_isaac else ""
        self.config["temp_download_path"] = self.entry_downloads.get() if self.entry_downloads else ""
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=4)
    
    def ejecutar_isaac(self):
        """Ejecuta el juego Isaac"""
        isaac_exe = self.entry_isaac.get()
        if isaac_exe and os.path.exists(isaac_exe):
            if IS_LINUX and not os.access(isaac_exe, os.X_OK):
                os.chmod(isaac_exe, 0o755)
            subprocess.Popen([isaac_exe] if IS_LINUX else [isaac_exe])
        else:
            print("Error: No se encontró el ejecutable del juego.")

    def setup_downloader_tab(self):
        tab = self.tabview.tab("Downloader")
        
        nav_bar = ctk.CTkFrame(tab, height=45)
        nav_bar.pack(fill="x", padx=5, pady=5)
        
        # Entrada de URL
        self.url_entry = ctk.CTkEntry(nav_bar, placeholder_text="Pega el link aquí si la web falla...")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Botones de acción
        ctk.CTkButton(nav_bar, text="Detectar", width=80, command=self.capturar_url_actual).pack(side="left", padx=2)
        self.btn_dl = ctk.CTkButton(nav_bar, text="INSTALAR", fg_color="#1f538d", command=self.iniciar_descarga)
        self.btn_dl.pack(side="left", padx=5)

        # Navegador
        self.browser_frame = ctk.CTkFrame(tab)
        self.browser_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        try:
            self.browser = HtmlFrame(self.browser_frame, messages_enabled=False)
            self.browser.pack(fill="both", expand=True)
            self.browser.load_website("https://steamcommunity.com/app/250900/workshop/")
        except Exception as e:
            print(f"Error navegador: {e}")

    # === TODAS ESTAS FUNCIONES ESTÁN AHORA DENTRO DE LA CLASE ===
    
    def capturar_url_actual(self):
        """Lee la URL del navegador y la pone en el cuadro de texto."""
        try:
            url_real = self.browser.get_url()
            if url_real:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, str(url_real))
                print(f"URL detectada: {url_real}")
        except Exception as e:
            print("Usa el copiado manual si el botón falla.")

    def iniciar_descarga(self):
        """Inicia el proceso de SteamCMD en un hilo separado."""
        url = self.url_entry.get()
        match = re.search(r"id=(\d+)", url)
        if match:
            mod_id = match.group(1)
            threading.Thread(target=self.proceso_descarga_logic, args=(mod_id,), daemon=True).start()
        else:
            print("Error: No hay un ID de mod válido en el cuadro de texto.")

    def proceso_descarga_logic(self, mod_id):
        """Lógica de descarga y movimiento de archivos."""
        self.btn_dl.configure(state="disabled", text="Bajando...")
        try:
            temp_dir = os.path.abspath(self.config["temp_download_path"])
            
            if IS_LINUX:
                comando = [
                    "steamcmd",
                    "+force_install_dir", temp_dir,
                    "+login", "anonymous",
                    "+workshop_download_item", "250900", mod_id,
                    "+quit"
                ]
            else:
                comando = [
                    self.config["steamcmd_path"],
                    "+force_install_dir", f'"{temp_dir}"',
                    "+login", "josuejere",
                    "+workshop_download_item", "250900", mod_id,
                    "+quit"
                ]
            subprocess.run(comando, check=True)
            
            # Rutas de origen y destino
            origen = os.path.join(temp_dir, "steamapps", "workshop", "content", "250900", mod_id)
            destino = os.path.join(self.config["isaac_mods_path"], f"workshop_{mod_id}")
            
            if os.path.exists(origen):
                if os.path.exists(destino): shutil.rmtree(destino)
                shutil.copytree(origen, destino)
                print(f"¡Mod {mod_id} instalado con éxito!")
            else:
                print("SteamCMD terminó pero no se encontraron los archivos descargados.")
        except Exception as e:
            print(f"Error en el proceso: {e}")
        finally:
            self.btn_dl.configure(state="normal", text="INSTALAR")

if __name__ == "__main__":
    app = IsaacRimLauncher()
    app.mainloop()