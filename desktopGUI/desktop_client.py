import sys
import requests
import os
import math
from datetime import datetime, timezone
import tempfile
import shutil
import base64

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QDialog, QLabel, QMessageBox, QFileDialog, QCheckBox,
    QProgressDialog, QMenu, QWidgetAction, QStyledItemDelegate, QStyle,
    QTextEdit, QInputDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QSize, QRectF, QMimeData, QUrl
from PyQt6.QtGui import QIcon, QPainter, QColor, QFont, QPixmap, QBrush, QPen, QPainterPath, QDrag

# --- Helper Functions ---
def format_size(size_bytes):
    """Converts bytes to a human-readable format (KB, MB, GB)."""
    if size_bytes is None or size_bytes < 0:
        return "N/A"
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 1)
    return f"{s} {size_name[i]}"

# --- Custom Table Widget Items and Delegates ---
class SizeTableWidgetItem(QTableWidgetItem):
    """A QTableWidgetItem that sorts numerically based on a raw byte value."""
    def __init__(self, size_bytes):
        self.raw_size = size_bytes if size_bytes is not None else -1
        super().__init__(format_size(size_bytes))

    def __lt__(self, other):
        return self.raw_size < other.raw_size

class DateTimeTableWidgetItem(QTableWidgetItem):
    """A QTableWidgetItem that sorts by datetime object."""
    def __init__(self, iso_date_string):
        try:
            self.datetime_obj = datetime.fromisoformat(iso_date_string.replace('Z', '+00:00'))
            display_text = self.datetime_obj.astimezone(None).strftime('%d %b %Y at %H:%M')
        except (ValueError, TypeError):
            self.datetime_obj = datetime.min.replace(tzinfo=timezone.utc)
            display_text = "N/A"
            
        super().__init__(display_text)

    def __lt__(self, other):
        return self.datetime_obj < other.datetime_obj


class RoundedSelectionDelegate(QStyledItemDelegate):
    """A delegate to draw a continuous, rounded selection across a row."""
    def paint(self, painter, option, index):
        if not (option.state & QStyle.StateFlag.State_Selected):
            super().paint(painter, option, index)
            return
        
        first_col = -1
        for col in range(index.model().columnCount()):
            if not option.widget.isColumnHidden(col):
                first_col = col
                break
        
        if first_col == -1:
             super().paint(painter, option, index)
             return

        if index.column() == first_col:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            first_column_item = option.widget.item(index.row(), first_col)
            if first_column_item:
                full_row_rect = QRectF(
                    option.widget.visualItemRect(first_column_item).left(),
                    option.rect.y(),
                    option.widget.viewport().width(),
                    option.rect.height()
                )
                path = QPainterPath()
                path.addRoundedRect(full_row_rect, 8.0, 8.0)
                painter.fillPath(path, QBrush(QColor("#0d63f2")))
            painter.restore()

        painter.save()
        painter.setPen(QColor("white"))
        text = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        text_alignment = index.model().data(index, Qt.ItemDataRole.TextAlignmentRole)
        if text_alignment is None:
            text_alignment = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        text_rect = option.rect.adjusted(5, 0, -5, 0)
        painter.drawText(text_rect, text_alignment, text)
        painter.restore()

# --- Helper Class for Upload Progress ---
class ProgressTracker:
    """A file-like object that tracks read progress and calls a callback."""
    def __init__(self, file_path, callback=None):
        self.file = open(file_path, 'rb')
        self.total_size = os.path.getsize(file_path)
        self.bytes_read = 0
        self.callback = callback

    def read(self, size=-1):
        chunk = self.file.read(size)
        if chunk and self.callback:
            self.bytes_read += len(chunk)
            self.callback(self.bytes_read, self.total_size)
        return chunk

    def __len__(self):
        return self.total_size

    def __getattr__(self, attr):
        return getattr(self.file, attr)
        
    def close(self):
        self.file.close()

