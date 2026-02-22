import customtkinter as ctk
from tkinterweb import HtmlFrame 
import os
import json
import subprocess
import shutil
import zipfile
import requests
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

        shortcuts_bar = ctk.CTkFrame(tab)
        shortcuts_bar.pack(fill="x", padx=5, pady=(0, 5))
        
        ctk.CTkLabel(shortcuts_bar, text="Enlaces:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        
        shortcuts = [
            ("Steam Workshop", "https://steamcommunity.com/app/250900/workshop/"),
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
        
        self.lista_mods = ctk.CTkScrollableFrame(left_panel, label_text="Mods instalados")
        self.lista_mods.pack(fill="both", expand=True, padx=5, pady=5)
        
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
        for widget in self.lista_mods.winfo_children():
            widget.destroy()
        
        mods_path = self.entry_mods.get()
        if not os.path.exists(mods_path):
            os.makedirs(mods_path, exist_ok=True)
        
        items = os.listdir(mods_path)
        if not items:
            ctk.CTkLabel(self.lista_mods, text="No hay mods instalados").pack(pady=20)
            return
        
        self.mod_seleccionado = None
        
        for item in sorted(items):
            item_path = os.path.join(mods_path, item)
            if os.path.isdir(item_path):
                frame = ctk.CTkFrame(self.lista_mods)
                frame.pack(fill="x", pady=2, padx=5)
                
                btn = ctk.CTkButton(
                    frame, 
                    text=item, 
                    anchor="w",
                    command=lambda n=item: self.seleccionar_mod(n)
                )
                btn.pack(side="left", fill="x", expand=True, padx=5)
                
                archivos = os.listdir(item_path)
                count = len(archivos)
                ctk.CTkLabel(frame, text=f"{count} archivos", width=80).pack(side="right", padx=5)

    def seleccionar_mod(self, nombre):
        self.mod_seleccionado = nombre
        for widget in self.lista_mods.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ctk.CTkButton) and child.cget("text") == nombre:
                    child.configure(fg_color="#1f538d")
                elif isinstance(child, ctk.CTkButton):
                    child.configure(fg_color="#3a3a3a")
        
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
                    self.after(0, lambda m=mod_id, t=titulo: self.mostrar_info_mod(m, t))
                else:
                    self.after(0, lambda: self.lbl_info_buscar.configure(text="No se encontró en Steam"))
            else:
                self.after(0, lambda: self.lbl_info_buscar.configure(text="Error de conexión"))
        except Exception as e:
            self.after(0, lambda: self.lbl_info_buscar.configure(text=f"Error: {str(e)[:30]}"))

    def mostrar_info_mod(self, mod_id, titulo):
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
            
            filename = os.path.basename(filepath)
            nombre_mod = os.path.splitext(filename)[0]
            destino = os.path.join(mods_path, nombre_mod)
            
            try:
                if filepath.endswith(".zip"):
                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                        zip_ref.extractall(destino)
                else:
                    os.makedirs(destino, exist_ok=True)
                    shutil.copy2(filepath, destino)
                
                print(f"Mod instalado en: {destino}")
                self.actualizar_lista_mods()
            except Exception as e:
                print(f"Error instalando mod: {e}")

if __name__ == "__main__":
    app = IsaacRimLauncher()
    app.mainloop()
