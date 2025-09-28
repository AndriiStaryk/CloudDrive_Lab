import os
import shutil
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

# Import the models we defined in models.py
from models import User, UserInDB, Token, TokenData, FileMetadata

# --- Configuration & Setup ---

# This is for hashing passwords. In a real app, this would be more complex.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Secret key to sign JWTs. In a real app, load this from an environment variable!
SECRET_KEY = "YOUR_SECRET_KEY_NEEDS_TO_BE_CHANGED"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
UPLOADS_DIR = "uploads"

# Ensure the uploads directory exists
os.makedirs(UPLOADS_DIR, exist_ok=True)

# --- In-Memory Database (for demonstration) ---
# NOTE: This data is lost when the server restarts.

fake_users_db = {
    "john": {
        "username": "john",
        "full_name": "John Doe",
        "email": "john.doe@example.com",
        "hashed_password": pwd_context.hash("secret"), # Hashing the password "secret"
        "disabled": False,
    }
}

# We'll use a list of dictionaries to act as our file metadata DB
fake_files_db: List[dict] = [
    {
        "id": 1,
        "name": "example_document.c",
        "creation_date": datetime.now() - timedelta(days=2),
        "modification_date": datetime.now() - timedelta(days=1),
        "uploader_username": "john",
        "last_editor_username": "john",
        "file_type": "c",
    },
    {
        "id": 2,
        "name": "photo_of_cat.jpg",
        "creation_date": datetime.now() - timedelta(hours=5),
        "modification_date": datetime.now() - timedelta(hours=2),
        "uploader_username": "john",
        "last_editor_username": "john",
        "file_type": "jpg",
    }
]

# --- Authentication Helpers ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# --- FastAPI App Instance ---
app = FastAPI()


# --- API Endpoints ---

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Takes username and password and returns an access token.
    """
    user = get_user(fake_users_db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/files", response_model=List[FileMetadata])
async def get_files_list(
    sort_by: Optional[str] = None,
    filter_by: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns a list of file metadata.
    Supports filtering by file type and sorting by uploader username.
    """
    # In a real app, you'd filter/sort this at the database level.
    files = list(fake_files_db)

    if filter_by:
        # Filter for files with a specific extension (e.g., "py", "jpg")
        files = [f for f in files if f["name"].lower().endswith(f".{filter_by.lower()}")]

    if sort_by == "uploader_username":
        files = sorted(files, key=lambda f: f["uploader_username"])

    return files


@app.post("/files/upload", response_model=FileMetadata, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Uploads a file to the server.
    """
    file_path = os.path.join(UPLOADS_DIR, file.filename)

    # Save the file to the 'uploads' directory
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Create metadata and add it to our fake DB
    new_id = max(f["id"] for f in fake_files_db) + 1 if fake_files_db else 1
    file_type = file.filename.split('.')[-1] if '.' in file.filename else ''
    
    new_file_metadata = {
        "id": new_id,
        "name": file.filename,
        "creation_date": datetime.now(),
        "modification_date": datetime.now(),
        "uploader_username": current_user.username,
        "last_editor_username": current_user.username,
        "file_type": file_type,
    }
    fake_files_db.append(new_file_metadata)
    
    return new_file_metadata


@app.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Downloads a specific file by its ID.
    """
    metadata = next((f for f in fake_files_db if f["id"] == file_id), None)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = os.path.join(UPLOADS_DIR, metadata["name"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(path=file_path, filename=metadata["name"], media_type='application/octet-stream')


@app.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    Deletes a file's metadata and the actual file from disk.
    """
    global fake_files_db
    metadata_index = -1
    for i, metadata in enumerate(fake_files_db):
        if metadata["id"] == file_id:
            metadata_index = i
            break
            
    if metadata_index == -1:
        raise HTTPException(status_code=404, detail="File metadata not found")

    # Delete the actual file
    metadata = fake_files_db[metadata_index]
    file_path = os.path.join(UPLOADS_DIR, metadata["name"])
    if os.path.exists(file_path):
        os.remove(file_path)

    # Remove metadata from our "DB"
    fake_files_db.pop(metadata_index)
    
    return
