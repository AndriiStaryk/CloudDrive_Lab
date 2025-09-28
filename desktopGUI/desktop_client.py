import sys
import requests
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QDialog, QLabel, QMessageBox, QFileDialog, QCheckBox, QMenuBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

# --- Configuration ---
# Change this to your actual server address if it's not running locally
BASE_API_URL = "http://127.0.0.1:8000"

# --- API Client ---
class ApiClient:
    """Handles all communication with the FastAPI backend."""
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None

    def _get_headers(self):
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def signup(self, username, password):
        try:
            response = requests.post(
                f"{self.base_url}/auth/signup",
                json={"username": username, "password": password}
            )
            response.raise_for_status()
            self.token = response.json().get("access_token")
            return True, ""
        except requests.exceptions.HTTPError as e:
            return False, e.response.json().get("detail", "Unknown error")
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {e}"

    def login(self, username, password):
        try:
            response = requests.post(
                f"{self.base_url}/auth/token",
                data={"username": username, "password": password}
            )
            response.raise_for_status()
            self.token = response.json().get("access_token")
            return True, ""
        except requests.exceptions.HTTPError as e:
            return False, e.response.json().get("detail", "Invalid credentials")
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {e}"

    def get_files(self):
        if not self.token:
            return None, "Not authenticated"
        try:
            response = requests.get(f"{self.base_url}/files", headers=self._get_headers())
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            return None, str(e)

    def upload_file(self, file_path):
        if not self.token:
            return False, "Not authenticated"
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.split('/')[-1], f)}
                response = requests.post(f"{self.base_url}/files/upload", headers=self._get_headers(), files=files)
                response.raise_for_status()
            return True, None
        except requests.exceptions.RequestException as e:
            return False, str(e)
        
    def delete_file(self, filename):
        if not self.token:
            return False, "Not authenticated"
        try:
            url = f"{self.base_url}/files/delete/{filename}"
            response = requests.delete(url, headers=self._get_headers())
            response.raise_for_status()
            return True, None
        except requests.exceptions.RequestException as e:
            return False, str(e)

    def download_file(self, filename, save_path):
        if not self.token:
            return False, "Not authenticated"
        try:
            url = f"{self.base_url}/files/download/{filename}"
            with requests.get(url, headers=self._get_headers(), stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return True, None
        except requests.exceptions.RequestException as e:
            return False, str(e)

    def sync_folder(self, folder_path):
        if not self.token:
            return False, "Not authenticated"
        try:
            response = requests.post(
                f"{self.base_url}/files/sync",
                headers=self._get_headers(),
                json={"local_folder_path": folder_path}
            )
            response.raise_for_status()
            return True, response.json().get('message', 'Sync completed')
        except requests.exceptions.RequestException as e:
            return False, str(e)

# --- GUI ---
class LoginDialog(QDialog):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.username = None
        self.setWindowTitle("Login or Signup")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addWidget(QLabel("Enter Credentials:"))
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)

        btn_layout = QHBoxLayout()
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.handle_login)
        signup_btn = QPushButton("Sign Up")
        signup_btn.clicked.connect(self.handle_signup)
        
        btn_layout.addWidget(login_btn)
        btn_layout.addWidget(signup_btn)
        layout.addLayout(btn_layout)

    def handle_login(self):
        user = self.username_input.text()
        pwd = self.password_input.text()
        success, message = self.api_client.login(user, pwd)
        if success:
            self.username = user
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", message)

    def handle_signup(self):
        user = self.username_input.text()
        pwd = self.password_input.text()
        success, message = self.api_client.signup(user, pwd)
        if success:
            QMessageBox.information(self, "Signup Successful", "Account created. You are now logged in.")
            self.username = user
            self.accept()
        else:
            QMessageBox.warning(self, "Signup Failed", message)

