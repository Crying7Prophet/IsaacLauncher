import sys
import os
import json
import subprocess
import shutil
import zipfile
import re
import tempfile

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QFrame, QLabel, QPushButton, QLineEdit, QListWidget,
    QScrollArea, QFileDialog, QMessageBox, QGridLayout, QSizePolicy, QDialog,
    QProgressBar, QMenu
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import QUrl, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QImage, QColor, QAction

from mod_downloader import abrir_skymods

IS_LINUX = sys.platform.startswith("linux")

def get_default_mods_path():
    return ""

def get_default_exe_path():
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


class BrowserView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._previous_url = None
        self._pending_popup = False
    
    def createWindow(self, window_type):
        self._previous_url = self.url()
        self._pending_popup = True
        return self


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
        
        self.setWindowTitle("PyIsaac Launcher")
        self.setGeometry(100, 100, 1100, 650)
        
        app = QApplication.instance()
        font = app.font()
        font.setPointSize(10)
        app.setFont(font)
        
        self.setup_ui()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.browser_window = None
        
        self.setup_header(main_layout)
        
        self.mods_content = QFrame()
        self.mods_content.setStyleSheet("background-color: #1e1e1e;")
        main_layout.addWidget(self.mods_content, 1)
        
        self.setup_mods_tab()
        
    def setup_header(self, main_layout):
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            background-color: #252525;
            border-bottom: 1px solid #3d3d3d;
            padding: 6px;
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(8)
        
        self.entry_mods = QLineEdit()
        self.entry_mods.setText(self.config.get("isaac_mods_path", get_default_mods_path()))
        self.entry_mods.setVisible(False)
        
        self.entry_isaac = QLineEdit()
        self.entry_isaac.setText(self.config.get("isaac_exe_path", get_default_exe_path()))
        self.entry_isaac.setVisible(False)
        
        self.btn_run = QPushButton("Launch")
        self.btn_run.setFixedSize(70, 28)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #2d5a27;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d7a37;
            }
        """)
        self.btn_run.clicked.connect(self.ejecutar_isaac)
        
        btn_settings = QPushButton("Settings")
        btn_settings.setFixedSize(70, 28)
        btn_settings.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        btn_settings.clicked.connect(self.show_settings_dialog)
        
        btn_about = QPushButton("About")
        btn_about.setFixedSize(70, 28)
        btn_about.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        btn_about.clicked.connect(self.show_about_dialog)
        
        header_layout.addStretch()
        header_layout.addWidget(self.btn_run)
        header_layout.addWidget(btn_settings)
        header_layout.addWidget(btn_about)
        
        main_layout.addWidget(header_frame)
        
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
                exe_dir = os.path.dirname(isaac_exe)
                subprocess.Popen([isaac_exe], cwd=exe_dir)
        else:
            QMessageBox.warning(self, "Error", "Game executable not found.")
    
    def show_browser_window(self):
        if self.browser_window and self.browser_window.isVisible():
            self.browser_window.raise_()
            self.browser_window.activateWindow()
            return
        
        self.browser_window = QDialog(self)
        self.browser_window.setWindowTitle("Browser")
        self.browser_window.setMinimumSize(750, 500)
        self.browser_window.resize(900, 550)
        self.browser_window.setStyleSheet("background-color: #1e1e1e;")
        
        layout = QVBoxLayout(self.browser_window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #252525;")
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(4, 2, 4, 2)
        toolbar_layout.setSpacing(0)
        
        btn_style = """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 3px 6px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """
        
        input_style = """
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 3px 6px;
            }
            QLineEdit:focus {
                border: 1px solid #1f538d;
            }
        """
        
        primary_btn_style = """
            QPushButton {
                background-color: #1f538d;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 3px 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a6fbd;
            }
        """
        
        link_style = """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """
        
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        
        btn_back = QPushButton("<")
        btn_back.setFixedSize(70, 28)
        btn_back.setStyleSheet(btn_style)
        btn_back.clicked.connect(self.atras)
        
        btn_forward = QPushButton(">")
        btn_forward.setFixedSize(70, 28)
        btn_forward.setStyleSheet(btn_style)
        btn_forward.clicked.connect(self.adelante)
        
        btn_reload = QPushButton("Reload")
        btn_reload.setFixedSize(70, 28)
        btn_reload.setStyleSheet(btn_style)
        btn_reload.clicked.connect(self.recargar)
        
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("Enter a URL...")
        self.url_entry.setStyleSheet(input_style)
        self.url_entry.returnPressed.connect(self.navegar_url)
        
        btn_go = QPushButton("Go")
        btn_go.setFixedSize(70, 28)
        btn_go.setStyleSheet(primary_btn_style)
        btn_go.clicked.connect(self.navegar_url)
        
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setFixedWidth(36)
        
        btn_zoom_out = QPushButton("-")
        btn_zoom_out.setFixedSize(70, 28)
        btn_zoom_out.setStyleSheet(btn_style)
        btn_zoom_out.clicked.connect(self.zoom_out)
        
        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(70, 28)
        btn_zoom_in.setStyleSheet(btn_style)
        btn_zoom_in.clicked.connect(self.zoom_in)
        
        row1.addWidget(btn_back)
        row1.addWidget(btn_forward)
        row1.addWidget(btn_reload)
        row1.addWidget(self.url_entry, 1)
        row1.addWidget(btn_go)
        row1.addWidget(btn_zoom_out)
        row1.addWidget(btn_zoom_in)
        row1.addWidget(self.lbl_zoom)
        
        toolbar_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        
        shortcuts = [
            ("Workshop", "https://steamcommunity.com/app/250900/workshop/"),
            ("Smods", "https://catalogue.smods.ru/?app=250900"),
            ("NexusMods", "https://www.nexusmods.com/bindingofisaacrebirth"),
            ("ModDB", "https://www.moddb.com/games/the-binding-of-isaac-rebirth"),
            ("ModIO", "https://moddingofisaac.com/"),
        ]
        
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #3d3d3d;")
        sep1.setFixedHeight(20)
        row2.addWidget(sep1)
        
        for name, url in shortcuts:
            btn = QPushButton(name)
            btn.setFixedSize(70, 28)
            btn.setStyleSheet(link_style)
            btn.clicked.connect(lambda checked, u=url: self.navegar_a(u))
            row2.addWidget(btn)
        
        row2.addStretch()
        
        toolbar_layout.addLayout(row2)
        
        layout.addWidget(toolbar)
        
        self.browser = BrowserView()
        
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        layout.addWidget(self.browser)
        
        self.browser_status = QFrame()
        self.browser_status.setStyleSheet("background-color: #252525; border-top: 1px solid #3d3d3d;")
        status_layout = QHBoxLayout(self.browser_status)
        status_layout.setContentsMargins(8, 2, 8, 2)
        self.browser_status_label = QLabel("Ready")
        self.browser_status_label.setStyleSheet("color: #888888;")
        status_layout.addWidget(self.browser_status_label)
        status_layout.addStretch()
        layout.addWidget(self.browser_status)
        
        self.browser.urlChanged.connect(self.on_url_changed)
        self.browser.urlChanged.connect(lambda: QTimer.singleShot(300, self.check_popup_navigation))
        self.browser.loadStarted.connect(lambda: self.browser_status_label.setText("Loading..."))
        self.browser.loadProgress.connect(lambda p: self.browser_status_label.setText(f"Loading... {p}%"))
        self.browser.loadFinished.connect(lambda ok: self.browser_status_label.setText("Ready" if ok else "Failed to load"))
        
        QWebEngineProfile.defaultProfile().downloadRequested.connect(self.on_download_requested)
        
        self.browser.load(QUrl("https://steamcommunity.com/app/250900/workshop/"))
        
        self.browser_window.show()
    
    def on_url_changed(self, url):
        self.url_entry.setText(url.toString())
        self.browser_status_label.setText(f"Navigating to {url.host()}")
    
    def check_popup_navigation(self):
        if not self.browser._pending_popup:
            return
        self.browser._pending_popup = False
        
        current_url = self.browser.url().toString()
        previous_url = self.browser._previous_url.toString() if self.browser._previous_url else ""
        
        reply = QMessageBox.question(
            self.browser_window,
            "Popup detected",
            f"A page tried to open a popup:\n\n{current_url}\n\nDo you want to stay on this page?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No and previous_url:
            self.browser.setUrl(QUrl(previous_url))
    
    def on_download_requested(self, download):
        filename = download.suggestedFileName()
        if not filename.lower().endswith('.zip'):
            download.reject()
            return
        
        total_bytes = download.totalBytes()
        if total_bytes > 0:
            size_mb = total_bytes / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB"
        else:
            size_str = "Unknown size"
        
        reply = QMessageBox.question(
            self.browser_window,
            "Download file",
            f"Do you want to download this file?\n\nName: {filename}\nSize: {size_str}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.No:
            download.reject()
            return
        
        temp_dir = os.path.abspath("temp_downloads")
        os.makedirs(temp_dir, exist_ok=True)
        
        download.setDownloadDirectory(temp_dir)
        download.setDownloadFileName(filename)
        download.accept()
        
        self.browser_status_label.setText(f"Downloading: {filename}")
        
        download.finished.connect(lambda: self.procesar_zip_descargado(
            os.path.join(temp_dir, filename)
        ))
    
    def procesar_zip_descargado(self, filepath, silent=False):
        mods_path = self.entry_mods.text() if self.entry_mods else self.config.get("isaac_mods_path", "")
        if not mods_path or not os.path.exists(mods_path):
            try:
                os.makedirs(mods_path, exist_ok=True)
            except (OSError, FileNotFoundError):
                if not silent and hasattr(self, "browser_status_label"):
                    self.browser_status_label.setText("Ready")
                if not silent:
                    QMessageBox.warning(self, "Error", f"Mods folder not found: {mods_path}\nSet a valid path in the settings tab")
                    return
                raise
        
        if not os.path.exists(filepath):
            if not silent and hasattr(self, "browser_status_label"):
                self.browser_status_label.setText("Ready")
            return
        
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
                destino = os.path.join(mods_path, self.sanitizar_nombre(nombre_oficial))
            else:
                nombre_base = os.path.splitext(os.path.basename(filepath))[0]
                destino = os.path.join(mods_path, nombre_base)
            
            if os.path.exists(destino):
                shutil.rmtree(destino)
            shutil.copytree(carpeta_extraida, destino)
        
        os.remove(filepath)
        if not silent and hasattr(self, "browser_status_label"):
            self.browser_status_label.setText("Ready")
        if not silent:
            self.actualizar_lista_mods()
            QMessageBox.information(self, "Success", f"Mod installed: {os.path.basename(destino)}")
    
    def setup_mods_tab(self):
        layout = QHBoxLayout(self.mods_content)
        
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
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """
        
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setFixedSize(70, 28)
        btn_refresh.setStyleSheet(toolbar_btn_style)
        btn_refresh.clicked.connect(self.actualizar_lista_mods)
        
        btn_add = QPushButton("Add")
        btn_add.setFixedSize(70, 28)
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #1f538d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a6fbd;
            }
        """)
        btn_add.clicked.connect(self.seleccionar_archivo)
        
        btn_delete = QPushButton("Delete")
        btn_delete.setFixedSize(70, 28)
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #8d1f1f;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #bd2f2f;
            }
        """)
        btn_delete.clicked.connect(self.eliminar_mod_seleccionado)
        
        btn_open_folder = QPushButton("Folder")
        btn_open_folder.setFixedSize(70, 28)
        btn_open_folder.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        btn_open_folder.clicked.connect(self.abrir_carpeta_mods)
        
        btn_download = QPushButton("Download")
        btn_download.setFixedSize(80, 28)
        btn_download.setStyleSheet("""
            QPushButton {
                background-color: #1f538d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a6fbd;
            }
        """)
        
        btn_download.clicked.connect(lambda: abrir_skymods(self, self.browser, self.entry_mods.text()))
        
        toolbar_layout.addWidget(btn_refresh)
        toolbar_layout.addWidget(btn_add)
        toolbar_layout.addWidget(btn_delete)
        toolbar_layout.addWidget(btn_open_folder)
        toolbar_layout.addWidget(btn_download)
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
        self.lbl_info_titulo.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.lbl_info_titulo.setAlignment(Qt.AlignmentFlag.AlignTop)
        center_layout.addWidget(self.lbl_info_titulo)
        
        self.lbl_info_desc = QLabel("")
        self.lbl_info_desc.setStyleSheet("color: #cccccc;")
        self.lbl_info_desc.setWordWrap(True)
        self.lbl_info_desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        center_layout.addWidget(self.lbl_info_desc)
        
        center_layout.addStretch()
        
        layout.addWidget(center_panel, 1)
        
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #1e1e1e;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
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
    
    def show_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setFixedSize(520, 180)
        dialog.setStyleSheet("background-color: #1e1e1e;")
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)
        
        input_style = """
            QLineEdit {
                background-color: #252525;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 8px;
            }
            QLineEdit:focus {
                border: 1px solid #1f538d;
            }
        """
        browse_style = """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """
        save_style = """
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
        """
        
        mods_row = QHBoxLayout()
        mods_label = QLabel("Mods path:")
        mods_label.setFixedWidth(100)
        mods_label.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        entry_mods = QLineEdit(self.entry_mods.text())
        entry_mods.setStyleSheet(input_style)
        btn_browse_mods = QPushButton("...")
        btn_browse_mods.setFixedSize(70, 28)
        btn_browse_mods.setStyleSheet(browse_style)
        
        def browse_mods():
            path = QFileDialog.getExistingDirectory(dialog, "Select Mods Folder")
            if path:
                entry_mods.setText(path)
        btn_browse_mods.clicked.connect(browse_mods)
        
        mods_row.addWidget(mods_label)
        mods_row.addWidget(entry_mods, 1)
        mods_row.addWidget(btn_browse_mods)
        layout.addLayout(mods_row)
        
        game_row = QHBoxLayout()
        game_label = QLabel("Game exe:")
        game_label.setFixedWidth(100)
        game_label.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        entry_game = QLineEdit(self.entry_isaac.text())
        entry_game.setStyleSheet(input_style)
        btn_browse_game = QPushButton("...")
        btn_browse_game.setFixedSize(70, 28)
        btn_browse_game.setStyleSheet(browse_style)
        
        def browse_game():
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Game Executable", "", "Executable (*.exe)")
            if path:
                entry_game.setText(path)
        btn_browse_game.clicked.connect(browse_game)
        
        game_row.addWidget(game_label)
        game_row.addWidget(entry_game, 1)
        game_row.addWidget(btn_browse_game)
        layout.addLayout(game_row)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton("Save")
        btn_save.setFixedSize(70, 28)
        btn_save.setStyleSheet(save_style)
        
        def save_settings():
            self.entry_mods.setText(entry_mods.text())
            self.entry_isaac.setText(entry_game.text())
            self.guardar_config()
            self.actualizar_lista_mods()
            dialog.close()
        btn_save.clicked.connect(save_settings)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)
        
        dialog.exec()
    
    def show_about_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About")
        dialog.setFixedSize(360, 200)
        dialog.setStyleSheet("background-color: #1e1e1e;")
        
        layout = QVBoxLayout(dialog)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)
        
        title = QLabel("PyIsaac Launcher")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        version = QLabel("Version 1.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        desc = QLabel("A mod manager for\nThe Binding of Isaac: Repentance")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #cccccc; margin: 6px 0px;")
        layout.addWidget(desc)
        
        github_label = QLabel('<a href="https://github.com/Crying7Prophet/IsaacLauncher">GitHub</a>')
        github_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github_label.setOpenExternalLinks(True)
        layout.addWidget(github_label)
        
        layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.setFixedSize(70, 28)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)
        
        dialog.exec()
    
    def actualizar_lista_mods(self):
        if self.entry_mods and self.entry_mods.text():
            mods_path = self.entry_mods.text()
        else:
            mods_path = self.config.get("isaac_mods_path", get_default_mods_path())
        
        if not mods_path or not os.path.exists(mods_path):
            try:
                os.makedirs(mods_path, exist_ok=True)
            except (OSError, FileNotFoundError):
                self.lista_mods.clear()
                self.lista_mods.addItem("Mods folder not found")
                self.lista_mods.addItem(f"Configured path: {mods_path}")
                self.lista_mods.addItem("Set a valid path in the settings tab")
                return
        
        self.procesar_zips_en_carpeta(mods_path)
        
        self.lista_mods.clear()
        
        try:
            items = os.listdir(mods_path)
        except OSError:
            self.lista_mods.addItem("Could not read mods folder")
            return
        if not items:
            self.lista_mods.addItem("No mods installed")
            return
        
        self.mods_list = []
        
        for item in sorted(items):
            item_path = os.path.join(mods_path, item)
            if os.path.isdir(item_path):
                self.mods_list.append(item)
                self.lista_mods.addItem(item)
        
        if self.mods_list:
            self.lista_mods.setCurrentRow(0)
            self.on_mod_select(self.lista_mods.currentItem())
        else:
            self.mod_seleccionado = None
            self.mostrar_info_mod("")
    
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
                            destino = os.path.join(mods_path, self.sanitizar_nombre(nombre_oficial))
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
        self.mod_seleccionado = nombre if nombre else None
        
        if not nombre:
            self.lbl_info_titulo.setText("Select a mod")
            self.lbl_info_desc.setText("")
            
            for i in range(self.images_layout.count()):
                widget = self.images_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            
            placeholder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "placeholder.svg")
            if os.path.exists(placeholder_path):
                placeholder = QSvgWidget(placeholder_path)
                placeholder.setFixedSize(200, 150)
                self.images_layout.addWidget(placeholder)
            else:
                lbl = QLabel("No images")
                lbl.setStyleSheet("color: gray;")
                self.images_layout.addWidget(lbl)
            return
        
        self.lbl_info_titulo.setText(nombre)
        self.lbl_info_desc.setText("Loading...")
        
        self.leer_metadata_local(nombre)
    
    def leer_metadata_local(self, nombre):
        import xml.etree.ElementTree as ET
        
        if self.entry_mods and self.entry_mods.text():
            mods_path = self.entry_mods.text()
        else:
            mods_path = self.config.get("isaac_mods_path", get_default_mods_path())
        
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
        
        self.lbl_info_titulo.setText("")
        
        html = f"<h3 style='color:#ffffff;'>{titulo}</h3>"
        if version or tags:
            meta_parts = []
            if version:
                meta_parts.append(f"Version: {version}")
            if tags:
                meta_parts.append(f"Tags: {', '.join(tags)}")
            html += f"<p style='color:#aaaaaa;'>{' | '.join(meta_parts)}</p>"
        if descripcion:
            html += f"<p style='color:#cccccc;'>{descripcion}</p>"
        self.lbl_info_desc.setText(html)
        
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
                placeholder.setFixedSize(200, 150)
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
            self.mod_seleccionado = None
            self.actualizar_lista_mods()
    
    def abrir_carpeta_mods(self):
        mods_path = self.entry_mods.text() if self.entry_mods else self.config.get("isaac_mods_path", get_default_mods_path())
        if mods_path and os.path.exists(mods_path):
            if IS_LINUX:
                subprocess.run(["xdg-open", mods_path])
            elif sys.platform == "darwin":
                subprocess.run(["open", mods_path])
            else:
                os.startfile(mods_path)
        else:
            QMessageBox.warning(self, "Error", "Mods folder not found")
    
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
    
    def seleccionar_archivo(self):
        filepaths, _ = QFileDialog.getOpenFileNames(self, "Select mod files", "", "ZIP files (*.zip);;All files (*.*)")
        
        if not filepaths:
            return
        
        zip_files = [f for f in filepaths if f.endswith(".zip")]
        non_zip = [f for f in filepaths if not f.endswith(".zip")]
        
        if non_zip:
            names = ", ".join(os.path.basename(f) for f in non_zip[:3])
            if len(non_zip) > 3:
                names += f" and {len(non_zip) - 3} more"
            QMessageBox.warning(self, "Skipped files", f"The following files are not ZIP and were skipped:\n{names}")
        
        if not zip_files:
            QMessageBox.warning(self, "Error", "No valid ZIP files selected")
            return
        
        mods_path = self.entry_mods.text()
        try:
            os.makedirs(mods_path, exist_ok=True)
        except (OSError, FileNotFoundError):
            QMessageBox.warning(self, "Error", f"Mods folder not found: {mods_path}\nSet a valid path in the settings tab")
            return
        
        total = len(zip_files)
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Installing mods")
        progress_dialog.setFixedSize(420, 120)
        progress_dialog.setStyleSheet("background-color: #1e1e1e;")
        progress_dialog.setWindowFlags(progress_dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        progress_layout = QVBoxLayout(progress_dialog)
        progress_layout.setContentsMargins(16, 16, 16, 16)
        progress_layout.setSpacing(10)
        
        lbl_status = QLabel(f"[1/{total}] Preparing...")
        lbl_status.setStyleSheet("color: #ffffff; font-weight: bold;")
        lbl_status.setAlignment(Qt.AlignmentFlag.AlignLeft)
        progress_layout.addWidget(lbl_status)
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, total)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("%v / %m")
        progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                height: 20px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #1f538d;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(progress_bar)
        
        progress_dialog.show()
        QApplication.processEvents()
        
        installed = []
        failed = []
        
        for i, filepath in enumerate(zip_files):
            filename = os.path.basename(filepath)
            lbl_status.setText(f"[{i + 1}/{total}] Installing: {filename}")
            progress_bar.setValue(i)
            QApplication.processEvents()
            
            try:
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
                        destino = os.path.join(mods_path, self.sanitizar_nombre(nombre_oficial))
                    else:
                        nombre_mod = os.path.splitext(filename)[0]
                        destino = os.path.join(mods_path, nombre_mod)
                    
                    if os.path.exists(destino):
                        shutil.rmtree(destino)
                    
                    shutil.copytree(carpeta_extraida, destino)
                
                installed.append(filename)
                print(f"Mod instalado en: {destino}")
            
            except Exception as e:
                failed.append(f"{filename}: {e}")
                print(f"Error installing {filename}: {e}")
        
        progress_bar.setValue(total)
        lbl_status.setText("Done!")
        QApplication.processEvents()
        progress_dialog.close()
        
        self.actualizar_lista_mods()
        
        if not failed:
            QMessageBox.information(self, "Success", f"Successfully installed {len(installed)} mod(s)")
        else:
            failed_names = "\n".join(failed[:10])
            if len(failed) > 10:
                failed_names += f"\n...and {len(failed) - 10} more"
            QMessageBox.warning(
                self, "Import complete",
                f"Installed: {len(installed)} mod(s)\nFailed: {len(failed)} mod(s)\n\n{failed_names}"
            )
    
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

    def sanitizar_nombre(self, name):
        return re.sub(r'[\\/:*?"<>|]', '_', name).strip()

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
