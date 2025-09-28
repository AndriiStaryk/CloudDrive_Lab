import os
import shutil
from pathlib import Path
from typing import List, Optional
import mimetypes
from datetime import datetime

class FileManager:
    def __init__(self, base_upload_dir: str = "uploads"):
        self.base_dir = Path(base_upload_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def get_user_directory(self, username: str) -> Path:
        user_dir = self.base_dir / username
        user_dir.mkdir(exist_ok=True)
        return user_dir
    
    def save_file(self, username: str, file_content: bytes, filename: str) -> bool:
        try:
            user_dir = self.get_user_directory(username)
            file_path = user_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(file_content)
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False
    
    def delete_file(self, username: str, filename: str) -> bool:
        try:
            user_dir = self.get_user_directory(username)
            file_path = user_dir / filename
            
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    
    def get_file_content(self, username: str, filename: str) -> Optional[bytes]:
        try:
            user_dir = self.get_user_directory(username)
            file_path = user_dir / filename
            
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return f.read()
            return None
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    
    def list_files(self, username: str) -> List[dict]:
        user_dir = self.get_user_directory(username)
        files = []
        
        for file_path in user_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    'id': str(hash(str(file_path))),
                    'name': file_path.name,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime),
                    'uploaded_by': username,
                    'last_modified_by': username,
                    'file_type': mimetypes.guess_type(str(file_path))[0] or 'unknown',
                    'is_supported_for_preview': self._is_supported_for_preview(file_path.name)
                })
        
        return files
    
    def _is_supported_for_preview(self, filename: str) -> bool:
        """Згідно варіанту: .c, .jpg"""
        return filename.lower().endswith(('.c', '.jpg', '.jpeg'))
    
    def sync_folder(self, username: str, local_folder_path: str) -> dict:
        """Синхронізація папки (спрощена версія)"""
        try:
            user_dir = self.get_user_directory(username)
            local_path = Path(local_folder_path)
            
            if not local_path.exists():
                return {"status": "error", "message": "Local folder does not exist"}
            
            synced_files = []
            
            # Копіюємо файли з локальної папки на сервер
            for file_path in local_path.iterdir():
                if file_path.is_file():
                    dest_path = user_dir / file_path.name
                    shutil.copy2(file_path, dest_path)
                    synced_files.append(file_path.name)
            
            return {
                "status": "success", 
                "message": f"Synced {len(synced_files)} files",
                "files": synced_files
            }
        
        except Exception as e:
            return {"status": "error", "message": str(e)}