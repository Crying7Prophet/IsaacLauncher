import re
import os
import tempfile
import html as html_module
import requests

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QSizePolicy, QMessageBox,
    QProgressBar, QTextBrowser
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QBuffer
from PyQt6.QtGui import QPixmap, QImage

SKYMODS_BASE = "https://catalogue.smods.ru"
SKYMODS_APP = "250900"


def _esc(text):
    return html_module.escape(str(text)).replace("'", "&#39;")


class SkymodItem:
    def __init__(self, title="", page_url="", download_url="", author="",
                 file_size="", thumbnail_url="", categories=None):
        self.title = title
        self.page_url = page_url
        self.download_url = download_url
        self.author = author
        self.file_size = file_size
        self.thumbnail_url = thumbnail_url
        self.categories = categories or []


class SkymodsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            resp = requests.get(self.url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            resp.raise_for_status()
            items = self._parse_html(resp.text)
            self.finished.emit(items)
        except Exception as e:
            self.error.emit(str(e))

    def _parse_html(self, text):
        items = []
        articles = re.findall(
            r'<article\b[^>]*class="[^"]*grid-item[^"]*"[^>]*>(.*?)</article>',
            text, re.DOTALL
        )
        for article in articles:
            title = ""
            page_url = ""
            m = re.search(
                r'<h2\s+class="post-title[^"]*">\s*<a\s+href="([^"]+)"[^>]*>([^<]+)</a>',
                article, re.DOTALL
            )
            if m:
                page_url = m.group(1).strip()
                title = html_module.unescape(m.group(2).strip())

            thumbnail_url = ""
            m = re.search(r'<div\s+class="post-thumbnail">\s*<a[^>]*>\s*<img\s+src="([^"]+)"', article, re.DOTALL)
            if m:
                thumbnail_url = m.group(1).strip()

            download_url = ""
            m = re.search(r'<a\s+class="skymods-excerpt-btn[^"]*"\s+href="([^"]+)"[^>]*>Download</a>', article)
            if m:
                download_url = m.group(1).strip()

            author = ""
            m = re.search(r'Author:\s*</?\w+>?\s*<a[^>]*>([^<]+)</a>', article)
            if m:
                author = html_module.unescape(m.group(1).strip())

            file_size = ""
            m = re.search(r'<span\s+class="skymods-item-file-size"[^>]*>([^<]+)</span>', article)
            if m:
                file_size = html_module.unescape(m.group(1).strip())

            categories = []
            m = re.search(r'<p\s+class="post-category">(.*?)</p>', article, re.DOTALL)
            if m:
                categories = [
                    html_module.unescape(c.strip())
                    for c in re.findall(r'>([^<]+)<', m.group(1))
                    if c.strip() and c.strip() != "/"
                ]

            if title:
                items.append(SkymodItem(
                    title=title,
                    page_url=page_url,
                    download_url=download_url,
                    author=author,
                    file_size=file_size,
                    thumbnail_url=thumbnail_url,
                    categories=categories,
                ))
        return items


class ThumbnailLoader(QThread):
    finished = pyqtSignal(object, QPixmap)

    def __init__(self, item, url):
        super().__init__()
        self.item = item
        self.url = url

    def run(self):
        try:
            resp = requests.get(self.url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0"
            })
            img = QImage()
            img.loadFromData(resp.content)
            pixmap = QPixmap.fromImage(img)
            self.finished.emit(self.item, pixmap)
        except Exception:
            pass