# --- API Client ---
class ApiClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
    def _get_headers(self):
        if not self.token: return {}
        return {"Authorization": f"Bearer {self.token}"}
    def signup(self, username, password):
        try:
            response = requests.post(f"{self.base_url}/auth/signup", json={"username": username, "password": password})
            response.raise_for_status()
            self.token = response.json().get("access_token")
            return True, ""
        except requests.exceptions.HTTPError as e: return False, e.response.json().get("detail", "Unknown error")
        except requests.exceptions.RequestException as e: return False, f"Connection error: {e}"
    def login(self, username, password):
        try:
            response = requests.post(f"{self.base_url}/auth/token", data={"username": username, "password": password})
            response.raise_for_status()
            self.token = response.json().get("access_token")
            return True, ""
        except requests.exceptions.HTTPError as e: return False, e.response.json().get("detail", "Invalid credentials")
        except requests.exceptions.RequestException as e: return False, f"Connection error: {e}"
    def get_files(self):
        if not self.token: return None, "Not authenticated"
        try:
            response = requests.get(f"{self.base_url}/files", headers=self._get_headers())
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e: return None, str(e)
    def upload_file(self, file_path, progress_callback=None):
        if not self.token: return False, "Not authenticated"
        progress_tracker = None
        try:
            file_name = os.path.basename(file_path)
            progress_tracker = ProgressTracker(file_path, progress_callback)
            files = {'file': (file_name, progress_tracker)}
            response = requests.post(f"{self.base_url}/files/upload", headers=self._get_headers(), files=files)
            response.raise_for_status()
            return True, None
        except requests.exceptions.RequestException as e: return False, str(e)
        finally:
            if progress_tracker:
                progress_tracker.close()
    def delete_file(self, filename):
        if not self.token: return False, "Not authenticated"
        try:
            response = requests.delete(f"{self.base_url}/files/delete/{filename}", headers=self._get_headers())
            response.raise_for_status()
            return True, None
        except requests.exceptions.RequestException as e: return False, str(e)
    def download_file(self, filename, save_path, progress_callback=None):
        if not self.token: return False, "Not authenticated"
        try:
            url = f"{self.base_url}/files/download/{filename}"
            with requests.get(url, headers=self._get_headers(), stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                bytes_downloaded = 0
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            if progress_callback:
                                bytes_downloaded += len(chunk)
                                progress_callback(bytes_downloaded, total_size)
            return True, None
        except requests.exceptions.RequestException as e: return False, str(e)

    def get_file_content(self, filename):
        if not self.token: return None, "Not authenticated"
        try:
            response = requests.get(f"{self.base_url}/files/content/{filename}", headers=self._get_headers())
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            return None, str(e)

    def rename_file(self, old_filename, new_name_base):
        if not self.token: return False, "Not authenticated"
        try:
            response = requests.put(
                f"{self.base_url}/files/rename/{old_filename}",
                headers=self._get_headers(),
                json={"new_name_base": new_name_base}
            )
            response.raise_for_status()
            return True, None
        except requests.exceptions.HTTPError as e:
            return False, e.response.json().get("detail", "Rename failed")
        except requests.exceptions.RequestException as e:
            return False, str(e)

    def update_file_content(self, filename, content_bytes):
        if not self.token: return False, "Not authenticated"
        try:
            encoded_content = base64.b64encode(content_bytes).decode('utf-8')
            response = requests.put(
                f"{self.base_url}/files/update/{filename}",
                headers=self._get_headers(),
                json={"content": encoded_content}
            )
            response.raise_for_status()
            return True, None
        except requests.exceptions.RequestException as e:
            return False, str(e)

# --- Modern Stylesheet (macOS Inspired) ---
STYLESHEET = """
QWidget { font-family: 'Helvetica Neue', 'Arial', sans-serif; font-size: 11pt; color: #e0e0e0; }
LoginDialog, MainWindow { background-color: #3c3c3c; }
LoginDialog #TitleLabel { font-size: 24pt; font-weight: bold; color: #ecf0f1; }
LoginDialog #SubtitleLabel { font-size: 10pt; color: #bdc3c7; }
QLineEdit { background-color: #4a4a4a; border: 1px solid #566573; border-radius: 8px; padding: 10px; color: #ecf0f1; }
QLineEdit:focus { border: 1px solid #0d63f2; }
QPushButton { background-color: #0d63f2; color: white; font-weight: bold; border: none; border-radius: 8px; padding: 10px 15px; min-height: 24px; }
QPushButton:hover { background-color: #0b58d1; }
QPushButton:pressed { background-color: #0a4cac; }
QPushButton:disabled { background-color: #555; color: #888; }
QPushButton#SecondaryButton { background-color: #555; }
QPushButton#SecondaryButton:hover { background-color: #666; }
QPushButton:checkable:checked { background-color: #0a4cac; border: 1px solid #0d63f2; }
QTableWidget { background-color: #3c3c3c; border: none; gridline-color: transparent; alternate-background-color: #464646; }
QTableWidget::item { padding: 8px 5px; border: none; color: #e0e0e0; }
QTableWidget::item:selected { color: white; background-color: transparent; }
QTableWidget::item:focus { border: none; outline: none; }
QHeaderView::section { background-color: #3c3c3c; padding: 5px; border: none; border-bottom: 1px solid #555; border-right: 1px solid #4a4a4a; }
QHeaderView::section:last { border-right: none; }
QMenu { background-color: #4a4a4a; border: 1px solid #555; padding: 5px; }
QMenu::item { padding: 5px 25px 5px 20px; }
QMenu::item:selected { background-color: #0d63f2; }
QMessageBox, QProgressDialog, QDialog { background-color: #4a4a4a; }
QProgressDialog { font-weight: bold; }
QLabel#StatusBar { font-size: 10pt; color: #a0a0a0; }
QTextEdit { background-color: #2e2e2e; border: 1px solid #555; border-radius: 8px; padding: 5px; color: #f0f0f0; }
"""

# --- SVG Icons ---
def create_icon_from_svg(svg_data, color="#ecf0f1"):
    svg_data = svg_data.replace('fill="currentColor"', f'fill="{color}"')
    pixmap = QPixmap()
    pixmap.loadFromData(svg_data.encode('utf-8'))
    return QIcon(pixmap)
ICON_UPLOAD = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z"/></svg>'
ICON_DOWNLOAD = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>'
ICON_DELETE = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>'
ICON_SYNC = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/></svg>'
ICON_REFRESH = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>'

# --- Preview and Edit Dialog ---
class PreviewDialog(QDialog):
    def __init__(self, filename, api_client, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.api_client = api_client
        self.is_text_file = filename.lower().endswith(('.c', '.py', '.txt'))
        self.is_image_file = filename.lower().endswith(('.jpg', '.jpeg', '.png'))
        self.setWindowTitle(f"Preview - {filename}"); self.setMinimumSize(700, 500); self.layout = QVBoxLayout(self)
        self.content_widget = None; self.edit_button = None; self.save_button = None
        self.load_content(); self.setup_buttons()
    def load_content(self):
        data, error = self.api_client.get_file_content(self.filename)
        if error: QMessageBox.critical(self, "Error", f"Could not load file content: {error}"); self.reject(); return
        content, encoding = data.get("content"), data.get("encoding")
        if self.is_image_file and encoding == 'base64':
            pixmap = QPixmap(); pixmap.loadFromData(base64.b64decode(content))
            image_label = QLabel(); image_label.setPixmap(pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)); image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_widget = image_label
        elif self.is_text_file:
            text_edit = QTextEdit(); text_edit.setPlainText(content); text_edit.setReadOnly(True); text_edit.setFont(QFont("Courier New", 11))
            self.content_widget = text_edit
        else:
            self.content_widget = QLabel("Preview is not available for this file type."); self.content_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.content_widget: self.layout.addWidget(self.content_widget)
    def setup_buttons(self):
        button_box = QDialogButtonBox()
        if self.is_text_file:
            self.edit_button = button_box.addButton("Edit", QDialogButtonBox.ButtonRole.ActionRole); self.save_button = button_box.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole); self.save_button.setEnabled(False)
            self.edit_button.clicked.connect(self.toggle_edit_mode); self.save_button.clicked.connect(self.save_content)
        close_button = button_box.addButton("Close", QDialogButtonBox.ButtonRole.RejectRole); close_button.clicked.connect(self.reject); self.layout.addWidget(button_box)
    def toggle_edit_mode(self):
        if self.content_widget and isinstance(self.content_widget, QTextEdit):
            self.content_widget.setReadOnly(False); self.edit_button.setEnabled(False); self.save_button.setEnabled(True); self.content_widget.setFocus()
    def save_content(self):
        if not (self.content_widget and isinstance(self.content_widget, QTextEdit)): return
        success, error = self.api_client.update_file_content(self.filename, self.content_widget.toPlainText().encode('utf-8'))
        if success:
            QMessageBox.information(self, "Success", "File updated successfully."); self.content_widget.setReadOnly(True); self.edit_button.setEnabled(True); self.save_button.setEnabled(False)
        else: QMessageBox.critical(self, "Save Failed", f"Could not save file: {error}")

