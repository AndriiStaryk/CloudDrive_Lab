from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import os
import shutil
import hashlib
import jwt
from pathlib import Path
import mimetypes
from enum import Enum

app = FastAPI(title="Cloud Drive API", description="Simplified Google Drive Clone")

# CORS для веб-клієнта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфігурація
SECRET_KEY = "your-secret-key-here"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

security = HTTPBearer()

# Моделі даних
class UserSignup(BaseModel):
    username: str
    password: str

class User(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class FileInfo(BaseModel):
    id: str
    name: str
    size: int
    created_at: datetime
    modified_at: datetime
    uploaded_by: str
    last_modified_by: str
    file_type: str
    is_supported_for_preview: bool

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class FileFilter(str, Enum):
    ALL = "all"
    PY_JPG = "py_jpg"

# Тимчасова "база даних" користувачів (в реальному проекті - PostgreSQL/MongoDB)
fake_users_db = {
    "user1": {"username": "user1", "password": "password1"},
    "user2": {"username": "user2", "password": "password2"},
}

# Функції аутентифікації
def verify_password(password: str, hashed_password: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed_password

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username: str, password: str):
    user = fake_users_db.get(username)
    if not user or not verify_password(password, get_password_hash(user["password"])):
        return False
    return user

def create_user(username: str, password: str) -> bool:
    """Створити нового користувача"""
    if username in fake_users_db:
        return False  # Користувач вже існує
    
    fake_users_db[username] = {
        "username": username,
        "password": password  # В реальності треба хешувати
    }
    return True

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm="HS256")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_user_dir(username: str) -> Path:
    """Отримати директорію користувача"""
    user_dir = UPLOAD_DIR / username
    user_dir.mkdir(exist_ok=True)
    return user_dir

def is_supported_file_type(filename: str) -> bool:
    """Перевірити чи файл підтримується для перегляду (.c, .jpg згідно варіанту)"""
    return filename.lower().endswith(('.c', '.jpg', '.jpeg'))

def get_file_info(file_path: Path, username: str) -> FileInfo:
    """Отримати інформацію про файл"""
    stat = file_path.stat()
    
    return FileInfo(
        id=str(hash(str(file_path))),
        name=file_path.name,
        size=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_ctime),
        modified_at=datetime.fromtimestamp(stat.st_mtime),
        uploaded_by=username,  # В реальності треба зберігати в БД
        last_modified_by=username,  # В реальності треба зберігати в БД
        file_type=mimetypes.guess_type(str(file_path))[0] or "unknown",
        is_supported_for_preview=is_supported_file_type(file_path.name)
    )

# API ендпоінти

@app.post("/auth/signup", response_model=LoginResponse)
async def signup(user: UserSignup):
    """Реєстрація нового користувача"""
    # Перевіряємо чи користувач вже існує
    if user.username in fake_users_db:
        raise HTTPException(
            status_code=400, 
            detail="Username already exists"
        )
    
    # Базова валідація
    if len(user.username.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters long"
        )
    
    if len(user.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters long"
        )
    
    # Створюємо користувача
    if create_user(user.username.strip(), user.password):
        # Автоматично логінимо після реєстрації
        access_token = create_access_token(data={"sub": user.username.strip()})
        return LoginResponse(access_token=access_token)
    else:
        raise HTTPException(status_code=500, detail="Failed to create user")

@app.post("/auth/login", response_model=LoginResponse)
async def login(user: User):
    """Авторизація користувача"""
    if not authenticate_user(user.username, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.username})
    return LoginResponse(access_token=access_token)

@app.get("/files", response_model=List[FileInfo])
async def get_files(
    current_user: str = Depends(get_current_user),
    sort_by_uploader: Optional[SortOrder] = None,
    filter_type: FileFilter = FileFilter.ALL
):
    """Отримати список файлів користувача з сортуванням та фільтрацією"""
    user_dir = get_user_dir(current_user)
    files = []
    
    for file_path in user_dir.iterdir():
        if file_path.is_file():
            file_info = get_file_info(file_path, current_user)
            
            # Фільтрація згідно варіанту (всі файли або тільки .py, .jpg)
            if filter_type == FileFilter.PY_JPG:
                if not file_path.name.lower().endswith(('.py', '.jpg', '.jpeg')):
                    continue
            
            files.append(file_info)
    
    # Сортування за ім'ям того, хто завантажив (згідно варіанту)
    if sort_by_uploader:
        reverse = sort_by_uploader == SortOrder.DESC
        files.sort(key=lambda x: x.uploaded_by, reverse=reverse)
    
    return files

@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    """Завантажити файл"""
    user_dir = get_user_dir(current_user)
    file_path = user_dir / file.filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"message": f"File {file.filename} uploaded successfully"}

@app.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: str = Depends(get_current_user)
):
    """Завантажити файл"""
    user_dir = get_user_dir(current_user)
    
    # Знайти файл за ID (спрощений підхід)
    for file_path in user_dir.iterdir():
        if str(hash(str(file_path))) == file_id:
            return {"download_url": f"/static/{current_user}/{file_path.name}"}
    
    raise HTTPException(status_code=404, detail="File not found")

@app.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: str = Depends(get_current_user)
):
    """Видалити файл"""
    user_dir = get_user_dir(current_user)
    
    for file_path in user_dir.iterdir():
        if str(hash(str(file_path))) == file_id:
            file_path.unlink()
            return {"message": "File deleted successfully"}
    
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/files/{file_id}/content")
async def get_file_content(
    file_id: str,
    current_user: str = Depends(get_current_user)
):
    """Отримати вміст файлу для перегляду (.c, .jpg згідно варіанту)"""
    user_dir = get_user_dir(current_user)
    
    for file_path in user_dir.iterdir():
        if str(hash(str(file_path))) == file_id:
            if not is_supported_file_type(file_path.name):
                raise HTTPException(status_code=400, detail="File type not supported for preview")
            
            if file_path.suffix.lower() == '.c':
                # Текстовий файл
                with open(file_path, 'r', encoding='utf-8') as f:
                    return {"content": f.read(), "type": "text"}
            else:
                # Зображення - повертаємо base64 або URL
                return {"content": f"/static/{current_user}/{file_path.name}", "type": "image"}
    
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/user/info")
async def get_user_info(current_user: str = Depends(get_current_user)):
    """Отримати інформацію про поточного користувача"""
    return {"username": current_user}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)