import customtkinter as ctk
from tkinterweb import HtmlFrame 
from PIL import Image
import os
import json
import subprocess
import shutil
import zipfile
import requests
import threading
from tkinter import filedialog

import sys

IS_LINUX = sys.platform.startswith("linux")

def get_default_mods_path():
    if IS_LINUX:
        return os.path.expanduser("~/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/mods")
    return "D:/Juegos/The.Binding.of.Isaac.Rebirth.v1.9.7.15-0xdeadcode/The.Binding.of.Isaac.Rebirth.v1.9.7.15-0xdeadcode/mods"

def get_default_exe_path():
    if IS_LINUX:
        return os.path.expanduser("~/.local/share/Steam/steamapps/common/The Binding of Isaac Rebirth/isaac-ng")
    return ""

def cargar_config():
    ruta_mods_default = get_default_mods_path()
    config_default = {
        "isaac_mods_path": ruta_mods_default,
        "isaac_exe_path": get_default_exe_path(),
    }
    config_file = "config.json"
    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            json.dump(config_default, f, indent=4)
        return config_default
    with open(config_file, "r") as f:
        return json.load(f)

class PyIsaacLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.config = cargar_config()
        
        self.title("PyIsaac Launcher v1.0")
        self.geometry("1100x600")
        ctk.set_appearance_mode("dark")

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=5, pady=(5, 0))

        self.tabview = ctk.CTkTabview(self.main_container)
        self.tabview.pack(side="left", fill="both", expand=True)
        self.tabview.add("Browser")
        self.tabview.add("Mods")
        self.tabview.add("About")
        
        self.update()
        
        self.tabview.set("Mods")

        self.header = ctk.CTkFrame(self, height=60)
        self.header.pack(fill="x", padx=5, pady=5, side="bottom")
        
        self.btn_run = ctk.CTkButton(self.header, text="🎮 Run Game", fg_color="#2d5a27", height=40, command=self.ejecutar_isaac)
        self.btn_run.pack(side="right", padx=5, pady=5)
        
        self.entry_mods, _ = self.crear_input_ruta("Mods:", self.config["isaac_mods_path"], is_folder=True)
        self.entry_isaac, _ = self.crear_input_ruta("Game:", self.config["isaac_exe_path"], is_file=True)
        
        self.setup_browser_tab()
        self.setup_mods_tab()
        self.setup_about_tab()

    def crear_input_ruta(self, etiqueta, valor, is_file=False, is_folder=False):
        frame = ctk.CTkFrame(self.header, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        ctk.CTkLabel(frame, text=etiqueta, width=120, anchor="w").pack(side="left", padx=5)
        
        entry = ctk.CTkEntry(frame)
        entry.insert(0, valor)
        entry.pack(side="left", fill="x", expand=True, padx=5)
        
        def browse_path():
            if is_file:
                path = filedialog.askopenfilename(title=f"Select {etiqueta}")
            elif is_folder:
                path = filedialog.askdirectory(title=f"Select {etiqueta}")
            else:
                path = None
            if path:
                entry.delete(0, "end")
                entry.insert(0, path)
                self.guardar_config()
        
        ctk.CTkButton(frame, text="📁", width=40, command=browse_path).pack(side="left", padx=2)
        
        return entry, None
    
    def guardar_config(self):
        self.config["isaac_mods_path"] = self.entry_mods.get() if self.entry_mods else ""
        self.config["isaac_exe_path"] = self.entry_isaac.get() if self.entry_isaac else ""
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=4)
    
    def ejecutar_isaac(self):
        isaac_exe = self.entry_isaac.get()
        if isaac_exe and os.path.exists(isaac_exe):
            if IS_LINUX and not os.access(isaac_exe, os.X_OK):
                os.chmod(isaac_exe, 0o755)
            if IS_LINUX:
                exe_dir = os.path.dirname(isaac_exe)
                subprocess.Popen(["wine", os.path.basename(isaac_exe)], cwd=exe_dir)
            else:
                subprocess.Popen([isaac_exe])
        else:
            print("Error: Game executable not found.")
    
    def descargar_por_id(self):
        mod_id = self.mod_id_entry.get().strip()
        if not mod_id:
            print("Error: Enter a mod ID")
            return
        
        if not mod_id.isdigit():
            print("Error: ID must be numbers only")
            return
        
        threading.Thread(target=self._descarga_steamcmd, args=(mod_id,), daemon=True).start()
    
    def _descarga_steamcmd(self, mod_id):
        self.btn_descarga_directa.configure(state="disabled", text="Bajando...")
        try:
            temp_dir = os.path.abspath(self.config["temp_download_path"])
            os.makedirs(temp_dir, exist_ok=True)
            
            comando = [
                self.config["steamcmd_path"],
                "+force_install_dir", temp_dir,
                "+login", "anonymous",
                "+workshop_download_item", "250900", mod_id,
                "+quit"
            ]
            
            subprocess.run(comando, check=True, capture_output=True)
            
            origen = os.path.join(temp_dir, "steamapps", "workshop", "content", "250900", mod_id)
            destino = os.path.join(self.config["isaac_mods_path"], f"workshop_{mod_id}")
            
            if os.path.exists(origen):
                if os.path.exists(destino):
                    shutil.rmtree(destino)
                shutil.copytree(origen, destino)
                print(f"¡Mod {mod_id} instalado con éxito!")
            else:
                print("SteamCMD terminó pero no se encontraron los archivos.")
        except Exception as e:
                print(f"Error in process: {e}")
        finally:
            self.btn_descarga_directa.configure(state="normal", text="INSTALAR")

    def descargar_desde_smods(self):
        url_or_id = self.mod_id_entry.get().strip()
        
        if not url_or_id:
            print("Enter a Smods URL or mod ID")
            return
        
        if "catalogue.smods.ru/archives/" in url_or_id:
            url = url_or_id
        elif url_or_id.isdigit():
            url = f"https://catalogue.smods.ru/archives/{url_or_id}"
        else:
            print("Invalid URL. Use a Smods URL or mod ID")
            return
        
        threading.Thread(target=self._descarga_smods_thread, args=(url,), daemon=True).start()
    
    def _descarga_smods_thread(self, url):
        self.btn_descarga_directa.configure(state="disabled", text="Searching...")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            import re
            download_match = re.search(r'href="(https?://[^"]+\.zip[^"]*)"', response.text)
            
            if not download_match:
                download_match = re.search(r'class="skymods-excerpt-btn"[^>]*href="([^"]+)"', response.text)
            
            if not download_match:
                print("No se encontró enlace de descarga en la página")
                self.btn_descarga_directa.configure(state="normal", text="Download from Smods")
                return
            
            download_url = download_match.group(1)
            print(f"Download URL: {download_url}")
            
            self.btn_descarga_directa.configure(state="disabled", text="Downloading...")
            
            temp_dir = os.path.abspath(self.config["temp_download_path"])
            os.makedirs(temp_dir, exist_ok=True)
            
            filename = "mod.zip"
            filepath = os.path.join(temp_dir, filename)
            
            response = requests.get(download_url, headers=headers, stream=True, timeout=120)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            print(f"Download completed: {filepath}")
            
            mods_path = self.config["isaac_mods_path"]
            os.makedirs(mods_path, exist_ok=True)
            
            import tempfile
            with tempfile.TemporaryDirectory() as temp_extract:
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract)
                
                contenido = os.listdir(temp_extract)
                
                if len(contenido) == 1 and os.path.isdir(os.path.join(temp_extract, contenido[0])):
                    carpeta_extraida = os.path.join(temp_extract, contenido[0])
                else:
                    carpeta_extraida = temp_extract
                
                nombre_oficial = self.buscar_nombre_en_metadata(carpeta_extraida)
                
                if nombre_oficial:
                    destino = os.path.join(mods_path, nombre_oficial)
                    print(f"Nombre oficial del mod: {nombre_oficial}")
                else:
                    destino = None
                    print("No se encontró nombre en metadata, usa nombre manual")
                
                if destino:
                    if os.path.exists(destino):
                        shutil.rmtree(destino)
                    shutil.copytree(carpeta_extraida, destino)
                else:
                    destino = os.path.join(mods_path, "mod_sin_nombre")
                    if os.path.exists(destino):
                        shutil.rmtree(destino)
                    shutil.copytree(carpeta_extraida, destino)
            
            print(f"Mod instalado en: {destino}")
            self.actualizar_lista_mods()
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.btn_descarga_directa.configure(state="normal", text="Download from Smods")

    def setup_about_tab(self):
        tab = self.tabview.tab("About")
        
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.svg")
        logo_photo = None
        
        if os.path.exists(logo_path):
            try:
                import cairosvg
                from io import BytesIO
                png_data = cairosvg.svg2png(url=logo_path, output_width=120, output_height=120)
                img = Image.open(BytesIO(png_data))
                from PIL import ImageTk
                logo_photo = ImageTk.PhotoImage(img)
            except ImportError:
                print("cairosvg not installed")
            except Exception as e:
                print(f"Error loading SVG logo: {e}")
        
        if logo_photo:
            lbl = ctk.CTkLabel(tab, image=logo_photo, text="")
            lbl.image = logo_photo
            lbl.pack(pady=0)
        
        ctk.CTkLabel(tab, text="PyIsaac Launcher", font=("Arial", 20, "bold")).pack(pady=0)
        ctk.CTkLabel(tab, text="Version 1.0", font=("Arial", 14)).pack()
        
        ctk.CTkLabel(tab, text="A mod manager for\nThe Binding of Isaac: Repentance", justify="center").pack(pady=5)
        
        ctk.CTkLabel(tab, text="Features:", font=("Arial", 12, "bold")).pack(pady=(5, 2))
        features = [
            "• Integrated browser for mod sites",
            "• Automatic metadata from Steam",
            "• Easy mod installation",
            "• Modern dark UI"
        ]
        for f in features:
            ctk.CTkLabel(tab, text=f, justify="left").pack()

    def setup_browser_tab(self):
        tab = self.tabview.tab("Browser")
        
        nav_bar = ctk.CTkFrame(tab, height=50)
        nav_bar.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(nav_bar, text="←", width=40, command=self.atras).pack(side="left", padx=2)
        ctk.CTkButton(nav_bar, text="→", width=40, command=self.adelante).pack(side="left", padx=2)
        ctk.CTkButton(nav_bar, text="⟳", width=40, command=self.recargar).pack(side="left", padx=2)
        
        self.url_entry = ctk.CTkEntry(nav_bar, placeholder_text="Enter a URL...")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.url_entry.bind("<Return>", lambda e: self.navegar_url())
        
        ctk.CTkButton(nav_bar, text="Go", width=60, command=self.navegar_url).pack(side="left", padx=2)
        
        ctk.CTkButton(nav_bar, text="−", width=35, command=self.zoom_out).pack(side="left", padx=(10, 2))
        ctk.CTkButton(nav_bar, text="+", width=35, command=self.zoom_in).pack(side="left", padx=2)

        self.lbl_zoom = ctk.CTkLabel(nav_bar, text="100%", width=50)
        self.lbl_zoom.pack(side="left", padx=5)

        download_bar = ctk.CTkFrame(tab, height=45)
        download_bar.pack(fill="x", padx=5, pady=(0, 5))
        
        ctk.CTkLabel(download_bar, text="Direct download (Steam ID):", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        
        self.mod_id_entry = ctk.CTkEntry(download_bar, placeholder_text="Mod ID or URL", width=200)
        self.mod_id_entry.pack(side="left", padx=5)
        
        self.btn_descarga_directa = ctk.CTkButton(download_bar, text="Download", fg_color="#1f538d", command=self.descargar_por_id)
        self.btn_descarga_directa.pack(side="left", padx=5)
        
        ctk.CTkButton(download_bar, text="Desde Smods", fg_color="#2d5a27", command=self.descargar_desde_smods).pack(side="left", padx=5)

        shortcuts_bar = ctk.CTkFrame(tab)
        shortcuts_bar.pack(fill="x", padx=5, pady=(0, 5))
        
        ctk.CTkLabel(shortcuts_bar, text="Links:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        
        shortcuts = [
            ("Steam Workshop", "https://steamcommunity.com/app/250900/workshop/"),
            ("Smods", "https://catalogue.smods.ru/?app=250900"),
            ("NexusMods", "https://www.nexusmods.com/bindingofisaacrebirth"),
            ("ModDB", "https://www.moddb.com/games/the-binding-of-isaac-rebirth"),
            ("Modding of Isaac", "https://moddingofisaac.com/"),
        ]
        
        for name, url in shortcuts:
            ctk.CTkButton(
                shortcuts_bar, 
                text=name, 
                width=110, 
                command=lambda u=url: self.navegar_a(u)
            ).pack(side="left", padx=3)

        self.browser_frame = ctk.CTkFrame(tab)
        self.browser_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        try:
            self.browser = HtmlFrame(self.browser_frame)
            self.browser.pack(fill="both", expand=True, padx=2, pady=2)
            self.browser.load_url("https://steamcommunity.com/app/250900/workshop/")
        except Exception as e:
            ctk.CTkLabel(self.browser_frame, text=f"Error: {e}").pack()
            print(f"Error navegador: {e}")

    def setup_mods_tab(self):
        tab = self.tabview.tab("Mods")
        
        mods_container = ctk.CTkFrame(tab)
        mods_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        left_panel = ctk.CTkFrame(mods_container, width=300)
        left_panel.pack(side="left", fill="both", padx=(0, 5))
        left_panel.pack_propagate(False)
        
        toolbar = ctk.CTkFrame(left_panel)
        toolbar.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(toolbar, text="↻", width=35, command=self.actualizar_lista_mods).pack(side="left", padx=2)
        ctk.CTkButton(toolbar, text="+", width=35, fg_color="#1f538d", command=self.seleccionar_archivo).pack(side="left", padx=2)
        ctk.CTkButton(toolbar, text="🗑", width=35, fg_color="#8d1f1f", command=self.eliminar_mod_seleccionado).pack(side="left", padx=2)
        
        self.lista_mods_frame = ctk.CTkFrame(left_panel)
        self.lista_mods_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        from tkinter import Listbox
        self.lista_mods = Listbox(self.lista_mods_frame, bg="#2b2b2b", fg="white", selectbackground="#1f538d", borderwidth=0, highlightthickness=0)
        self.lista_mods.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.lista_mods.bind("<<ListboxSelect>>", self.on_mod_select)
        
        self.panel_info = ctk.CTkFrame(mods_container)
        self.panel_info.pack(side="left", fill="both", expand=True)
        
        from tkinter import Canvas, Scrollbar
        self.info_canvas = Canvas(self.panel_info, bg="#2b2b2b", highlightthickness=0)
        self.info_canvas.pack(side="left", fill="both", expand=True)
        
        self.info_scrollbar = Scrollbar(self.panel_info, command=self.info_canvas.yview)
        self.info_scrollbar.pack(side="right", fill="y")
        
        self.info_canvas.configure(yscrollcommand=self.info_scrollbar.set)
        
        self.info_content = ctk.CTkFrame(self.info_canvas, fg_color="transparent")
        self.info_canvas.create_window((0, 0), window=self.info_content, anchor="nw")
        
        self.info_content.bind("<Configure>", lambda e: self.info_canvas.configure(scrollregion=self.info_canvas.bbox("all")))
        
        self.lbl_info_titulo = ctk.CTkLabel(self.info_content, text="Select a mod", font=("Arial", 16, "bold"), wraplength=300)
        self.lbl_info_titulo.pack(pady=(20, 10), padx=10)
        
        self.lbl_info_buscar = ctk.CTkLabel(self.info_content, text="Loading...", text_color="gray", wraplength=300)
        self.lbl_info_buscar.pack(pady=5, padx=10)
        
        self.lbl_info_desc = ctk.CTkLabel(self.info_content, text="", wraplength=300, justify="left")
        self.lbl_info_desc.pack(pady=10, padx=10)
        
        self.lbl_info_autor = ctk.CTkLabel(self.info_content, text="", wraplength=300)
        self.lbl_info_autor.pack(pady=5, padx=10)
        
        self.panel_imagenes = ctk.CTkFrame(mods_container)
        self.panel_imagenes.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self.imagenes_canvas = Canvas(self.panel_imagenes, bg="#2b2b2b", highlightthickness=0)
        self.imagenes_canvas.pack(side="left", fill="both", expand=True)
        
        self.imagenes_scrollbar = Scrollbar(self.panel_imagenes, command=self.imagenes_canvas.yview)
        self.imagenes_scrollbar.pack(side="right", fill="y")
        
        self.imagenes_canvas.configure(yscrollcommand=self.imagenes_scrollbar.set)
        
        self.imagenes_frame = ctk.CTkFrame(self.imagenes_canvas, fg_color="transparent")
        self.imagenes_canvas.create_window((0, 0), window=self.imagenes_frame, anchor="nw")
        
        self.imagenes_frame.bind("<Configure>", lambda e: self.imagenes_canvas.configure(scrollregion=self.imagenes_canvas.bbox("all")))
        
        ctk.CTkLabel(self.imagenes_frame, text="Images", font=("Arial", 14, "bold")).pack(pady=(10, 5), padx=10)
        
        self.actualizar_lista_mods()

    def actualizar_lista_mods(self):
        mods_path = self.entry_mods.get()
        if not os.path.exists(mods_path):
            os.makedirs(mods_path, exist_ok=True)
        
        self.procesar_zips_en_carpeta(mods_path)
        
        self.lista_mods.delete(0, "end")
        
        items = os.listdir(mods_path)
        if not items:
            self.lista_mods.insert("end", "No mods installed")
            return
        
        self.mod_seleccionado = None
        self.mods_list = []
        
        for item in sorted(items):
            item_path = os.path.join(mods_path, item)
            if os.path.isdir(item_path):
                self.lista_mods.insert("end", item)
                self.mods_list.append(item)
        
        if self.mods_list:
            self.lista_mods.selection_set(0)
            self.lista_mods.see(0)
            self.mod_seleccionado = self.mods_list[0]
            self.mostrar_info_mod(self.mods_list[0])
    
    def procesar_zips_en_carpeta(self, mods_path):
        import tempfile
        
        for item in os.listdir(mods_path):
            if item.endswith(".zip"):
                zip_path = os.path.join(mods_path, item)
                print(f"Procesando: {item}")
                
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(temp_dir)
                        
                        contenido = os.listdir(temp_dir)
                        
                        if len(contenido) == 1 and os.path.isdir(os.path.join(temp_dir, contenido[0])):
                            carpeta_extraida = os.path.join(temp_dir, contenido[0])
                        else:
                            carpeta_extraida = temp_dir
                        
                        nombre_oficial = self.buscar_nombre_en_metadata(carpeta_extraida)
                        
                        if nombre_oficial:
                            destino = os.path.join(mods_path, nombre_oficial)
                            print(f"Nombre oficial del mod: {nombre_oficial}")
                        else:
                            destino = None
                        
                        if destino:
                            if os.path.exists(destino):
                                shutil.rmtree(destino)
                            shutil.copytree(carpeta_extraida, destino)
                        else:
                            nombre_base = os.path.splitext(item)[0]
                            destino = os.path.join(mods_path, nombre_base)
                            if os.path.exists(destino):
                                shutil.rmtree(destino)
                            shutil.copytree(carpeta_extraida, destino)
                        
                        os.remove(zip_path)
                        print(f"Mod instalado y zip eliminado: {destino}")
                        
                except Exception as e:
                    print(f"Error processing {item}: {e}")
    
    def on_mod_select(self, event):
        selection = self.lista_mods.curselection()
        if selection:
            index = selection[0]
            if index < len(self.mods_list):
                mod_name = self.mods_list[index]
                self.mod_seleccionado = mod_name
                self.mostrar_info_mod(mod_name)

    def mostrar_info_mod(self, nombre):
        self.mod_seleccionado = nombre
        
        self.lbl_info_titulo.configure(text=nombre)
        self.lbl_info_buscar.configure(text="Loading...")
        self.lbl_info_desc.configure(text="")
        self.lbl_info_autor.configure(text="")
        
        self.leer_metadata_local(nombre)

    def leer_metadata_local(self, nombre):
        import xml.etree.ElementTree as ET
        import re
        from PIL import Image, ImageTk, ImageDraw
        
        mods_path = self.entry_mods.get()
        mod_path = os.path.join(mods_path, nombre)
        
        metadata_file = os.path.join(mod_path, "metadata.xml")
        
        titulo = nombre
        descripcion = ""
        autor = ""
        version = ""
        tags = []
        
        if os.path.exists(metadata_file):
            try:
                tree = ET.parse(metadata_file)
                root = tree.getroot()
                
                name_elem = root.find("name")
                if name_elem is not None:
                    titulo = name_elem.text or nombre
                
                desc_elem = root.find("description")
                if desc_elem is not None and desc_elem.text:
                    descripcion = desc_elem.text.strip()[:500]
                
                version_elem = root.find("version")
                if version_elem is not None and version_elem.text:
                    version = version_elem.text
                
                for tag in root.findall("tag"):
                    tag_id = tag.get("id")
                    if tag_id:
                        tags.append(tag_id)
                
            except Exception as e:
                print(f"Error reading metadata.xml: {e}")
        
        imagenes = []
        for file in os.listdir(mod_path):
            if os.path.isfile(os.path.join(mod_path, file)):
                ext = os.path.splitext(file)[1].lower()
                if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]:
                    imagenes.append(os.path.join(mod_path, file))
        
        self.lbl_info_titulo.configure(text=titulo)
        
        info_text = ""
        if version:
            info_text += f"Version: {version}"
        if tags:
            info_text += f" | Tags: {', '.join(tags)}"
        self.lbl_info_buscar.configure(text=info_text or "No metadata")
        self.lbl_info_desc.configure(text=descripcion)
        
        for widget in self.imagenes_frame.winfo_children():
            widget.destroy()
        
        if imagenes:
            for img_path in imagenes:
                try:
                    img = Image.open(img_path)
                    img.thumbnail((400, 300), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    lbl = ctk.CTkLabel(self.imagenes_frame, image=photo, text="")
                    lbl.image = photo
                    lbl.pack(pady=5)
                except Exception as e:
                    print(f"Error loading image {img_path}: {e}")
            self.imagenes_frame.update_idletasks()
            self.imagenes_canvas.configure(scrollregion=self.imagenes_canvas.bbox("all"))
        else:
            placeholder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "placeholder.svg")
            photo = None
            
            if os.path.exists(placeholder_path):
                try:
                    import cairosvg
                    png_data = cairosvg.svg2png(url=placeholder_path, output_width=400, output_height=300)
                    from io import BytesIO
                    img = Image.open(BytesIO(png_data))
                    photo = ImageTk.PhotoImage(img)
                except ImportError:
                    print("cairosvg not installed, trying with PIL (won't work for SVG)")
                except Exception as e:
                    print(f"Error loading SVG placeholder: {e}")
            
            if not photo:
                placeholder = Image.new('RGB', (400, 300), color='#2b2b2b')
                draw = ImageDraw.Draw(placeholder)
                try:
                    draw.text((200, 150), "No images", fill="gray", anchor="mm")
                except:
                    pass
                photo = ImageTk.PhotoImage(placeholder)
            
            if photo:
                lbl = ctk.CTkLabel(self.imagenes_frame, image=photo, text="")
                lbl.image = photo
                lbl.pack(pady=20)

    def eliminar_mod_seleccionado(self):
        if not self.mod_seleccionado:
            print("Select a mod first")
            return
        
        mods_path = self.entry_mods.get()
        mod_path = os.path.join(mods_path, self.mod_seleccionado)
        
        if os.path.exists(mod_path):
            shutil.rmtree(mod_path)
            print(f"Mod eliminado: {self.mod_seleccionado}")
            self.mod_seleccionado = None
            self.actualizar_lista_mods()

    def navegar_url(self):
        url = self.url_entry.get().strip()
        if url:
            if not url.startswith("http"):
                url = "https://" + url
            try:
                print(f"Navegando a: {url}")
                self.browser.load_url(url)
            except Exception as e:
                print(f"Error browsing: {e}")
                try:
                    self.browser.load_website(url)
                except Exception as e2:
                    print(f"También falló load_website: {e2}")

    def atras(self):
        try:
            self.browser.back()
        except Exception:
            pass

    def adelante(self):
        try:
            self.browser.forward()
        except Exception:
            pass

    def recargar(self):
        url = self.url_entry.get()
        if url:
            self.navegar_url()

    def zoom_in(self):
        print("Zoom in no disponible en esta versión")

    def zoom_out(self):
        print("Zoom out no disponible en esta versión")

    def navegar_a(self, url):
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url)
        self.navegar_url()

    def seleccionar_archivo(self):
        filepath = filedialog.askopenfilename(title="Select downloaded file", filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")])
        
        if filepath:
            mods_path = self.entry_mods.get()
            os.makedirs(mods_path, exist_ok=True)
            
            try:
                if filepath.endswith(".zip"):
                    import tempfile
                    
                    with tempfile.TemporaryDirectory() as temp_dir:
                        with zipfile.ZipFile(filepath, 'r') as zip_ref:
                            zip_ref.extractall(temp_dir)
                        
                        contenido = os.listdir(temp_dir)
                        
                        if len(contenido) == 1 and os.path.isdir(os.path.join(temp_dir, contenido[0])):
                            carpeta_extraida = os.path.join(temp_dir, contenido[0])
                        else:
                            carpeta_extraida = temp_dir
                        
                        nombre_oficial = self.buscar_nombre_en_metadata(carpeta_extraida)
                        
                        if nombre_oficial:
                            destino = os.path.join(mods_path, nombre_oficial)
                            print(f"Nombre oficial del mod: {nombre_oficial}")
                        else:
                            destino = None
                        
                        if destino and os.path.exists(destino):
                            shutil.rmtree(destino)
                        
                        if destino:
                            shutil.copytree(carpeta_extraida, destino)
                        else:
                            print("No se encontró nombre en metadata")
                else:
                    filename = os.path.basename(filepath)
                    nombre_mod = os.path.splitext(filename)[0]
                    destino = os.path.join(mods_path, nombre_mod)
                    os.makedirs(destino, exist_ok=True)
                    shutil.copy2(filepath, destino)
                
                print(f"Mod instalado en: {destino}")
                self.actualizar_lista_mods()
            except Exception as e:
                print(f"Error installing mod: {e}")
    
    def buscar_nombre_en_metadata(self, folder):
        import re
        
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file in ["metadata.xml", "metadata.txt", "info.xml", "info.txt"]:
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        match = re.search(r'<name>([^<]+)</name>', content, re.IGNORECASE)
                        if match:
                            nombre = match.group(1).strip()
                            return nombre
                        
                        match = re.search(r'^Name\s*=\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
                        if match:
                            nombre = match.group(1).strip()
                            return nombre
                    except:
                        pass
        return None

if __name__ == "__main__":
    app = PyIsaacLauncher()
    app.mainloop()