# --- Custom Draggable Table Widget ---
class DraggableTableWidget(QTableWidget):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.temp_dir = tempfile.mkdtemp()
    
    def startDrag(self, supportedActions):
        selected_items = self.selectedItems()
        if not selected_items: return

        row = selected_items[0].row()
        filename_item = self.item(row, 0)
        if not filename_item: return
        filename = filename_item.text()

        temp_path = os.path.join(self.temp_dir, filename)
        success, error = self.api_client.download_file(filename, temp_path)

        if not success:
            QMessageBox.critical(self, "Drag Error", f"Could not prepare file for dragging: {error}")
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(temp_path)])
        
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        pixmap = QPixmap(self.viewport().grab(self.visualItemRect(selected_items[0])))
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())
        
        drag.exec(Qt.DropAction.CopyAction)

    def cleanup(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

# --- GUI ---
class LoginDialog(QDialog):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.username = None
        self.setWindowTitle("Cloud Drive - Authentication"); self.setModal(True); self.setFixedSize(400, 450)
        layout = QVBoxLayout(self); layout.setContentsMargins(40, 40, 40, 40); layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Cloud Drive"); title.setObjectName("TitleLabel"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Sign in to your account"); subtitle.setObjectName("SubtitleLabel"); subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.username_input = QLineEdit(); self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit(); self.password_input.setPlaceholderText("Password"); self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_btn = QPushButton("Login")
        self.signup_btn = QPushButton("Sign Up"); self.signup_btn.setObjectName("SecondaryButton")
        layout.addWidget(title); layout.addWidget(subtitle); layout.addSpacing(30)
        layout.addWidget(self.username_input); layout.addSpacing(10); layout.addWidget(self.password_input); layout.addSpacing(30)
        layout.addWidget(self.login_btn); layout.addSpacing(10); layout.addWidget(self.signup_btn)
        self.login_btn.clicked.connect(self.handle_login); self.signup_btn.clicked.connect(self.handle_signup)
    def handle_login(self):
        user, pwd = self.username_input.text(), self.password_input.text()
        success, message = self.api_client.login(user, pwd)
        if success: self.username = user; self.accept()
        else: QMessageBox.warning(self, "Login Failed", message)
    def handle_signup(self):
        user, pwd = self.username_input.text(), self.password_input.text()
        success, message = self.api_client.signup(user, pwd)
        if success: QMessageBox.information(self, "Signup Successful", "Account created and logged in."); self.username = user; self.accept()
        else: QMessageBox.warning(self, "Signup Failed", message)