class DetailLoader(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            resp = requests.get(self.url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            resp.raise_for_status()
            html_content = self._parse_detail(resp.text)
            self.finished.emit(html_content)
        except Exception as e:
            self.error.emit(str(e))

    def _parse_detail(self, text):
        title = ""
        m = re.search(r'<h1\s+class="post-title[^"]*"[^>]*>([^<]+)</h1>', text)
        if m:
            title = html_module.unescape(m.group(1).strip())

        preview_img = ""
        m = re.search(
            r'<div\s+class="skymods-single-preview-wrap">\s*<img\s+src="([^"]+)"',
            text, re.DOTALL
        )
        if m:
            preview_img = m.group(1).strip()

        meta_html = ""
        m = re.search(
            r'<div\s+class="skymods-single-meta">(.*?)</div>\s*(?:<h5|<div)',
            text, re.DOTALL
        )
        if m:
            raw = m.group(1)
            meta_html = self._clean_meta(raw)

        desc = ""
        m = re.search(
            r'<h5>Description:</h5>(.*?)<div\s+class="skymods-single-after"',
            text, re.DOTALL
        )
        if m:
            desc = m.group(1).strip()
            desc = self._download_images(desc)
            desc = self._clean_description(desc)

        parts = []
        if title:
            parts.append(
                f'<h2 style="color:#ffffff;margin:0 0 12px 0;">{_esc(title)}</h2>'
            )
        if meta_html:
            parts.append(meta_html)
        if preview_img:
            data_uri = self._fetch_image_as_data_uri(preview_img, max_w=600)
            if data_uri:
                parts.append(
                    f'<p><img src="{data_uri}" style="max-width:100%;border-radius:6px;"></p>'
                )
        if desc:
            parts.append(desc)
        if not parts:
            parts.append(
                '<p style="color:#888;text-align:center;margin-top:40px;">No description available.</p>'
            )
        return "\n".join(parts)

    def _clean_meta(self, raw):
        items = []
        for m in re.finditer(r'<p>(.*?)</p>', raw, re.DOTALL):
            inner = m.group(1)
            inner = re.sub(r'<svg[^>]*>.*?</svg>', '', inner, flags=re.DOTALL)
            inner = re.sub(r'<[^>]+>', ' ', inner).strip()
            inner = " ".join(inner.split())
            inner = html_module.unescape(inner)
            if inner:
                items.append(inner)
        if not items:
            return ""
        lines = "".join(f'<li style="margin:3px 0;color:#cccccc;">{_esc(it)}</li>' for it in items)
        return (
            '<div style="background:#252525;border:1px solid #3d3d3d;border-radius:6px;'
            'padding:8px 12px;margin:0 0 12px 0;"><ul style="list-style:none;padding:0;margin:0;">'
            f'{lines}</ul></div>'
        )

    def _clean_description(self, desc):
        desc = re.sub(r'<div\s+class="[^"]*"[^>]*>\s*</div>', '', desc)
        desc = re.sub(r'<hr\s*/?\s*>', '<hr style="border:0;border-top:1px solid #3d3d3d;margin:12px 0;">', desc)
        desc = re.sub(
            r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>',
            lambda m: f'<a href="{_esc(m.group(1))}" style="color:#3b8dbd;">{m.group(2)}</a>',
            desc
        )
        desc = re.sub(
            r'<(?:strong|b)>(.*?)</(?:strong|b)>',
            r'<strong style="color:#ffffff;">\1</strong>',
            desc
        )
        desc = re.sub(
            r'<(?:em|i)>(.*?)</(?:em|i)>',
            r'<em style="color:#dddddd;">\1</em>',
            desc
        )
        desc = re.sub(
            r'<p([^>]*)>',
            r'<p\1 style="color:#cccccc;margin:6px 0;line-height:1.5;">',
            desc
        )
        desc = re.sub(
            r'<h([1-6])([^>]*)>',
            lambda m: f'<h{m.group(1)}{m.group(2)} style="color:#ffffff;margin:12px 0 6px 0;">',
            desc
        )
        return desc

    def _download_images(self, desc):
        urls = re.findall(r'<img\s+src="([^"]+)"', desc)
        for url in urls:
            data_uri = self._fetch_image_as_data_uri(url, max_w=600)
            if data_uri:
                desc = desc.replace(f'src="{url}"', f'src="{data_uri}"')
        return desc

    def _fetch_image_as_data_uri(self, url, max_w=600):
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            img = QImage()
            img.loadFromData(resp.content)
            if img.isNull():
                return None
            if img.width() > max_w:
                img = img.scaledToWidth(max_w, Qt.TransformationMode.SmoothTransformation)
            import base64
            buf = QBuffer()
            buf.open(QBuffer.OpenModeFlag.WriteOnly)
            img.save(buf, "PNG")
            b64 = base64.b64encode(buf.data()).decode()
            buf.close()
            return f"data:image/png;base64,{b64}"
        except Exception:
            return None


class DownloadWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/131.0.0.0 Safari/537.36",
    }

    def __init__(self, url, title="mod"):
        super().__init__()
        self.url = url
        self.title = title

    def run(self):
        try:
            self.progress.emit("Fetching download page...")
            session = requests.Session()
            session.headers.update(self.HEADERS)

            resp = session.get(self.url, timeout=20)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")

            if "text/html" not in content_type:
                filepath = self._save_response(resp)
                self.finished.emit(filepath)
                return

            form_data = self._parse_download_form(resp.text)
            if not form_data:
                self.error.emit("Could not parse download page")
                return

            self.progress.emit("Creating download link...")
            post_resp = session.post(
                self.url, data=form_data, timeout=30, allow_redirects=True
            )
            post_resp.raise_for_status()
            post_ct = post_resp.headers.get("Content-Type", "")

            if "text/html" not in post_ct:
                filepath = self._save_response(post_resp)
                self.finished.emit(filepath)
                return

            direct_url = self._find_direct_link(post_resp.text)
            if direct_url:
                self.progress.emit("Downloading mod...")
                dl_resp = session.get(direct_url, timeout=60, stream=True)
                dl_resp.raise_for_status()
                filepath = self._save_response(dl_resp)
                self.finished.emit(filepath)
                return

            self.error.emit("Could not obtain download link")
        except Exception as e:
            self.error.emit(str(e))

    def _parse_download_form(self, html_text):
        fields = {"op": "download2"}
        for name in ("id", "rand", "referer", "method_free", "method_premium"):
            m = re.search(
                rf'<input[^>]+name="{name}"[^>]+value="([^"]*)"', html_text
            )
            fields[name] = m.group(1) if m else ""
        if "id" not in fields or not fields["id"]:
            m = re.search(r'name="id"\s+value="([^"]+)"', html_text)
            if m:
                fields["id"] = m.group(1)
        return fields if fields.get("id") else None

    def _find_direct_link(self, html_text):
        patterns = [
            r'<a[^>]+href="([^"]+\.zip[^"]*)"',
            r'(https?://[^\s"\'<>]+\.zip\b[^\s"\'<>]*)',
            r'<a[^>]+id="downloadbtn"[^>]+href="([^"]+)"',
        ]
        for pat in patterns:
            m = re.search(pat, html_text, re.IGNORECASE)
            if m:
                url = html_module.unescape(m.group(1).strip())
                if not url.startswith("http"):
                    url = "https://modsbase.com" + url
                return url
        return None

    def _save_response(self, resp):
        temp_dir = os.path.join(os.getcwd(), "temp_downloads")
        os.makedirs(temp_dir, exist_ok=True)

        cd = resp.headers.get("Content-Disposition", "")
        fname = ""
        m = re.search(r'filename="?([^";\s]+)"?', cd)
        if m:
            fname = m.group(1)

        if not fname:
            from urllib.parse import urlparse, unquote
            path = urlparse(resp.url).path
            fname = unquote(os.path.basename(path)) or "mod_download.zip"

        if not fname.endswith(".zip"):
            fname += ".zip"

        filepath = os.path.join(temp_dir, fname)
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        if os.path.getsize(filepath) < 100:
            try:
                with open(filepath, "r", errors="replace") as f:
                    text = f.read(500)
                if "<html" in text.lower() or "<!doctype" in text.lower():
                    os.remove(filepath)
                    raise Exception("Download page returned instead of file")
            except UnicodeDecodeError:
                pass

        return filepath


class DownloadProgressDialog(QDialog):
    def __init__(self, parent, queue):
        super().__init__(parent)
        self.queue = list(queue)
        self.cancelled = False
        self.failed = []
        self.succeeded = []
        self.current_worker = None

        self.setWindowTitle("Downloading Mods")
        self.setMinimumSize(450, 160)
        self.setFixedSize(450, 160)
        self.setStyleSheet("background-color: #1e1e1e;")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.lbl_status = QLabel(f"Preparing... (0/{len(self.queue)})")
        self.lbl_status.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
        layout.addWidget(self.lbl_status)

        self.lbl_detail = QLabel("")
        self.lbl_detail.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self.lbl_detail)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.queue))
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #1f538d;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedSize(80, 28)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: 1px solid #5a2d2d;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover { background-color: #5a2d2d; border-color: #5a2d2d; }
        """)
        self.btn_cancel.clicked.connect(self._cancel)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def start(self):
        self._process_next()

    def _process_next(self):
        if self.cancelled:
            self._finish()
            return

        idx = len(self.succeeded) + len(self.failed)
        if idx >= len(self.queue):
            self._finish()
            return

        item = self.queue[idx]
        self.lbl_status.setText(f"Downloading {idx + 1}/{len(self.queue)}: {item.title}")
        self.lbl_detail.setText("Fetching download page...")

        worker = DownloadWorker(item.download_url, item.title)
        self.current_worker = worker

        def on_progress(text):
            if not self.cancelled:
                self.lbl_detail.setText(text)

        def on_finished(filepath):
            self.current_worker = None
            if self.cancelled:
                return
            self.lbl_detail.setText("Installing...")
            try:
                self.parent().procesar_zip_descargado(filepath, silent=True)
                self.succeeded.append(item)
            except Exception as e:
                self.failed.append((item, str(e)))
            self.progress_bar.setValue(len(self.succeeded) + len(self.failed))
            self._process_next()

        def on_error(msg):
            self.current_worker = None
            if self.cancelled:
                return
            self.failed.append((item, msg))
            self.progress_bar.setValue(len(self.succeeded) + len(self.failed))
            self._process_next()

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.start()

    def _cancel(self):
        self.cancelled = True
        if self.current_worker:
            self.current_worker.terminate()
        self._finish()

    def _finish(self):
        self.btn_cancel.setEnabled(False)
        total = len(self.queue)
        ok = len(self.succeeded)
        fail = len(self.failed)
        self.parent().actualizar_lista_mods()

        if self.cancelled:
            self.lbl_status.setText("Cancelled")
            self.lbl_detail.setText(f"Completed: {ok} | Failed: {fail} | Remaining: {total - ok - fail}")
        else:
            self.lbl_status.setText("All done!")
            if fail:
                names = ", ".join(it.title for it, _ in self.failed[:5])
                extra = f" (+{fail - 5} more)" if fail > 5 else ""
                self.lbl_detail.setText(f"Installed: {ok} | Failed: {fail}: {names}{extra}")
            else:
                self.lbl_detail.setText(f"Successfully installed {ok} mod(s)")

        self.btn_cancel.setText("Close")
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.clicked.disconnect()
        self.btn_cancel.clicked.connect(self.accept)


class SkymodsDialog(QDialog):
    def __init__(self, parent, browser, mods_path):
        super().__init__(parent)
        self.browser = browser
        self.mods_path = mods_path
        self.current_page = 1
        self.total_pages = 1
        self.search_query = ""
        self.items = []
        self.workers = []
        self.thumb_loaders = []
        self.download_queue = []
        self.card_buttons = {}

        self.setWindowTitle("Skymods - Mod Browser")
        self.setMinimumSize(1100, 550)
        self.resize(1200, 600)
        self.setStyleSheet("background-color: #1e1e1e;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        search_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search mods...")
        self.search_entry.setStyleSheet("""
            QLineEdit {
                background-color: #252525;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border: 1px solid #1f538d;
            }
        """)
        self.search_entry.returnPressed.connect(self.buscar)
        search_layout.addWidget(self.search_entry)

        btn_search = QPushButton("Search")
        btn_search.setFixedSize(70, 30)
        btn_search.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: 1px solid #1f538d;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1f538d;
                border-color: #1f538d;
            }
        """)
        btn_search.clicked.connect(self.buscar)
        search_layout.addWidget(btn_search)

        btn_browser = QPushButton("Browser")
        btn_browser.setFixedSize(70, 30)
        btn_browser.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #3d3d3d;
            }
        """)
        btn_browser.clicked.connect(lambda: self.parent().show_browser_window())
        search_layout.addWidget(btn_browser)

        layout.addLayout(search_layout)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")
        self.mods_container = QFrame()
        self.mods_container.setStyleSheet("background-color: #1e1e1e;")
        self.mods_layout = QVBoxLayout(self.mods_container)
        self.mods_layout.setContentsMargins(0, 0, 0, 0)
        self.mods_layout.setSpacing(6)
        self.mods_layout.addStretch()
        self.scroll_area.setWidget(self.mods_container)
        content_layout.addWidget(self.scroll_area, 1)

        self.detail_browser = QTextBrowser()
        self.detail_browser.setOpenExternalLinks(True)
        self.detail_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        self.detail_browser.setHtml(
            "<p style='color:#888;text-align:center;margin-top:40px;'>"
            "Select a mod to view details</p>"
        )
        content_layout.addWidget(self.detail_browser, 1)

        layout.addLayout(content_layout, 1)

        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("< Prev")
        self.btn_prev.setFixedSize(70, 28)
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover { background-color: #3d3d3d; border-color: #3d3d3d; }
            QPushButton:disabled { color: #555555; border-color: #333333; }
        """)
        self.btn_prev.clicked.connect(self.pagina_anterior)
        nav_layout.addWidget(self.btn_prev)

        self.lbl_page = QLabel("Page 1")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page.setStyleSheet("color: #cccccc;")
        nav_layout.addWidget(self.lbl_page)

        self.btn_download_all = QPushButton("Download All (0)")
        self.btn_download_all.setFixedSize(130, 28)
        self.btn_download_all.setEnabled(False)
        self.btn_download_all.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: 1px solid #1f538d;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1f538d; border-color: #1f538d; }
            QPushButton:disabled { color: #555555; border-color: #333333; }
        """)
        self.btn_download_all.clicked.connect(self.start_queue_download)
        nav_layout.addWidget(self.btn_download_all)

        self.btn_next = QPushButton("Next >")
        self.btn_next.setFixedSize(70, 28)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover { background-color: #3d3d3d; border-color: #3d3d3d; }
            QPushButton:disabled { color: #555555; border-color: #333333; }
        """)
        self.btn_next.clicked.connect(self.pagina_siguiente)
        nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)

        self.lbl_status = QLabel("Loading...")
        self.lbl_status.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        self.cargar_pagina()

    def _build_url(self, page=1):
        if self.search_query:
            if page > 1:
                return f"{SKYMODS_BASE}/page/{page}/?s={self.search_query}&app={SKYMODS_APP}"
            return f"{SKYMODS_BASE}/?s={self.search_query}&app={SKYMODS_APP}"
        if page > 1:
            return f"{SKYMODS_BASE}/page/{page}/?app={SKYMODS_APP}"
        return f"{SKYMODS_BASE}/?app={SKYMODS_APP}"

    def cargar_pagina(self):
        self.lbl_status.setText("Loading mods...")
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

        url = self._build_url(self.current_page)
        self.worker = SkymodsWorker(url)
        self.worker.finished.connect(self._on_loaded)
        self.worker.error.connect(self._on_error)
        self.workers.append(self.worker)
        self.worker.start()

    def _on_loaded(self, items):
        self.items = items
        self._clear_mods()

        if items:
            self.total_pages = max(self.current_page, self.current_page)
            self.lbl_page.setText(f"Page {self.current_page}")

        for item in items:
            self._add_mod_card(item)

        self.lbl_status.setText(f"Loaded {len(items)} mods")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(len(items) >= 10)

    def _on_error(self, msg):
        self.lbl_status.setText(f"Error: {msg}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(False)

    def _clear_mods(self):
        for loader in self.thumb_loaders:
            try:
                loader.finished.disconnect()
            except TypeError:
                pass
        self.thumb_loaders.clear()
        self.card_buttons.clear()
        while self.mods_layout.count():
            child = self.mods_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.mods_layout.addStretch()

    def _add_mod_card(self, item):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
            }
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(12)

        thumb_label = QLabel()
        thumb_label.setFixedSize(120, 68)
        thumb_label.setStyleSheet("background-color: #1e1e1e; border-radius: 4px;")
        thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_label.setText("No img")
        card_layout.addWidget(thumb_label)

        if item.thumbnail_url:
            loader = ThumbnailLoader(item, item.thumbnail_url)
            loader.finished.connect(lambda it, pm, lbl=thumb_label: self._set_thumbnail(lbl, pm))
            self.thumb_loaders.append(loader)
            loader.start()

        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)

        title_label = QLabel(item.title)
        title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        title_label.setWordWrap(True)
        info_layout.addWidget(title_label)

        meta_parts = []
        if item.author:
            meta_parts.append(f"Author: {item.author}")
        if item.file_size:
            meta_parts.append(f"Size: {item.file_size}")
        if meta_parts:
            meta_label = QLabel("  |  ".join(meta_parts))
            meta_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
            info_layout.addWidget(meta_label)

        if item.categories:
            cat_layout = QHBoxLayout()
            cat_layout.setSpacing(4)
            for cat in item.categories[:4]:
                cat_label = QLabel(cat)
                cat_label.setStyleSheet("""
                    background-color: transparent;
                    color: #ffffff;
                    border: 1px solid #1f538d;
                    border-radius: 3px;
                    padding: 1px 6px;
                    font-size: 10px;
                """)
                cat_layout.addWidget(cat_label)
            cat_layout.addStretch()
            info_layout.addLayout(cat_layout)

        info_layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_download = QPushButton("Download")
        btn_download.setFixedSize(80, 26)
        is_queued = item.download_url in [q.download_url for q in self.download_queue]
        if is_queued:
            btn_download.setText("Queued")
            btn_download.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #ffffff;
                    border: 1px solid #8b6914;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #8b6914;
                    border-color: #8b6914;
                }
            """)
        else:
            btn_download.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #ffffff;
                    border: 1px solid #2d5a27;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2d5a27;
                    border-color: #2d5a27;
                }
            """)
        btn_download.clicked.connect(lambda checked, i=item, b=btn_download: self.toggle_queue(i, b))
        self.card_buttons[item.download_url] = btn_download
        btn_row.addWidget(btn_download)

        info_layout.addLayout(btn_row)
        card_layout.addLayout(info_layout, 1)

        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda e, url=item.page_url: self._show_mod_detail(url)

        self.mods_layout.insertWidget(self.mods_layout.count() - 1, card)

    def _set_thumbnail(self, label, pixmap):
        try:
            import sip
            if sip.isdeleted(label):
                return
        except (ImportError, RuntimeError):
            pass
        if not pixmap.isNull():
            scaled = pixmap.scaled(120, 68, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(scaled)

    def _show_mod_detail(self, url):
        self.detail_browser.setHtml(
            "<p style='color:#888;text-align:center;margin-top:40px;'>Loading...</p>"
        )
        self.detail_loader = DetailLoader(url)
        self.detail_loader.finished.connect(
            lambda html: self.detail_browser.setHtml(html)
        )
        self.detail_loader.error.connect(
            lambda msg: self.detail_browser.setHtml(
                f'<p style="color:#ff6666;text-align:center;margin-top:40px;">'
                f'Error loading details: {_esc(msg)}</p>'
            )
        )
        self.detail_loader.start()

    def buscar(self):
        self.search_query = self.search_entry.text().strip()
        self.current_page = 1
        self.cargar_pagina()

    def pagina_anterior(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.cargar_pagina()

    def pagina_siguiente(self):
        self.current_page += 1
        self.cargar_pagina()

    def toggle_queue(self, item, btn):
        queued_urls = [q.download_url for q in self.download_queue]
        if item.download_url in queued_urls:
            self.download_queue = [q for q in self.download_queue if q.download_url != item.download_url]
            btn.setText("Download")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #ffffff;
                    border: 1px solid #2d5a27;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #2d5a27; border-color: #2d5a27; }
            """)
        else:
            self.download_queue.append(item)
            btn.setText("Queued")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #ffffff;
                    border: 1px solid #8b6914;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #8b6914; border-color: #8b6914; }
            """)
        self._update_download_all_button()

    def _update_download_all_button(self):
        n = len(self.download_queue)
        self.btn_download_all.setText(f"Download All ({n})")
        self.btn_download_all.setEnabled(n > 0)

    def _restore_queued_buttons(self):
        queued_urls = {q.download_url for q in self.download_queue}
        for url, btn in self.card_buttons.items():
            if url in queued_urls:
                btn.setText("Queued")
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #ffffff;
                        border: 1px solid #8b6914;
                        border-radius: 4px;
                        padding: 4px 10px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #8b6914; border-color: #8b6914; }
                """)
            else:
                btn.setText("Download")
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #ffffff;
                        border: 1px solid #2d5a27;
                        border-radius: 4px;
                        padding: 4px 10px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #2d5a27; border-color: #2d5a27; }
                """)

    def start_queue_download(self):
        if not self.download_queue:
            return
        dialog = DownloadProgressDialog(self.parent(), self.download_queue)
        dialog.exec()
        self.download_queue.clear()
        self.card_buttons.clear()
        self._restore_queued_buttons()
        self._update_download_all_button()


def abrir_skymods(parent, browser, mods_path):
    dialog = SkymodsDialog(parent, browser, mods_path)
    dialog.exec()