class MainWindow(QWidget):
    def __init__(self, api_client, username):
        super().__init__()
        self.api_client = api_client
        self.username = username
        self.COLUMNS = {
            "Name": 0, "Size (Bytes)": 1, "Uploaded By": 2, 
            "Last Modified By": 3, "Created At": 4, "Modified At": 5
        }
        self.init_ui()
        self.refresh_files()

    def init_ui(self):
        self.setWindowTitle(f"Simple Drive - Logged in as {self.username}")
        self.setGeometry(100, 100, 1000, 600)
        
        main_layout = QVBoxLayout(self)
        
        # --- Menu Bar for Toggling Columns ---
        menu_bar = QMenuBar(self)
        view_menu = menu_bar.addMenu("View")
        
        self.toggle_actions = {}
        for col_name, col_idx in self.COLUMNS.items():
            if col_name != "Name": # Name is always visible
                action = QAction(col_name, self, checkable=True)
                action.setChecked(True)
                action.toggled.connect(lambda checked, idx=col_idx: self.toggle_column(idx, checked))
                view_menu.addAction(action)
                self.toggle_actions[col_idx] = action
        
        main_layout.setMenuBar(menu_bar)

        # --- Button Layout ---
        btn_layout = QHBoxLayout()
        upload_btn = QPushButton("Upload File")
        upload_btn.clicked.connect(self.upload_file)
        download_btn = QPushButton("Download File")
        download_btn.clicked.connect(self.download_file)
        delete_btn = QPushButton("Delete File")
        delete_btn.clicked.connect(self.delete_file)
        sync_btn = QPushButton("Sync Folder")
        sync_btn.clicked.connect(self.sync_folder)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_files)

        btn_layout.addWidget(upload_btn)
        btn_layout.addWidget(download_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(sync_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(refresh_btn)
        main_layout.addLayout(btn_layout)

        # --- File Table ---
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(len(self.COLUMNS))
        self.file_table.setHorizontalHeaderLabels(self.COLUMNS.keys())
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(self.COLUMNS["Name"], QHeaderView.ResizeMode.Interactive)
        main_layout.addWidget(self.file_table)

    def toggle_column(self, col_index, is_visible):
        self.file_table.setColumnHidden(col_index, not is_visible)

    def refresh_files(self):
        self.file_table.setRowCount(0)
        files, error = self.api_client.get_files()
        if error:
            QMessageBox.critical(self, "Error", f"Could not fetch files: {error}")
            return
            
        self.file_table.setRowCount(len(files))
        for row, file_info in enumerate(files):
            # Helper to format datetime strings
            def format_date(date_str):
                try:
                    return datetime.fromisoformat(date_str).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    return "N/A"

            self.file_table.setItem(row, self.COLUMNS["Name"], QTableWidgetItem(file_info.get("name")))
            self.file_table.setItem(row, self.COLUMNS["Size (Bytes)"], QTableWidgetItem(str(file_info.get("size", 0))))
            self.file_table.setItem(row, self.COLUMNS["Uploaded By"], QTableWidgetItem(file_info.get("uploaded_by")))
            self.file_table.setItem(row, self.COLUMNS["Last Modified By"], QTableWidgetItem(file_info.get("last_modified_by")))
            self.file_table.setItem(row, self.COLUMNS["Created At"], QTableWidgetItem(format_date(file_info.get("created_at"))))
            self.file_table.setItem(row, self.COLUMNS["Modified At"], QTableWidgetItem(format_date(file_info.get("modified_at"))))

    def get_selected_filename(self):
        selected_items = self.file_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a file first.")
            return None
        return selected_items[self.COLUMNS["Name"]].text()

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Upload")
        if file_path:
            success, error = self.api_client.upload_file(file_path)
            if success:
                self.refresh_files()
            else:
                QMessageBox.critical(self, "Upload Failed", str(error))

    def delete_file(self):
        filename = self.get_selected_filename()
        if filename:
            reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {filename}?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                success, error = self.api_client.delete_file(filename)
                if success:
                    self.refresh_files()
                else:
                    QMessageBox.critical(self, "Delete Failed", str(error))

    def download_file(self):
        filename = self.get_selected_filename()
        if filename:
            save_path, _ = QFileDialog.getSaveFileName(self, "Save File As", filename)
            if save_path:
                success, error = self.api_client.download_file(filename, save_path)
                if not success:
                    QMessageBox.critical(self, "Download Failed", str(error))
                else:
                    QMessageBox.information(self, "Success", f"Downloaded {filename} successfully.")

    def sync_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder to Sync")
        if folder_path:
            success, message = self.api_client.sync_folder(folder_path)
            if success:
                QMessageBox.information(self, "Sync Complete", message)
                self.refresh_files()
            else:
                QMessageBox.critical(self, "Sync Failed", message)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    api = ApiClient(BASE_API_URL)
    
    login_dialog = LoginDialog(api)
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        main_window = MainWindow(api, login_dialog.username)
        main_window.show()
        sys.exit(app.exec())

