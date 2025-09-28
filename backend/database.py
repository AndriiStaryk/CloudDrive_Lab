import json
from pathlib import Path
from typing import Dict, Optional
import hashlib
from datetime import datetime

class SimpleDatabase:
    def __init__(self, db_file: str = "users.json"):
        self.db_file = Path(db_file)
        self.users = self._load_users()
    
    def _load_users(self) -> Dict:
        if self.db_file.exists():
            with open(self.db_file, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}
    
    def _save_users(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.users, f, indent=4)
    
    def create_user(self, username: str, password: str) -> bool:
        if username in self.users:
            return False
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        self.users[username] = {
            "username": username,
            "password": hashed_password,
            "created_at": datetime.now().isoformat()
        }
        self._save_users()
        return True
    
    def authenticate_user(self, username: str, password: str) -> bool:
        user = self.users.get(username)
        if not user:
            return False
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return user["password"] == hashed_password
    
    def get_user(self, username: str) -> Optional[Dict]:
        return self.users.get(username)
