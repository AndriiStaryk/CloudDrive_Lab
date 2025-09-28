import sqlite3
from pathlib import Path
from typing import Dict, Optional
import hashlib
from datetime import datetime

class SimpleDatabase:
    def __init__(self, db_file: str = "users.sqlite"):
        """
        Initializes the database connection and creates the users table if it doesn't exist.
        """
        self.db_file = Path(db_file)
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        """Creates the 'users' table if it doesn't already exist."""
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
        """
        Creates a new user in the database with a hashed password.
        Returns False if the username already exists.
        """
        if self.get_user(username):
            return False  # User already exists

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        created_at_iso = datetime.now().isoformat()
        
        try:
            self.cursor.execute(
                "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                (username, hashed_password, created_at_iso)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # This is a fallback check in case two requests try to create the same user at once
            return False

    def authenticate_user(self, username: str, password: str) -> bool:
        """
        Authenticates a user by checking the username and hashed password.
        """
        user = self.get_user(username)
        if not user:
            return False
        
        # Hash the provided password and compare it with the stored hash
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return user["password"] == hashed_password

    def get_user(self, username: str) -> Optional[Dict]:
        """
        Retrieves a single user from the database by their username.
        Returns a dictionary-like row object or None if not found.
        """
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_row = self.cursor.fetchone()
        return dict(user_row) if user_row else None

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()

