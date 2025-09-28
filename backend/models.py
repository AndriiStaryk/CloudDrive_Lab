from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- User and Token Models ---

class User(BaseModel):
    """
    Represents a user in the system (in-memory).
    """
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False

class UserInDB(User):
    """
    Represents a user as stored in our "database", including the hashed password.
    """
    hashed_password: str

class Token(BaseModel):
    """
    Defines the structure of the access token response.
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Defines the data contained within the JWT.
    """
    username: Optional[str] = None


# --- File Metadata Models ---

class FileMetadata(BaseModel):
    """
    Represents the metadata for a single file.
    This model is used when returning file info to the client.
    """
    id: int
    name: str
    creation_date: datetime
    modification_date: datetime
    uploader_username: str
    last_editor_username: str
    file_type: str

    class Config:
        # Pydantic v2 requires this for from_attributes to work
        from_attributes = True