class MainWindow(QWidget):
    def __init__(self, api_client, username):
        super().__init__()
        self.api_client = api_client; self.username = username
        self.all_files_data = []; self.current_filter = "all"
        self.COLUMNS = {"Name": 0, "Size": 1, "Uploaded By": 2, "Modified By": 3, "Date Created": 4, "Date Modified": 5}
        self.setAcceptDrops(True); self.init_ui(); self.refresh_files()
    def init_ui(self):
        self.setWindowTitle(f"Cloud Drive - Logged in as {self.username}"); self.setGeometry(100, 100, 1200, 700)
        main_layout = QVBoxLayout(self); main_layout.setContentsMargins(10, 10, 10, 10)
        top_layout = QHBoxLayout(); btn_layout = QHBoxLayout(); btn_layout.setSpacing(10)
        def create_tool_button(text, icon_svg, callback):
            btn = QPushButton(text); btn.setIcon(create_icon_from_svg(icon_svg)); btn.setIconSize(QSize(20, 20)); btn.clicked.connect(callback); return btn
        self.upload_btn = create_tool_button("Upload", ICON_UPLOAD, self.trigger_upload_dialog); self.download_btn = create_tool_button("Download", ICON_DOWNLOAD, self.download_file)
        self.delete_btn = create_tool_button("Delete", ICON_DELETE, self.delete_file); self.sync_btn = create_tool_button("Sync Folder", ICON_SYNC, self.sync_folder)
        self.refresh_btn = create_tool_button("Refresh", ICON_REFRESH, self.refresh_files)
        btn_layout.addWidget(self.upload_btn); btn_layout.addWidget(self.download_btn); btn_layout.addWidget(self.delete_btn); btn_layout.addWidget(self.sync_btn)
        top_layout.addLayout(btn_layout); top_layout.addStretch()
        filter_label = QLabel("Filter by:"); self.filter_all_btn = QPushButton("All Files"); self.filter_py_btn = QPushButton("Python (.py)"); self.filter_jpg_btn = QPushButton("Images (.jpg)")
        for btn in [self.filter_all_btn, self.filter_py_btn, self.filter_jpg_btn]: btn.setCheckable(True)
        self.filter_all_btn.setChecked(True)
        self.filter_all_btn.clicked.connect(lambda: self.apply_filter('all')); self.filter_py_btn.clicked.connect(lambda: self.apply_filter('py')); self.filter_jpg_btn.clicked.connect(lambda: self.apply_filter('jpg'))
        top_layout.addWidget(filter_label); top_layout.addWidget(self.filter_all_btn); top_layout.addWidget(self.filter_py_btn); top_layout.addWidget(self.filter_jpg_btn); top_layout.addStretch(); top_layout.addWidget(self.refresh_btn)
        main_layout.addLayout(top_layout)
        self.action_buttons = [self.upload_btn, self.download_btn, self.delete_btn, self.sync_btn, self.refresh_btn]
        self.file_table = DraggableTableWidget(self.api_client); self.file_table.setColumnCount(len(self.COLUMNS)); self.file_table.setHorizontalHeaderLabels(self.COLUMNS.keys())
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.file_table.setAlternatingRowColors(True); self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(self.COLUMNS["Name"], QHeaderView.ResizeMode.Interactive)
        self.file_table.setSortingEnabled(True); self.file_table.verticalHeader().setVisible(False); self.file_table.setShowGrid(False)
        self.file_table.setItemDelegate(RoundedSelectionDelegate(self.file_table)); self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self.show_file_context_menu); main_layout.addWidget(self.file_table)
        self.status_bar = QLabel("0 items"); self.status_bar.setObjectName("StatusBar"); self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter); main_layout.addWidget(self.status_bar)
        self.file_table.itemSelectionChanged.connect(self.update_status_bar); self.file_table.itemDoubleClicked.connect(self.open_preview)
        header = self.file_table.horizontalHeader(); header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); header.customContextMenuRequested.connect(self.show_header_context_menu)

    def closeEvent(self, event):
        self.file_table.cleanup()
        super().closeEvent(event)
    def apply_filter(self, filter_type):
        self.current_filter = filter_type; self.filter_all_btn.setChecked(filter_type == 'all'); self.filter_py_btn.setChecked(filter_type == 'py'); self.filter_jpg_btn.setChecked(filter_type == 'jpg')
        if filter_type == 'all': self.populate_table(self.all_files_data)
        elif filter_type == 'py': self.populate_table([f for f in self.all_files_data if f['name'].lower().endswith('.py')])
        elif filter_type == 'jpg': self.populate_table([f for f in self.all_files_data if f['name'].lower().endswith(('.jpg', '.jpeg', '.png'))])
    def show_file_context_menu(self, pos):
        if not self.file_table.selectedItems(): return
        menu = QMenu(self); rename_action = menu.addAction("Rename"); download_action = menu.addAction("Download"); delete_action = menu.addAction("Delete")
        action = menu.exec(self.file_table.mapToGlobal(pos))
        if action == rename_action: self.rename_file()
        elif action == download_action: self.download_file()
        elif action == delete_action: self.delete_file()
    def show_header_context_menu(self, pos):
        menu = QMenu(self)
        for col_name, col_idx in self.COLUMNS.items():
            action = QWidgetAction(menu); checkbox = QCheckBox(col_name); checkbox.setChecked(not self.file_table.isColumnHidden(col_idx))
            if col_name == "Name": checkbox.setEnabled(False)
            checkbox.toggled.connect(lambda checked, idx=col_idx: self.file_table.setColumnHidden(idx, not checked))
            action.setDefaultWidget(checkbox); menu.addAction(action)
        menu.exec(self.file_table.horizontalHeader().mapToGlobal(pos))
    def _set_controls_enabled(self, enabled):
        for button in self.action_buttons: button.setEnabled(enabled)
    def refresh_files(self):
        self._set_controls_enabled(False)
        files, error = self.api_client.get_files()
        if error: QMessageBox.critical(self, "Error", f"Could not fetch files: {error}"); self._set_controls_enabled(True); return
        self.all_files_data = files; self.apply_filter(self.current_filter); self._set_controls_enabled(True)
    def populate_table(self, files_data):
        self.file_table.setSortingEnabled(False); self.file_table.setRowCount(0); self.file_table.setRowCount(len(files_data))
        for row, file_info in enumerate(files_data):
            self.file_table.setItem(row, self.COLUMNS["Name"], QTableWidgetItem(file_info.get("name")))
            size_item = SizeTableWidgetItem(file_info.get("size")); size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.file_table.setItem(row, self.COLUMNS["Size"], size_item)
            self.file_table.setItem(row, self.COLUMNS["Uploaded By"], QTableWidgetItem(file_info.get("uploaded_by")))
            self.file_table.setItem(row, self.COLUMNS["Modified By"], QTableWidgetItem(file_info.get("last_modified_by")))
            self.file_table.setItem(row, self.COLUMNS["Date Created"], DateTimeTableWidgetItem(file_info.get("created_at", "")))
            self.file_table.setItem(row, self.COLUMNS["Date Modified"], DateTimeTableWidgetItem(file_info.get("modified_at", "")))
        self.file_table.setSortingEnabled(True); self.update_status_bar()
    def update_status_bar(self):
        selected = len(set(item.row() for item in self.file_table.selectedItems())); total = self.file_table.rowCount()
        self.status_bar.setText(f"{selected} of {total} selected" if selected > 0 else f"{total} items")
    def get_selected_filename(self):
        selected_rows = list(set(item.row() for item in self.file_table.selectedItems()))
        if not selected_rows: QMessageBox.warning(self, "No Selection", "Please select a file first."); return None
        return self.file_table.item(selected_rows[0], self.COLUMNS["Name"]).text()
    def _perform_upload(self, file_path):
        self._set_controls_enabled(False)
        try:
            file_name = os.path.basename(file_path)
            progress = QProgressDialog(f"Uploading {file_name}...", "Cancel", 0, 100, self); progress.setWindowModality(Qt.WindowModality.WindowModal); progress.setAutoClose(True); progress.setMinimumDuration(0)
            def update_progress(bytes_read, total_size):
                if total_size > 0: progress.setValue(int(bytes_read / total_size * 100))
                QApplication.processEvents()
                if progress.wasCanceled(): raise ConnectionAbortedError("Upload canceled by user.")
            success, error = self.api_client.upload_file(file_path, update_progress); progress.setValue(100)
            if success: self.refresh_files()
            else: QMessageBox.critical(self, "Upload Failed", str(error)); self._set_controls_enabled(True)
        except ConnectionAbortedError as e: QMessageBox.warning(self, "Upload Canceled", str(e)); self._set_controls_enabled(True)
        except Exception as e: QMessageBox.critical(self, "Upload Error", f"An unexpected error occurred: {e}"); self._set_controls_enabled(True)
    def trigger_upload_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select File(s) to Upload")
        for file_path in file_paths:
            if file_path: self._perform_upload(file_path)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if os.path.isfile(url.toLocalFile()): self._perform_upload(url.toLocalFile())
    def delete_file(self):
        filename = self.get_selected_filename()
        if filename and QMessageBox.question(self, "Confirm Delete", f"Delete {filename}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            success, error = self.api_client.delete_file(filename)
            if success: self.refresh_files()
            else: QMessageBox.critical(self, "Delete Failed", str(error))
    def download_file(self):
        filename = self.get_selected_filename()
        if filename:
            save_path, _ = QFileDialog.getSaveFileName(self, "Save File As", filename)
            if save_path:
                success, error = self.api_client.download_file(filename, save_path)
                if success: QMessageBox.information(self, "Success", f"Downloaded {filename}.")
                else: QMessageBox.critical(self, "Download Failed", str(error))
    def sync_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder to Sync")
        if not folder_path: return
        items = ("Upload to Cloud", "Download from Cloud"); item, ok = QInputDialog.getItem(self, "Sync Action", "Choose an action:", items, 0, False)
        if not ok or not item: return
        if item == "Upload to Cloud": self._execute_sync_upload(folder_path)
        elif item == "Download from Cloud": self._execute_sync_download(folder_path)
    def _execute_sync_upload(self, folder_path):
        local_files_to_upload = [entry.path for entry in os.scandir(folder_path) if entry.is_file()]
        if not local_files_to_upload:
            QMessageBox.information(self, "Sync Upload", "No files to upload in the selected folder.")
            return
        
        reply = QMessageBox.question(self, "Confirm Sync Upload", f"This will upload {len(local_files_to_upload)} files to the cloud. Continue?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return
            
        for file_path in local_files_to_upload:
            self._perform_upload(file_path)
        QMessageBox.information(self, "Sync Complete", "Folder sync upload process has finished.")
        
    def _execute_sync_download(self, folder_path):
        files_to_download = self.all_files_data
        if not files_to_download: QMessageBox.information(self, "Sync Download", "No remote files to download."); return
        progress = QProgressDialog("Downloading remote files...", "Cancel", 0, len(files_to_download), self); progress.setWindowModality(Qt.WindowModality.WindowModal); progress.setMinimumDuration(0)
        for i, file_info in enumerate(files_to_download):
            progress.setValue(i); filename = file_info['name']; progress.setLabelText(f"Downloading {filename}...")
            if progress.wasCanceled(): break
            save_path = os.path.join(folder_path, filename)
            success, error = self.api_client.download_file(filename, save_path)
            if not success: QMessageBox.critical(self, "Download Failed", f"Could not download {filename}: {error}"); break
        progress.setValue(len(files_to_download))
        if not progress.wasCanceled(): QMessageBox.information(self, "Download Complete", "All remote files have been downloaded.")
    def open_preview(self, item):
        filename = self.file_table.item(item.row(), self.COLUMNS["Name"]).text()
        if not filename.lower().endswith(('.c', '.jpg', '.jpeg', '.py', '.png', '.txt')):
             QMessageBox.information(self, "Preview Unavailable", "Preview is only supported for specified text and image files."); return
        dialog = PreviewDialog(filename, self.api_client, self); dialog.exec(); self.refresh_files()
    def rename_file(self):
        old_filename = self.get_selected_filename()
        if not old_filename: return
        base_name, _ = os.path.splitext(old_filename)
        new_name_base, ok = QInputDialog.getText(self, "Rename File", "Enter new name (without extension):", QLineEdit.EchoMode.Normal, base_name)
        if ok and new_name_base and new_name_base != base_name:
            success, error = self.api_client.rename_file(old_filename, new_name_base)
            if success: self.refresh_files()
            else: QMessageBox.critical(self, "Rename Failed", str(error))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    api = ApiClient("http://127.0.0.1:8000")
    login_dialog = LoginDialog(api)
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        main_window = MainWindow(api, login_dialog.username)
        main_window.show()
        exit_code = app.exec()
        main_window.file_table.cleanup()
        sys.exit(exit_code)

