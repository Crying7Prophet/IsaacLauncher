import sys
import os
import json
import subprocess
import shutil
import zipfile
import requests
import threading
import re
import tempfile

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QFrame, QLabel, QPushButton, QLineEdit, QListWidget,
    QScrollArea, QFileDialog, QMessageBox, QGridLayout, QSizePolicy
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import QUrl, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QImage, QColor

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

class DescargaThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, mod_id, config):
        super().__init__()
        self.mod_id = mod_id
        self.config = config
    
    def run(self):
        try:
            temp_dir = os.path.abspath("temp_downloads")
            os.makedirs(temp_dir, exist_ok=True)
            
            steamcmd_path = self.config.get("steamcmd_path", "steamcmd")
            
            comando = [
                steamcmd_path,
                "+force_install_dir", temp_dir,
                "+login", "anonymous",
                "+workshop_download_item", "250900", self.mod_id,
                "+quit"
            ]
            
            subprocess.run(comando, check=True, capture_output=True)
            
            origen = os.path.join(temp_dir, "steamapps", "workshop", "content", "250900", self.mod_id)
            destino = os.path.join(self.config["isaac_mods_path"], f"workshop_{self.mod_id}")
            
            if os.path.exists(origen):
                if os.path.exists(destino):
                    shutil.rmtree(destino)
                shutil.copytree(origen, destino)
                self.finished.emit(f"Mod {self.mod_id} instalado con éxito!")
            else:
                self.error.emit("SteamCMD terminó pero no se encontraron los archivos.")
        except Exception as e:
            self.error.emit(f"Error: {e}")

class SmodsThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, url_or_id, config):
        super().__init__()
        self.url_or_id = url_or_id
        self.config = config
    
    def run(self):
        try:
            url_or_id = self.url_or_id.strip()
            
            if "catalogue.smods.ru/archives/" in url_or_id:
                url = url_or_id
            elif url_or_id.isdigit():
                url = f"https://catalogue.smods.ru/archives/{url_or_id}"
            else:
                self.error.emit("URL inválida")
                return
            
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            download_match = re.search(r'href="(https?://[^"]+\.zip[^"]*)"', response.text)
            if not download_match:
                download_match = re.search(r'class="skymods-excerpt-btn"[^>]*href="([^"]+)"', response.text)
            
            if not download_match:
                self.error.emit("No se encontró enlace de descarga")
                return
            
            download_url = download_match.group(1)
            self.progress.emit("Descargando...")
            
            temp_dir = os.path.abspath("temp_downloads")
            os.makedirs(temp_dir, exist_ok=True)
            
            filepath = os.path.join(temp_dir, "mod.zip")
            
            response = requests.get(download_url, headers=headers, stream=True, timeout=120)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            mods_path = self.config["isaac_mods_path"]
            os.makedirs(mods_path, exist_ok=True)
            
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
                else:
                    destino = os.path.join(mods_path, "mod_sin_nombre")
                
                if os.path.exists(destino):
                    shutil.rmtree(destino)
                shutil.copytree(carpeta_extraida, destino)
            
            os.remove(filepath)
            self.finished.emit(f"Mod instalado en: {destino}")
            
        except Exception as e:
            self.error.emit(f"Error: {e}")
    
    def buscar_nombre_en_metadata(self, folder):
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file in ["metadata.xml", "metadata.txt", "info.xml", "info.txt"]:
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        match = re.search(r'<name>([^<]+)</name>', content, re.IGNORECASE)
                        if match:
                            return match.group(1).strip()
                        match = re.search(r'^Name\s*=\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
                        if match:
                            return match.group(1).strip()
                    except:
                        pass
        return None

class PyIsaacLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.config = cargar_config()
        self.zoom_level = 1.0
        self.mod_seleccionado = None
        self.mods_list = []
        self.entry_mods = None
        self.entry_isaac = None
        self.url_entry = None
        self.browser = None
        self.lbl_zoom = None
        
        self.setWindowTitle("PyIsaac Launcher v1.0")
        self.setGeometry(100, 100, 1100, 650)
        
        self.setup_ui()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.setup_header(main_layout)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #aaaaaa;
                padding: 10px 20px;
                border: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #3d3d3d;
            }
        """)
        main_layout.addWidget(self.tab_widget)
        
        self.tab_browser = QWidget()
        self.tab_browser.setStyleSheet("background-color: #1e1e1e;")
        self.tab_mods = QWidget()
        self.tab_mods.setStyleSheet("background-color: #1e1e1e;")
        self.tab_about = QWidget()
        self.tab_about.setStyleSheet("background-color: #1e1e1e;")
        
        self.tab_widget.addTab(self.tab_browser, "Browser")
        self.tab_widget.addTab(self.tab_mods, "Mods")
        self.tab_widget.addTab(self.tab_about, "About")
        
        self.setup_browser_tab()
        self.setup_mods_tab()
        self.setup_about_tab()
        
        self.tab_widget.setCurrentIndex(1)
        
    def setup_header(self, main_layout):
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            background-color: #252525;
            border-bottom: 1px solid #3d3d3d;
            padding: 10px;
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setSpacing(15)
        
        self.entry_mods = QLineEdit()
        self.entry_mods.setText(self.config.get("isaac_mods_path", get_default_mods_path()))
        self.entry_mods.setPlaceholderText("Mods path...")
        self.entry_mods.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border: 1px solid #1f538d;
            }
        """)
        
        btn_browse_mods = QPushButton("📁")
        btn_browse_mods.setFixedWidth(40)
        btn_browse_mods.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        btn_browse_mods.clicked.connect(self.browse_mods_path)
        
        self.entry_isaac = QLineEdit()
        self.entry_isaac.setText(self.config.get("isaac_exe_path", get_default_exe_path()))
        self.entry_isaac.setPlaceholderText("Game executable...")
        self.entry_isaac.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border: 1px solid #1f538d;
            }
        """)
        
        btn_browse_isaac = QPushButton("📁")
        btn_browse_isaac.setFixedWidth(40)
        btn_browse_isaac.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        btn_browse_isaac.clicked.connect(self.browse_isaac_path)
        
        self.btn_run = QPushButton("🎮 Run Game")
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #2d5a27;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d7a37;
            }
        """)
        self.btn_run.clicked.connect(self.ejecutar_isaac)
        
        label_mods = QLabel("Mods:")
        label_mods.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        label_game = QLabel("Game:")
        label_game.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        
        header_layout.addWidget(label_mods)
        header_layout.addWidget(self.entry_mods)
        header_layout.addWidget(btn_browse_mods)
        header_layout.addWidget(label_game)
        header_layout.addWidget(self.entry_isaac)
        header_layout.addWidget(btn_browse_isaac)
        header_layout.addWidget(self.btn_run)
        
        main_layout.addWidget(header_frame)
        
    def browse_mods_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Mods Folder")
        if path:
            self.entry_mods.setText(path)
            self.guardar_config()
            self.actualizar_lista_mods()
    
    def browse_isaac_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Game Executable", "", "Executable (*.exe)")
        if path:
            self.entry_isaac.setText(path)
            self.guardar_config()
    
    def guardar_config(self):
        self.config["isaac_mods_path"] = self.entry_mods.text()
        self.config["isaac_exe_path"] = self.entry_isaac.text()
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=4)
    
    def ejecutar_isaac(self):
        isaac_exe = self.entry_isaac.text()
        if isaac_exe and os.path.exists(isaac_exe):
            if IS_LINUX and not os.access(isaac_exe, os.X_OK):
                os.chmod(isaac_exe, 0o755)
            if IS_LINUX:
                exe_dir = os.path.dirname(isaac_exe)
                subprocess.Popen(["wine", os.path.basename(isaac_exe)], cwd=exe_dir)
            else:
                subprocess.Popen([isaac_exe])
        else:
            QMessageBox.warning(self, "Error", "Game executable not found.")
    
    def setup_browser_tab(self):
        layout = QVBoxLayout(self.tab_browser)
        layout.setContentsMargins(0, 0, 0, 0)
        
        nav_bar = QFrame()
        nav_bar.setStyleSheet("background-color: #252525; padding: 8px;")
        nav_bar_layout = QHBoxLayout(nav_bar)
        nav_bar_layout.setSpacing(8)
        
        btn_style = """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """
        
        btn_back = QPushButton("←")
        btn_back.setFixedWidth(40)
        btn_back.setStyleSheet(btn_style)
        btn_back.clicked.connect(self.atras)
        
        btn_forward = QPushButton("→")
        btn_forward.setFixedWidth(40)
        btn_forward.setStyleSheet(btn_style)
        btn_forward.clicked.connect(self.adelante)
        
        btn_reload = QPushButton("⟳")
        btn_reload.setFixedWidth(40)
        btn_reload.setStyleSheet(btn_style)
        btn_reload.clicked.connect(self.recargar)
        
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("Enter a URL...")
        self.url_entry.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border: 1px solid #1f538d;
            }
        """)
        self.url_entry.returnPressed.connect(self.navegar_url)
        
        btn_go = QPushButton("Go")
        btn_go.setFixedWidth(60)
        btn_go.setStyleSheet("""
            QPushButton {
                background-color: #1f538d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a6fbd;
            }
        """)
        btn_go.clicked.connect(self.navegar_url)
        
        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedWidth(35)
        btn_zoom_out.setStyleSheet(btn_style)
        btn_zoom_out.clicked.connect(self.zoom_out)
        
        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedWidth(35)
        btn_zoom_in.setStyleSheet(btn_style)
        btn_zoom_in.clicked.connect(self.zoom_in)
        
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setFixedWidth(50)
        self.lbl_zoom.setStyleSheet("color: #aaaaaa;")
        
        nav_bar_layout.addWidget(btn_back)
        nav_bar_layout.addWidget(btn_forward)
        nav_bar_layout.addWidget(btn_reload)
        nav_bar_layout.addWidget(self.url_entry, 1)
        nav_bar_layout.addWidget(btn_go)
        nav_bar_layout.addSpacing(10)
        nav_bar_layout.addWidget(btn_zoom_out)
        nav_bar_layout.addWidget(btn_zoom_in)
        nav_bar_layout.addWidget(self.lbl_zoom)
        
        layout.addWidget(nav_bar)
        
        download_bar = QFrame()
        download_bar.setStyleSheet("background-color: #252525; padding: 8px;")
        download_layout = QHBoxLayout(download_bar)
        download_layout.setSpacing(10)
        
        label_steam = QLabel("Steam ID:")
        label_steam.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        download_layout.addWidget(label_steam)
        
        self.mod_id_entry = QLineEdit()
        self.mod_id_entry.setPlaceholderText("Mod ID")
        self.mod_id_entry.setFixedWidth(150)
        self.mod_id_entry.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border: 1px solid #1f538d;
            }
        """)
        
        self.btn_download = QPushButton("Download")
        self.btn_download.setStyleSheet("""
            QPushButton {
                background-color: #1f538d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a6fbd;
            }
        """)
        self.btn_download.clicked.connect(self.descargar_por_id)
        
        self.btn_smods = QPushButton("From Smods")
        self.btn_smods.setStyleSheet("""
            QPushButton {
                background-color: #2d5a27;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d7a37;
            }
        """)
        self.btn_smods.clicked.connect(self.descargar_desde_smods)
        
        download_layout.addWidget(self.mod_id_entry)
        download_layout.addWidget(self.btn_download)
        download_layout.addWidget(self.btn_smods)
        download_layout.addStretch()
        
        layout.addWidget(download_bar)
        
        shortcuts_bar = QFrame()
        shortcuts_bar.setStyleSheet("background-color: #252525; padding: 8px;")
        shortcuts_layout = QHBoxLayout(shortcuts_bar)
        shortcuts_layout.setSpacing(8)
        
        label_links = QLabel("Links:")
        label_links.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        shortcuts_layout.addWidget(label_links)
        
        shortcuts = [
            ("Steam Workshop", "https://steamcommunity.com/app/250900/workshop/"),
            ("Smods", "https://catalogue.smods.ru/?app=250900"),
            ("NexusMods", "https://www.nexusmods.com/bindingofisaacrebirth"),
            ("ModDB", "https://www.moddb.com/games/the-binding-of-isaac-rebirth"),
            ("Modding of Isaac", "https://moddingofisaac.com/"),
        ]
        
        link_style = """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """
        
        for name, url in shortcuts:
            btn = QPushButton(name)
            btn.setStyleSheet(link_style)
            btn.clicked.connect(lambda checked, u=url: self.navegar_a(u))
            shortcuts_layout.addWidget(btn)
        
        shortcuts_layout.addStretch()
        layout.addWidget(shortcuts_bar)
        
        self.browser_frame = QFrame()
        layout.addWidget(self.browser_frame)
        
        browser_layout = QVBoxLayout(self.browser_frame)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        
        self.browser = QWebEngineView()
        
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        self.browser.urlChanged.connect(self.on_url_changed)
        
        browser_layout.addWidget(self.browser)
        self.browser.load(QUrl("https://steamcommunity.com/app/250900/workshop/"))
    
    def on_url_changed(self, url):
        self.url_entry.setText(url.toString())
    
    def setup_mods_tab(self):
        layout = QHBoxLayout(self.tab_mods)
        
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        
        toolbar = QFrame()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        
        toolbar_btn_style = """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """
        
        btn_refresh = QPushButton("↻")
        btn_refresh.setFixedWidth(35)
        btn_refresh.setStyleSheet(toolbar_btn_style)
        btn_refresh.clicked.connect(self.actualizar_lista_mods)
        
        btn_add = QPushButton("+")
        btn_add.setFixedWidth(35)
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #1f538d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a6fbd;
            }
        """)
        btn_add.clicked.connect(self.seleccionar_archivo)
        
        btn_delete = QPushButton("🗑")
        btn_delete.setFixedWidth(35)
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #8d1f1f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #bd2f2f;
            }
        """)
        btn_delete.clicked.connect(self.eliminar_mod_seleccionado)
        
        toolbar_layout.addWidget(btn_refresh)
        toolbar_layout.addWidget(btn_add)
        toolbar_layout.addWidget(btn_delete)
        toolbar_layout.addStretch()
        
        left_layout.addWidget(toolbar)
        
        self.lista_mods = QListWidget()
        self.lista_mods.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #1f538d;
            }
            QListWidget::item:hover {
                background-color: #2d2d2d;
            }
        """)
        self.lista_mods.itemClicked.connect(self.on_mod_select)
        left_layout.addWidget(self.lista_mods)
        
        layout.addWidget(left_panel, 1)
        
        center_panel = QFrame()
        center_panel.setStyleSheet("background-color: #1e1e1e;")
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(10, 10, 10, 10)
        
        self.lbl_info_titulo = QLabel("Select a mod")
        self.lbl_info_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        center_layout.addWidget(self.lbl_info_titulo)
        
        self.lbl_info_buscar = QLabel("")
        self.lbl_info_buscar.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        center_layout.addWidget(self.lbl_info_buscar)
        
        scroll_desc = QScrollArea()
        scroll_desc.setStyleSheet("border: none;")
        scroll_desc.setWidgetResizable(True)
        self.lbl_info_desc = QLabel("")
        self.lbl_info_desc.setStyleSheet("color: #cccccc;")
        self.lbl_info_desc.setWordWrap(True)
        scroll_desc.setWidget(self.lbl_info_desc)
        center_layout.addWidget(scroll_desc, 1)
        
        self.lbl_info_autor = QLabel("")
        self.lbl_info_autor.setStyleSheet("color: #888888; font-size: 12px;")
        center_layout.addWidget(self.lbl_info_autor)
        
        layout.addWidget(center_panel, 1)
        
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #1e1e1e;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        self.lbl_images_title = QLabel("Images")
        self.lbl_images_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        right_layout.addWidget(self.lbl_images_title)
        
        self.scroll_images = QScrollArea()
        self.scroll_images.setStyleSheet("border: none;")
        self.scroll_images.setWidgetResizable(True)
        self.images_widget = QWidget()
        self.images_widget.setStyleSheet("background-color: #1e1e1e;")
        self.images_layout = QVBoxLayout(self.images_widget)
        self.images_layout.setSpacing(10)
        self.scroll_images.setWidget(self.images_widget)
        right_layout.addWidget(self.scroll_images)
        
        layout.addWidget(right_panel, 1)
        
        self.actualizar_lista_mods()
    
    def setup_about_tab(self):
        layout = QVBoxLayout(self.tab_about)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.svg")
        if os.path.exists(logo_path):
            logo_widget = QSvgWidget(logo_path)
            logo_widget.setMinimumSize(150, 150)
            logo_widget.setMaximumSize(200, 200)
            logo_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            layout.addWidget(logo_widget)
        
        title = QLabel("PyIsaac Launcher")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff; margin-top: 10px;")
        layout.addWidget(title)
        
        version = QLabel("Version 1.0")
        version.setStyleSheet("color: #aaaaaa; font-size: 14px;")
        layout.addWidget(version)
        
        desc = QLabel("A mod manager for\nThe Binding of Isaac: Repentance")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #cccccc; margin: 10px 0px;")
        layout.addWidget(desc)
        
        features_title = QLabel("Features:")
        features_title.setStyleSheet("font-weight: bold; color: #ffffff; margin-top: 10px;")
        layout.addWidget(features_title)
        
        features = [
            "• Integrated browser for mod sites",
            "• Automatic metadata from Steam",
            "• Easy mod installation",
            "• Modern dark UI"
        ]
        
        for f in features:
            lbl = QLabel(f)
            lbl.setStyleSheet("color: #aaaaaa;")
            layout.addWidget(lbl)
        
        layout.addStretch()
    
    def actualizar_lista_mods(self):
        if self.entry_mods and self.entry_mods.text():
            mods_path = self.entry_mods.text()
        else:
            mods_path = self.config.get("isaac_mods_path", get_default_mods_path())
        
        if not mods_path or not os.path.exists(mods_path):
            os.makedirs(mods_path, exist_ok=True)
        
        self.procesar_zips_en_carpeta(mods_path)
        
        self.lista_mods.clear()
        
        items = os.listdir(mods_path)
        if not items:
            self.lista_mods.addItem("No mods installed")
            return
        
        self.mods_list = []
        
        for item in sorted(items):
            item_path = os.path.join(mods_path, item)
            if os.path.isdir(item_path):
                self.lista_mods.addItem(item)
                self.mods_list.append(item)
        
        if self.mods_list:
            self.lista_mods.setCurrentRow(0)
    
    def procesar_zips_en_carpeta(self, mods_path):
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
                        else:
                            nombre_base = os.path.splitext(item)[0]
                            destino = os.path.join(mods_path, nombre_base)
                        
                        if os.path.exists(destino):
                            shutil.rmtree(destino)
                        shutil.copytree(carpeta_extraida, destino)
                        
                        os.remove(zip_path)
                        print(f"Mod instalado: {destino}")
                        
                except Exception as e:
                    print(f"Error processing {item}: {e}")
    
    def on_mod_select(self, item):
        index = self.lista_mods.row(item)
        if index < len(self.mods_list):
            mod_name = self.mods_list[index]
            self.mod_seleccionado = mod_name
            self.mostrar_info_mod(mod_name)
    
    def mostrar_info_mod(self, nombre):
        self.mod_seleccionado = nombre
        self.lbl_info_titulo.setText(nombre)
        self.lbl_info_buscar.setText("Loading...")
        self.lbl_info_desc.setText("")
        self.lbl_info_autor.setText("")
        
        self.leer_metadata_local(nombre)
    
    def leer_metadata_local(self, nombre):
        import xml.etree.ElementTree as ET
        
        mods_path = self.entry_mods.text()
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
        
        self.lbl_info_titulo.setText(titulo)
        
        info_text = ""
        if version:
            info_text += f"Version: {version}"
        if tags:
            info_text += f" | Tags: {', '.join(tags)}"
        self.lbl_info_buscar.setText(info_text or "No metadata")
        self.lbl_info_desc.setText(descripcion)
        
        for i in range(self.images_layout.count()):
            widget = self.images_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        if imagenes:
            for img_path in imagenes:
                try:
                    pixmap = QPixmap(img_path)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        lbl = QLabel()
                        lbl.setPixmap(pixmap)
                        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.images_layout.addWidget(lbl)
                except Exception as e:
                    print(f"Error loading image {img_path}: {e}")
        else:
            placeholder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "placeholder.svg")
            if os.path.exists(placeholder_path):
                placeholder = QSvgWidget(placeholder_path)
                placeholder.setFixedSize(400, 300)
                self.images_layout.addWidget(placeholder)
            else:
                lbl = QLabel("No images")
                lbl.setStyleSheet("color: gray;")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.images_layout.addWidget(lbl)
    
    def eliminar_mod_seleccionado(self):
        if not self.mod_seleccionado:
            QMessageBox.information(self, "Info", "Select a mod first")
            return
        
        mods_path = self.entry_mods.text()
        mod_path = os.path.join(mods_path, self.mod_seleccionado)
        
        reply = QMessageBox.question(self, "Confirm", f"Delete mod: {self.mod_seleccionado}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes and os.path.exists(mod_path):
            shutil.rmtree(mod_path)
            print(f"Mod eliminado: {self.mod_seleccionado}")
            self.mod_seleccionado = None
            self.actualizar_lista_mods()
    
    def navegar_url(self):
        url = self.url_entry.text().strip()
        if url:
            if not url.startswith("http"):
                url = "https://" + url
            self.browser.setUrl(QUrl(url))
    
    def atras(self):
        self.browser.back()
    
    def adelante(self):
        self.browser.forward()
    
    def recargar(self):
        self.browser.reload()
    
    def zoom_in(self):
        self.zoom_level = min(2.0, self.zoom_level + 0.25)
        self.browser.setZoomFactor(self.zoom_level)
        self.lbl_zoom.setText(f"{int(self.zoom_level * 100)}%")
    
    def zoom_out(self):
        self.zoom_level = max(0.5, self.zoom_level - 0.25)
        self.browser.setZoomFactor(self.zoom_level)
        self.lbl_zoom.setText(f"{int(self.zoom_level * 100)}%")
    
    def navegar_a(self, url):
        if self.url_entry:
            self.url_entry.setText(url)
        if self.browser:
            self.browser.setUrl(QUrl(url))
    
    def descargar_por_id(self):
        mod_id = self.mod_id_entry.text().strip()
        if not mod_id:
            QMessageBox.warning(self, "Error", "Enter a mod ID")
            return
        
        if not mod_id.isdigit():
            QMessageBox.warning(self, "Error", "ID must be numbers only")
            return
        
        self.btn_download.setEnabled(False)
        self.btn_download.setText("Downloading...")
        
        self.descarga_thread = DescargaThread(mod_id, self.config)
        self.descarga_thread.progress.connect(lambda m: self.btn_download.setText(m))
        self.descarga_thread.finished.connect(lambda m: self.on_descarga_finished(m, True))
        self.descarga_thread.error.connect(lambda m: self.on_descarga_finished(m, False))
        self.descarga_thread.start()
    
    def descargar_desde_smods(self):
        url_or_id = self.mod_id_entry.text().strip()
        
        if not url_or_id:
            QMessageBox.warning(self, "Error", "Enter a Smods URL or mod ID")
            return
        
        self.btn_smods.setEnabled(False)
        self.btn_smods.setText("Searching...")
        
        self.smods_thread = SmodsThread(url_or_id, self.config)
        self.smods_thread.progress.connect(lambda m: self.btn_smods.setText(m))
        self.smods_thread.finished.connect(lambda m: self.on_descarga_finished(m, True))
        self.smods_thread.error.connect(lambda m: self.on_descarga_finished(m, False))
        self.smods_thread.start()
    
    def on_descarga_finished(self, message, success):
        self.btn_download.setEnabled(True)
        self.btn_download.setText("Download")
        self.btn_smods.setEnabled(True)
        self.btn_smods.setText("From Smods")
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.actualizar_lista_mods()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def seleccionar_archivo(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select downloaded file", "", "ZIP files (*.zip);;All files (*.*)")
        
        if filepath:
            mods_path = self.entry_mods.text()
            os.makedirs(mods_path, exist_ok=True)
            
            try:
                if filepath.endswith(".zip"):
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
                        else:
                            filename = os.path.basename(filepath)
                            nombre_mod = os.path.splitext(filename)[0]
                            destino = os.path.join(mods_path, nombre_mod)
                        
                        if os.path.exists(destino):
                            shutil.rmtree(destino)
                        
                        shutil.copytree(carpeta_extraida, destino)
                    
                    print(f"Mod instalado en: {destino}")
                    self.actualizar_lista_mods()
                else:
                    QMessageBox.warning(self, "Error", "Unsupported file format")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error installing mod: {e}")
    
    def buscar_nombre_en_metadata(self, folder):
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file in ["metadata.xml", "metadata.txt", "info.xml", "info.txt"]:
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        match = re.search(r'<name>([^<]+)</name>', content, re.IGNORECASE)
                        if match:
                            return match.group(1).strip()
                        
                        match = re.search(r'^Name\s*=\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
                        if match:
                            return match.group(1).strip()
                    except:
                        pass
        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(palette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(palette.ColorRole.Base, QColor(45, 45, 45))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(35, 35, 35))
    palette.setColor(palette.ColorRole.ToolTipBase, QColor(50, 50, 50))
    palette.setColor(palette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(palette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(palette.ColorRole.Button, QColor(60, 60, 60))
    palette.setColor(palette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(palette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(palette.ColorRole.Highlight, QColor(31, 83, 141))
    palette.setColor(palette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = PyIsaacLauncher()
    window.show()
    sys.exit(app.exec())
