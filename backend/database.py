#database.py

import sqlite3
from pathlib import Path
from typing import Dict, Optional
import hashlib
from datetime import datetime, timezone

class SimpleDatabase:
    def __init__(self, db_file: str = "users.sqlite"):
        self.db_file = Path(db_file)
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def create_user(self, username: str, password: str) -> bool:
        if self.get_user(username):
            return False

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        # Use timezone-aware UTC for all timestamps
        created_at_iso = datetime.now(timezone.utc).isoformat()
        
        try:
            self.cursor.execute(
                "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                (username, hashed_password, created_at_iso)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def authenticate_user(self, username: str, password: str) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return user["password"] == hashed_password

    def get_user(self, username: str) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_row = self.cursor.fetchone()
        return dict(user_row) if user_row else None

    def close(self):
        if self.conn:
            self.conn.close()

