from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Union

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class FileMetadata(BaseModel):
    id: str
    name: str
    size: int
    created_at: Union[datetime, str] # Allow string for ISO format from server
    modified_at: Union[datetime, str]
    uploaded_by: str
    last_modified_by: str
    file_type: str
    is_supported_for_preview: bool

class SyncRequest(BaseModel):
    local_folder_path: str

# --- New Models for rename and edit ---
class RenameRequest(BaseModel):
    new_name_base: str # Filename without extension

class UpdateContentRequest(BaseModel):
    content: str # Base64 encoded file content
