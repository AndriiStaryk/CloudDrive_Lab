import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict
import mimetypes
from datetime import datetime
import json

class FileManager:
    """
    Manages files in a single shared directory and tracks metadata in a JSON file.
    """
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
        """Checks if the file type is supported for preview."""
        # You can customize this list based on your requirements
        return filename.lower().endswith(('.c', '.jpg', '.jpeg', '.py', '.png', '.txt'))

    def save_file(self, username: str, file_content: bytes, filename: str) -> bool:
        try:
            file_path = self.base_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(file_content)

            now = datetime.now().isoformat()
            if filename in self.metadata:
                # File exists, update modification info
                self.metadata[filename]['last_modified_by'] = username
                self.metadata[filename]['modified_at'] = now
            else:
                # New file, create metadata
                self.metadata[filename] = {
                    'uploaded_by': username,
                    'last_modified_by': username,
                    'created_at': now,
                    'modified_at': now,
                }
            
            self._save_metadata()
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

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
                
                files.append({
                    'id': file_path.name, # Using filename as ID
                    'name': file_path.name,
                    'size': stat.st_size,
                    'created_at': file_meta.get('created_at', datetime.fromtimestamp(stat.st_ctime).isoformat()),
                    'modified_at': file_meta.get('modified_at', datetime.fromtimestamp(stat.st_mtime).isoformat()),
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
                    self.save_file(username, content, file_in_local.name)
                    synced_files.append(file_in_local.name)
            
            return {
                "status": "success",
                "message": f"Synced {len(synced_files)} files",
                "files": synced_files
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

