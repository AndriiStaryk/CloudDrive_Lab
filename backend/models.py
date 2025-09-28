from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

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
    created_at: datetime
    modified_at: datetime
    uploaded_by: str
    last_modified_by: str
    file_type: str
    is_supported_for_preview: bool

class SyncRequest(BaseModel):
    local_folder_path: str