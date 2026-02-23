import customtkinter as ctk
from tkinterweb import HtmlFrame 
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

class IsaacRimLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = cargar_config()
        
        self.title("IsaacRim Mod Manager v1.0")
        self.geometry("1200x900")
        ctk.set_appearance_mode("dark")

        self.header = ctk.CTkFrame(self)
        self.header.pack(fill="x", padx=5, pady=5)
        
        self.btn_run = ctk.CTkButton(self.header, text="🎮 Run Game", fg_color="#2d5a27", command=self.ejecutar_isaac)
        self.btn_run.pack(side="right", padx=5)
        
        self.btn_about = ctk.CTkButton(self.header, text="ℹ️ About", width=70, command=self.mostrar_about)
        self.btn_about.pack(side="right", padx=5)
        
        self.entry_mods, _ = self.crear_input_ruta("Mods:", self.config["isaac_mods_path"], is_folder=True)
        self.entry_isaac, _ = self.crear_input_ruta("Isaac:", self.config["isaac_exe_path"], is_file=True)
        
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=5, pady=5)

        self.tabview = ctk.CTkTabview(self.main_container)
        self.tabview.pack(side="left", fill="both", expand=True)
        self.tabview.add("Navegador")
        self.tabview.add("Mods")
        
        self.update()
        
        self.tabview.set("Mods")
        
        self.setup_browser_tab()
        self.setup_mods_tab()

    def crear_input_ruta(self, etiqueta, valor, is_file=False, is_folder=False):
        frame = ctk.CTkFrame(self.header, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        ctk.CTkLabel(frame, text=etiqueta, width=120, anchor="w").pack(side="left", padx=5)
        
        entry = ctk.CTkEntry(frame)
        entry.insert(0, valor)
        entry.pack(side="left", fill="x", expand=True, padx=5)
        
        def browse_path():
            if is_file:
                path = filedialog.askopenfilename(title=f"Seleccionar {etiqueta}")
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
                subprocess.Popen(["wine", isaac_exe])
            else:
                subprocess.Popen([isaac_exe])
        else:
            print("Error: No se encontró el ejecutable del juego.")

    def descargar_por_id(self):
        mod_id = self.mod_id_entry.get().strip()
        if not mod_id:
            print("Error: Introduce un ID de mod")
            return
        
        if not mod_id.isdigit():
            print("Error: El ID debe ser solo números")
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
            print(f"Error en el proceso: {e}")
        finally:
            self.btn_descarga_directa.configure(state="normal", text="INSTALAR")

    def descargar_desde_smods(self):
        url_or_id = self.mod_id_entry.get().strip()
        
        if not url_or_id:
            print("Ingresa una URL o ID de mod de Smods")
            return
        
        if "catalogue.smods.ru/archives/" in url_or_id:
            url = url_or_id
        elif url_or_id.isdigit():
            url = f"https://catalogue.smods.ru/archives/{url_or_id}"
        else:
            print("URL inválida. Usa una URL de Smods o el ID del mod")
            return
        
        threading.Thread(target=self._descarga_smods_thread, args=(url,), daemon=True).start()
    
    def _descarga_smods_thread(self, url):
        self.btn_descarga_directa.configure(state="disabled", text="Buscando...")
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
                self.btn_descarga_directa.configure(state="normal", text="Descargar desde Smods")
                return
            
            download_url = download_match.group(1)
            print(f"URL de descarga: {download_url}")
            
            self.btn_descarga_directa.configure(state="disabled", text="Descargando...")
            
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
            
            print(f"Descarga completada: {filepath}")
            
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
            self.btn_descarga_directa.configure(state="normal", text="Descargar desde Smods")

    def mostrar_about(self):
        about_win = ctk.CTkToplevel(self)
        about_win.title("About IsaacRim")
        about_win.geometry("400x350")
        about_win.resizable(False, False)
        
        ctk.CTkLabel(about_win, text="IsaacRim Mod Manager", font=("Arial", 20, "bold")).pack(pady=20)
        ctk.CTkLabel(about_win, text="Versión 1.0", font=("Arial", 14)).pack()
        
        ctk.CTkLabel(about_win, text="A mod manager for\nThe Binding of Isaac: Repentance", justify="center").pack(pady=20)
        
        ctk.CTkLabel(about_win, text="Features:", font=("Arial", 12, "bold")).pack(pady=(10, 5))
        features = [
            "• Integrated browser for mod sites",
            "• Automatic metadata from Steam",
            "• Easy mod installation",
            "• Modern dark UI"
        ]
        for f in features:
            ctk.CTkLabel(about_win, text=f, justify="left").pack()
        
        ctk.CTkButton(about_win, text="Cerrar", command=about_win.destroy).pack(pady=20)

    def setup_browser_tab(self):
        tab = self.tabview.tab("Navegador")
        
        nav_bar = ctk.CTkFrame(tab, height=50)
        nav_bar.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(nav_bar, text="←", width=40, command=self.atras).pack(side="left", padx=2)
        ctk.CTkButton(nav_bar, text="→", width=40, command=self.adelante).pack(side="left", padx=2)
        ctk.CTkButton(nav_bar, text="⟳", width=40, command=self.recargar).pack(side="left", padx=2)
        
        self.url_entry = ctk.CTkEntry(nav_bar, placeholder_text="Escribe una URL...")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.url_entry.bind("<Return>", lambda e: self.navegar_url())
        
        ctk.CTkButton(nav_bar, text="Ir", width=60, command=self.navegar_url).pack(side="left", padx=2)
        
        ctk.CTkButton(nav_bar, text="−", width=35, command=self.zoom_out).pack(side="left", padx=(10, 2))
        ctk.CTkButton(nav_bar, text="+", width=35, command=self.zoom_in).pack(side="left", padx=2)

        self.lbl_zoom = ctk.CTkLabel(nav_bar, text="100%", width=50)
        self.lbl_zoom.pack(side="left", padx=5)

        download_bar = ctk.CTkFrame(tab, height=45)
        download_bar.pack(fill="x", padx=5, pady=(0, 5))
        
        ctk.CTkLabel(download_bar, text="Descarga directa (ID Steam):", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        
        self.mod_id_entry = ctk.CTkEntry(download_bar, placeholder_text="ID o URL de mod", width=200)
        self.mod_id_entry.pack(side="left", padx=5)
        
        self.btn_descarga_directa = ctk.CTkButton(download_bar, text="Descargar", fg_color="#1f538d", command=self.descargar_por_id)
        self.btn_descarga_directa.pack(side="left", padx=5)
        
        ctk.CTkButton(download_bar, text="Desde Smods", fg_color="#2d5a27", command=self.descargar_desde_smods).pack(side="left", padx=5)

        shortcuts_bar = ctk.CTkFrame(tab)
        shortcuts_bar.pack(fill="x", padx=5, pady=(0, 5))
        
        ctk.CTkLabel(shortcuts_bar, text="Enlaces:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        
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
        self.panel_info.pack(side="right", fill="both", expand=True)
        
        self.lbl_info_titulo = ctk.CTkLabel(self.panel_info, text="Selecciona un mod", font=("Arial", 16, "bold"))
        self.lbl_info_titulo.pack(pady=(20, 10), padx=10)
        
        self.lbl_info_imagen = ctk.CTkLabel(self.panel_info, text="")
        self.lbl_info_imagen.pack(pady=10, padx=10)
        
        self.lbl_info_buscar = ctk.CTkLabel(self.panel_info, text="Buscando automáticamente...", text_color="gray")
        self.lbl_info_buscar.pack(pady=5, padx=10)
        
        self.lbl_info_desc = ctk.CTkLabel(self.panel_info, text="", wraplength=300, justify="left")
        self.lbl_info_desc.pack(pady=10, padx=10)
        
        self.lbl_info_autor = ctk.CTkLabel(self.panel_info, text="")
        self.lbl_info_autor.pack(pady=5, padx=10)
        
        self.actualizar_lista_mods()

    def buscar_info_mod(self, mod_id):
        if not mod_id:
            return
        
        self.lbl_info_titulo.configure(text="Buscando...")
        self.update()
        
        self.buscar_info_mod_por_id(mod_id)

    def buscar_info_mod_por_id(self, mod_id):
        self.lbl_info_buscar.configure(text=f"ID: {mod_id}")
        
        try:
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                html = response.text
                
                import re
                
                title_match = re.search(r'<div class="workshopItemTitle">([^<]+)</div>', html)
                title = title_match.group(1) if title_match else "Título no encontrado"
                
                author_match = re.search(r'<div class="workshopItemAuthor">[^:]+: <a[^>]*>([^<]+)</a>', html)
                author = author_match.group(1) if author_match else "Autor desconocido"
                
                desc_match = re.search(r'<div class="workshopItemDescription">(.+?)</div>', html, re.DOTALL)
                description = desc_match.group(1) if desc_match else ""
                description = re.sub(r'<[^>]+>', '', description)[:500]
                
                img_match = re.search(r'https://steamuserimages-a\.akamaihd\.net/ugc/(\d+)/(\w+)', html)
                
                self.lbl_info_titulo.configure(text=title)
                self.lbl_info_autor.configure(text=f"Autor: {author}")
                self.lbl_info_desc.configure(text=description)
                
                if img_match:
                    img_url = f"https://steamuserimages-a.akamaihd.net/ugc/{img_match.group(1)}/{img_match.group(2)}"
                    self.descargar_y_mostrar_imagen(img_url)
                else:
                    self.lbl_info_imagen.configure(text="[Sin imagen]")
            else:
                self.lbl_info_titulo.configure(text="Mod no encontrado")
        except Exception as e:
            self.lbl_info_titulo.configure(text=f"Error: {str(e)[:50]}")
            print(f"Error buscando mod: {e}")

    def descargar_y_mostrar_imagen(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                import base64
                from PIL import Image, ImageTk
                import io
                
                img_data = response.content
                image = Image.open(io.BytesIO(img_data))
                image.thumbnail((300, 300))
                self.imagen_tk = ImageTk.PhotoImage(image)
                self.lbl_info_imagen.configure(image=self.imagen_tk, text="")
            else:
                self.lbl_info_imagen.configure(text="[Error de imagen]")
        except Exception as e:
            self.lbl_info_imagen.configure(text=f"[Error: {str(e)[:30]}]")
            print(f"Error imagen: {e}")

    def actualizar_lista_mods(self):
        mods_path = self.entry_mods.get()
        if not os.path.exists(mods_path):
            os.makedirs(mods_path, exist_ok=True)
        
        self.procesar_zips_en_carpeta(mods_path)
        
        self.lista_mods.delete(0, "end")
        
        items = os.listdir(mods_path)
        if not items:
            self.lista_mods.insert("end", "No hay mods instalados")
            return
        
        self.mod_seleccionado = None
        self.mods_list = []
        
        for item in sorted(items):
            item_path = os.path.join(mods_path, item)
            if os.path.isdir(item_path):
                self.lista_mods.insert("end", item)
                self.mods_list.append(item)
    
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
                    print(f"Error procesando {item}: {e}")
    
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
        self.lbl_info_imagen.configure(image="", text="")
        self.lbl_info_buscar.configure(text="Buscando automáticamente...")
        self.lbl_info_desc.configure(text="")
        self.lbl_info_autor.configure(text="")
        
        import threading
        threading.Thread(target=self.buscar_mod_por_nombre, args=(nombre,), daemon=True).start()

    def buscar_mod_por_nombre(self, nombre_mod):
        try:
            search_url = "https://steamcommunity.com/app/250900/workshop/browse/"
            params = {"query": nombre_mod, "numperpage": "10"}
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                html = response.text
                import re
                
                matches = re.findall(r'filedetails/\?id=(\d+)">([^<]+)</a>', html)
                
                mejor_match = None
                nombre_clean = nombre_mod.lower().replace("workshop_", "").replace("_", " ").strip()
                
                for mod_id, titulo in matches:
                    titulo_clean = titulo.lower().strip()
                    if nombre_clean in titulo_clean or titulo_clean in nombre_clean:
                        mejor_match = (mod_id, titulo)
                        break
                
                if mejor_match:
                    mod_id, titulo = mejor_match
                    self.after(0, lambda m=mod_id, t=titulo: self.mostrar_info_mod_por_id(m, t))
                else:
                    self.after(0, lambda: self.lbl_info_buscar.configure(text="No se encontró en Steam"))
            else:
                self.after(0, lambda: self.lbl_info_buscar.configure(text="Error de conexión"))
        except Exception as e:
            self.after(0, lambda: self.lbl_info_buscar.configure(text=f"Error: {str(e)[:30]}"))

    def mostrar_info_mod_por_id(self, mod_id, titulo):
        self.lbl_info_buscar.configure(text=f"ID: {mod_id}")
        self.lbl_info_titulo.configure(text=titulo)
        self.buscar_info_mod_por_id(mod_id)

    def eliminar_mod_seleccionado(self):
        if not self.mod_seleccionado:
            print("Selecciona un mod primero")
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
                print(f"Error navegando: {e}")
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
        filepath = filedialog.askopenfilename(title="Seleccionar archivo descargado", filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")])
        
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
                print(f"Error instalando mod: {e}")
    
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
    app = IsaacRimLauncher()
    app.mainloop()
