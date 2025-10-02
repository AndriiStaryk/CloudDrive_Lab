import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import mimetypes
from datetime import datetime, timezone
import json

class FileManager:
    def __init__(self, base_upload_dir: str = "uploads"):
        self.base_dir = Path(base_upload_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.metadata_file = self.base_dir / "metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def _save_metadata(self):
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=4)

    def _is_supported_for_preview(self, filename: str) -> bool:
        # Added .txt to support text editing
        return filename.lower().endswith(('.c', '.jpg', '.jpeg', '.py', '.png', '.txt'))

    def _get_unique_filename(self, filename: str) -> Path:
        """Generates a unique filename path if the original already exists."""
        file_path = self.base_dir / filename
        if not file_path.exists():
            return file_path

        stem = file_path.stem
        suffix = file_path.suffix
        counter = 1
        while True:
            new_filename = f"{stem} ({counter}){suffix}"
            new_file_path = self.base_dir / new_filename
            if not new_file_path.exists():
                return new_file_path
            counter += 1

    def save_file(self, username: str, file_content: bytes, filename: str) -> Tuple[bool, str]:
        """Saves a file, handling name conflicts by appending (n). Returns the actual filename."""
        try:
            unique_file_path = self._get_unique_filename(filename)
            actual_filename = unique_file_path.name
            
            with open(unique_file_path, 'wb') as f:
                f.write(file_content)

            now = datetime.now(timezone.utc).isoformat()
            
            self.metadata[actual_filename] = {
                'uploaded_by': username,
                'last_modified_by': username,
                'created_at': now,
                'modified_at': now,
            }
            
            self._save_metadata()
            return True, actual_filename
        except Exception as e:
            print(f"Error saving file: {e}")
            return False, ""

    def update_file_content(self, username: str, filename: str, file_content: bytes) -> bool:
        """Updates the content of an existing file."""
        try:
            file_path = self.base_dir / filename
            if not file_path.exists():
                return False
                
            with open(file_path, 'wb') as f:
                f.write(file_content)
                
            now = datetime.now(timezone.utc).isoformat()
            if filename in self.metadata:
                self.metadata[filename]['last_modified_by'] = username
                self.metadata[filename]['modified_at'] = now
                self._save_metadata()
                return True
            return False
        except Exception as e:
            print(f"Error updating file content: {e}")
            return False

    def rename_file(self, old_filename: str, new_filename_base: str, username: str) -> Tuple[bool, str]:
        """Renames a file, preserving its extension."""
        try:
            old_path = self.base_dir / old_filename
            if not old_path.exists():
                return False, "Source file not found."
            
            extension = old_path.suffix
            new_filename = f"{new_filename_base}{extension}"
            
            if old_filename == new_filename:
                return True, new_filename

            new_path = self.base_dir / new_filename
            if new_path.exists():
                return False, "A file with the new name already exists."

            os.rename(old_path, new_path)

            if old_filename in self.metadata:
                file_meta = self.metadata.pop(old_filename)
                file_meta['last_modified_by'] = username
                file_meta['modified_at'] = datetime.now(timezone.utc).isoformat()
                self.metadata[new_filename] = file_meta
                self._save_metadata()

            return True, new_filename
        except Exception as e:
            print(f"Error renaming file: {e}")
            return False, str(e)

    def delete_file(self, filename: str) -> bool:
        try:
            file_path = self.base_dir / filename
            if file_path.exists():
                file_path.unlink()
                if filename in self.metadata:
                    del self.metadata[filename]
                    self._save_metadata()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def get_file_content(self, filename: str) -> Optional[bytes]:
        try:
            file_path = self.base_dir / filename
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
            
    def get_file_path(self, filename: str) -> Optional[Path]:
        file_path = self.base_dir / filename
        return file_path if file_path.exists() else None

    def list_files(self) -> List[dict]:
        files = []
        for file_path in self.base_dir.iterdir():
            if file_path.is_file() and file_path.name != "metadata.json":
                stat = file_path.stat()
                file_meta = self.metadata.get(file_path.name, {})
                
                created_at_utc = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
                modified_at_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

                files.append({
                    'id': file_path.name,
                    'name': file_path.name,
                    'size': stat.st_size,
                    'created_at': file_meta.get('created_at', created_at_utc),
                    'modified_at': file_meta.get('modified_at', modified_at_utc),
                    'uploaded_by': file_meta.get('uploaded_by', 'unknown'),
                    'last_modified_by': file_meta.get('last_modified_by', 'unknown'),
                    'file_type': mimetypes.guess_type(str(file_path))[0] or 'unknown',
                    'is_supported_for_preview': self._is_supported_for_preview(file_path.name)
                })
        return files
    
    def sync_folder(self, username: str, local_folder_path: str) -> dict:
        try:
            local_path = Path(local_folder_path)
            if not local_path.exists() or not local_path.is_dir():
                return {"status": "error", "message": "Local folder does not exist"}

            synced_files = []
            for file_in_local in local_path.iterdir():
                if file_in_local.is_file():
                    with open(file_in_local, 'rb') as f:
                        content = f.read()
                    success, actual_filename = self.save_file(username, content, file_in_local.name)
                    if success:
                        synced_files.append(actual_filename)
            
            return {
                "status": "success",
                "message": f"Synced {len(synced_files)} files",
                "files": synced_files
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
