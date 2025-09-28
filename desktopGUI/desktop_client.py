import sys
import requests
import os
import math
from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QDialog, QLabel, QMessageBox, QFileDialog, QCheckBox,
    QProgressDialog, QMenu, QWidgetAction, QStyledItemDelegate, QStyle
)
from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtGui import QIcon, QPainter, QColor, QFont, QPixmap, QBrush, QPen, QPainterPath
import base64

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

class RoundedSelectionDelegate(QStyledItemDelegate):
    """A delegate to draw a continuous, rounded selection across a row."""
    def paint(self, painter, option, index):
        # Fallback to default painting if the item is not selected
        if not (option.state & QStyle.StateFlag.State_Selected):
            super().paint(painter, option, index)
            return

        # --- If selected, handle all painting manually to ensure correct appearance ---

        # Find the first visible column to ensure we only draw the background once
        first_col = -1
        for col in range(index.model().columnCount()):
            if not option.widget.isColumnHidden(col):
                first_col = col
                break
        
        # If all columns are somehow hidden, fallback to default painting
        if first_col == -1:
             super().paint(painter, option, index)
             return

        # Draw the main selection background only once per row (when painting the first visible column)
        if index.column() == first_col:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # CRITICAL FIX: Get the QTableWidgetItem, not the QModelIndex
            first_column_item = option.widget.item(index.row(), first_col)

            # Ensure item exists before trying to get its rectangle
            if first_column_item:
                full_row_rect = QRectF(
                    option.widget.visualItemRect(first_column_item).left(),
                    option.rect.y(),
                    option.widget.viewport().width(),
                    option.rect.height()
                )
                
                selection_color = QColor("#0d63f2")
                radius = 8.0
                path = QPainterPath()
                path.addRoundedRect(full_row_rect, radius, radius)
                painter.fillPath(path, QBrush(selection_color))
            
            painter.restore()

        # Now, draw the text for the current cell manually to ensure it's white
        painter.save()
        painter.setPen(QColor("white"))
        
        text = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        
        # Get alignment from the item itself, otherwise use a default
        text_alignment = index.model().data(index, Qt.ItemDataRole.TextAlignmentRole)
        if text_alignment is None:
            text_alignment = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        
        # Add some horizontal padding to the text's drawing rectangle
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
    def download_file(self, filename, save_path):
        if not self.token: return False, "Not authenticated"
        try:
            url = f"{self.base_url}/files/download/{filename}"
            with requests.get(url, headers=self._get_headers(), stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
            return True, None
        except requests.exceptions.RequestException as e: return False, str(e)
    def sync_folder(self, folder_path):
        if not self.token: return False, "Not authenticated"
        try:
            response = requests.post(f"{self.base_url}/files/sync", headers=self._get_headers(), json={"local_folder_path": folder_path})
            response.raise_for_status()
            return True, response.json().get('message', 'Sync completed')
        except requests.exceptions.RequestException as e: return False, str(e)

# --- Modern Stylesheet (macOS Inspired) ---
STYLESHEET = """
QWidget {
    font-family: 'Helvetica Neue', 'Arial', sans-serif;
    font-size: 11pt;
    color: #e0e0e0;
}
LoginDialog, MainWindow {
    background-color: #3c3c3c;
}
LoginDialog #TitleLabel {
    font-size: 24pt;
    font-weight: bold;
    color: #ecf0f1;
}
LoginDialog #SubtitleLabel {
    font-size: 10pt;
    color: #bdc3c7;
}
QLineEdit {
    background-color: #4a4a4a;
    border: 1px solid #566573;
    border-radius: 8px;
    padding: 10px;
    color: #ecf0f1;
}
QLineEdit:focus {
    border: 1px solid #0d63f2;
}
QPushButton {
    background-color: #0d63f2;
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 10px 15px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #0b58d1;
}
QPushButton:pressed {
    background-color: #0a4cac;
}
QPushButton:disabled {
    background-color: #555;
    color: #888;
}
QPushButton#SecondaryButton {
    background-color: #555;
}
QPushButton#SecondaryButton:hover {
    background-color: #666;
}
QTableWidget {
    background-color: #3c3c3c;
    border: none;
    gridline-color: transparent;
    alternate-background-color: #464646;
}
QTableWidget::item {
    padding: 8px 5px;
    border: none;
    color: #e0e0e0;
}
QTableWidget::item:selected {
    color: white; /* Text color is handled by the delegate */
    background-color: transparent; /* Background is handled by delegate */
}
QHeaderView::section {
    background-color: #3c3c3c;
    padding: 5px;
    border: none;
    border-bottom: 1px solid #555;
    font-weight: bold;
}
QMenu {
    background-color: #4a4a4a;
    border: 1px solid #555;
    padding: 5px;
}
QMenu::item {
    padding: 5px 25px 5px 20px;
}
QMenu::item:selected {
    background-color: #0d63f2;
}
QMessageBox, QProgressDialog {
     background-color: #4a4a4a;
}
QProgressDialog {
    font-weight: bold;
}
QLabel#StatusBar {
    font-size: 10pt;
    color: #a0a0a0;
}
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


# --- GUI ---
class LoginDialog(QDialog):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.username = None
        self.setWindowTitle("Cloud Drive - Authentication")
        self.setModal(True)
        self.setFixedSize(400, 450)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Cloud Drive")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Sign in to your account")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_btn = QPushButton("Login")
        self.signup_btn = QPushButton("Sign Up")
        self.signup_btn.setObjectName("SecondaryButton")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(30)
        layout.addWidget(self.username_input)
        layout.addSpacing(10)
        layout.addWidget(self.password_input)
        layout.addSpacing(30)
        layout.addWidget(self.login_btn)
        layout.addSpacing(10)
        layout.addWidget(self.signup_btn)
        self.login_btn.clicked.connect(self.handle_login)
        self.signup_btn.clicked.connect(self.handle_signup)

    def handle_login(self):
        user, pwd = self.username_input.text(), self.password_input.text()
        success, message = self.api_client.login(user, pwd)
        if success: self.username = user; self.accept()
        else: QMessageBox.warning(self, "Login Failed", message)

    def handle_signup(self):
        user, pwd = self.username_input.text(), self.password_input.text()
        success, message = self.api_client.signup(user, pwd)
        if success:
            QMessageBox.information(self, "Signup Successful", "Account created and logged in.")
            self.username = user; self.accept()
        else: QMessageBox.warning(self, "Signup Failed", message)

class MainWindow(QWidget):
    def __init__(self, api_client, username):
        super().__init__()
        self.api_client = api_client
        self.username = username
        self.current_files = []
        self.COLUMNS = {"Name": 0, "Size": 1, "Uploaded By": 2, "Modified By": 3, "Date Created": 4, "Date Modified": 5}
        self.setAcceptDrops(True)
        self.init_ui()
        self.refresh_files()

    def init_ui(self):
        self.setWindowTitle(f"Cloud Drive - Logged in as {self.username}")
        self.setGeometry(100, 100, 1200, 700)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Button Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        def create_tool_button(text, icon_svg, callback):
            btn = QPushButton(text)
            btn.setIcon(create_icon_from_svg(icon_svg))
            btn.setIconSize(QSize(20, 20))
            btn.clicked.connect(callback)
            return btn
        self.upload_btn = create_tool_button("Upload", ICON_UPLOAD, self.trigger_upload_dialog)
        self.download_btn = create_tool_button("Download", ICON_DOWNLOAD, self.download_file)
        self.delete_btn = create_tool_button("Delete", ICON_DELETE, self.delete_file)
        self.sync_btn = create_tool_button("Sync Folder", ICON_SYNC, self.sync_folder)
        self.refresh_btn = create_tool_button("Refresh", ICON_REFRESH, self.refresh_files)

        btn_layout.addWidget(self.upload_btn)
        btn_layout.addWidget(self.download_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.sync_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)
        main_layout.addLayout(btn_layout)
        self.action_buttons = [self.upload_btn, self.download_btn, self.delete_btn, self.sync_btn, self.refresh_btn]

        # File Table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(len(self.COLUMNS))
        self.file_table.setHorizontalHeaderLabels(self.COLUMNS.keys())
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(self.COLUMNS["Name"], QHeaderView.ResizeMode.Interactive)
        self.file_table.setSortingEnabled(True)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setShowGrid(False)
        
        # Apply the custom delegate for rounded selections
        self.file_table.setItemDelegate(RoundedSelectionDelegate(self.file_table))
        
        main_layout.addWidget(self.file_table)

        # Status Bar
        self.status_bar = QLabel("0 items")
        self.status_bar.setObjectName("StatusBar")
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_bar)
        
        # Connect signals
        self.file_table.itemSelectionChanged.connect(self.update_status_bar)

        # Header Context Menu for showing/hiding columns
        header = self.file_table.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_header_context_menu)

    def show_header_context_menu(self, pos):
        menu = QMenu(self)
        for col_name, col_idx in self.COLUMNS.items():
            # Use a QWidgetAction to host a checkbox, which prevents the menu from closing on click
            action = QWidgetAction(menu)
            checkbox = QCheckBox(col_name)
            checkbox.setChecked(not self.file_table.isColumnHidden(col_idx))
            if col_name == "Name":
                checkbox.setEnabled(False)
            checkbox.toggled.connect(
                lambda checked, idx=col_idx: self.file_table.setColumnHidden(idx, not checked)
            )
            action.setDefaultWidget(checkbox)
            menu.addAction(action)
        menu.exec(self.file_table.horizontalHeader().mapToGlobal(pos))

    def _set_controls_enabled(self, enabled):
        for button in self.action_buttons:
            button.setEnabled(enabled)

    def refresh_files(self):
        self._set_controls_enabled(False)
        self.file_table.setSortingEnabled(False)
        self.file_table.setRowCount(0)
        files, error = self.api_client.get_files()
        if error:
            QMessageBox.critical(self, "Error", f"Could not fetch files: {error}")
            self._set_controls_enabled(True)
            return
        
        self.current_files = [f.get("name") for f in files]
        self.file_table.setRowCount(len(files))
        for row, file_info in enumerate(files):
            def format_utc_to_local(date_str):
                try:
                    utc_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    local_dt = utc_dt.astimezone(None)
                    # Format: 29 Sep 2025 at 22:58
                    return local_dt.strftime('%d %b %Y at %H:%M')
                except (ValueError, TypeError): return "N/A"
            self.file_table.setItem(row, self.COLUMNS["Name"], QTableWidgetItem(file_info.get("name")))
            
            # Use the custom item for correct sorting
            size_item = SizeTableWidgetItem(file_info.get("size"))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.file_table.setItem(row, self.COLUMNS["Size"], size_item)
            
            self.file_table.setItem(row, self.COLUMNS["Uploaded By"], QTableWidgetItem(file_info.get("uploaded_by")))
            self.file_table.setItem(row, self.COLUMNS["Modified By"], QTableWidgetItem(file_info.get("last_modified_by")))
            self.file_table.setItem(row, self.COLUMNS["Date Created"], QTableWidgetItem(format_utc_to_local(file_info.get("created_at"))))
            self.file_table.setItem(row, self.COLUMNS["Date Modified"], QTableWidgetItem(format_utc_to_local(file_info.get("modified_at"))))
        self.file_table.setSortingEnabled(True)
        self._set_controls_enabled(True)
        self.update_status_bar()

    def update_status_bar(self):
        selected_rows = len(set(item.row() for item in self.file_table.selectedItems()))
        total_rows = self.file_table.rowCount()

        if selected_rows > 0:
            self.status_bar.setText(f"{selected_rows} of {total_rows} selected")
        else:
            self.status_bar.setText(f"{total_rows} items")

    def get_selected_filename(self):
        selected_rows = list(set(item.row() for item in self.file_table.selectedItems()))
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a file first.")
            return None
        return self.file_table.item(selected_rows[0], self.COLUMNS["Name"]).text()

    def _perform_upload(self, file_path):
        self._set_controls_enabled(False)
        try:
            file_name = os.path.basename(file_path)
            if file_name in self.current_files:
                reply = QMessageBox.question(self, "File Exists", 
                    f"'{file_name}' already exists. Do you want to overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    # Must re-enable controls if we bail early
                    self._set_controls_enabled(True)
                    return

            progress = QProgressDialog(f"Uploading {file_name}...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setAutoClose(True)
            progress.setMinimumDuration(0)

            def update_progress(bytes_read, total_size):
                if total_size > 0:
                    progress.setValue(int(bytes_read / total_size * 100))
                QApplication.processEvents()
                if progress.wasCanceled():
                    raise ConnectionAbortedError("Upload canceled by user.")

            success, error = self.api_client.upload_file(file_path, update_progress)
            progress.setValue(100)
            if success:
                self.refresh_files()
            else:
                QMessageBox.critical(self, "Upload Failed", str(error))
                self._set_controls_enabled(True)

        except ConnectionAbortedError as e:
            QMessageBox.warning(self, "Upload Canceled", str(e))
            self._set_controls_enabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Upload Error", f"An unexpected error occurred: {e}")
            self._set_controls_enabled(True)
        # No finally block needed as refresh_files or other paths will re-enable controls

    def trigger_upload_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select File(s) to Upload")
        for file_path in file_paths:
            if file_path:
                self._perform_upload(file_path)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self._perform_upload(file_path)

    def delete_file(self):
        filename = self.get_selected_filename()
        if filename:
            reply = QMessageBox.question(self, "Confirm Delete", f"Delete {filename}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
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
        if folder_path:
            success, message = self.api_client.sync_folder(folder_path)
            if success:
                QMessageBox.information(self, "Sync Complete", message)
                self.refresh_files()
            else: QMessageBox.critical(self, "Sync Failed", message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    api = ApiClient("http://127.0.0.1:8000")
    
    login_dialog = LoginDialog(api)
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        main_window = MainWindow(api, login_dialog.username)
        main_window.show()
        sys.exit(app.exec())

